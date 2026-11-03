#!/usr/bin/env python3.14
"""Replay RenderDoc captures and report GPU frame cost, draw-call counts and per-enemy submission.

The pymodule is ABI-pinned to the python it was built against (3.14 on the player laptop) and sits beside the
librenderdoc it was built with, so:
    python3.14 scripts/renderdoc_replay.py --baseline empty.rdc --json out.json empty.rdc full.rdc

InitialiseReplay/ShutdownReplay must bracket every call and shutdown must run before exit; skipping it dumps
core in interpreter teardown, which reads like an import-time segfault.

--structured reads only the capture's serialised API log, so it costs no GPU time; the default mode opens a
replay device and is refused while the game is running, which would skew both sides. --force overrides.
"""

import argparse
import glob
import json
import os
import re
import subprocess
import sys
from collections import namedtuple
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

Draw = namedtuple("Draw", "event_id indices instances")

GAME_PROCESS = re.compile(r"^[A-Za-z]:\\.*\\Megabonk\.exe(?:\s|$)")
DRAW_CHUNKS = {
    "vkCmdDraw": "vertexCount",
    "vkCmdDrawIndexed": "indexCount",
    "vkCmdDrawIndirect": "vertexCount",
    "vkCmdDrawIndexedIndirect": "indexCount",
}
TOP_EVENTS = 15
TOP_SHAPES = 12


def game_pids(listing: str) -> list[str]:
    """Pids from `ps -axo pid=,comm=,args=` whose arguments are the Windows game itself, not Wine's stubs or Proton's wrappers."""
    pids = []
    for line in listing.splitlines():
        pid, _, rest = line.strip().partition(" ")
        _, _, arguments = rest.strip().partition(" ")
        if pid.isdigit() and GAME_PROCESS.match(arguments.strip()):
            pids.append(pid)
    return pids


def draw_histogram(draws: Sequence[Draw]) -> dict[tuple[int, int], int]:
    histogram: dict[tuple[int, int], int] = {}
    for draw in draws:
        key = (draw.indices, draw.instances)
        histogram[key] = histogram.get(key, 0) + 1
    return histogram


def top_shapes(draws: Sequence[Draw], limit: int = TOP_SHAPES) -> list[dict[str, int]]:
    """Submission shapes ranked by the vertices they put on the GPU, which is what a mesh costs per frame."""
    shapes = []
    for (indices, instances), count in draw_histogram(draws).items():
        shapes.append({"drawCalls": count, "indicesPerDraw": indices, "instances": instances,
                       "vertices": indices * instances * count, "verticesPerDraw": indices * instances})
    shapes.sort(key=lambda shape: -shape["vertices"])
    return shapes[:limit]


def gpu_totals(samples: Iterable[tuple[int, float]], top: int = TOP_EVENTS) -> dict[str, Any]:
    """Sum per-event GPU durations (seconds) into a frame total in microseconds, with the heaviest events first."""
    pairs = list(samples)
    ordered = sorted(pairs, key=lambda pair: -pair[1])
    return {
        "gpuFrameTotalUSec": round(sum(seconds for _, seconds in pairs) * 1e6, 1),
        "gpuEventsMeasured": len(pairs),
        "gpuTopEvents": [{"eventId": event_id, "uSec": round(seconds * 1e6, 1)} for event_id, seconds in ordered[:top]],
    }


def per_enemy_cost(baseline: Mapping[str, Any], capture: Mapping[str, Any], enemies: int) -> dict[str, Any]:
    """What one extra enemy costs, from the delta between an empty-level capture and a populated one."""
    if enemies <= 0:
        raise ValueError("enemies must be positive")
    empty, full = baseline.get("gpuFrameTotalUSec"), capture.get("gpuFrameTotalUSec")
    delta = None if empty is None or full is None else round(full - empty, 1)

    def growth(field: str) -> float:
        return (capture.get(field, 0) or 0) - (baseline.get(field, 0) or 0)

    return {
        "enemies": enemies,
        "gpuFrameDeltaUSec": delta,
        "gpuPerEnemyNanoseconds": None if delta is None else delta * 1000.0 / enemies,
        "drawCallsPerEnemy": growth("drawCalls") / enemies,
        "verticesPerEnemy": growth("verticesSubmitted") / enemies,
        "instancesPerEnemy": growth("instances") / enemies,
    }


RENDERDOC_LIB_PATTERNS = ("git/renderdoc-build/*/lib", "git/renderdoc-build/*/*/lib", ".local/share/renderdoc/lib")


