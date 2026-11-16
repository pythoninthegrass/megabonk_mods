#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = ["unitypy>=1.24.0"]
# ///

"""
Scores the GLSL-to-Metal translation failure rate of a native Linux Megabonk build.

The Linux player ships every baked shader as a GLSL source chunk (platform 15) whose 7,305
programs are `#ifdef <STAGE>` guarded GLSL 150/330 units, plus a per-program metadata
container with no SPIR-V in it. A macOS player takes Metal only, so route B needs every
program driven through the chain: glslangValidator to SPIR-V, spirv-cross to MSL, then the
macOS Metal compiler. This pass runs them all and reports pass/fail per stage with failure
reasons grouped, which is the evidence for whether that translation is scriptable.

Usage:
    uv run --script scripts/shader_metal_pass.py <linux-build> [options]

Args:
    linux-build: The extracted native Linux build, or its Megabonk_Data directory.
        Pull it with `task re:shaders-pull` before the first run.

Note:
    GLSL is raised to `#version 450 core` and `#extension` lines are dropped before glslang;
    the shipped source is scored verbatim with --no-normalize. glslang runs with GL semantics,
    since the shipped programs declare their uniforms loosely and Vulkan semantics rejects
    almost all of them. Three mechanical fixes are on by default because each undoes a toolchain
    choice rather than editing shipped source: glslang's own suggested `#extension` lines,
    --msl-version 20100, and dense renumbering of the bindings --auto-map-bindings leaves
    sparse. All three are counted in the summary's `fixes` and switchable off. Needs
    glslangValidator, spirv-cross and the macOS Metal toolchain. Artifacts and summary.json land
    under .tools/shaders-metal/, and --resume reuses recorded results so a re-run after a depot
    push only pays for changed programs.
"""

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from functools import partial
from pathlib import Path

SCHEMA = 1
STAGES = ("glslang", "spirv", "metal")
SKIP_NAMES = {"app.info", "boot.config", "RuntimeInitializeOnLoads.json", "ScriptingAssemblies.json"}
TARGET_VERSION = "450 core"
TOOL_TIMEOUT_SECONDS = 120
STAGE_SUFFIX = {"vert": ".vert", "frag": ".frag", "geom": ".geom", "comp": ".comp", "hull": ".tesc", "domain": ".tese", "other": ".glsl"}
STAGE_FLAGS = {"vert": "vert", "frag": "frag", "geom": "geom", "comp": "comp", "hull": "tesc", "domain": "tese", "other": "vert"}
GUARD_STAGES = {
    "VERTEX": "vert",
    "FRAGMENT": "frag",
    "GEOMETRY": "geom",
    "COMPUTE": "comp",
    "HULL": "hull",
    "DOMAIN": "domain",
    "MESH": "mesh",
}
GUARD = re.compile(r"#ifdef\s+(" + "|".join(GUARD_STAGES) + r")\b")
VERSION = re.compile(r"^\s*#version\s+(\d+)(\s+\w+)?")
EXTENSION = re.compile(r"^\s*#extension\s+([A-Za-z0-9_]+)")
IF_DIRECTIVE = re.compile(r"^\s*#(if|ifdef|ifndef)\b")
ENDIF_DIRECTIVE = re.compile(r"^\s*#endif\b")
SOURCE_STAGE_PROBES = (
    ("comp", ("local_size_x", "gl_LocalInvocationID", "gl_WorkGroupID", "gl_NumWorkGroups")),
    ("vert", ("gl_Position", "gl_VertexID", "gl_InstanceID", "gl_MultiTexCoord")),
    ("frag", ("gl_FragColor", "gl_FragData", "gl_FragCoord", "gl_FragDepth", "discard")),
    ("geom", ("gl_PositionIn", "EmitVertex", "EndPrimitive")),
)

