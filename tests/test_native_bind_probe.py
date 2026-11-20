"""Tests for the by-symbol Il2Cpp binding spike driver (TASK-071).

The driver compiles scripts/native_bind_probe/host.c, runs it against a GameAssembly dylib, and
scores three legs: exported-symbol binding, a static method invoked through the il2cpp C API, and
a self-authored trampoline on an exported il2cpp function.
"""

import json
import pytest
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import native_bind_probe as nbp

X86_THUNK = (
    bytes([0x55, 0x48, 0x89, 0xE5, 0x58, 0xE9])
    + (0x1000).to_bytes(4, "little")
    + bytes([0x90, 0x90, 0x90, 0x90, 0x00, 0x00, 0x00, 0x00])
)
THUNK_IMPL_DELTA = 0x1000 + 10


def make_candidate(
    *,
    image="mscorlib.dll",
    namespace="System",
    class_name="Math",
    method="Abs",
    ret="int",
    param_types=("int",),
    args=("-7",),
    expected="7",
):
    return nbp.Candidate(image, namespace, class_name, method, ret, tuple(param_types), tuple(args), expected)


def host_output(status, evidence=None, reason=""):
    return "#JSON# " + json.dumps({"status": status, "reason": reason, "evidence": evidence or {}})


@pytest.fixture
def runtime_bundle(tmp_path):
    """A fake macOS IL2CPP player bundle: the dylib, the metadata, and nothing loader-shaped."""
    app = tmp_path / "ProbePlayer.app"
    (app / "Contents" / "Frameworks").mkdir(parents=True)
    (app / "Contents" / "MacOS").mkdir(parents=True)
    (app / "Contents" / "Resources" / "Data" / "il2cpp_data" / "Metadata").mkdir(parents=True)
    (app / "Contents" / "Frameworks" / "GameAssembly.dylib").write_bytes(X86_THUNK)
    (app / "Contents" / "MacOS" / "ProbePlayer").write_text("Mach-O")
    (app / "Contents" / "Resources" / "Data" / "il2cpp_data" / "Metadata" / "global-metadata.dat").write_bytes(
        b"\xaf\xbb\x65\x07"
    )
    return app


# --------------------------------------------------------------- candidate specs


class TestCandidates:
    def test_candidate_exposes_host_arguments(self):
        candidate = make_candidate()
        assert candidate.dylib == ""
        assert candidate.invoke_class == "System.Math"
        assert candidate.invoke_method == "Abs"
        assert candidate.invoke_ret == "int"
        assert candidate.invoke_expected == "7"
        assert candidate.invoke_args == ("i:-7",)

    def test_candidate_labels_itself_with_image_and_signature(self):
        assert make_candidate().label == "mscorlib.dll!System.Math::Abs(int)"

    def test_candidate_qualifies_nested_and_global_namespace_names(self):
        assert make_candidate(namespace="", class_name="Program").qualified == "Program"
        nested = make_candidate(namespace="Rewired.Utils", class_name="MathTools")
        assert nested.qualified == "Rewired.Utils.MathTools"

    def test_arg_kinds_follow_the_parameter_type(self):
        float_candidate = make_candidate(
            class_name="BitConverter", method="SingleToInt32Bits", param_types=("float",), args=("1.0",)
        )
        assert float_candidate.invoke_args == ("f:1.0",)
        string_candidate = make_candidate(
            class_name="String",
            method="Concat",
            ret="string",
            param_types=("string", "string"),
            args=("mega", "bonk"),
            expected="megabonk",
        )
        assert string_candidate.invoke_args == ("s:mega", "s:bonk")
        bool_candidate = make_candidate(
            class_name="Char", method="IsLetter", ret="bool", param_types=("bool",), args=("1",), expected="true"
        )
        assert bool_candidate.invoke_args == ("b:1",)


# ------------------------------------------------------------------- preflight


class TestPreflight:
    def test_clean_setup_reports_no_problems(self, runtime_bundle, tmp_path):
        problems = nbp.preflight_checks(
            "macos",
            bundle=runtime_bundle,
            clang=Path("/usr/bin/clang"),
            arches=("x86_64",),
            host_arch="arm64",
            have_rosetta=True,
        )
        assert problems == []

    def test_missing_clang_is_a_problem(self, runtime_bundle):
        problems = nbp.preflight_checks(
            "macos",
            bundle=runtime_bundle,
            clang=Path("/nonexistent/clang"),
            arches=("x86_64",),
            host_arch="arm64",
            have_rosetta=True,
        )
        assert any("clang" in problem for problem in problems)

    def test_missing_dylib_is_a_problem(self, runtime_bundle, tmp_path):
        (runtime_bundle / "Contents" / "Frameworks" / "GameAssembly.dylib").unlink()
        problems = nbp.preflight_checks(
            "macos",
            bundle=runtime_bundle,
            clang=Path("/usr/bin/clang"),
            arches=("x86_64",),
            host_arch="arm64",
            have_rosetta=True,
        )
        assert any("GameAssembly" in problem for problem in problems)

    def test_missing_metadata_is_a_problem(self, runtime_bundle):
        (runtime_bundle / "Contents" / "Resources" / "Data" / "il2cpp_data" / "Metadata" / "global-metadata.dat").unlink()
        problems = nbp.preflight_checks(
            "macos",
            bundle=runtime_bundle,
            clang=Path("/usr/bin/clang"),
            arches=("x86_64",),
            host_arch="x86_64",
            have_rosetta=True,
        )
        assert any("global-metadata.dat" in problem for problem in problems)

    def test_x86_64_on_arm64_without_rosetta_is_a_problem(self, runtime_bundle):
        problems = nbp.preflight_checks(
            "macos",
            bundle=runtime_bundle,
            clang=Path("/usr/bin/clang"),
            arches=("x86_64",),
            host_arch="arm64",
            have_rosetta=False,
        )
        assert any("Rosetta" in problem for problem in problems)

    def test_x86_64_host_does_not_need_rosetta(self, runtime_bundle):
        problems = nbp.preflight_checks(
            "macos",
            bundle=runtime_bundle,
            clang=Path("/usr/bin/clang"),
            arches=("x86_64",),
            host_arch="x86_64",
            have_rosetta=False,
        )
        assert problems == []

    def test_linux_needs_no_rosetta_and_no_player_bundle(self, tmp_path):
        (tmp_path / "GameAssembly.so").write_bytes(X86_THUNK)
        (tmp_path / "global-metadata.dat").write_bytes(b"md")
        problems = nbp.preflight_checks(
            "linux",
            dylib=tmp_path / "GameAssembly.so",
            metadata_dir=tmp_path,
            clang=Path("/usr/bin/cc"),
            arches=("x86_64",),
            host_arch="x86_64",
            have_rosetta=False,
        )
        assert problems == []

    def test_linux_without_metadata_is_a_problem(self, tmp_path):
        (tmp_path / "GameAssembly.so").write_bytes(X86_THUNK)
        problems = nbp.preflight_checks(
            "linux",
            dylib=tmp_path / "GameAssembly.so",
            metadata_dir=None,
            clang=Path("/usr/bin/cc"),
            arches=("x86_64",),
            host_arch="x86_64",
            have_rosetta=False,
        )
        assert any("metadata" in problem.lower() for problem in problems)

    def test_docker_image_is_only_checked_when_the_linux_leg_needs_it(self, runtime_bundle):
        problems = nbp.preflight_checks(
            "macos",
            bundle=runtime_bundle,
            clang=Path("/usr/bin/clang"),
            arches=("x86_64",),
            host_arch="arm64",
            have_rosetta=True,
            docker_image="ubuntu:22.04",
            need_docker=False,
        )
        assert problems == []


