"""Exception-oracle mode of the native bind host, run against a stub il2cpp runtime."""

import json
import os
import pytest
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / "scripts/native_bind_probe/host.c"
STUB = ROOT / "tests/fixtures/bind/il2cpp_stub.c"

pytestmark = pytest.mark.skipif(shutil.which("clang") is None, reason="clang not installed")


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("host-oracle")
    ext = "dylib" if os.uname().sysname == "Darwin" else "so"
    stub = out / f"stub.{ext}"
    host = out / "host"
    subprocess.run(["clang", "-shared", "-o", str(stub), str(STUB)], check=True)
    subprocess.run(["clang", "-O1", "-o", str(host), str(HOST), "-ldl", "-lm"], check=True)
    return host, stub


def run_host(built, *extra, throw):
    host, stub = built
    env = {**os.environ, **({"STUB_THROW": "1"} if throw else {})}
    command = [
        str(host), "--dylib", str(stub), "--leg", "leg2", "--invoke-image", "mscorlib.dll",
        "--invoke-class", "System.ThrowHelper", "--invoke-method", "Throw", "--invoke-ret", "int",
        "--invoke-expected", "7", *extra,
    ]  # fmt: skip
    result = subprocess.run(command, capture_output=True, text=True, env=env, timeout=60)
    line = next(line for line in result.stdout.splitlines() if line.startswith("#JSON#"))
    return json.loads(line.removeprefix("#JSON#"))


def test_throw_without_the_flag_still_fails(built):
    report = run_host(built, throw=True)
    assert report["status"] == "fail"
    assert report["reason"] == "invoke threw"


def test_expect_throw_records_class_and_message(built):
    report = run_host(built, "--expect-throw", throw=True)
    assert report["status"] == "pass"
    assert report["evidence"]["exception_class"] == "System.InvalidOperationException"
    assert report["evidence"]["exception_message"] == "System.InvalidOperationException: Nullable object must have a value."


def test_expect_throw_fails_when_nothing_is_thrown(built):
    report = run_host(built, "--expect-throw", throw=False)
    assert report["status"] == "fail"
    assert report["reason"] == "expected a throw but the invoke returned"
