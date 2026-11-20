"""Per-shard lifted objects and a relocated data object, linked into one arm64 dylib."""

import ctypes
import lift_image as li
import lift_link as ll
import lift_probe as lp
import lift_reloc as rl
import os
import pytest
import subprocess
import sys
import test_pcode_lift as t
from pathlib import Path
from types import SimpleNamespace

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin" or os.uname().machine != "arm64" or not (lp.LLVM / "llc").exists(),
    reason="needs native arm64 macOS and LLVM",
)

SECTIONS = [
    {"name": "text", "va": 0x1000, "size": 0x2000, "exec": True},
    {"name": "data", "va": 0x4000, "size": 16, "exec": False},
]
SHA, FINGERPRINT, GHIDRA = "sha", "fingerprint", "ghidra"
LIBC = {"abort", "getenv", "fopen", "fprintf", "fclose", "__stderrp", "dyld_stub_binder"}


def returns_seven():
    return {
        **t.body(
            t.insn(0x1000, 2, t.op("COPY", "register,0,8", "const,7,8")),
            t.insn(0x1002, 1, t.op("RETURN", None, "register,288,8")),
        ),
        "undecoded": 0,
    }


def calls_the_first():
    return {
        **t.body(
            t.insn(0x2000, 5, t.op("CALL", None, "ram,1000,8")),
            t.insn(0x2005, 1, t.op("RETURN", None, "register,288,8")),
            start=0x2000,
        ),
        "undecoded": 0,
    }


def jumps_through_a_register():
    return {**t.body(t.insn(0x3000, 2, t.op("BRANCHIND", None, "register,0,8")), start=0x3000), "undecoded": 0}


def write_baseline(directory, shards):
    """Writes one valid pcode shard per list of body rows; returns the Fde parts."""
    parts = []
    for index, rows in enumerate(shards):
        part = [lp.Fde(r["start"], r["size"]) for r in rows]
        identity = li.shard_identity(SHA, FINGERPRINT, GHIDRA, part, "")
        li.write_shard(directory / f"pcode-{index:04d}.jsonl", identity, [{"kind": "sections", "sections": SECTIONS}, *rows])
        parts.append(part)
    return parts


def context(tmp_path, **extra):
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    return {
        "baseline": tmp_path,
        "out": out,
        "sha": SHA,
        "fingerprint": FINGERPRINT,
        "ghidra": GHIDRA,
        "link": "link-1",
        "tool_timeout": 120,
        "so": None,
        **extra,
    }


def test_a_shard_object_is_written_and_reused_while_its_identity_holds(tmp_path, monkeypatch):
    parts = write_baseline(tmp_path, [[returns_seven()]])
    ctx = context(tmp_path)
    first = ll.shard_object(0, parts[0], ctx)
    assert Path(first["object"]).stat().st_size == first["bytes"] > 0
    assert first["bodies"] == 1 and first["holes"] == {}
    monkeypatch.setattr(lp, "run_tool_body", lambda *a, **k: pytest.fail("recompiled a shard whose identity held"))
    assert ll.shard_object(0, parts[0], ctx) == first


def test_a_changed_link_fingerprint_recompiles_the_shard(tmp_path, monkeypatch):
    parts = write_baseline(tmp_path, [[returns_seven()]])
    ll.shard_object(0, parts[0], context(tmp_path))
    calls = []
    real = lp.run_tool_body
    monkeypatch.setattr(lp, "run_tool_body", lambda *a, **k: calls.append(a[0]) or real(*a, **k))
    ll.shard_object(0, parts[0], context(tmp_path, link="link-2"))
    assert calls == ["llc"]


def test_a_baseline_shard_with_another_identity_is_refused(tmp_path):
    parts = write_baseline(tmp_path, [[returns_seven()]])
    with pytest.raises(ValueError, match="baseline pcode shard 0"):
        ll.shard_object(0, parts[0], context(tmp_path, fingerprint="a different dump"))


def test_a_body_with_a_hole_is_recorded_and_calls_the_logging_trap(tmp_path):
    parts = write_baseline(tmp_path, [[jumps_through_a_register()]])
    record = ll.shard_object(0, parts[0], context(tmp_path))
    assert record["holes"] == {"12288": ["BRANCHIND"]}
    undefined = subprocess.run([lp.LLVM / "llvm-nm", "-u", record["object"]], capture_output=True, text=True, check=True).stdout
    assert "_lift_hole" in undefined


