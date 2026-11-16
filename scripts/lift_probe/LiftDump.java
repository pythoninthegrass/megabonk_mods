// Dumps raw pcode, jump tables and memory sections for sampled bodies as JSON lines.
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.pcode.HighFunction;
import ghidra.program.model.pcode.JumpTable;
import ghidra.program.model.pcode.PcodeOp;
import ghidra.program.model.pcode.Varnode;
import java.io.PrintWriter;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.List;

public class LiftDump extends GhidraScript {

    private long imageBase;

    // Ghidra rebases a shared object, so every address is reported as the file virtual address.
    private long fileVa(long ghidraAddress) {
        return ghidraAddress - imageBase;
    }

    private String varnode(Varnode v, boolean isLea) {
        if (v == null) {
            return "null";
        }
        String space = v.getAddress().getAddressSpace().getName();
        long offset = v.getOffset();
        if (space.equals("ram")) {
            offset = fileVa(offset);
        } else if (space.equals("const") && v.getSize() == 8 && isLea && currentProgram.getMemory().contains(toAddr(offset))) {
            // a LEA constant inside loaded memory is an address, not an integer
            space = "cptr";
            offset = fileVa(offset);
        }
        return "\"" + space + "," + Long.toHexString(offset) + "," + v.getSize() + "\"";
    }

    private void writeSections(String path) throws Exception {
        StringBuilder sb = new StringBuilder("[");
        boolean first = true;
        for (MemoryBlock b : currentProgram.getMemory().getBlocks()) {
            if (b.isOverlay()) {
                continue;
            }
            if (!first) {
                sb.append(",");
            }
            first = false;
            sb.append("{\"name\":\"").append(b.getName().replaceAll("[^A-Za-z0-9_]", "_")).append("\",\"va\":")
                .append(fileVa(b.getStart().getOffset())).append(",\"size\":").append(b.getSize())
                .append(",\"exec\":").append(b.isExecute()).append("}");
        }
        sb.append("]");
        Files.writeString(Paths.get(path), sb.toString());
    }

    private String jumpTables(Address entry, AddressSet body, DecompInterface decomp) throws Exception {
        Function fn = getFunctionAt(entry);
        if (fn == null) {
            fn = createFunction(entry, null);
        }
        if (fn == null) {
            return "[]";
        }
        DecompileResults res = decomp.decompileFunction(fn, 120, monitor);
        HighFunction hf = res.getHighFunction();
        if (hf == null) {
            return "[]";
        }
        JumpTable[] tables = hf.getJumpTables();
        if (tables == null) {
            return "[]";
        }
        StringBuilder sb = new StringBuilder("[");
        for (int t = 0; t < tables.length; t++) {
            if (t > 0) {
                sb.append(",");
            }
            sb.append("{\"at\":").append(fileVa(tables[t].getSwitchAddress().getOffset())).append(",\"cases\":[");
            Address[] cases = tables[t].getCases();
            for (int c = 0; c < cases.length; c++) {
                if (c > 0) {
                    sb.append(",");
                }
                sb.append(fileVa(cases[c].getOffset()));
            }
            sb.append("]}");
        }
        return sb.append("]").toString();
    }

    @Override
    public void run() throws Exception {
        imageBase = currentProgram.getImageBase().getOffset();
        String[] args = getScriptArgs();
        List<String> ranges = Files.readAllLines(Paths.get(args[0]));
        writeSections(args[2]);
        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);
        try (PrintWriter out = new PrintWriter(Files.newBufferedWriter(Paths.get(args[1])))) {
            for (String line : ranges) {
                String[] f = line.trim().split("\\s+");
                if (f.length < 2) {
                    continue;
                }
                long start = Long.parseLong(f[0], 16);
                long size = Long.parseLong(f[1]);
                Address a = currentProgram.getImageBase().add(start);
                AddressSet body = new AddressSet(a, a.add(size - 1));
                new DisassembleCommand(a, body, true).applyTo(currentProgram, monitor);
                // code reachable only through jump tables is missed by flow-following, so sweep the rest linearly
                Address cur = a;
                long undecoded = 0;
                while (cur.compareTo(a.add(size - 1)) <= 0) {
                    Instruction at = getInstructionAt(cur);
                    if (at == null) {
                        new DisassembleCommand(cur, body, false).applyTo(currentProgram, monitor);
                        at = getInstructionAt(cur);
                    }
                    if (at == null) {
                        undecoded++;
                        cur = cur.add(1);
                    } else {
                        cur = at.getMaxAddress().add(1);
                    }
                }
                StringBuilder sb = new StringBuilder();
                sb.append("{\"start\":").append(start).append(",\"size\":").append(size).append(",\"undecoded\":").append(undecoded).append(",\"insns\":[");
                InstructionIterator it = currentProgram.getListing().getInstructions(body, true);
                boolean firstInsn = true;
                boolean hasBranchInd = false;
                while (it.hasNext()) {
                    Instruction ins = it.next();
                    boolean isLea = ins.getMnemonicString().equals("LEA");
                    if (!firstInsn) {
                        sb.append(",");
                    }
                    firstInsn = false;
                    sb.append("{\"a\":").append(fileVa(ins.getAddress().getOffset())).append(",\"len\":").append(ins.getLength());
                    sb.append(",\"m\":\"").append(ins.getMnemonicString()).append("\",\"ops\":[");
                    PcodeOp[] ops = ins.getPcode();
                    for (int i = 0; i < ops.length; i++) {
                        if (i > 0) {
                            sb.append(",");
                        }
                        PcodeOp op = ops[i];
                        hasBranchInd |= op.getOpcode() == PcodeOp.BRANCHIND;
                        sb.append("{\"op\":\"").append(op.getMnemonic()).append("\",\"out\":").append(varnode(op.getOutput(), isLea)).append(",\"in\":[");
                        for (int j = 0; j < op.getNumInputs(); j++) {
                            if (j > 0) {
                                sb.append(",");
                            }
                            sb.append(varnode(op.getInput(j), isLea));
                        }
                        sb.append("]");
                        if (op.getOpcode() == PcodeOp.CALLOTHER) {
                            sb.append(",\"user\":\"").append(currentProgram.getLanguage().getUserDefinedOpName((int) op.getInput(0).getOffset())).append("\"");
                        }
                        sb.append("}");
                    }
                    sb.append("]}");
                }
                sb.append("],\"jt\":").append(hasBranchInd ? jumpTables(a, body, decomp) : "[]").append("}");
                out.println(sb);
            }
        }
    }
}