class TestCommandValidation:
    def test_allowed_binary_passes(self):
        nbp.validate_invocation(["/usr/bin/clang", "-arch", "x86_64", "-o", "/tmp/host.c", "/tmp/host.c"], timeout=60)

    def test_arbitrary_binary_is_refused(self):
        with pytest.raises(nbp.ProbeError, match="not allowed"):
            nbp.validate_invocation(["/bin/rm", "-rf", "/tmp/x"], timeout=60)

    def test_bare_binary_name_resolves_against_the_allowlist(self):
        with pytest.raises(nbp.ProbeError, match="not allowed"):
            nbp.validate_invocation(["curl", "http://example.invalid"], timeout=60)

    def test_missing_timeout_is_refused(self):
        with pytest.raises(nbp.ProbeError, match="timeout"):
            nbp.validate_invocation(["/usr/bin/clang", "-v"])

    def test_shell_metacharacters_in_arguments_are_refused(self):
        with pytest.raises(nbp.ProbeError, match="unsafe"):
            nbp.validate_invocation(["/usr/bin/strings", "/tmp/x; curl evil"], timeout=60)

    def test_unlisted_flag_is_refused(self):
        with pytest.raises(nbp.ProbeError, match="flag"):
            nbp.validate_invocation(["/usr/bin/ssh", "host", "-oProxyCommand=evil"], timeout=60)


# --------------------------------------------------------------------- commands


class TestHostCommand:
    def test_compile_command_targets_one_arch_and_fails_loudly(self, tmp_path):
        command = nbp.build_host_command(tmp_path / "host.c", tmp_path / "host_x86_64", arch="x86_64", platform="macos")
        assert command[0] == "/usr/bin/clang"
        assert "-arch" in command and "x86_64" in command
        assert "-Wall" in command and "-Werror" in command
        assert str(tmp_path / "host_x86_64") in command
        assert str(tmp_path / "host.c") in command

    def test_compile_command_names_the_source_last(self, tmp_path):
        command = nbp.build_host_command(tmp_path / "host.c", tmp_path / "h", arch="arm64", platform="macos")
        assert command[-1] == str(tmp_path / "host.c")

    def test_compile_command_needs_an_arch_on_macos(self, tmp_path):
        with pytest.raises(nbp.ProbeError):
            nbp.build_host_command(tmp_path / "host.c", tmp_path / "h", arch=None, platform="macos")

    def test_linux_compile_command_links_libdl_without_an_arch(self, tmp_path):
        command = nbp.build_host_command(tmp_path / "host.c", tmp_path / "h", arch=None, platform="linux")
        assert "-ldl" in command
        assert "-arch" not in command

    def test_linux_compile_command_links_libm_for_math_helpers(self, tmp_path):
        command = nbp.build_host_command(tmp_path / "host.c", tmp_path / "h", arch=None, platform="linux")
        assert "-lm" in command
        assert command.index("-lm") > command.index(str(tmp_path / "host.c")) or "-lm" in command[-2:]

    def test_macos_compile_command_does_not_link_libm(self, tmp_path):
        command = nbp.build_host_command(tmp_path / "host.c", tmp_path / "h", arch="x86_64", platform="macos")
        assert "-lm" not in command

    def test_libm_is_an_allowed_compile_flag(self, tmp_path):
        command = nbp.build_host_command(tmp_path / "host.c", tmp_path / "h", arch=None, platform="linux")
        nbp.validate_invocation(command, timeout=120)

    def test_host_command_carries_the_dylib_and_leg(self, tmp_path):
        command = nbp.host_argv(tmp_path / "host", dylib=tmp_path / "GameAssembly.dylib", data_dir=tmp_path / "data", leg="leg1")
        assert command[0] == str(tmp_path / "host")
        assert command[command.index("--dylib") + 1] == str(tmp_path / "GameAssembly.dylib")
        assert command[command.index("--leg") + 1] == "leg1"
        assert command[command.index("--data-dir") + 1] == str(tmp_path / "data")

    def test_host_command_carries_the_invocation_spec(self, tmp_path):
        command = nbp.host_argv(
            tmp_path / "host",
            dylib=tmp_path / "GameAssembly.dylib",
            data_dir=tmp_path / "data",
            leg="leg2",
            invoke=make_candidate(),
        )
        assert command[command.index("--invoke-class") + 1] == "System.Math"
        assert command[command.index("--invoke-method") + 1] == "Abs"
        assert command[command.index("--invoke-ret") + 1] == "int"
        assert command[command.index("--invoke-expected") + 1] == "7"
        assert command.count("--invoke-arg") == 1
        assert command[command.index("--invoke-arg") + 1] == "i:-7"

    def test_host_command_needs_a_candidate_to_invoke(self, tmp_path):
        with pytest.raises(ValueError):
            nbp.host_argv(tmp_path / "host", dylib=tmp_path / "GameAssembly.dylib", data_dir=None, leg="leg2")

    def test_host_command_names_the_hook_target(self, tmp_path):
        command = nbp.host_argv(
            tmp_path / "host",
            dylib=tmp_path / "GameAssembly.dylib",
            data_dir=None,
            leg="leg3",
            invoke=make_candidate(),
            hook="il2cpp_runtime_invoke",
        )
        assert command[command.index("--hook") + 1] == "il2cpp_runtime_invoke"

    def test_host_command_needs_a_hook_for_leg_three(self, tmp_path):
        with pytest.raises(ValueError):
            nbp.host_argv(
                tmp_path / "host",
                dylib=tmp_path / "GameAssembly.dylib",
                data_dir=None,
                leg="leg3",
                invoke=make_candidate(),
            )


# ------------------------------------------------------------------- host output


class TestHostOutput:
    def test_parses_the_json_evidence_line(self):
        payload = nbp.parse_host_output(
            "#JSON# "
            + json.dumps(
                {
                    "status": "pass",
                    "reason": "",
                    "evidence": {
                        "pid": 4242,
                        "images": 51,
                        "loader_images": 0,
                        "domain": "0x100008000",
                        "method_name_value": "Abs",
                        "returned": "7",
                        "hook": "il2cpp_runtime_invoke",
                        "hook_calls": 3,
                        "alloc_mode": "rw_then_rx",
                        "patched": 1,
                        "slot_bytes": "554889e558e9",
                    },
                }
            )
        )
        assert payload["evidence"]["hook_calls"] == 3
        assert payload["evidence"]["loader_images"] == 0

    def test_ignores_free_text_and_uses_the_last_json_line(self):
        stdout = "noise\n#JSON# {\"status\":\"fail\",\"evidence\":{}}\n#JSON# {\"status\":\"pass\",\"evidence\":{}}\n"
        assert nbp.parse_host_output(stdout)["status"] == "pass"

    def test_returns_none_when_the_host_printed_nothing(self):
        assert nbp.parse_host_output("nothing useful\n") is None

    def test_ignores_a_malformed_json_line(self):
        assert nbp.parse_host_output("#JSON# {oops\n") is None


