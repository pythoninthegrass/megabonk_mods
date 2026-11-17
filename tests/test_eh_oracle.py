"""The thrown-exception oracle must bind its report to the binary and method that produced it."""

import eh_oracle
import json
import pytest


def report(**evidence):
    base = {
        "platform": "linux",
        "arch": "x86_64",
        "loader_images": 0,
        "image": "mscorlib.dll",
        "method_name": eh_oracle.ORACLES[0].method,
        "invoke_class": eh_oracle.ORACLES[0].class_name,
        "exception_class": "System.InvalidOperationException",
        "exception_message": "System.InvalidOperationException: Nullable object must have a value.",
    }
    return "#JSON# " + json.dumps({"status": "pass", "reason": "", "evidence": {**base, **evidence}})


def test_command_expects_a_throw_from_the_named_method(tmp_path):
    command = eh_oracle.host_command("/g", eh_oracle.ORACLES[0])
    assert "--expect-throw" in command
    assert command[command.index("--invoke-method") + 1] == eh_oracle.ORACLES[0].method
    assert command[command.index("--invoke-ret") + 1] == "void"


def test_parse_returns_the_thrown_class_and_message():
    parsed = eh_oracle.parse_report(report(), eh_oracle.ORACLES[0])
    assert parsed == {
        "exception_class": "System.InvalidOperationException",
        "exception_message": "System.InvalidOperationException: Nullable object must have a value.",
    }


@pytest.mark.parametrize(
    "change",
    [{"platform": "macos"}, {"method_name": "Other"}, {"loader_images": 1}, {"exception_class": ""}],
)
def test_parse_rejects_a_report_from_another_method_or_a_modded_runtime(change):
    with pytest.raises(eh_oracle.OracleError):
        eh_oracle.parse_report(report(**change), eh_oracle.ORACLES[0])


def test_parse_rejects_a_failed_host():
    failed = "#JSON# " + json.dumps({"status": "fail", "reason": "invoke threw", "evidence": {}})
    with pytest.raises(eh_oracle.OracleError):
        eh_oracle.parse_report(failed, eh_oracle.ORACLES[0])


def test_unsafe_host_is_refused(tmp_path):
    with pytest.raises(eh_oracle.OracleError):
        eh_oracle.capture("-oProxyCommand=x", "/g", tmp_path)