def renderdoc_lib(home: str | None = None) -> str:
    """Where the built pymodule and its librenderdoc live; the newest build wins."""
    override = os.environ.get("MEGABONK_RENDERDOC_LIB")
    if override:
        return os.path.expanduser(override)
    root = os.path.expanduser(home or "~")
    found: list[str] = []
    for pattern in RENDERDOC_LIB_PATTERNS:
        found += sorted(glob.glob(os.path.join(root, pattern)), reverse=True)
    for candidate in found:
        if os.path.exists(os.path.join(candidate, "renderdoc.so")):
            return candidate
    raise FileNotFoundError(f"no RenderDoc pymodule (renderdoc.so) under {root}; build it with ENABLE_PYMOD")


def load_pymodule() -> Any:
    sys.path.insert(0, renderdoc_lib())
    import renderdoc

    return renderdoc


def flatten(actions) -> list:
    flat = []
    queue = list(actions)
    while queue:
        action = queue.pop(0)
        flat.append(action)
        queue[0:0] = list(action.children or [])
    return flat


def is_draw(rd: Any, action) -> bool:
    flags = getattr(rd.ActionFlags, "Drawcall", None)
    return flags is not None and bool(action.flags & flags)


def counter_seconds(result) -> float:
    """CounterValue is a union; duration counters arrive in its double member."""
    value = result.value
    for attribute in ("d", "f"):
        raw = getattr(value, attribute, None)
        if isinstance(raw, (int, float)) and raw:
            return float(raw)
    return 0.0


def walk_chunks(chunk) -> Iterable[Any]:
    yield chunk
    for index in range(chunk.NumChildren()):
        yield from walk_chunks(chunk.GetChild(index))


def structured_draws(capture) -> tuple[list[Draw], dict[str, int]]:
    """Draws and API-call counts from the serialised log, which needs no replay device and therefore no GPU."""
    data = capture.GetStructuredData()
    if not data:
        return [], {}
    draws: list[Draw] = []
    api: dict[str, int] = {}
    for chunk in (data.chunks or []):
        for node in walk_chunks(chunk):
            name = str(node.name)
            if name.startswith("vk"):
                api[name] = api.get(name, 0) + 1
            count_field = DRAW_CHUNKS.get(name)
            if count_field is None:
                continue
            child = node.FindChild(count_field)
            instances = node.FindChild("instanceCount")
            indices = child.AsInt() if child is not None else 0
            draws.append(Draw(len(draws) + 1, int(indices or 0), max(1, int(instances.AsInt()) if instances is not None else 1)))
    return draws, api


def pipeline_signature(rd: Any, controller, event_id: int) -> dict[str, Any]:
    """What a draw binds: the shaders and the index and vertex buffers behind it."""
    try:
        state = controller.GetVulkanPipelineState(event_id)
    except BaseException:
        return {}
    if not state:
        return {}

    def shader(stage):
        entry = getattr(getattr(state, stage, None), "entry", None)
        return str(getattr(entry, "resource", "null"))

    inputs = getattr(state, "descriptorInputs", None)
    bound = getattr(inputs, "indexBound", None) if inputs else None
    vertex_inputs = getattr(inputs, "vertexInputs", None) if inputs else []
    return {
        "vertexShader": shader("vertexEntry"),
        "pixelShader": shader("pixelEntry"),
        "indexBuffer": str(getattr(bound, "resource", "null")),
        "vertexBuffers": [str(v.resource) for v in (vertex_inputs or []) if getattr(v, "resource", None)],
    }


def summary_fields(draws: Sequence[Draw]) -> dict[str, Any]:
    return {
        "drawCalls": len(draws),
        "instancedDraws": sum(1 for draw in draws if draw.instances > 1),
        "instances": sum(draw.instances for draw in draws),
        "verticesSubmitted": sum(draw.indices * draw.instances for draw in draws),
        "submission": top_shapes(draws),
    }


def example_event(draws: Sequence[Draw], shape: Mapping[str, int]) -> int:
    for draw in draws:
        if draw.indices == shape["indicesPerDraw"] and draw.instances == shape["instances"]:
            return draw.event_id
    return 0