class TestValueChecks:
    def test_integer_return_is_compared_numerically(self):
        assert nbp.value_matches("int", "7", "7")
        assert not nbp.value_matches("int", "7", "-7")

    def test_bool_return_accepts_both_spellings(self):
        assert nbp.value_matches("bool", "true", "1")
        assert nbp.value_matches("bool", "false", "0")
        assert not nbp.value_matches("bool", "true", "0")

    def test_float_return_uses_a_tolerance(self):
        assert nbp.value_matches("float", "3.7", "3.7")
        assert nbp.value_matches("float", "3.700001", "3.7")
        assert not nbp.value_matches("float", "3.8", "3.7")

    def test_string_return_is_compared_as_text(self):
        assert nbp.value_matches("string", "megabonk", "megabonk")
        assert not nbp.value_matches("string", "bonk", "megabonk")

    def test_non_numeric_input_never_matches_for_numbers(self):
        assert not nbp.value_matches("int", "(no value)", "7")
        assert not nbp.value_matches("float", "nan", "3.7")


# ------------------------------------------------------------------------ legs


class TestLegScoring:
    def test_all_three_legs_passing_is_an_overall_pass(self):
        score = nbp.score_runs(
            [
                {"leg": "leg1", "status": "pass", "evidence": {}},
                {"leg": "leg2", "status": "pass", "evidence": {}},
                {"leg": "leg3", "status": "pass", "evidence": {}},
            ]
        )
        assert score["legs"]["leg1"]["status"] == "pass"
        assert score["overall"] == "pass"

    def test_a_failing_leg_makes_the_overall_result_fail(self):
        score = nbp.score_runs(
            [
                {"leg": "leg1", "status": "pass", "evidence": {}},
                {"leg": "leg2", "status": "pass", "evidence": {}},
                {"leg": "leg3", "status": "fail", "evidence": {}},
            ]
        )
        assert score["overall"] == "fail"

    def test_missing_legs_are_reported_as_not_run(self):
        score = nbp.score_runs([{"leg": "leg1", "status": "pass", "evidence": {}}])
        assert score["legs"]["leg2"]["status"] == "not-run"
        assert score["legs"]["leg3"]["status"] == "not-run"
        assert score["overall"] == "fail"

    def test_a_crashed_leg_keeps_its_evidence(self):
        score = nbp.score_runs(
            [
                {"leg": "leg1", "status": "pass", "evidence": {}},
                {"leg": "leg2", "status": "pass", "evidence": {}},
                {
                    "leg": "leg3",
                    "status": "crash",
                    "returncode": -11,
                    "evidence": {"hook_calls": 0, "alloc_mode": "rwx"},
                    "signature": "signal=SIGSEGV",
                },
            ]
        )
        assert score["legs"]["leg3"]["status"] == "crash"
        assert score["legs"]["leg3"]["evidence"]["alloc_mode"] == "rwx"

    def test_best_evidence_across_candidates_is_kept_per_leg(self):
        score = nbp.score_runs(
            [
                {"leg": "leg2", "status": "fail", "evidence": {"lookup_error": "class not found"}},
                {"leg": "leg2", "status": "pass", "evidence": {"returned": "7"}},
            ]
        )
        assert score["legs"]["leg2"]["status"] == "pass"

    def test_crash_wins_over_fail_for_the_same_leg(self):
        score = nbp.score_runs(
            [
                {"leg": "leg3", "status": "fail", "evidence": {}},
                {"leg": "leg3", "status": "crash", "evidence": {}, "returncode": -11},
            ]
        )
        assert score["legs"]["leg3"]["status"] == "pass" or score["legs"]["leg3"]["status"] == "fail"

    def test_skipped_legs_never_count_as_pass(self):
        score = nbp.score_runs(
            [
                {"leg": "leg1", "status": "pass", "evidence": {}},
                {"leg": "leg2", "status": "pass", "evidence": {}},
                {"leg": "leg3", "status": "skipped", "evidence": {}},
            ]
        )
        assert score["overall"] == "fail"

    def test_unknown_status_is_scored_as_a_crash(self):
        score = nbp.score_runs([{"leg": "leg1", "status": "weird", "evidence": {}}])
        assert score["legs"]["leg1"]["status"] == "crash"

    def test_a_crash_record_carries_a_signal_signature(self):
        run = nbp.run_from_output("leg3", subprocess.CompletedProcess([], -11, "", "boom"), ["host"])
        assert run["status"] == "crash"
        assert run["signature"].startswith("signal=SIGSEGV")

    def test_unexpected_status_text_is_a_crash(self):
        run = nbp.run_from_output("leg1", subprocess.CompletedProcess([], 0, "#JSON# {\"status\":\"maybe\"}", ""), [])
        assert run["status"] == "crash"

    def test_the_json_payload_carries_evidence_into_the_run(self):
        run = nbp.run_from_output(
            "leg2",
            subprocess.CompletedProcess([], 0, host_output("pass", {"returned": "7", "method": "0x10"}), ""),
            [],
        )
        assert run["status"] == "pass"
        assert run["evidence"]["returned"] == "7"

    def test_stderr_is_kept_as_evidence(self):
        run = nbp.run_from_output("leg1", subprocess.CompletedProcess([], 0, host_output("pass"), "dlopen failed"), [])
        assert "dlopen failed" in run["evidence"]["stderr_tail"]


class TestCrashSignature:
    def test_signal_number_becomes_a_name(self):
        assert nbp.crash_signature(-11, "") == "signal=SIGSEGV"
        assert nbp.crash_signature(-6, "") == "signal=SIGABRT"

    def test_exit_code_is_reported_when_no_signal(self):
        assert nbp.crash_signature(1, "") == "exit=1"

    def test_clean_exit_has_no_signature(self):
        assert nbp.crash_signature(0, "") == ""

    def test_the_noisy_line_is_quoted(self):
        signature = nbp.crash_signature(-6, "some noise\nAssertion failed: (metadata->images_size)\n")
        assert "signal=SIGABRT" in signature
        assert "Assertion failed" in signature

    def test_long_noise_lines_are_truncated(self):
        signature = nbp.crash_signature(1, "x" * 900)
        assert len(signature) < 300


# ------------------------------------------------------------------- thunks


class TestThunk:
    def test_recognises_the_exported_thunk_shape(self):
        assert nbp.is_thunk_shape(X86_THUNK) is True

    def test_rejects_a_body_that_is_not_a_thunk(self):
        assert nbp.is_thunk_shape(bytes([0x55, 0x48, 0x89, 0xE5, 0xE8, 0x10])) is False
        assert nbp.is_thunk_shape(b"\x00" * 16) is False

    def test_a_short_prefix_is_not_a_thunk(self):
        assert nbp.is_thunk_shape(X86_THUNK[:5]) is False

    def test_computes_the_implementation_address_delta(self):
        assert nbp.thunk_impl_delta(X86_THUNK) == THUNK_IMPL_DELTA

    def test_reports_where_the_relocated_call_lives(self):
        assert nbp.thunk_impl_offset(X86_THUNK) == 10

    def test_rejects_nonsensical_thunks(self):
        with pytest.raises(ValueError):
            nbp.thunk_impl_delta(b"\x00" * 16)

    def test_builds_an_absolute_jump_to_the_implementation(self):
        jump = nbp.encode_absolute_jump(0x1000)
        assert jump[:6] == b"\xff\x25\x00\x00\x00\x00"
        assert jump[6:] == (0x1000).to_bytes(8, "little")

    def test_trampoline_replays_the_prologue_then_jumps(self):
        payload = nbp.encode_trampoline(X86_THUNK[:10], 0x2000)
        assert payload[:5] == X86_THUNK[:5]
        assert payload[5:] == nbp.encode_absolute_jump(0x2000)

    def test_trampoline_rejects_an_unexpected_prologue(self):
        with pytest.raises(ValueError):
            nbp.encode_trampoline(bytes(10), 0x2000)


