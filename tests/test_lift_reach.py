"""
Self-test for scripts/lift_reach.py.

Builds a synthetic ELF program-header table and scored body rows, so no real
GameAssembly.so, scored image or running game is needed.
"""

import json
import lift_reach
import pytest
import struct

PT_LOAD, PT_NOTE = 1, 4


def elf64(phdrs: list[tuple[int, int]]) -> bytes:
    """Little-endian ELF64 header plus program headers given as (p_type, p_vaddr)."""
    ehsize, phentsize = 64, 56
    header = bytearray(ehsize)
    header[:4] = b"\x7fELF"
    header[4], header[5] = 2, 1
    struct.pack_into("<Q", header, 0x20, ehsize)
    struct.pack_into("<HHH", header, 0x34, ehsize, phentsize, len(phdrs))
    body = b"".join(struct.pack("<IIQQQQQQ", p_type, 0, 0, p_vaddr, p_vaddr, 0, 0, 0x1000) for p_type, p_vaddr in phdrs)
    return bytes(header) + body


def row(start: int, clean: bool, size: int = 16) -> str:
    return json.dumps({"start": start, "size": size, "stages": {"clean": clean}, "holes": [] if clean else ["BRANCHIND"]})


def test_lowest_load_vaddr_ignores_non_load_segments():
    data = elf64([(PT_NOTE, 0x10), (PT_LOAD, 0x4000), (PT_LOAD, 0x1000)])
    assert lift_reach.lowest_load_vaddr(data) == 0x1000


def test_lowest_load_vaddr_rejects_non_elf():
    with pytest.raises(ValueError):
        lift_reach.lowest_load_vaddr(b"MZ" + bytes(100))


def test_lowest_load_vaddr_rejects_an_image_with_no_load_segment():
    with pytest.raises(ValueError):
        lift_reach.lowest_load_vaddr(elf64([(PT_NOTE, 0)]))


def test_blocked_starts_keeps_only_unclean_bodies(tmp_path):
    bodies = tmp_path / "bodies.jsonl"
    bodies.write_text("\n".join([row(0x100, True), row(0x200, False), "", row(0x300, False)]))
    assert lift_reach.blocked_starts(bodies) == [0x200, 0x300]


def test_gdb_script_is_valid_python_and_carries_its_inputs():
    script = lift_reach.gdb_script([0x200, 0x300], lowest_vaddr=0, log="/tmp/hits.log")
    compile(script, "<gdb>", "exec")
    assert "0x200" in script and "0x300" in script
    assert "/tmp/hits.log" in script
    assert "GameAssembly.so" in script


def test_gdb_script_passes_signals_through_and_keeps_resuming():
    script = lift_reach.gdb_script([0x200], lowest_vaddr=0, log="/tmp/hits.log")
    assert 'gdb.execute("handle all nostop noprint pass")' in script
    assert "while True:" in script
    assert 'gdb.execute("continue")' in script


def test_launch_script_plants_probes_when_the_library_loads_not_after_boot():
    script = lift_reach.gdb_script([0x200], lowest_vaddr=0, log="/tmp/hits.log", launch=True)
    compile(script, "<gdb>", "exec")
    order = [
        script.index('gdb.execute("handle all nostop noprint pass")'),
        script.index('gdb.execute("catch load GameAssembly")'),
        script.index('gdb.execute("run")'),
        script.index("probes = ["),
        script.index('gdb.execute("continue")'),
    ]
    assert order == sorted(order)


def test_launch_script_clears_the_load_catchpoint_before_planting_probes():
    script = lift_reach.gdb_script([0x200], lowest_vaddr=0, log="/tmp/hits.log", launch=True)
    assert script.index('gdb.execute("delete")') < script.index("probes = [")


def test_attach_script_does_not_launch_or_catch_loads():
    script = lift_reach.gdb_script([0x200], lowest_vaddr=0, log="/tmp/hits.log")
    assert "catch load" not in script
    assert 'gdb.execute("run")' not in script


def test_gdb_script_round_trips_a_log_path_with_quotes():
    log = '/tmp/"x" \\ y.log'
    script = lift_reach.gdb_script([0x200], lowest_vaddr=0, log=log)
    namespace = {}
    # Only the constant block, since the rest needs a live gdb.
    exec(script.split("def ", 1)[0].replace("import gdb\n", ""), namespace)
    assert namespace["LOG"] == log


def test_parse_hits_reads_one_start_per_hit_line_and_ignores_noise():
    log = "attached\nHIT 0x200\nsome gdb chatter\nHIT 0x300\nHIT 0x200\n"
    assert lift_reach.parse_hits(log) == {0x200, 0x300}


def test_classify_splits_probed_starts_into_hot_and_cold():
    assert lift_reach.classify([0x200, 0x300, 0x400], {0x300}) == {"hot": [0x300], "cold": [0x200, 0x400]}


def test_classify_refuses_a_hit_that_was_never_probed():
    with pytest.raises(ValueError, match="0x999"):
        lift_reach.classify([0x200], {0x999})


def test_report_is_keyed_on_the_image_hash_and_names_each_body():
    names = {0x300: ["Assembly-CSharp.dll:MapGenerator::GenerateMap"]}
    report = lift_reach.report("ab" * 32, "forest-run", [0x200, 0x300], {0x300}, names)
    assert report["binary_sha256"] == "ab" * 32
    assert report["scenario"] == "forest-run"
    assert report["hot"] == [{"start": "0x300", "names": ["Assembly-CSharp.dll:MapGenerator::GenerateMap"]}]
    assert report["cold"] == [{"start": "0x200", "names": []}]
