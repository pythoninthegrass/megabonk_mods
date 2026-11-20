"""
Self-test for scripts/shader_metal_pass.py: chunk directory parsing, stage inference,
diagnostic classification, command builders and the scored summary.
"""

import json
import pytest
import re
import shader_metal_pass as smp


def result(pid: str, stage: str, *, glslang="pass", spirv="pass", metal="pass", kind=None, fixes=None) -> dict:
    def step(status):
        if status == "pass":
            return {"status": "pass", "kind": None, "diagnostic": ""}
        if status == "skip":
            return {"status": "skip", "kind": None, "diagnostic": ""}
        return {"status": "fail", "kind": kind or "other", "diagnostic": f"{kind or 'other'} boom"}

    return {
        "id": pid,
        "shader": f"Shaders/{pid}",
        "unit": 0,
        "stage": stage,
        "version": "150",
        "program_type": "GLCore35Vertex",
        "platform": 15,
        "source_bytes": 100,
        "keywords": ["FOG_LINEAR"],
        "fixes": fixes or {},
        "glslang": step(glslang),
        "spirv": step(spirv),
        "metal": step(metal),
    }


@pytest.mark.parametrize(
    ("program_type", "expected"),
    [
        ("GLCore35Vertex", "vert"),
        ("GLES31Fragment", "frag"),
        ("MetalPixel", "frag"),
        ("DX11GeometrySM50", "geom"),
        ("VulkanCompute", "comp"),
        ("MetalHull", "hull"),
        ("MetalDomain", "domain"),
    ],
)
def test_stage_for_program_reads_the_stage_from_the_type_name(program_type: str, expected: str) -> None:
    assert smp.stage_for_program(program_type, "") == expected


def test_stage_for_program_falls_back_to_the_source_when_the_name_is_opaque() -> None:
    assert smp.stage_for_program("GLCore41", "void main() { gl_Position = vec4(0.0); }") == "vert"
    assert smp.stage_for_program("GLCore41", "void main() { gl_FragColor = vec4(1.0); }") == "frag"
    assert smp.stage_for_program("GLCore41", "layout(local_size_x = 8) in; void main() {}") == "comp"
    assert smp.stage_for_program("GLCore41", "void main() {}") == "other"


def test_stage_for_program_prefers_the_type_name_over_the_source() -> None:
    assert smp.stage_for_program("GLCore35Fragment", "void main() { gl_Position = vec4(0.0); }") == "frag"


@pytest.mark.parametrize(
    ("diagnostic", "expected"),
    [
        ("ERROR: 0:1: '#version' : invalid value: 110", "version"),
        ("WARNING: 0:2: '#extension' : extension 'GL_OES_FMA' not supported", "extension"),
        ("ERROR: 1:9: 'texture2D' : no matching overloaded function found", "texture-sampling"),
        ("ERROR: 1:9: 'textureCube' : no matching overloaded function found", "texture-sampling"),
        ("ERROR: 1:3: 'gl_FragColor' : undeclared identifier", "fixed-function-output"),
        ("ERROR: 1:3: 'gl_TexCoord[0]' : undeclared identifier", "fixed-function-output"),
        ("ERROR: 1:5: 'unity_ObjectToWorld' : undeclared identifier", "undeclared-identifier"),
        ("ERROR: 1:19: 'non-opaque uniforms outside a block' : not allowed when using GLSL for Vulkan", "loose-uniform"),
        (
            "ERROR: 1:19: 'hlslcc_mtx4x4unity_ObjectToWorld' : non-opaque uniform variables need a layout(location=L)",
            "loose-uniform",
        ),
        ("ERROR: 1:2: 'mediump' : syntax error: precision", "precision"),
        ("ERROR: Linking fragment stage: Missing entry point: Each stage requires one entry point", "entry-point"),
        ("ERROR: 1:12: '}' : syntax error, unexpected RIGHT_BRACE", "syntax"),
        ("segmentation fault", "other"),
    ],
)
def test_classify_glslang_groups_diagnostics(diagnostic: str, expected: str) -> None:
    assert smp.classify("glslang", diagnostic) == expected


