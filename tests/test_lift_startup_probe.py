import json
import lift_reloc as reloc
import lift_startup_probe as probe
import os
import pytest
import subprocess
import sys
from types import SimpleNamespace


def test_startup_order_comes_from_dynamic_tags_and_relocated_words():
    dynamic = {"INIT": 0x1000, "INIT_ARRAY": 0x4000, "INIT_ARRAYSZ": 24, "FINI": 0x9000}
    sections = [{"name": "init_array", "va": 0x4000, "size": 24}]
    patches = [
        reloc.Patch("init_array", 16, None, None, function=0x2000),
        reloc.Patch("init_array", 0, None, None, function=0x3000),
        reloc.Patch("init_array", 8, None, None, function=0x2000),
    ]
    assert probe.startup_hooks(dynamic, sections, patches, {0x1000, 0x2000, 0x3000}) == [
        0x1000,
        0x3000,
        0x2000,
        0x2000,
    ]


@pytest.mark.parametrize(
    ("dynamic", "patch", "message"),
    [
        ({"INIT": 0x2000}, None, "INIT target 0x2000"),
        ({"INIT_ARRAYSZ": 8}, None, "incomplete INIT_ARRAY"),
        ({"INIT_ARRAY": 0x4000}, None, "incomplete INIT_ARRAY"),
        ({"INIT_ARRAY": 0x4000, "INIT_ARRAYSZ": 7}, None, "invalid INIT_ARRAY"),
        ({"INIT_ARRAY": 0x4000, "INIT_ARRAYSZ": 16}, None, "not contained"),
        ({"INIT_ARRAY": 0x4000, "INIT_ARRAYSZ": 8}, None, "slot 0x4000"),
        (
            {"INIT_ARRAY": 0x4000, "INIT_ARRAYSZ": 8},
            reloc.Patch("init_array", 0, None, None, function=0x2000),
            "slot 0x4000",
        ),
    ],
)
def test_invalid_startup_plan_fails_before_execution(dynamic, patch, message):
    with pytest.raises(probe.StartupError, match=message):
        probe.startup_hooks(dynamic, [{"name": "init_array", "va": 0x4000, "size": 8}], [patch] if patch else [], {0x1000})


@pytest.mark.skipif(sys.platform != "darwin" or os.uname().machine != "arm64", reason="needs native macOS arm64")
def test_native_probe_reports_completed_hooks_and_preserves_first_failure(tmp_path):
    dylib = tmp_path / "fixture.dylib"
    source = tmp_path / "fixture.c"
    source.write_text(
        """
        #include <stdlib.h>
        #include <stdint.h>
        #include <string.h>
        #include <stdio.h>
        static int state;
        void sub_1000(unsigned char *reg) {
            if (state++ != 0) abort();
            uintptr_t sp;
            memcpy(&sp, reg + 32, 8);
            sp += 8;
            memcpy(reg + 32, &sp, 8);
            puts("guest output is not a probe event");
        }
        void sub_2000(unsigned char *reg) {
            if (state != 1) abort();
            fputs("lift_import_refused: fixture: unsupported\\n", stderr);
            abort();
        }
        """
    )
    subprocess.run(["cc", "-dynamiclib", "-o", dylib, source], check=True, timeout=30)
    out = tmp_path / "out"
    result = probe.run_probe(dylib, [0x1000, 0x2000, 0x1000], out, timeout=10)
    assert result["events"] == [
        {"event": "enter", "index": 0, "address": 0x1000},
        {"event": "return", "index": 0, "address": 0x1000},
        {"event": "enter", "index": 1, "address": 0x2000},
    ]
    assert result["returncode"] < 0
    assert not result["complete"]
    assert "lift_import_refused: fixture: unsupported" in (out / "startup.stderr").read_text()
    assert json.loads((out / "startup.json").read_text()) == result


def test_timeout_preserves_partial_progress(tmp_path, monkeypatch):
    event = {"event": "enter", "index": 0, "address": 4096}
    events = b"#STARTUP#" + json.dumps(event).encode() + b"\n"

    def run(argv, **kwargs):
        if kwargs.get("check"):
            return SimpleNamespace(returncode=0)
        raise subprocess.TimeoutExpired(argv, kwargs["timeout"], output=events, stderr=b"diagnostic\n")

    monkeypatch.setattr(probe.subprocess, "run", run)
    result = probe.run_probe(tmp_path / "unused.dylib", [0x1000], tmp_path, timeout=1)
    assert result["events"] == [event]
    assert result["returncode"] is None
    assert result["timed_out"] and not result["complete"]
    assert (tmp_path / "startup.stderr").read_bytes() == b"diagnostic\n"