RULES: dict[str, tuple[tuple[str, re.Pattern[str]], ...]] = {
    "glslang": (
        ("missing-extension", re.compile(r"required extension not requested", re.I)),
        ("version", re.compile(r"#version|Version unsupported|version .* not supported", re.I)),
        ("extension", re.compile(r"#extension|extension .*not supported|unsupported extension", re.I)),
        ("texture-sampling", re.compile(r"\b(texture[123]D\w*|textureCube\w*|shadow2D\w*|sampler[12]D\w*)\b", re.I)),
        ("fixed-function-output", re.compile(r"\bgl_(FragColor|FragData|TexCoord|Vertex|Normal|FogFragCoord|ClipVertex|SecondaryColor)\b", re.I)),
        ("entry-point", re.compile(r"entry point", re.I)),
        ("precision", re.compile(r"precision", re.I)),
        ("loose-uniform", re.compile(r"non-opaque uniform", re.I)),
        ("interface-block", re.compile(r"uniform block|interface block|buffer block|layout\(binding", re.I)),
        ("undeclared-identifier", re.compile(r"undeclared identifier|not declared", re.I)),
        ("syntax", re.compile(r"syntax error|unexpected", re.I)),
        ("other", re.compile(r".")),
    ),
    "spirv": (
        ("unsupported-decoration", re.compile(r"unsupported decoration", re.I)),
        ("unsupported-operand", re.compile(r"unsupported .*operand|operand .*unsupported", re.I)),
        ("unimplemented-opcode", re.compile(r"unimplemented|unhandled opcode|unhandled instruction", re.I)),
        ("msl-version-too-low", re.compile(r"supported from \d", re.I)),
        ("threw-exception", re.compile(r"threw an exception|^ERROR:", re.I | re.M)),
        ("other", re.compile(r".")),
    ),
    "metal": (
        ("unsupported-builtin", re.compile(r"'gl_[A-Za-z]", re.I)),
        ("unknown-type", re.compile(r"unknown type name|unknown type", re.I)),
        ("implicit-conversion", re.compile(r"implicit conversion|cannot convert|no viable conversion", re.I)),
        ("resource-limit", re.compile(r"too many|exceeds the maximum|resource limit|attribute parameter is out of bounds", re.I)),
        ("address-space", re.compile(r"address space", re.I)),
        ("function-not-found", re.compile(r"no matching function|no member named", re.I)),
        ("undeclared-identifier", re.compile(r"undeclared identifier|use of undeclared", re.I)),
        ("other", re.compile(r".")),
    ),
}


class ShaderPassError(Exception):
    """A problem the user can act on; reported as `error: <message>` with exit 1."""


def stage_from_source(source: str) -> str:
    for stage, needles in SOURCE_STAGE_PROBES:
        if any(needle in source for needle in needles):
            return stage
    return "other"


def strip_guard(body: str) -> str:
    """Drops the leading #ifdef <STAGE> line and the #endif that closes it, keeping nested guards."""
    lines = body.splitlines()
    while lines and not lines[0].lstrip().startswith("#version"):
        lines.pop(0)
    depth = 0
    for index, line in enumerate(lines):
        if IF_DIRECTIVE.match(line):
            depth += 1
        elif ENDIF_DIRECTIVE.match(line):
            depth -= 1
            if depth < 0:
                lines = lines[:index]
                break
    return "\n".join(lines).strip() + "\n"


def split_glsl_units(chunk: bytes) -> list[dict]:
    """Splits a GLSL platform chunk into its `#ifdef <STAGE>` guarded programs."""
    text = chunk.decode("latin-1")
    guards = [(match.start(), GUARD_STAGES[match.group(1)]) for match in GUARD.finditer(text)]
    units = []
    for index, (start, stage) in enumerate(guards):
        stop = guards[index + 1][0] if index + 1 < len(guards) else len(text)
        source = strip_guard(text[start:stop]).encode("utf-8", "replace")
        if b"void main" not in source and b"main(" not in source:
            continue
        match = VERSION.match(source.decode("utf-8", "replace"))
        units.append({"unit": index, "stage": stage, "version": match.group(1) if match else "unknown", "source": source})
    return units


def normalize_glsl(source: bytes) -> tuple[bytes, dict]:
    """Raises a unit to the Vulkan-required #version 450 core and drops #extension lines."""
    text = source.decode("utf-8", "replace")
    lines = text.splitlines()
    notes = {"version": "unknown", "version_bumped": False, "extensions_dropped": []}
    for index, line in enumerate(lines):
        match = VERSION.match(line)
        if match:
            notes["version"] = match.group(1)
            if match.group(1) != "450":
                lines[index] = f"#version {TARGET_VERSION}"
                notes["version_bumped"] = True
            break
    kept = []
    for line in lines:
        extension = EXTENSION.match(line)
        if extension:
            notes["extensions_dropped"].append(extension.group(1))
            continue
        kept.append(line)
    return ("\n".join(kept).strip() + "\n").encode("utf-8"), notes