@pytest.mark.parametrize(
    ("diagnostic", "expected"),
    [
        ("SPIRV-Cross threw an exception: Unhandled builtin", "threw-exception"),
        ("ERROR: 0: Unsupported decoration 44", "unsupported-decoration"),
        ("ERROR: 0: unimplemented opcode OpGroupNonSubgroupBallot", "unimplemented-opcode"),
        ("ERROR: 3: Unsupported image operand", "unsupported-operand"),
        ("", "no-diagnostic"),
    ],
)
def test_classify_spirv_groups_diagnostics(diagnostic: str, expected: str) -> None:
    assert smp.classify("spirv", diagnostic) == expected


@pytest.mark.parametrize(
    ("diagnostic", "expected"),
    [
        ("error: use of undeclared identifier 'gl_FragColor'", "unsupported-builtin"),
        ("error: unknown type name 'sampler2D'", "unknown-type"),
        ("error: implicit conversion of non-scalar type", "implicit-conversion"),
        ("error: cannot convert 'int3' to 'float3' in initialization", "implicit-conversion"),
        ("error: too many resources requested for this device", "resource-limit"),
        ("error: 'threadgroup' variables must be in address space", "address-space"),
        ("error: no matching function for call to 'mix'", "function-not-found"),
        ("error: use of undeclared identifier 'MK_Toontexture'", "undeclared-identifier"),
        ("error: something unexpected", "other"),
    ],
)
def test_classify_metal_groups_diagnostics(diagnostic: str, expected: str) -> None:
    assert smp.classify("metal", diagnostic) == expected


def test_classify_glslang_precedence_puts_builtin_before_undeclared() -> None:
    assert smp.classify("glslang", "ERROR: 1:3: 'gl_FragColor' : undeclared identifier") == "fixed-function-output"
    assert smp.classify("glslang", "ERROR: 1:3: 'texture2D' : undeclared identifier") == "texture-sampling"


def test_glslang_command_defaults_to_opengl_semantics_that_tolerate_loose_uniforms() -> None:
    argv = smp.glslang_command("glslangValidator", source="a.vert", target="a.spv", stage="vert")

    assert argv[0] == "glslangValidator"
    assert "-V" not in argv
    assert argv[argv.index("--target-env") + 1] == "opengl"
    assert argv[argv.index("-S") + 1] == "vert"
    assert argv[argv.index("-o") + 1] == "a.spv"
    assert "--auto-map-bindings" in argv and "--auto-map-locations" in argv
    assert argv[-1] == "a.vert"


def test_glslang_command_switches_to_vulkan_semantics_when_asked() -> None:
    argv = smp.glslang_command("glslangValidator", source="a.frag", target="a.spv", stage="frag", target_env="vulkan1.0")

    assert "-V" in argv
    assert argv[argv.index("--target-env") + 1] == "vulkan1.0"


def test_spirv_command_writes_msl_with_vulkan_semantics() -> None:
    argv = smp.spirv_command("spirv-cross", source="a.spv", target="a.metal")

    assert argv[:2] == ["spirv-cross", "a.spv"]
    assert argv[-2:] == ["--output", "a.metal"]
    assert "--msl" in argv and "--vulkan-semantics" in argv


def test_spirv_command_can_target_an_msl_version() -> None:
    argv = smp.spirv_command("spirv-cross", source="a.spv", target="a.metal", msl_version="20100")

    assert argv[argv.index("--msl-version") + 1] == "20100"
    assert smp.spirv_command("spirv-cross", source="a.spv", target="a.metal", msl_version=None).count("--msl-version") == 0


def test_compact_msl_bindings_renumbers_sparse_bindings_densely() -> None:
    text = (
        "vertex out main0(main0_in in [[stage_in]], constant A& a [[buffer(0)]],"
        " constant B& b [[buffer(16)]], constant C& c [[buffer(39)]],"
        " constant D& d [[buffer(29)]], texture2d<float> t [[texture(7)]],"
        " sampler s [[sampler(3)]])"
    )

    compacted, used = smp.compact_msl_bindings(text)

    assert used == 4
    assert "[[buffer(0)]]" in compacted and "[[buffer(1)]]" in compacted
    assert "[[buffer(2)]]" in compacted and "[[buffer(3)]]" in compacted
    assert not re.search(r"\[\[buffer\((1[6-9]|[2-9]\d)\)\]\]", compacted)
    assert "[[texture(0)]]" in compacted and "[[sampler(0)]]" in compacted
    assert "[[stage_in]]" in compacted