def read_capture(path: str, options: argparse.Namespace, rd: Any) -> dict[str, Any]:
    report: dict[str, Any] = {"capture": path, "ok": False}
    capture = rd.OpenCaptureFile()
    opened = capture.OpenFile(path, "rdc", None)
    if not opened.OK():
        report["error"] = f"OpenFile: {opened}"
        return report

    controller = None
    try:
        if options.structured:
            report["mode"] = "structured"
            draws, api = structured_draws(capture)
            report["apiCalls"] = sum(api.values())
            report["topApiCalls"] = sorted(api.items(), key=lambda item: -item[1])[:12]
            report.update(summary_fields(draws))
            report["gpuFrameTotalUSec"] = None
            report["ok"] = True
            return report

        result = capture.OpenCapture(rd.ReplayOptions(), None)
        verdict, controller = (result[0], result[-1]) if isinstance(result, tuple) else (None, result)
        if verdict is not None and not verdict.OK():
            report["error"] = f"OpenCapture: {verdict}"
            return report
        if controller is None:
            report["error"] = "OpenCapture returned no controller"
            return report
        report["mode"] = "replay"
        report["driver"] = controller.GetAPIProperties().graphicsDriver

        actions = flatten(controller.GetRootActions())
        draws = [Draw(action.eventId, action.numIndices, max(1, action.numInstances))
                 for action in actions if is_draw(rd, action)]
        report["actions"] = len(actions)
        report["markers"] = sorted({str(action.customName) for action in actions if getattr(action, "customName", "")})[:40]
        report.update(summary_fields(draws))

        available = list(controller.EnumerateCounters() or [])
        report["countersAvailable"] = sorted(str(counter) for counter in available)[:24]
        if rd.GPUCounter.EventGPUDuration in available:
            results = controller.FetchCounters([rd.GPUCounter.EventGPUDuration]) or []
            report.update(gpu_totals([(result.eventId, counter_seconds(result)) for result in results]))
        else:
            report["gpuFrameTotalUSec"] = None
            report["gpuCountersUnavailable"] = True

        if options.pipelines:
            for shape in report["submission"]:
                shape.update(pipeline_signature(rd, controller, example_event(draws, shape)))
        report["ok"] = True
        return report
    finally:
        if controller is not None:
            try:
                controller.Shutdown()
            except BaseException as error:
                print(f"controller shutdown: {error}", file=sys.stderr)
        try:
            capture.Shutdown()
        except BaseException as error:
            print(f"capture shutdown: {error}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("captures", nargs="+")
    parser.add_argument("--json", help="write every report as JSON to this file")
    parser.add_argument("--structured", action="store_true", help="parse the serialised API log without a replay device")
    parser.add_argument("--pipelines", action="store_true", help="read pipeline state for the top submission shapes")
    parser.add_argument("--baseline", help="capture to treat as the empty-level control; must also be listed")
    parser.add_argument("--enemies", type=int, default=240, help="enemy population the populated captures hold (default 240)")
    parser.add_argument("--force", action="store_true", help="replay even while the game is running")
    options = parser.parse_args(argv)

    if options.baseline and options.baseline not in options.captures:
        parser.error("--baseline must be one of the listed captures")

    if not options.structured:
        listing = subprocess.run(["ps", "-axo", "pid=,comm=,args="], capture_output=True, text=True, check=True).stdout
        running = game_pids(listing)
        if running and not options.force:
            print(f"refusing to replay while the game is running (pid {running[0]}); --force to override", file=sys.stderr)
            return 3

    rd = load_pymodule()
    reports: list[dict[str, Any]] = []
    try:
        rd.InitialiseReplay(rd.GlobalEnvironment(), [])
        for path in options.captures:
            try:
                reports.append(read_capture(path, options, rd))
            except BaseException as error:
                reports.append({"capture": path, "ok": False, "error": f"{type(error).__name__}: {error}"})
    finally:
        try:
            rd.ShutdownReplay()
        except BaseException as error:
            print(f"replay shutdown: {error}", file=sys.stderr)
        sys.stdout.flush()

    baseline = next((report for report in reports if report["capture"] == options.baseline), None)
    if baseline is not None:
        for report in reports:
            if report is not baseline:
                report["perEnemy"] = per_enemy_cost(baseline, report, options.enemies)

    if options.json:
        with open(options.json, "w", encoding="utf-8") as handle:
            json.dump(reports, handle, indent=1)
    for report in reports:
        keys = ("capture", "ok", "error", "driver", "mode", "drawCalls", "instancedDraws", "instances",
                "verticesSubmitted", "gpuFrameTotalUSec", "perEnemy")
        print(json.dumps({key: report[key] for key in keys if key in report}))
    return 0 if reports and all(report.get("ok") for report in reports) else 1


if __name__ == "__main__":
    sys.exit(main())