def test_a_call_into_the_middle_of_another_body_is_a_hole_not_an_unresolved_symbol(tmp_path):
    middle = {
        **calls_the_first(),
        "insns": [{**calls_the_first()["insns"][0], "ops": [t.op("CALL", None, "ram,1001,8")]}, calls_the_first()["insns"][1]],
    }
    parts = write_baseline(tmp_path, [[middle]])
    ctx = context(tmp_path, entries=frozenset({0x1000, 0x2000}), entries_id="e1")
    record = ll.shard_object(0, parts[0], ctx)
    assert record["holes"] == {"8192": ["MID_BODY_TARGET"]}
    undefined = subprocess.run([lp.LLVM / "llvm-nm", "-u", record["object"]], capture_output=True, text=True, check=True).stdout
    assert "_sub_1001" not in undefined


def test_a_different_set_of_entries_recompiles_the_shard(tmp_path, monkeypatch):
    parts = write_baseline(tmp_path, [[returns_seven()]])
    ll.shard_object(0, parts[0], context(tmp_path, entries=frozenset({0x1000}), entries_id="e1"))
    calls = []
    real = lp.run_tool_body
    monkeypatch.setattr(lp, "run_tool_body", lambda *a, **k: calls.append(a[0]) or real(*a, **k))
    ll.shard_object(0, parts[0], context(tmp_path, entries=frozenset({0x1000, 0x2000}), entries_id="e2"))
    assert calls == ["llc"]


def test_a_body_that_cannot_be_lifted_is_a_recorded_failure_not_an_object(tmp_path):
    bad = {**returns_seven(), "insns": [{"a": 0x1000, "len": 1, "m": "x", "ops": [{"op": "NOT_AN_OP", "out": None, "in": []}]}]}
    parts = write_baseline(tmp_path, [[bad]])
    record = ll.shard_object(0, parts[0], context(tmp_path))
    assert record["holes"] != {} or record["failed"]


def test_section_images_read_file_bytes_and_zero_fill_nobits():
    elf = SimpleNamespace(
        sections=[
            SimpleNamespace(addr=0x4000, size=4, offset=2, type=1),
            SimpleNamespace(addr=0x5000, size=8, offset=0, type=8),
        ]
    )
    sections = [
        {"name": "data", "va": 0x4000, "size": 4, "exec": False},
        {"name": "bss", "va": 0x5000, "size": 8, "exec": False},
        {"name": "EXTERNAL", "va": 0x6000, "size": 3, "exec": False},
    ]
    images = ll.section_images(elf, bytes(range(16)), sections, {"data", "bss", "EXTERNAL"})
    assert images == {"data": bytes([2, 3, 4, 5]), "bss": bytes(8), "EXTERNAL": bytes(3)}


def test_undefined_symbols_are_grouped_by_what_would_bind_them():
    nm = "_sub_4e26440\n_sub_4e26450\n_lift_cpuid_leaf_at\n_memcpy\n"
    assert ll.classify_undefined(nm) == {
        "bodies": ["sub_4e26440", "sub_4e26450"],
        "lift": ["lift_cpuid_leaf_at"],
        "other": ["memcpy"],
    }


def test_two_shards_and_a_relocated_word_link_into_a_loadable_dylib(tmp_path):
    parts = write_baseline(tmp_path, [[returns_seven()], [calls_the_first()]])
    image = rl.Image(SECTIONS, {0x4008: rl.Reloc(rl.R_X86_64_RELATIVE, 0, 0x2000)}, [])
    plan = rl.plan_image(image, frozenset({0x1000, 0x2000}))
    ctx = context(tmp_path)
    summary = ll.link_image(ctx, parts, plan, lambda names: {"data": bytes(16)})
    assert summary["undefined"]["bodies"] == [] and summary["undefined"]["lift"] == []
    assert set(summary["undefined"]["other"]) <= LIBC
    lib = ctypes.CDLL(summary["dylib"])
    reg, stack = (ctypes.c_ubyte * 8192)(), (ctypes.c_ubyte * 4096)()
    ctypes.c_uint64.from_buffer(reg, 32).value = ctypes.addressof(stack) + 2048
    lib.sub_2000(reg)
    assert ctypes.c_uint64.from_buffer(reg, 0).value == 7
    word = ctypes.c_uint64.from_buffer((ctypes.c_ubyte * 16).in_dll(lib, "sec_data"), 8).value
    assert word == ctypes.cast(lib.sub_2000, ctypes.c_void_p).value


def test_a_second_link_with_unchanged_inputs_reuses_the_dylib(tmp_path):
    parts = write_baseline(tmp_path, [[returns_seven()]])
    plan = rl.plan_image(rl.Image(SECTIONS, {}, []), frozenset({0x1000}))
    ctx = context(tmp_path)
    first = ll.link_image(ctx, parts, plan, lambda names: {"data": bytes(16)})
    stamp = Path(first["dylib"]).stat().st_mtime_ns
    second = ll.link_image(ctx, parts, plan, lambda names: {"data": bytes(16)})
    assert second["dylib"] == first["dylib"] and Path(second["dylib"]).stat().st_mtime_ns == stamp