def test_compact_msl_bindings_is_the_identity_for_dense_bindings() -> None:
    text = "fragment out main0(constant A& a [[buffer(0)]], constant B& b [[buffer(1)]], texture2d<float> t [[texture(0)]])"

    assert smp.compact_msl_bindings(text) == (text, 2)


def test_suggested_extensions_reads_glslangs_candidates() -> None:
    output = (
        "ERROR: 0004-vert-glsl330.vert:49: 'gl_Layer' : required extension not requested: Possible extensions include:\n"
        "GL_ARB_shader_viewport_layer_array\n"
        "GL_NV_viewport_array2\n"
        "ERROR: 2 compilation errors.  No code generated."
    )

    assert smp.suggested_extensions(output) == ["GL_ARB_shader_viewport_layer_array", "GL_NV_viewport_array2"]
    assert smp.suggested_extensions("ERROR: something else") == []


def test_request_extensions_inserts_requires_after_the_version_line() -> None:
    source = b"#version 330 core\nprecision highp float;\nvoid main() {}\n"

    patched = smp.request_extensions(source, ["GL_EXT_geometry_shader4"]).decode()

    assert patched.splitlines()[:3] == [
        "#version 330 core",
        "#extension GL_EXT_geometry_shader4 : require",
        "precision highp float;",
    ]
    assert smp.request_extensions(source, []) == source


def test_classify_names_the_two_mechanical_failure_shapes() -> None:
    assert (
        smp.classify("metal", "error: 'buffer' attribute parameter is out of bounds: must be between 0 and 30")
        == "resource-limit"
    )
    assert (
        smp.classify("glslang", "'gl_Layer' : required extension not requested: Possible extensions include:")
        == "missing-extension"
    )
    assert (
        smp.classify("spirv", "SPIRV-Cross threw an exception: Multisampled array textures are supported from 2.1.")
        == "msl-version-too-low"
    )


def test_metal_command_compiles_for_macos_without_linking() -> None:
    argv = smp.metal_command("metal", source="a.metal", target="a.air")

    assert argv[:3] == ["xcrun", "-sdk", "macosx"]
    assert argv[3:] == ["metal", "-c", "a.metal", "-o", "a.air"]


def test_program_id_is_stable_and_distinguishes_stage_version_and_unit() -> None:
    first = smp.program_id("Custom/Toon", "vert", "150", 3)
    assert first == smp.program_id("Custom/Toon", "vert", "150", 3)
    assert first != smp.program_id("Custom/Toon", "frag", "150", 3)
    assert first != smp.program_id("Custom/Toon", "vert", "330", 3)
    assert first != smp.program_id("Other/Toon", "vert", "150", 3)
    assert first != smp.program_id("Custom/Toon", "vert", "150", 4)


def test_program_id_survives_unfriendly_shader_names() -> None:
    pid = smp.program_id("Custom/Some Shader (#1) [x]", "frag", "330", 0)

    assert "/" not in pid and " " not in pid and "#" not in pid and "[" not in pid and "]" not in pid
    assert pid.startswith("Custom_Some_Shader")


def test_program_id_falls_back_when_a_name_is_unusable() -> None:
    assert smp.slug("///") == "unnamed"


GUARD_CHUNK = (
    b"\x02\x00\x00\x00"
    + b"#ifdef VERTEX\n#version 150\n#extension GL_ARB_explicit_attrib_location : require\n"
    + b"#ifdef GL_ARB_shader_bit_encoding\n#extension GL_ARB_shader_bit_encoding : enable\n#endif\n"
    + b"out vec4 vP;\nvoid main()\n{\n    vP = vec4(0.0);\n    return;\n}\n\n#endif\n"
    + b"\x00\x00\x00\x00garbage\x00\x00"
    + b"#ifdef FRAGMENT\n#version 330\nlayout(location = 0) out vec4 SV_Target0;\nvoid main()\n{\n    SV_Target0 = vec4(1.0);\n    return;\n}\n\n#endif\n"
)