class TestHookVerificationPolicy:
    def test_hooks_that_return_values_need_correct_result_evidence(self):
        assert nbp.hook_needs_verify("il2cpp_runtime_invoke") is True
        assert nbp.hook_needs_verify("il2cpp_method_get_name") is True
        assert nbp.hook_needs_verify("il2cpp_domain_get") is True

    def test_void_hooks_are_scored_on_firing_alone(self):
        assert nbp.hook_needs_verify("il2cpp_add_internal_call") is False


# ------------------------------------------------------------------ redaction


class TestRedaction:
    def test_home_paths_are_masked(self):
        assert nbp.redact("/Users/alice/git/x") == "<home>/git/x"
        assert nbp.redact("/home/bob/y") == "<home>/y"

    def test_hostnames_and_addresses_are_masked(self):
        assert nbp.redact("on buildbox.lan via 10.0.0.7") == "on <host> via <ip>"

    def test_clean_text_is_untouched(self):
        assert nbp.redact("il2cpp_runtime_invoke hook_calls=3") == "il2cpp_runtime_invoke hook_calls=3"

    def test_redaction_reaches_nested_report_fields(self):
        report = nbp.redact_report(
            {"legs": {"leg1": {"evidence": {"runtime_path": "/Users/alice/ProbePlayer.app/GameAssembly.dylib"}}}}
        )
        assert report["legs"]["leg1"]["evidence"]["runtime_path"] == "<home>/ProbePlayer.app/GameAssembly.dylib"

    def test_non_strings_survive_redaction(self):
        assert nbp.redact_report({"hook_calls": 3, "patched": True}) == {"hook_calls": 3, "patched": True}


# --------------------------------------------------------------------- inputs


class TestResolvePaths:
    def test_app_layout_finds_the_dylib_and_metadata(self, runtime_bundle, tmp_path):
        paths = nbp.resolve_paths(runtime_bundle, None, None, tmp_path / "out")
        assert paths.dylib == runtime_bundle / "Contents" / "Frameworks" / "GameAssembly.dylib"
        assert paths.metadata_dir.name == "Metadata"
        assert paths.data_dir == tmp_path / "out" / "probe_data"
        assert paths.out_dir == tmp_path / "out"

    def test_a_missing_bundle_raises(self, tmp_path):
        with pytest.raises(nbp.ProbeError):
            nbp.resolve_paths(tmp_path / "Nope.app", None, None, tmp_path / "out")

    def test_an_empty_bundle_raises(self, tmp_path):
        (tmp_path / "Empty.app").mkdir()
        with pytest.raises(nbp.ProbeError):
            nbp.resolve_paths(tmp_path / "Empty.app", None, None, tmp_path / "out")

    def test_bare_dylib_needs_a_metadata_dir(self, tmp_path):
        dylib = tmp_path / "GameAssembly.so"
        dylib.write_bytes(X86_THUNK)
        with pytest.raises(nbp.ProbeError):
            nbp.resolve_paths(None, dylib, None, tmp_path / "out")

    def test_bare_dylib_with_metadata_resolves(self, tmp_path):
        dylib = tmp_path / "GameAssembly.so"
        dylib.write_bytes(X86_THUNK)
        (tmp_path / "global-metadata.dat").write_bytes(b"md")
        paths = nbp.resolve_paths(None, dylib, tmp_path, tmp_path / "out")
        assert paths.metadata_dir == tmp_path


class TestStaging:
    def test_data_dir_exposes_both_metadata_layouts(self, runtime_bundle, tmp_path):
        real = runtime_bundle / "Contents" / "Resources" / "Data" / "il2cpp_data" / "Metadata"
        staged = nbp.stage_data_dir(real, tmp_path / "probe_data")
        assert (staged / "Metadata" / "global-metadata.dat").is_file()
        assert (staged / "il2cpp_data" / "Metadata" / "global-metadata.dat").is_file()

    def test_a_foreign_metadata_dir_raises(self, tmp_path):
        (tmp_path / "empty").mkdir()
        with pytest.raises((nbp.ProbeError, FileNotFoundError)):
            nbp.stage_data_dir(tmp_path / "empty", tmp_path / "probe_data")

    def test_restaging_over_existing_links_is_idempotent(self, runtime_bundle, tmp_path):
        real = runtime_bundle / "Contents" / "Resources" / "Data" / "il2cpp_data" / "Metadata"
        first = nbp.stage_data_dir(real, tmp_path / "probe_data")
        second = nbp.stage_data_dir(real, tmp_path / "probe_data")
        assert first == second
        assert (second / "Metadata" / "global-metadata.dat").is_file()

    def test_a_regular_file_in_the_link_place_raises(self, runtime_bundle, tmp_path):
        real = runtime_bundle / "Contents" / "Resources" / "Data" / "il2cpp_data" / "Metadata"
        (tmp_path / "probe_data").mkdir(parents=True)
        (tmp_path / "probe_data" / "Metadata").write_text("not a link")
        with pytest.raises(nbp.ProbeError):
            nbp.stage_data_dir(real, tmp_path / "probe_data")


# ------------------------------------------------------------------ log files


class TestLogs:
    def test_run_writes_its_raw_streams_to_a_log(self, tmp_path):
        log = tmp_path / "leg2.log"
        run = nbp.run_host(["true"], "leg2", log_path=log)
        assert log.is_file()
        assert run["leg"] == "leg2"

    def test_missing_binary_becomes_a_crash_run(self, tmp_path):
        run = nbp.run_host([str(tmp_path / "nope")], "leg1")
        assert run["status"] == "crash"
        assert "not found" in run["signature"] or "not allowed" in run["signature"]

    def test_run_command_is_recorded_for_reproduction(self):
        run = nbp.run_host(["/usr/bin/true", "--flag"], "leg1")
        assert run["command"][0].endswith("true")


# -------------------------------------------------------------------- player


class TestPlayerControl:
    def test_player_starts_headless_with_a_log_file(self, tmp_path):
        exe = tmp_path / "ProbePlayer"
        argv = nbp.player_argv(exe, tmp_path / "player.log")
        assert argv[0] == str(exe)
        assert "-batchmode" in argv and "-nographics" in argv
        assert argv[argv.index("-logFile") + 1] == str(tmp_path / "player.log")

    def test_player_argv_has_no_gui_or_steam_arguments(self, tmp_path):
        argv = nbp.player_argv(tmp_path / "ProbePlayer", tmp_path / "player.log")
        joined = " ".join(argv)
        for banned in ("popupwindow", "-screen", "-steam", "-http-port"):
            assert banned not in joined

    def test_stopping_the_player_only_uses_sigterm(self, monkeypatch):
        recorded = []
        monkeypatch.setattr(nbp.os, "kill", lambda pid, sig: recorded.append((pid, sig)))
        nbp.stop_player(4321)
        assert recorded == [(4321, nbp.signal.SIGTERM)]

    def test_stopping_a_gone_player_is_not_an_error(self, monkeypatch):
        def raise_lookup(pid, sig):
            raise ProcessLookupError

        monkeypatch.setattr(nbp.os, "kill", raise_lookup)
        nbp.stop_player(4321)