def stage_for_program(program_type: str, source: str) -> str:
    """Names the shader stage from the guard token, falling back to source probes."""
    stage = GUARD_STAGES.get(program_type.upper())
    if stage:
        return stage
    lowered = program_type.lower().replace("_", "")
    for needle, candidate in (("vertex", "vert"), ("fragment", "frag"), ("pixel", "frag"), ("geometry", "geom"), ("compute", "comp"), ("hull", "hull"), ("domain", "domain")):
        if needle in lowered:
            return candidate
    return stage_from_source(source)


def first_diagnostic(text: str) -> str:
    """The first meaningful line of a tool's output, trimmed for reporting."""
    for line in (text or "").splitlines():
        stripped = line.strip()
        if stripped and not re.fullmatch(r"(ERROR|WARNING|error|warning|NOTE|Note):", stripped):
            return stripped[:400]
    return (text or "").strip()[:400]


def classify(stage: str, diagnostic: str) -> str:
    """Groups a tool failure under one taxonomy category, or `no-diagnostic` / `other`."""
    if not diagnostic.strip():
        return "no-diagnostic"
    for category, pattern in RULES[stage]:
        if pattern.search(diagnostic):
            return category
    return "other"


def glslang_command(binary: str, source: str, target: str, stage: str, target_env: str = "opengl") -> list[str]:
    """glslangValidator argv: SPIR-V for one stage; opengl semantics accept the shipped loose uniforms."""
    head = [binary] + (["-V"] if target_env.startswith("vulkan") else [])
    return [*head, "--target-env", target_env, "--auto-map-bindings", "--auto-map-locations", "-S", STAGE_FLAGS[stage], "--quiet", "-o", target, source]


def spirv_command(binary: str, source: str, target: str, msl_version: str | None = None) -> list[str]:
    """spirv-cross argv: MSL with Vulkan semantics, which is what the Metal stage expects."""
    argv = [binary, source, "--msl", "--vulkan-semantics", "--output", target]
    if msl_version:
        argv += ["--msl-version", msl_version]
    return argv


def metal_command(binary: str, source: str, target: str) -> list[str]:
    """Metal argv: compile-only against the macOS SDK through xcrun."""
    return ["xcrun", "-sdk", "macosx", binary, "-c", source, "-o", target]


BUFFER_ATTR = re.compile(r"\[\[(buffer|texture|sampler)\((\d+)\)\]\]")
SUGGESTED_EXTENSION = re.compile(r"^\s*(GL_[A-Za-z0-9_]+)\s*(?:\(|$)", re.M)


def compact_msl_bindings(text: str) -> tuple[str, int]:
    """Renumbers MSL resource bindings densely; glslang's --auto-map-bindings leaves gaps that pass Metal's 31-per-stage limit.

    Returns the rewritten source and how many distinct indices it now uses.
    """
    highest = 0
    for kind in ("buffer", "texture", "sampler"):
        used = sorted({int(m) for m in re.findall(rf"\[\[{kind}\((\d+)\)\]\]", text)})
        highest = max(highest, len(used))
        remap = {old: new for new, old in enumerate(used)}
        if not remap:
            continue
        text = re.sub(
            rf"\[\[{kind}\((\d+)\)\]\]",
            lambda match, remap=remap, kind=kind: f"[[{kind}({remap[int(match.group(1))]})]]",
            text,
        )
    return text, highest


def suggested_extensions(diagnostic: str) -> list[str]:
    """GL_* names a glslang `required extension not requested` error offers as the fix."""
    names: list[str] = []
    for name in SUGGESTED_EXTENSION.findall(diagnostic or ""):
        if name not in names:
            names.append(name)
    return names[:6]


def request_extensions(source: bytes, extensions: list[str]) -> bytes:
    """Inserts `#extension <name> : require` lines after the #version directive."""
    if not extensions:
        return source
    lines = source.decode("utf-8", "replace").splitlines()
    for index, line in enumerate(lines):
        if VERSION.match(line):
            lines[index + 1 : index + 1] = [f"#extension {name} : require" for name in extensions]
            break
    return ("\n".join(lines) + "\n").encode()


def slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_") or "unnamed"


def program_id(shader: str, stage: str, version: str, index: int) -> str:
    """A stable, filesystem-safe identifier that distinguishes shader, stage, GLSL version and unit."""
    return f"{slug(f'{shader}_{stage}_glsl{version}')}_{index}"


def source_key(source: bytes) -> str:
    """Content hash used to decide whether a cached result can be reused."""
    return hashlib.sha256(source).hexdigest()[:16]


def looks_like_glsl(raw: bytes) -> bool:
    return b"#version" in raw[:2000000] and b"void main" in raw[:2000000]


def write_manifest(programs: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(programs, indent=1) + "\n")


def read_manifest(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return json.loads(path.read_text())


def _read_cache(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    records = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def load_cache(path: Path) -> dict[str, str]:
    """Program ids with a recorded, error-free result mapped to the source key it scored."""
    return {r["id"]: r["source_key"] for r in _read_cache(path) if "id" in r and "source_key" in r and "error" not in r}


def append_cache(path: Path, record: dict) -> None:
    with path.open("a") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def verdict(passed: int, total: int) -> dict:
    """Scores the end-to-end pass rate against the go/no-go thresholds for route B."""
    thresholds = {"scriptable": 0.95, "hand_edits": 0.6}
    rate = 0.0 if total == 0 else round(passed / total, 4)
    if total == 0:
        kind = "no-data"
    elif rate >= thresholds["scriptable"]:
        kind = "scriptable"
    elif rate >= thresholds["hand_edits"]:
        kind = "scriptable-with-hand-edits"
    else:
        kind = "hand-or-route-c"
    return {"rate": rate, "classification": kind, "thresholds": thresholds}


def sorted_counts(counter: dict[str, int]) -> dict[str, int]:
    return dict(sorted(counter.items(), key=lambda item: (-item[1], item[0])))


def summarize(results: list[dict], tools: dict[str, str] | None = None, build_path: str | None = None) -> dict:
    """Aggregates per-program stage results into counts, failure kinds and a verdict."""
    stages = {stage: {"pass": 0, "fail": 0, "skip": 0} for stage in STAGES}
    by_shader_stage: dict[str, dict[str, int]] = {}
    kinds: dict[str, dict[str, int]] = {stage: {} for stage in STAGES}
    hand_edits: dict[str, int] = {}
    hand_edit_stages: dict[str, int] = {}
    platforms: dict[str, int] = {}
    versions: dict[str, int] = {}
    preprocess = {"version_bumped": 0, "extensions_dropped": 0, "programs_normalized": 0}
    fixes = {"extensions_requested": 0, "bindings_renumbered": 0}
    offenders: dict[str, dict[str, int]] = {}
    end_to_end = 0

    for record in results:
        shader_stage = record.get("stage", "other")
        bucket = by_shader_stage.setdefault(shader_stage, {"programs": 0, "glslang_pass": 0, "spirv_pass": 0, "metal_pass": 0})
        bucket["programs"] += 1
        platforms[str(record.get("platform"))] = platforms.get(str(record.get("platform")), 0) + 1
        versions[str(record.get("version", "unknown"))] = versions.get(str(record.get("version", "unknown")), 0) + 1
        notes = record.get("preprocess") or {}
        if notes:
            preprocess["programs_normalized"] += 1
            preprocess["version_bumped"] += 1 if notes.get("version_bumped") else 0
            preprocess["extensions_dropped"] += len(notes.get("extensions_dropped") or [])

        all_passed = True
        first_failure = None
        for stage in STAGES:
            step = record.get(stage) or {"status": "skip", "kind": None}
            status = step.get("status", "skip")
            stages[stage][status if status in stages[stage] else "skip"] += 1
            if status == "pass":
                bucket[f"{stage}_pass"] += 1
            else:
                all_passed = False
            if status == "fail" and first_failure is None:
                kind = step.get("kind") or "other"
                kinds[stage][kind] = kinds[stage].get(kind, 0) + 1
                first_failure = kind

        if all_passed:
            end_to_end += 1
        else:
            kind = first_failure or "skipped"
            hand_edits[kind] = hand_edits.get(kind, 0) + 1
            hand_edit_stages[shader_stage] = hand_edit_stages.get(shader_stage, 0) + 1
            shader = record.get("shader") or "unknown"
            bucket = offenders.setdefault(shader, {"hand_edits": 0})
            bucket["hand_edits"] += 1
            bucket[kind] = bucket.get(kind, 0) + 1

        applied = record.get("fixes") or {}
        if applied.get("extensions_requested"):
            fixes["extensions_requested"] += 1
        if applied.get("bindings_renumbered"):
            fixes["bindings_renumbered"] += 1

    total = len(results)
    return {
        "schema": SCHEMA,
        "build_path": build_path,
        "tools": tools or {},
        "totals": {
            "programs": total,
            "shaders": len({record.get("shader") for record in results}),
            "source_bytes": sum(int(record.get("source_bytes") or 0) for record in results),
        },
        "stages": stages,
        "by_shader_stage": {stage: by_shader_stage[stage] for stage in sorted(by_shader_stage)},
        "by_platform": {platform: platforms[platform] for platform in sorted(platforms)},
        "by_glsl_version": dict(sorted(versions.items(), key=lambda item: (-item[1], item[0]))),
        "preprocess": preprocess,
        "fixes": fixes,
        "failure_kinds": {stage: sorted_counts(kinds[stage]) for stage in STAGES},
        "end_to_end_pass": end_to_end,
        "hand_edits": {
            "count": total - end_to_end,
            "by_kind": sorted_counts(hand_edits),
            "by_stage": dict(sorted(hand_edit_stages.items())),
            "worst_shaders": [
                dict((key, value) for key, value in row.items() if key != "hand_edits")
                | {"shader": shader, "hand_edits": row["hand_edits"]}
                for shader, row in sorted(offenders.items(), key=lambda item: -item[1]["hand_edits"])[:20]
            ],
        },
        "verdict": verdict(end_to_end, total),
    }


def tool_versions(binaries: dict[str, str]) -> dict[str, str]:
    versions = {}
    for name, binary in binaries.items():
        if not binary:
            versions[name] = "missing"
            continue
        argv = ["xcrun", "-sdk", "macosx", "metal", "--version"] if name == "metal" else [binary, "--version"]
        try:
            done = subprocess.run(argv, capture_output=True, text=True, timeout=30)
            text = (done.stdout or done.stderr).strip().splitlines()
            versions[name] = text[0] if text else "unknown"
        except (OSError, subprocess.SubprocessError):
            versions[name] = "unknown"
    return versions


def run_tool(argv: list[str]) -> tuple[bool, str, str]:
    """Runs one compiler invocation, returning (ok, first diagnostic, full output)."""
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=TOOL_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        return False, "timeout", "timeout"
    except OSError as error:
        return False, f"{type(error).__name__}: {error}", str(error)
    output = (done.stderr or done.stdout or "").strip()
    return (True, "", output) if done.returncode == 0 else (False, first_diagnostic(output), output)


def resolve_data_dir(build: str) -> Path:
    """Accepts a build root or a Megabonk_Data directory and returns the latter."""
    root = Path(build).expanduser()
    if not root.exists():
        raise ShaderPassError(f"no such build path: {root}")
    if root.name == "Megabonk_Data":
        return root
    candidate = root / "Megabonk_Data"
    if candidate.is_dir():
        return candidate
    raise ShaderPassError(f"{root} has no Megabonk_Data directory; pass the build root or the data directory")


def asset_files(data_dir: Path) -> list[Path]:
    """Serialized files that can hold Shader objects, skipping streamed resource bundles."""
    return [
        path
        for path in sorted(data_dir.rglob("*"))
        if path.is_file() and path.name not in SKIP_NAMES and not path.name.endswith((".resS", ".resource"))
    ]


def shader_chunks(data_dir: Path, platform: int | None, stats: dict):
    """Yields (shader name, platform id, decompressed chunk) for every platform chunk read."""
    try:
        import UnityPy
        from UnityPy.helpers import CompressionHelper
    except ImportError as error:
        raise ShaderPassError(f"unitypy is required (run it through the task alias): {error}") from error

    for path in asset_files(data_dir):
        try:
            env = UnityPy.load(str(path))
        except Exception:
            continue
        for obj in env.objects:
            if obj.type.name != "Shader":
                continue
            try:
                data = obj.read()
            except Exception:
                stats["reader_failures"] = stats.get("reader_failures", 0) + 1
                continue
            stats["shader_objects"] += 1
            parsed = getattr(data, "m_ParsedForm", None)
            shader = getattr(parsed, "m_Name", "") or f"unnamed-{obj.path_id}"
            blob = bytes(getattr(data, "compressedBlob", None) or b"")
            platforms = [int(x) for x in (getattr(data, "platforms", []) or [])]
            lengths = [x[0] if isinstance(x, list) else x for x in (getattr(data, "compressedLengths", []) or [])]
            decompressed = [x[0] if isinstance(x, list) else x for x in (getattr(data, "decompressedLengths", []) or [])]
            offsets = [x[0] if isinstance(x, list) else x for x in (getattr(data, "offsets", []) or [])]
            for index, chunk_platform in enumerate(platforms):
                if index >= len(lengths) or index >= len(decompressed) or index >= len(offsets):
                    continue
                if platform is not None and chunk_platform != platform:
                    continue
                try:
                    raw = CompressionHelper.decompress_lz4(blob[offsets[index] : offsets[index] + lengths[index]], decompressed[index])
                except Exception:
                    stats["lz4_failures"] = stats.get("lz4_failures", 0) + 1
                    continue
                stats["chunks"] += 1
                yield shader, chunk_platform, raw


def extract_programs(data_dir: Path, platform: int | None, normalize: bool) -> tuple[list[dict], dict]:
    """Reads every baked Shader and returns its GLSL programs plus extraction diagnostics."""
    programs: list[dict] = []
    seen: set[str] = set()
    stats = {"shader_objects": 0, "chunks": 0, "glsl_chunks": 0, "shaders_with_glsl": 0, "programs_extracted": 0, "ids_collided": 0}
    shaders_with_glsl: set[str] = set()
    for shader, chunk_platform, raw in shader_chunks(data_dir, platform, stats):
        if not looks_like_glsl(raw):
            continue
        stats["glsl_chunks"] += 1
        found = 0
        for unit in split_glsl_units(raw):
            source = unit["source"]
            notes: dict = {}
            if normalize:
                source, notes = normalize_glsl(source)
            pid = program_id(shader, unit["stage"], unit["version"], unit["unit"])
            if pid in seen:
                stats["ids_collided"] += 1
                continue
            seen.add(pid)
            stem = f"{slug(shader)}/{unit['unit']:04d}-{unit['stage']}-glsl{unit['version']}"
            programs.append(
                {
                    "id": pid,
                    "shader": shader,
                    "unit": unit["unit"],
                    "stage": unit["stage"],
                    "version": unit["version"],
                    "platform": chunk_platform,
                    "source_bytes": len(source),
                    "source_key": source_key(source),
                    "source_path": f"{'norm' if normalize else 'raw'}/{stem}{STAGE_SUFFIX.get(unit['stage'], '.glsl')}",
                    "preprocess": notes,
                    "_code": source,
                }
            )
            found += 1
        if found:
            shaders_with_glsl.add(shader)
    stats["shaders_with_glsl"] = len(shaders_with_glsl)
    stats["programs_extracted"] = len(programs)
    return programs, stats


def write_sources(programs: list[dict], out_dir: Path) -> None:
    for program in programs:
        target = out_dir / program["source_path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(program["_code"])


def score(
    program: dict,
    out_dir: Path,
    binaries: dict[str, str],
    enabled: tuple[str, ...],
    target_env: str = "opengl",
    msl_version: str | None = None,
    retry_extensions: bool = True,
    compact_bindings: bool = True,
) -> dict:
    """Runs one program through the enabled stages, stopping at the first failure.

    Two mechanical fixes run by default because they only undo choices the pass itself makes:
    re-asking for extensions glslang names, and renumbering the sparse bindings
    `--auto-map-bindings` produces. Both are recorded in `fixes` and never edit shipped source.
    """
    record = {key: value for key, value in program.items() if not key.startswith("_")}
    fixes: dict[str, object] = {}
    record["fixes"] = fixes
    source_path = out_dir / program["source_path"]
    stem = source_path.with_suffix("")
    for stage in STAGES:
        record[stage] = {"status": "skip", "kind": None, "diagnostic": ""}

    if program["source_bytes"] == 0:
        record["glslang"] = {"status": "fail", "kind": "empty-source", "diagnostic": "empty program"}
        return record

    spirv_path = stem.with_suffix(".spv")
    if "glslang" in enabled:
        glslang = partial(glslang_command, binaries["glslang"], target=str(spirv_path), stage=program["stage"], target_env=target_env)
        ok, diagnostic, output = run_tool(glslang(source=str(source_path)))
        if not ok and retry_extensions and "required extension not requested" in output:
            extensions = suggested_extensions(output)
            retry_path = stem.with_suffix(f".retry{source_path.suffix}")
            retry_path.write_bytes(request_extensions(program["_code"], extensions))
            retry_ok, retry_diagnostic, _ = run_tool(glslang(source=str(retry_path)))
            if retry_ok:
                ok, diagnostic = True, ""
                fixes["extensions_requested"] = extensions
        if not ok:
            record["glslang"] = {"status": "fail", "kind": classify("glslang", diagnostic), "diagnostic": diagnostic}
            return record
        record["glslang"] = {"status": "pass", "kind": None, "diagnostic": ""}

    msl_path = stem.with_suffix(".metal")
    if "spirv" in enabled:
        ok, diagnostic = run_tool(spirv_command(binaries["spirv-cross"], str(spirv_path), str(msl_path), msl_version))[:2]
        if not ok:
            record["spirv"] = {"status": "fail", "kind": classify("spirv", diagnostic), "diagnostic": diagnostic}
            return record
        if not msl_path.is_file() or msl_path.stat().st_size == 0:
            record["spirv"] = {"status": "fail", "kind": "empty-output", "diagnostic": "spirv-cross wrote no MSL"}
            return record
        record["spirv"] = {"status": "pass", "kind": None, "diagnostic": ""}

    if "metal" in enabled:
        compiled = msl_path
        if compact_bindings and msl_path.is_file():
            text = msl_path.read_text()
            compacted, bindings = compact_msl_bindings(text)
            if compacted != text:
                compiled = stem.with_suffix(".bound.metal")
                compiled.write_text(compacted)
                fixes["bindings_renumbered"] = bindings
        ok, diagnostic = run_tool(metal_command(binaries["metal"], str(compiled), str(stem.with_suffix(".air"))))[:2]
        if not ok:
            record["metal"] = {"status": "fail", "kind": classify("metal", diagnostic), "diagnostic": diagnostic}
            return record
        record["metal"] = {"status": "pass", "kind": None, "diagnostic": ""}

    return record


def resolve_binaries(args: argparse.Namespace) -> dict[str, str]:
    binaries = {
        "glslang": args.glslang or shutil.which("glslangValidator") or shutil.which("glslang"),
        "spirv-cross": args.spirv_cross or shutil.which("spirv-cross"),
        "metal": "metal" if shutil.which("xcrun") else None,
    }
    missing = [name for name, binary in binaries.items() if not binary]
    if missing:
        hints = {"glslang": "brew install glslang", "spirv-cross": "brew install spirv-cross", "metal": "xcode-select --install"}
        raise ShaderPassError("missing toolchain: " + ", ".join(f"{name} ({hints[name]})" for name in missing))
    return binaries


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="shader_metal_pass", description="Score GLSL to Metal translation failure rates for a native Linux build.")
    parser.add_argument("build", help="native Linux build root, or its Megabonk_Data directory")
    parser.add_argument("--out", default=None, help="output directory (default: <repo>/.tools/shaders-metal)")
    parser.add_argument("--json", dest="json_path", default=None, help="summary path (default: <out>/summary.json)")
    parser.add_argument("--stages", default=",".join(STAGES), help="comma list of glslang,spirv,metal to run")
    parser.add_argument("--platform", type=int, default=None, help="only read this platform chunk id (15 is the GLSL source chunk)")
    parser.add_argument("--limit", type=int, default=None, help="score at most N programs (smoke runs)")
    parser.add_argument("--jobs", type=int, default=None, help="parallel compiler processes (default: 2x CPUs)")
    parser.add_argument("--no-normalize", action="store_true", help="score the shipped GLSL verbatim instead of raising it to #version 450")
    parser.add_argument("--glslang-target-env", choices=("opengl", "vulkan1.0"), default="opengl", help="glslang semantics; opengl keeps the shipped loose uniforms legal")
    parser.add_argument("--msl-version", default="20100", help="spirv-cross MSL target (empty to omit; 2.1 unlocks multisampled array textures)")
    parser.add_argument("--no-retry-extensions", action="store_true", help="do not re-ask glslang with the extensions its error names")
    parser.add_argument("--no-compact-bindings", action="store_true", help="do not renumber the sparse bindings --auto-map-bindings produces")
    parser.add_argument("--resume", action="store_true", help="reuse cached results for unchanged program sources")
    parser.add_argument("--fresh", action="store_true", help="delete the output directory before running")
    parser.add_argument("--glslang", default=None, help="glslangValidator binary override")
    parser.add_argument("--spirv-cross", default=None, help="spirv-cross binary override")
    parser.add_argument("--sample", type=int, default=0, help="print this many failing diagnostics per stage to stderr")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        data_dir = resolve_data_dir(args.build)
        binaries = resolve_binaries(args)
        enabled = tuple(stage for stage in STAGES if stage in [item.strip() for item in args.stages.split(",") if item.strip()])
        if not enabled:
            raise ShaderPassError("--stages must name at least one of glslang,spirv,metal")

        out_dir = Path(args.out).expanduser() if args.out else Path(__file__).resolve().parents[1] / ".tools/shaders-metal"
        if args.fresh and out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        programs, stats = extract_programs(data_dir, args.platform, normalize=not args.no_normalize)
        if args.limit is not None:
            programs = programs[: args.limit]
        if not programs:
            raise ShaderPassError(f"no GLSL programs found under {data_dir}; check --platform")
        write_sources(programs, out_dir)
        write_manifest([{key: value for key, value in program.items() if not key.startswith("_")} for program in programs], out_dir / "manifest.json")

        cache_path = out_dir / "cache.jsonl"
        cached_keys = load_cache(cache_path) if args.resume else {}
        cached_records = {record["id"]: record for record in _read_cache(cache_path) if "id" in record} if args.resume else {}

        jobs = args.jobs or max(1, (os.cpu_count() or 4) * 2)
        results: list[dict] = []
        failures: dict[str, int] = {stage: 0 for stage in STAGES}
        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
            futures = {}
            for program in programs:
                cached = cached_records.get(program["id"])
                if cached and cached.get("source_key") == program["source_key"] and cached_keys.get(program["id"]) == program["source_key"]:
                    results.append({key: cached.get(key) for key in ("id", "shader", "unit", "stage", "version", "platform", "source_bytes", "source_key", "source_path", "preprocess", "fixes", *STAGES)})
                    continue
                futures[pool.submit(
                    score,
                    program,
                    out_dir,
                    binaries,
                    enabled,
                    args.glslang_target_env,
                    args.msl_version or None,
                    not args.no_retry_extensions,
                    not args.no_compact_bindings,
                )] = program
            for future in concurrent.futures.as_completed(futures):
                program = futures[future]
                try:
                    record = future.result()
                except Exception as error:
                    record = {key: value for key, value in program.items() if not key.startswith("_")}
                    record["error"] = f"{type(error).__name__}: {error}"
                    for stage in STAGES:
                        record[stage] = {"status": "fail", "kind": "runner-error", "diagnostic": str(error)}
                append_cache(cache_path, record)
                for stage in STAGES:
                    step = record.get(stage) or {}
                    if step.get("status") == "fail" and failures[stage] < args.sample:
                        failures[stage] += 1
                        print(f"{stage} {step.get('kind')}: {record['id']}: {step.get('diagnostic')}", file=sys.stderr)
                results.append(record)

        summary = summarize(results, tools=tool_versions(binaries), build_path=str(data_dir))
        summary["extraction"] = stats
        summary["enabled_stages"] = list(enabled)
        summary["normalized"] = not args.no_normalize
        summary["glslang_target_env"] = args.glslang_target_env
        summary["msl_version"] = args.msl_version or None
        summary["retry_extensions"] = not args.no_retry_extensions
        summary["compact_bindings"] = not args.no_compact_bindings
        summary["out_dir"] = str(out_dir)
        summary["cached"] = len(results) - len(futures)
        json_path = Path(args.json_path).expanduser() if args.json_path else out_dir / "summary.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(summary, indent=1) + "\n")
        print(json.dumps(summary))
    except ShaderPassError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