def test_split_glsl_units_finds_one_program_per_stage_guard() -> None:
    units = smp.split_glsl_units(GUARD_CHUNK)

    assert [(unit["stage"], unit["version"]) for unit in units] == [("vert", "150"), ("frag", "330")]
    assert [unit["unit"] for unit in units] == [0, 1]


def test_split_glsl_units_strips_the_stage_guard_and_its_closing_endif() -> None:
    vertex = smp.split_glsl_units(GUARD_CHUNK)[0]["source"].decode()

    assert vertex.startswith("#version 150")
    assert "#ifdef VERTEX" not in vertex
    assert vertex.count("#endif") == vertex.count("#ifdef")
    assert "vP = vec4(0.0)" in vertex
    assert "garbage" not in vertex


def test_split_glsl_units_keeps_nested_guards_and_the_next_unit_is_clean() -> None:
    fragment = smp.split_glsl_units(GUARD_CHUNK)[1]["source"].decode()

    assert fragment.startswith("#version 330")
    assert "SV_Target0" in fragment
    assert "GL_ARB_shader_bit_encoding" not in fragment


def test_split_glsl_units_skips_guarded_blocks_without_a_main() -> None:
    chunk = b"#ifdef VERTEX\n#version 150\nuniform vec4 u_tint;\n#endif\n" + GUARD_CHUNK[4:]

    assert [unit["stage"] for unit in smp.split_glsl_units(chunk)] == ["vert", "frag"]


def test_normalize_glsl_raises_the_version_and_records_extensions() -> None:
    source = b"#version 150\n#extension GL_ARB_foo : require\nvoid main() {}\n"

    normalized, notes = smp.normalize_glsl(source)

    assert normalized.decode().splitlines()[0] == "#version 450 core"
    assert "#extension" not in normalized.decode()
    assert notes == {"version": "150", "version_bumped": True, "extensions_dropped": ["GL_ARB_foo"]}


def test_normalize_glsl_leaves_a_450_source_untouched_apart_from_extensions() -> None:
    normalized, notes = smp.normalize_glsl(b"#version 450 core\nvoid main() {}\n")

    assert normalized.decode() == "#version 450 core\nvoid main() {}\n"
    assert notes["version_bumped"] is False
    assert notes["version"] == "450"


def test_normalize_glsl_keeps_nested_guard_lines() -> None:
    normalized, _notes = smp.normalize_glsl(b"#version 330\n#ifdef FOG\nvec4 f;\n#endif\nvoid main() {}\n")

    assert "#ifdef FOG" in normalized.decode() and "#endif" in normalized.decode()


def test_source_key_changes_only_with_the_source() -> None:
    assert smp.source_key(b"void main(){}") == smp.source_key(b"void main(){}")
    assert smp.source_key(b"void main(){}") != smp.source_key(b"void main(){;}")


def test_write_and_read_manifest_round_trip(tmp_path) -> None:
    programs = [
        {
            "id": "a",
            "shader": "Custom/A",
            "unit": 0,
            "stage": "vert",
            "version": "150",
            "platform": 15,
            "source_bytes": 12,
            "source_key": "deadbeef",
            "preprocess": {"version": "150", "version_bumped": True, "extensions_dropped": ["GL_ARB_foo"]},
            "source_path": "norm/custom_a/0000-vert-glsl150.vert",
        }
    ]
    path = tmp_path / "manifest.json"
    smp.write_manifest(programs, path)

    assert smp.read_manifest(path) == programs


def test_summarize_counts_the_mechanical_fixes_it_applied() -> None:
    results = [
        result("a", "vert", fixes={"extensions_requested": ["GL_EXT_geometry_shader4"]}),
        result("b", "frag", fixes={"bindings_renumbered": 23}),
        result("c", "frag", fixes={"bindings_renumbered": 9, "extensions_requested": ["GL_ARB_a"]}),
    ]

    assert smp.summarize(results)["fixes"] == {"extensions_requested": 2, "bindings_renumbered": 2}