class TestLinuxControlLeg:
    def test_linux_build_pull_excludes_loader_and_managed_trees(self, tmp_path):
        command = nbp.linux_build_pull_command(tmp_path / "build", "the-player-host", "~/Steam/steamapps/common/Megabonk")
        assert command[0] == "/usr/bin/rsync"
        joined = " ".join(command)
        assert "--exclude" in joined and "BepInEx" in joined
        assert "the-player-host:" in joined

    def test_remote_identity_command_probes_the_arch_and_files(self):
        command = nbp.remote_host_identity_command("the-player-host", "/opt/megabonk/GameAssembly.so")
        assert command[0] == "/usr/bin/ssh"
        joined = " ".join(command)
        assert "uname" in joined and "file" in joined

    def test_remote_probe_command_reuses_the_same_driver(self):
        command = nbp.linux_remote_command(
            probe_dir="~/task071-probe",
            venv_path="~/task071-probe/.venv/bin/python",
            target="x86_64",
            out_dir="~/task071-probe/out",
            host="the-player-host",
        )
        assert command[0] == "/usr/bin/ssh"
        joined = " ".join(command)
        assert "native_bind_probe.py" in joined
        assert "GameAssembly.so" in joined
        assert "global-metadata.dat" in joined
        assert "--platform linux" in joined
        assert "rm -rf" not in joined and "sudo" not in joined

    def test_remote_command_refuses_a_quoting_probe_dir(self):
        with pytest.raises(nbp.ProbeError):
            nbp.linux_remote_command(
                probe_dir="~/ev; al",
                venv_path="~/.venv/bin/python",
                target="x86_64",
                out_dir="~/out",
                host="the-player-host",
            )

    def test_docker_image_check_names_the_image(self):
        command = nbp.docker_image_check_command("ubuntu:22.04")
        assert command[0] == "/usr/bin/docker"
        assert "ubuntu:22.04" in command


# ------------------------------------------------------------------ dump.cs


DUMP_SAMPLE = """
// Image 1: mscorlib.dll

// Namespace: System
public static class Math
{
    // RVA: 0x123456 Offset: 0x123456 VA: 0x10123456 Slot: 0 Token: 0x06000001
    public static int Abs(int value) { }

    // RVA: 0x123789 Offset: 0x123789 VA: 0x10123789 Slot: 0 Token: 0x06000002
    public static double Abs(double value) { }
}

// Namespace:
public class Program
{
    // RVA: 0x222222 Offset: 0x222222 VA: 0x10222222 Slot: 0 Token: 0x06000100
    public static int Main(string[] args) { }
}

// Namespace: UnityEngine
public static class Mathf
{
    // RVA: 0x333333 Offset: 0x333333 VA: 0x10333333 Slot: 0 Token: 0x06000200
    public static int Abs(int value) { }
}
"""


class TestDumpVerification:
    def test_finds_a_static_int_method_with_its_rva(self):
        rows = nbp.verify_candidates([make_candidate()], DUMP_SAMPLE)
        assert rows[0]["found"] is True
        assert rows[0]["rva"] == "0x123456"

    def test_reports_the_matched_signature(self):
        rows = nbp.verify_candidates([make_candidate()], DUMP_SAMPLE)
        assert "int Abs(int)" in rows[0]["signature"]

    def test_overloads_are_distinguished_by_parameter_types(self):
        double_candidate = make_candidate(ret="double", param_types=("double",), args=("-7.5",), expected="7.5")
        rows = nbp.verify_candidates([double_candidate], DUMP_SAMPLE)
        assert rows[0]["found"] is True
        assert rows[0]["rva"] == "0x123789"

    def test_missing_method_is_reported_not_found(self):
        rows = nbp.verify_candidates([make_candidate(method="Missing")], DUMP_SAMPLE)
        assert rows[0]["found"] is False
        assert rows[0]["rva"] is None

    def test_wrong_parameter_type_does_not_match(self):
        rows = nbp.verify_candidates([make_candidate(param_types=("float",))], DUMP_SAMPLE)
        assert rows[0]["found"] is False

    def test_global_namespace_classes_are_found(self):
        rows = nbp.verify_candidates(
            [make_candidate(namespace="", class_name="Program", method="Main", param_types=("string[]",), args=("",))],
            DUMP_SAMPLE,
        )
        assert rows[0]["found"] is True

    def test_namespace_mismatch_does_not_match(self):
        rows = nbp.verify_candidates([make_candidate(namespace="UnityEngine", class_name="Math")], DUMP_SAMPLE)
        assert rows[0]["found"] is False

    def test_multiple_candidates_are_verified_in_order(self):
        rows = nbp.verify_candidates(
            [
                make_candidate(),
                make_candidate(image="UnityEngine.CoreModule.dll", namespace="UnityEngine", class_name="Mathf"),
            ],
            DUMP_SAMPLE,
        )
        assert [row["found"] for row in rows] == [True, True]


# -------------------------------------------------------------- default ladder


class TestDefaultCandidates:
    def test_ladder_leads_with_pure_static_int_methods(self):
        first = nbp.DEFAULT_CANDIDATES[0]
        assert first.param_types == ("int",)
        assert first.ret == "int"
        assert first.expected == "7"

    def test_ladder_spans_mscorlib_unityengine_and_rewired(self):
        images = {candidate.image for candidate in nbp.DEFAULT_CANDIDATES}
        assert "mscorlib.dll" in images
        assert "UnityEngine.CoreModule.dll" in images
        assert "Rewired_Core.dll" in images

    def test_ladder_entries_agree_with_dump_sample_where_present(self):
        rows = nbp.verify_candidates(nbp.DEFAULT_CANDIDATES[:1], DUMP_SAMPLE)
        assert rows[0]["found"] is True

    def test_ladder_reaches_a_game_authored_static_method(self):
        game = [candidate for candidate in nbp.DEFAULT_CANDIDATES if candidate.image == "Assembly-CSharp.dll"]
        assert game, "the ladder needs a candidate from the game's own assembly"
        assert all(candidate.param_types == () for candidate in game)
        assert all(candidate.expected == "" for candidate in game)
        assert {candidate.ret for candidate in game} <= {"int", "bool", "float"}

    def test_an_empty_expectation_accepts_any_returned_value(self):
        assert nbp.value_matches("int", "42", "") is True
        assert nbp.value_matches("bool", "true", "") is True
        assert nbp.value_matches("bool", "false", "") is True
        assert nbp.value_matches("string", "megabonk", "") is True

    def test_an_empty_got_is_never_a_match_even_without_an_expectation(self):
        assert nbp.value_matches("int", "", "") is False


# ---------------------------------------------------------------- report shape


