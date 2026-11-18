// Recover jump tables without emitting raw pcode or modifying the baseline dump.
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.database.function.OverlappingFunctionException;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.pcode.HighFunction;
import ghidra.program.model.pcode.JumpTable;
import ghidra.program.model.symbol.SourceType;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;

public class LiftJumpEvidence extends GhidraScript {
    private void checkpoint(Path path, String contents) throws Exception {
        Path tmp = path.resolveSibling(path.getFileName() + ".tmp");
        Files.writeString(tmp, contents);
        Files.move(tmp, path, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
    }

    private void disassembleBody(Address entry, long size) throws Exception {
        Address end = entry.add(size - 1);
        AddressSet body = new AddressSet(entry, end);
        new DisassembleCommand(entry, body, true).applyTo(currentProgram, monitor);
        for (Address cursor = entry; cursor.compareTo(end) <= 0;) {
            Instruction instruction = getInstructionAt(cursor);
            if (instruction == null) {
                new DisassembleCommand(cursor, body, false).applyTo(currentProgram, monitor);
                instruction = getInstructionAt(cursor);
            }
            cursor = instruction == null ? cursor.add(1) : instruction.getMaxAddress().add(1);
        }
    }

    private String tables(DecompileResults result, long base) {
        HighFunction high = result == null ? null : result.getHighFunction();
        JumpTable[] tables = high == null ? null : high.getJumpTables();
        StringBuilder out = new StringBuilder("[");
        if (tables != null) {
            for (int i = 0; i < tables.length; i++) {
                if (i > 0) out.append(",");
                out.append("{\"at\":").append(tables[i].getSwitchAddress().getOffset() - base).append(",\"cases\":[");
                Address[] cases = tables[i].getCases();
                for (int j = 0; j < cases.length; j++) {
                    if (j > 0) out.append(",");
                    out.append(cases[j].getOffset() - base);
                }
                out.append("]}");
            }
        }
        return out.append("]").toString();
    }

    private Function functionFor(Address entry, AddressSet body, boolean bounded) throws Exception {
        Function fn = getFunctionAt(entry);
        if (!bounded) return fn == null ? createFunction(entry, null) : fn;
        if (fn == null) {
            return currentProgram.getFunctionManager().createFunction(null, entry, body, SourceType.ANALYSIS);
        }
        fn.setBody(body);
        return fn;
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        Path out = Path.of(args[1]);
        int timeout = Integer.parseInt(args[2]);
        boolean bounded = Boolean.parseBoolean(args[4]);
        Address base = currentProgram.getImageBase();
        DecompInterface decomp = new DecompInterface();
        decomp.toggleCCode(Boolean.parseBoolean(args[3]));
        try {
            if (!decomp.openProgram(currentProgram)) {
                throw new IllegalStateException(decomp.getLastMessage());
            }
            for (String line : Files.readAllLines(Path.of(args[0]))) {
                String[] fields = line.split("\\s+");
                long start = Long.parseLong(fields[0], 16);
                long size = Long.parseLong(fields[1]);
                Path row = out.resolve(fields[0] + ".json");
                checkpoint(out.resolve("active"), fields[0]);
                println("jump-table evidence: 0x" + fields[0]);
                long began = System.nanoTime();
                Address entry = base.add(start);
                disassembleBody(entry, size);
                AddressSet body = new AddressSet(entry, entry.add(size - 1));
                Function fn = null;
                String noFunction = "no_function";
                try {
                    fn = functionFor(entry, body, bounded);
                } catch (OverlappingFunctionException ex) {
                    noFunction = "overlapping_function";
                }
                long bodyBytes = fn == null ? 0 : fn.getBody().getNumAddresses();
                long outsideBytes = fn == null ? 0 : fn.getBody().subtract(body).getNumAddresses();
                DecompileResults result = fn == null ? null : decomp.decompileFunction(fn, timeout, monitor);
                String status = result == null ? noFunction : result.decompileCompleted() ? "complete"
                    : result.isTimedOut() ? "function_timeout" : "decompile_failed";
                long elapsedMs = (System.nanoTime() - began) / 1_000_000;
                checkpoint(row, "{\"start\":" + start + ",\"size\":" + size + ",\"status\":\"" + status
                    + "\",\"elapsed_ms\":" + elapsedMs + ",\"function_bytes\":" + bodyBytes
                    + ",\"outside_function_bytes\":" + outsideBytes + ",\"jt\":" + tables(result, base.getOffset()) + "}");
                println("jump-table evidence: 0x" + fields[0] + " " + status + " in " + elapsedMs + " ms");
            }
        } finally {
            decomp.dispose();
        }
    }
}