def test_summarize_scores_every_stage_and_groups_failures() -> None:
    results = [
        result("ok-frag", "frag"),
        result("bad-glslang", "frag", glslang="fail", kind="texture-sampling"),
        result("bad-metal", "vert", metal="fail", kind="implicit-conversion"),
        result("skipped", "comp", glslang="skip", spirv="skip", metal="skip"),
    ]

    summary = smp.summarize(results, tools={"glslang": "11"}, build_path="/tmp/build")

    assert summary["totals"] == {"programs": 4, "shaders": 4, "source_bytes": 400}
    assert summary["stages"]["glslang"] == {"pass": 2, "fail": 1, "skip": 1}
    assert summary["stages"]["metal"] == {"pass": 2, "fail": 1, "skip": 1}
    assert summary["by_shader_stage"]["frag"] == {"programs": 2, "glslang_pass": 1, "spirv_pass": 2, "metal_pass": 2}
    assert summary["failure_kinds"] == {"glslang": {"texture-sampling": 1}, "spirv": {}, "metal": {"implicit-conversion": 1}}
    assert summary["end_to_end_pass"] == 1
    assert summary["hand_edits"]["count"] == 3
    assert summary["hand_edits"]["by_kind"] == {"texture-sampling": 1, "implicit-conversion": 1, "skipped": 1}
    assert summary["hand_edits"]["by_stage"] == {"frag": 1, "vert": 1, "comp": 1}
    assert summary["hand_edits"]["worst_shaders"] == [
        {"texture-sampling": 1, "shader": "Shaders/bad-glslang", "hand_edits": 1},
        {"implicit-conversion": 1, "shader": "Shaders/bad-metal", "hand_edits": 1},
        {"skipped": 1, "shader": "Shaders/skipped", "hand_edits": 1},
    ]
    assert summary["by_glsl_version"] == {"150": 4}
    assert summary["by_platform"] == {"15": 4}
    assert summary["preprocess"] == {"version_bumped": 0, "extensions_dropped": 0, "programs_normalized": 0}
    assert summary["tools"] == {"glslang": "11"}
    assert summary["build_path"] == "/tmp/build"


def test_summarize_counts_the_preprocess_rewrites_it_was_given() -> None:
    results = [result("a", "vert"), result("b", "frag")]
    results[0]["preprocess"] = {"version": "150", "version_bumped": True, "extensions_dropped": ["GL_ARB_foo", "GL_ARB_bar"]}
    results[1]["preprocess"] = {"version": "330", "version_bumped": True, "extensions_dropped": []}

    assert smp.summarize(results)["preprocess"] == {"version_bumped": 2, "extensions_dropped": 2, "programs_normalized": 2}


def test_summarize_sorts_failure_kinds_by_count_then_name() -> None:
    results = [
        result("a", "frag", glslang="fail", kind="texture-sampling"),
        result("b", "frag", glslang="fail", kind="texture-sampling"),
        result("c", "frag", glslang="fail", kind="version"),
    ]

    kinds = smp.summarize(results)["failure_kinds"]["glslang"]

    assert list(kinds) == ["texture-sampling", "version"]


def test_verdict_classifies_scriptable_translation() -> None:
    assert smp.verdict(passed=96, total=100)["classification"] == "scriptable"


def test_verdict_classifies_a_hand_edit_tail() -> None:
    verdict = smp.verdict(passed=70, total=100)

    assert verdict["classification"] == "scriptable-with-hand-edits"
    assert verdict["rate"] == 0.7


def test_verdict_classifies_a_route_c_flip() -> None:
    assert smp.verdict(passed=12, total=100)["classification"] == "hand-or-route-c"


def test_verdict_reports_no_data_without_programs() -> None:
    verdict = smp.verdict(passed=0, total=0)

    assert verdict["classification"] == "no-data"
    assert verdict["rate"] == 0.0


def test_verdict_carries_the_thresholds_it_was_scored_against() -> None:
    assert smp.verdict(passed=1, total=1)["thresholds"] == {"scriptable": 0.95, "hand_edits": 0.6}


def test_load_cache_skips_programs_already_scored(tmp_path) -> None:
    cache = tmp_path / "cache.jsonl"
    cache.write_text(
        json.dumps({"id": "a", "source_key": "k1"}) + "\n" + json.dumps({"id": "b", "source_key": "k2", "error": "boom"}) + "\n"
    )

    done = smp.load_cache(cache)

    assert done == {"a": "k1"}


def test_read_manifest_tolerates_a_missing_file(tmp_path) -> None:
    assert smp.read_manifest(tmp_path / "nope.json") == []