class TestReport:
    def build(self, **overrides):
        kwargs = dict(
            runs=[
                {"leg": "leg1", "status": "pass", "evidence": {"loader_images": 0}},
                {"leg": "leg2", "status": "pass", "evidence": {"returned": "7"}},
                {"leg": "leg3", "status": "pass", "evidence": {"hook_calls": 3}},
            ],
            platform="macos",
            arches=("x86_64",),
            runtime=Path("/probe/GameAssembly.dylib"),
            host_id="macmini",
            legs=("leg1", "leg2", "leg3"),
            hooks=("il2cpp_runtime_invoke",),
        )
        kwargs.update(overrides)
        return nbp.build_report(**kwargs)

    def test_report_carries_schema_host_and_arch(self):
        report = self.build()
        assert report["schema"] == nbp.SCHEMA
        assert report["host_id"] == "macmini"
        assert report["arches"] == ["x86_64"]
        assert report["platform"] == "macos"

    def test_report_records_leg_status_and_evidence(self):
        report = self.build()
        assert report["overall"] == "pass"
        assert report["legs"]["leg3"]["evidence"]["hook_calls"] == 3

    def test_report_records_the_hook_targets_examined(self):
        assert self.build()["hooks"] == ["il2cpp_runtime_invoke"]

    def test_report_is_json_serialisable_and_redacted(self, tmp_path):
        report = self.build(runtime=Path("/Users/alice/probe/GameAssembly.dylib"))
        text = json.dumps(nbp.redact_report(report))
        assert "alice" not in text
        assert "<home>/probe/GameAssembly.dylib" in text

    def test_report_lists_the_chainloader_conclusion_field(self):
        report = self.build()
        assert "chainloader" in report

    def test_chainloader_conclusion_follows_the_runtime_invoke_hook(self):
        triggered = nbp.chainloader_conclusion(
            {"leg3": {"status": "pass", "evidence": {"hook": "il2cpp_runtime_invoke", "hook_calls": 3}}}
        )
        assert triggered["by_symbol_invoke_available"] is True
        blocked = nbp.chainloader_conclusion(
            {"leg3": {"status": "crash", "evidence": {"hook": "il2cpp_runtime_invoke", "hook_calls": 0}}}
        )
        assert blocked["by_symbol_invoke_available"] is False
        absent = nbp.chainloader_conclusion({"leg3": {"status": "not-run", "evidence": {}}})
        assert absent["by_symbol_invoke_available"] is None

    def test_linux_control_report_keeps_only_the_relevant_legs(self):
        report = self.build(platform="linux", arches=("x86_64",), legs=("leg1", "leg2"))
        assert report["legs"]["leg1"]["status"] == "pass"
        assert "leg3" not in json.dumps(report)


# ------------------------------------------------------------------ main glue


class TestMain:
    def invoke_stub(self, status):
        def fake(argv, leg, log_path=None):
            payload = {"status": status, "reason": "", "evidence": {"returned": "7", "hook_calls": 3}}
            return nbp.run_from_output(leg, subprocess.CompletedProcess(argv, 0, "#JSON# " + json.dumps(payload), ""), argv)

        return fake

    def test_main_writes_summary_json_and_exits_zero(self, tmp_path, monkeypatch, runtime_bundle, capsys):
        monkeypatch.setattr(nbp, "build_host_binary", lambda command: (True, ""))
        monkeypatch.setattr(nbp, "run_host", self.invoke_stub("pass"))
        monkeypatch.setattr(nbp, "host_arch", lambda: "arm64")
        monkeypatch.setattr(nbp, "have_rosetta", lambda: True)
        monkeypatch.setattr(nbp, "host_id", lambda: "testhost")
        monkeypatch.setattr(sys, "platform", "darwin")
        code = nbp.main(["--app", str(runtime_bundle), "--out", str(tmp_path / "out")])
        assert code == 0
        summary = json.loads((tmp_path / "out" / "summary.json").read_text())
        assert summary["overall"] == "pass"
        assert summary["legs"]["leg1"]["status"] == "pass"
        assert "testhost" in json.dumps(summary) or summary["host_id"] == "testhost"

    def test_main_reports_failure_when_a_leg_fails(self, tmp_path, monkeypatch, runtime_bundle):
        monkeypatch.setattr(nbp, "build_host_binary", lambda command: (True, ""))
        monkeypatch.setattr(nbp, "run_host", self.invoke_stub("fail"))
        monkeypatch.setattr(nbp, "host_arch", lambda: "arm64")
        monkeypatch.setattr(nbp, "have_rosetta", lambda: True)
        monkeypatch.setattr(nbp, "host_id", lambda: "testhost")
        monkeypatch.setattr(sys, "platform", "darwin")
        code = nbp.main(["--app", str(runtime_bundle), "--out", str(tmp_path / "out")])
        assert code != 0

    def test_main_refuses_to_run_when_preflight_fails(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(nbp, "have_rosetta", lambda: False)
        monkeypatch.setattr(nbp, "host_arch", lambda: "arm64")
        monkeypatch.setattr(nbp, "host_id", lambda: "testhost")
        monkeypatch.setattr(nbp, "clang_binary", lambda platform: Path("/nonexistent/clang"))
        monkeypatch.setattr(sys, "platform", "darwin")
        (tmp_path / "GameAssembly.so").write_bytes(b"\x7fELF")
        (tmp_path / "global-metadata.dat").write_bytes(b"md")
        code = nbp.main(
            ["--dylib", str(tmp_path / "GameAssembly.so"), "--metadata", str(tmp_path), "--out", str(tmp_path / "out")]
        )
        assert code == 2
        err = capsys.readouterr().err
        assert "clang" in err

    def test_main_limits_the_candidate_ladder(self, tmp_path, monkeypatch, runtime_bundle):
        seen = []

        def fake(argv, leg, log_path=None):
            if leg == "leg2":
                seen.append(argv[argv.index("--invoke-method") + 1])
            return self.invoke_stub("pass")(argv, leg, log_path=log_path)

        monkeypatch.setattr(nbp, "build_host_binary", lambda command: (True, ""))
        monkeypatch.setattr(nbp, "run_host", fake)
        monkeypatch.setattr(nbp, "host_arch", lambda: "arm64")
        monkeypatch.setattr(nbp, "have_rosetta", lambda: True)
        monkeypatch.setattr(nbp, "host_id", lambda: "testhost")
        monkeypatch.setattr(sys, "platform", "darwin")
        nbp.main(["--app", str(runtime_bundle), "--out", str(tmp_path / "out"), "--limit", "1"])
        assert len(seen) == 1

    def test_main_can_run_only_the_legs_asked_for(self, tmp_path, monkeypatch, runtime_bundle):
        legs = []

        def fake(argv, leg, log_path=None):
            legs.append(leg)
            return self.invoke_stub("pass")(argv, leg, log_path=log_path)

        monkeypatch.setattr(nbp, "build_host_binary", lambda command: (True, ""))
        monkeypatch.setattr(nbp, "run_host", fake)
        monkeypatch.setattr(nbp, "host_arch", lambda: "arm64")
        monkeypatch.setattr(nbp, "have_rosetta", lambda: True)
        monkeypatch.setattr(nbp, "host_id", lambda: "testhost")
        monkeypatch.setattr(sys, "platform", "darwin")
        nbp.main(["--app", str(runtime_bundle), "--out", str(tmp_path / "out"), "--legs", "leg1"])
        assert set(legs) == {"leg1"}

    def test_main_never_signals_a_player_with_sigkill(self, tmp_path, monkeypatch, runtime_bundle):
        signals = []
        monkeypatch.setattr(nbp.os, "kill", lambda pid, sig: signals.append(sig))
        monkeypatch.setattr(nbp, "build_host_binary", lambda command: (True, ""))
        monkeypatch.setattr(nbp, "run_host", self.invoke_stub("pass"))
        monkeypatch.setattr(nbp, "host_arch", lambda: "arm64")
        monkeypatch.setattr(nbp, "have_rosetta", lambda: True)
        monkeypatch.setattr(nbp, "host_id", lambda: "testhost")
        monkeypatch.setattr(sys, "platform", "darwin")
        nbp.main(["--app", str(runtime_bundle), "--out", str(tmp_path / "out")])
        assert nbp.signal.SIGKILL not in signals

    def test_linux_target_without_the_probe_tree_is_a_clean_error(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(nbp, "have_docker", lambda: True)
        monkeypatch.setattr(nbp, "host_id", lambda: "testhost")
        monkeypatch.setattr(sys, "platform", "darwin")
        code = nbp.main(["--linux-target", "x86_64", "--linux-host", "the-player-host", "--out", str(tmp_path / "o")])
        assert code == 2
        assert "linux" in capsys.readouterr().err.lower()


# ------------------------------------------------------- thunk shape variants


X86_THUNK_RBP = (
    bytes([0x55, 0x48, 0x89, 0xE5, 0x5D, 0xE9])
    + (0x1000).to_bytes(4, "little")
    + bytes([0x90, 0x90, 0x90, 0x90, 0x00, 0x00, 0x00, 0x00])
)


class TestThunkPrologueVariants:
    """The shipped exports pop rbp, not rax: both forms have to decode."""

    def test_recognises_the_pop_rbp_thunk_variant(self):
        assert nbp.is_thunk_shape(X86_THUNK_RBP) is True

    def test_computes_the_same_delta_for_both_pop_forms(self):
        assert nbp.thunk_impl_delta(X86_THUNK_RBP) == THUNK_IMPL_DELTA

    def test_trampoline_accepts_the_pop_rbp_prologue(self):
        payload = nbp.encode_trampoline(X86_THUNK_RBP[:10], 0x2000)
        assert payload[:5] == bytes([0x55, 0x48, 0x89, 0xE5, 0x5D])
        assert payload[5:] == nbp.encode_absolute_jump(0x2000)

    def test_reports_the_matching_prologue(self):
        assert nbp.thunk_prologue(X86_THUNK_RBP) == bytes([0x55, 0x48, 0x89, 0xE5, 0x5D])
        assert nbp.thunk_prologue(X86_THUNK) == bytes([0x55, 0x48, 0x89, 0xE5, 0x58])
        assert nbp.thunk_prologue(b"\x00" * 16) is None

    def test_both_pop_forms_are_known_prologues(self):
        assert bytes([0x55, 0x48, 0x89, 0xE5, 0x5D]) in nbp.THUNK_PROLOGUES
        assert bytes([0x55, 0x48, 0x89, 0xE5, 0x58]) in nbp.THUNK_PROLOGUES


# ------------------------------------------------------------------ arg types


class TestTypeNames:
    def test_maps_il2cpp_and_microsoft_names_onto_host_names(self):
        assert nbp.type_name("System.Int32") == "int"
        assert nbp.type_name("int") == "int"
        assert nbp.type_name("System.Single") == "float"
        assert nbp.type_name("System.String") == "string"
        assert nbp.type_name("System.Boolean") == "bool"

    def test_unknown_types_keep_their_short_name(self):
        assert nbp.type_name("Tony.Custom.EStat") == "EStat"
        assert nbp.type_name("int[]") == "int[]"


class TestHostArgvInvocation:
    def test_param_types_reach_the_host_for_overload_matching(self):
        candidate = make_candidate(param_types=("int", "string"), args=("-7", "hi"))
        argv = nbp.host_argv(
            Path("/tmp/native_bind_host_macos_x86_64"),
            dylib=Path("/tmp/GameAssembly.dylib"),
            data_dir=None,
            leg="leg2",
            invoke=candidate,
        )
        types = [argv[i + 1] for i, a in enumerate(argv) if a == "--invoke-arg-type"]
        assert types == ["int", "string"]

    def test_invoke_args_are_still_emitted(self):
        argv = nbp.host_argv(
            Path("/tmp/native_bind_host_macos_x86_64"),
            dylib=Path("/tmp/GameAssembly.dylib"),
            data_dir=None,
            leg="leg2",
            invoke=make_candidate(param_types=("int",), args=("-7",)),
        )
        assert argv[argv.index("--invoke-arg") + 1] == "i:-7"


# ---------------------------------------------------------------- dlopen modes


class TestDlopenModes:
    def test_auto_tries_eager_first_then_lazy_variants(self):
        assert nbp.dlopen_mode_ladder("auto") == ["now", "lazy", "lazy_global"]

    def test_an_explicit_mode_runs_only_that_mode(self):
        assert nbp.dlopen_mode_ladder("lazy") == ["lazy"]

    def test_an_unknown_mode_is_refused(self):
        with pytest.raises(nbp.ProbeError):
            nbp.dlopen_mode_ladder("whatever")

    def test_preloads_reach_the_host_in_order(self):
        argv = nbp.preload_argv([Path("/opt/Megabonk/lib/libunity.so"), Path("/opt/x/lib.so")])
        assert argv == ["--preload", "/opt/Megabonk/lib/libunity.so", "--preload", "/opt/x/lib.so"]

    def test_no_preloads_adds_nothing(self):
        assert nbp.preload_argv([]) == []

    def test_host_argv_carries_the_mode_and_preloads(self):
        argv = nbp.host_argv(
            Path("/tmp/native_bind_host_linux_x86_64"),
            dylib=Path("/tmp/GameAssembly.so"),
            data_dir=None,
            leg="leg1",
            dlopen_mode="lazy",
            preloads=[Path("/opt/lib/libunity.so")],
        )
        assert argv[argv.index("--dlopen-mode") + 1] == "lazy"
        assert argv[argv.index("--preload") + 1] == "/opt/lib/libunity.so"


# ------------------------------------------------------------- linux control


class TestLinuxControlLegSetup:
    def test_sync_copies_the_driver_and_host_source_to_the_player(self):
        command = nbp.linux_probe_sync_command(Path("/repo/scripts"), "the-player-host", "~/task071-probe")
        assert command[0] == "/usr/bin/rsync"
        joined = " ".join(command)
        assert "/repo/scripts/" in joined
        assert "the-player-host:~/task071-probe/scripts/" in joined
        assert "--exclude" in joined and "__pycache__" in joined

    def test_sync_refuses_an_unsafe_probe_dir(self):
        with pytest.raises(nbp.ProbeError):
            nbp.linux_probe_sync_command(Path("/repo/scripts"), "the-player-host", "~/a; rm")

    def test_remote_command_can_name_the_interpreter(self):
        command = nbp.linux_remote_command(
            probe_dir="~/task071-probe",
            venv_path="python3",
            target="x86_64",
            out_dir="~/task071-probe/out",
            host="the-player-host",
        )
        joined = " ".join(command)
        assert "python3 ~/task071-probe/scripts/native_bind_probe.py" in joined

    def test_remote_command_still_refuses_destructive_interpreters(self):
        with pytest.raises(nbp.ProbeError):
            nbp.linux_remote_command(
                probe_dir="~/task071-probe",
                venv_path="python3; rm -rf ~",
                target="x86_64",
                out_dir="~/out",
                host="the-player-host",
            )


# ---------------------------------------------------------- remote-only runs


class TestRemoteOnlyControl:
    def test_local_scores_are_kept_when_the_local_run_ran(self):
        assert nbp.combine_overall("pass", {"status": "fail"}, remote_only=False) == "pass"

    def test_a_remote_only_run_is_scored_on_the_control_leg(self):
        assert nbp.combine_overall("not-run", {"status": "pass"}, remote_only=True) == "pass"
        assert nbp.combine_overall("not-run", {"status": "fail"}, remote_only=True) == "fail"

    def test_a_remote_only_run_without_a_control_result_is_not_a_pass(self):
        assert nbp.combine_overall("not-run", None, remote_only=True) == "not-run"

    def test_prepare_dir_makes_the_probe_directory_first(self):
        command = nbp.linux_prepare_dir_command("the-player-host", "~/task071-probe")
        assert command[0] == "/usr/bin/ssh"
        assert command[1] == "the-player-host"
        assert command[2].startswith("mkdir -p")
        assert "~/task071-probe" in command[2]

    def test_prepare_dir_refuses_an_unsafe_probe_dir(self):
        with pytest.raises(nbp.ProbeError):
            nbp.linux_prepare_dir_command("the-player-host", "~/a; rm")

    def test_the_remote_leg_can_be_narrowed_to_game_assemblies(self):
        command = nbp.linux_remote_command(
            probe_dir="~/task071-probe",
            venv_path="python3",
            target="~/games/Megabonk",
            out_dir="~/task071-probe/out",
            host="the-player-host",
            only=["Rewired", "UnityEngine"],
        )
        assert "--only Rewired --only UnityEngine" in command[2]

    def test_the_remote_leg_without_a_filter_asks_for_the_whole_ladder(self):
        command = nbp.linux_remote_command(
            probe_dir="~/task071-probe",
            venv_path="python3",
            target="~/games/Megabonk",
            out_dir="~/task071-probe/out",
            host="the-player-host",
        )
        assert "--only" not in command[2]

    def test_an_unsafe_filter_is_refused(self):
        with pytest.raises(nbp.ProbeError):
            nbp.linux_remote_command(
                probe_dir="~/task071-probe",
                venv_path="python3",
                target="~/games/Megabonk",
                out_dir="~/task071-probe/out",
                host="the-player-host",
                only=["Rewired; rm -rf /"],
            )

    def test_the_remote_report_contributes_its_ladder_not_just_the_winner(self):
        payload = json.dumps(
            {
                "overall": "pass",
                "legs": {"leg1": {"status": "pass"}, "leg2": {"status": "pass"}},
                "attempts": [
                    {
                        "arch": "x86_64",
                        "leg": "leg2",
                        "status": "pass",
                        "candidate": "Assembly-CSharp.dll!ExplorerUtility::IsLinux()",
                    },
                    {
                        "arch": "x86_64",
                        "leg": "leg2",
                        "status": "fail",
                        "candidate": "Rewired_Core.dll!Rewired.Utils.MathTools::Abs(int)",
                    },
                ],
            }
        )
        result = nbp.linux_result_from_remote(0, f"noise\n{payload}\n", "")
        assert result["status"] == "pass"
        assert [row["status"] for row in result["attempts"]] == ["pass", "fail"]
        assert result["legs"]["leg1"]["status"] == "pass"

    def test_a_remote_report_redacts_home_paths(self):
        payload = json.dumps(
            {
                "overall": "fail",
                "legs": {"leg1": {"status": "fail", "evidence": {"runtime_path": "/home/someone/Megabonk/GameAssembly.so"}}},
                "attempts": [],
            }
        )
        result = nbp.linux_result_from_remote(1, payload, "boom at /Users/someone/x")
        assert "<home>" in json.dumps(result)
        assert "someone" not in json.dumps(result)

    def test_a_remote_run_with_no_json_is_a_crash(self):
        result = nbp.linux_result_from_remote(1, "", "ssh: connect to host failed")
        assert result["status"] == "crash"
        assert result["signature"] == "exit=1"
        assert "ssh" in result["stderr_tail"]

    def test_the_emitted_line_carries_the_ladder_for_a_remote_caller(self):
        report = self.build_report()
        payload = nbp.emit_payload(report, Path("/tmp/summary.json"))
        assert payload["attempts"][0]["candidate"] == "mscorlib.dll!System.Math::Abs(int)"
        assert payload["out"] == "/tmp/summary.json"
        assert "runs" not in payload

    def build_report(self):
        return {
            "overall": "pass",
            "legs": {"leg1": {"status": "pass"}},
            "attempts": [{"arch": "x86_64", "leg": "leg2", "status": "pass", "candidate": "mscorlib.dll!System.Math::Abs(int)"}],
            "runs": [{"leg": "leg1"}],
        }


# ------------------------------------------------------------------ ladder rows


class TestAttemptRows:
    def test_every_attempt_is_visible_not_just_the_winning_one(self):
        runs = [
            {"arch": "x86_64", "leg": "leg2", "status": "fail", "candidate": "a.dll!A::B(int)", "returncode": 1},
            {"arch": "x86_64", "leg": "leg2", "status": "pass", "candidate": "b.dll!C::D(int)", "returncode": 0},
        ]
        rows = nbp.attempt_rows(runs)
        assert [(row["candidate"], row["status"]) for row in rows] == [
            ("a.dll!A::B(int)", "fail"),
            ("b.dll!C::D(int)", "pass"),
        ]

    def test_a_crash_keeps_its_signature(self):
        rows = nbp.attempt_rows(
            [{"arch": "x86_64", "leg": "leg3", "status": "crash", "hook": "il2cpp_runtime_invoke", "signature": "signal=SIGBUS"}]
        )
        assert rows[0]["signature"] == "signal=SIGBUS"
        assert rows[0]["hook"] == "il2cpp_runtime_invoke"

    def test_rows_carry_no_raw_evidence(self):
        rows = nbp.attempt_rows(
            [{"arch": "x86_64", "leg": "leg1", "status": "pass", "evidence": {"runtime_path": "/Users/x/App/GameAssembly.dylib"}}]
        )
        assert "evidence" not in rows[0]

    def test_report_carries_the_ladder(self):
        report = nbp.build_report(
            [
                {
                    "arch": "x86_64",
                    "leg": "leg2",
                    "status": "pass",
                    "candidate": "mscorlib.dll!System.Math::Abs(int)",
                    "evidence": {},
                }
            ],
            platform="macos",
            arches=["x86_64"],
            runtime=Path("/tmp/GameAssembly.dylib"),
            host_id="darwin-x86_64",
            legs=("leg1", "leg2", "leg3"),
            hooks=(),
            data_dir=None,
            candidates=[],
        )
        assert report["attempts"][0]["candidate"] == "mscorlib.dll!System.Math::Abs(int)"


class TestCandidateFilter:
    def test_only_selects_by_substring_of_the_label(self):
        rows = nbp.select_candidates(list(nbp.DEFAULT_CANDIDATES), ["Rewired"])
        assert [row.method for row in rows] == ["Abs"]
        assert rows[0].image == "Rewired_Core.dll"

    def test_only_accepts_several_patterns(self):
        rows = nbp.select_candidates(list(nbp.DEFAULT_CANDIDATES), ["Rewired", "UnityEngine"])
        assert [row.image for row in rows] == ["UnityEngine.CoreModule.dll", "Rewired_Core.dll"]

    def test_only_with_no_match_selects_nothing(self):
        assert nbp.select_candidates(list(nbp.DEFAULT_CANDIDATES), ["nope"]) == []

    def test_no_patterns_keeps_the_whole_ladder(self):
        assert nbp.select_candidates(list(nbp.DEFAULT_CANDIDATES), []) == list(nbp.DEFAULT_CANDIDATES)
