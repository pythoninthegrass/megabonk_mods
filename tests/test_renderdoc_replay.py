"""Tests for the RenderDoc replay tool's pure analysis: process guard, draw shapes, GPU totals, per-enemy split."""

import renderdoc_replay as rr


def listing(*lines: str) -> str:
    return "\n".join(lines)


def test_game_pids_finds_the_proton_game_process() -> None:
    text = listing(
        " 1234 Megabonk.exe        C:\\steamapps\\common\\Megabonk\\Megabonk.exe -force-d3d11",
    )
    assert rr.game_pids(text) == ["1234"]


def test_game_pids_ignores_wine_stubs_and_proton_wrappers() -> None:
    text = listing(
        " 100 services.exe         C:\\windows\\system32\\services.exe",
        " 200 reaper               /home/u/.local/share/Steam/ubuntu12_32/reaper SteamLaunch AppId=3405340",
        " 300 pv-adverb            /usr/bin/pv-adverb -- /proton waitforexitandrun /games/Megabonk/Megabonk.exe -force-d3d11",
        " 400 wineserver           /usr/bin/wineserver -w",
    )
    assert rr.game_pids(text) == []


def test_game_pids_ignores_helpers_whose_command_lacks_the_exe() -> None:
    assert rr.game_pids(listing(" 700 bash   grep Megabonk.exe")) == []


def test_draw_histogram_counts_repeated_submission_shapes() -> None:
    draws = [rr.Draw(1, 660, 1), rr.Draw(2, 660, 1), rr.Draw(3, 6, 1), rr.Draw(4, 150, 2)]
    assert rr.draw_histogram(draws) == {(660, 1): 2, (6, 1): 1, (150, 2): 1}


def test_top_shapes_ranks_by_total_vertices_over_draw_count() -> None:
    draws = [rr.Draw(i, 6, 1) for i in range(20)] + [rr.Draw(100 + i, 4020, 1) for i in range(3)]
    ranked = rr.top_shapes(draws, limit=2)
    assert [shape["indicesPerDraw"] for shape in ranked] == [4020, 6]
    assert ranked[0]["drawCalls"] == 3
    assert ranked[1]["vertices"] == 120


def test_top_shapes_treats_instances_as_submitted_work() -> None:
    single = [rr.Draw(1, 1000, 1)]
    instanced = [rr.Draw(1, 100, 40)]
    assert rr.top_shapes(instanced, limit=1)[0]["vertices"] == 4000
    assert rr.top_shapes(instanced, limit=1)[0]["drawCalls"] == 1
    assert rr.top_shapes(single, limit=1)[0]["vertices"] == 1000


def test_gpu_totals_sums_seconds_and_reports_microseconds() -> None:
    totals = rr.gpu_totals([(1, 0.001), (2, 0.002), (3, 0.0)])
    assert totals["gpuFrameTotalUSec"] == 3000.0
    assert totals["gpuEventsMeasured"] == 3


def test_gpu_totals_lists_the_heaviest_events_first() -> None:
    totals = rr.gpu_totals([(7, 0.0005), (8, 0.004), (9, 0.0001)])
    assert [event["eventId"] for event in totals["gpuTopEvents"]] == [8, 7, 9]
    assert totals["gpuTopEvents"][0]["uSec"] == 4000.0


def test_gpu_totals_of_nothing_is_zero() -> None:
    assert rr.gpu_totals([]) == {"gpuFrameTotalUSec": 0.0, "gpuEventsMeasured": 0, "gpuTopEvents": []}


def test_per_enemy_cost_divides_the_delta_by_the_population() -> None:
    empty = {"gpuFrameTotalUSec": 2000.0, "drawCalls": 300, "verticesSubmitted": 90_000, "instances": 300}
    full = {"gpuFrameTotalUSec": 6000.0, "drawCalls": 900, "verticesSubmitted": 1_050_000, "instances": 540}
    cost = rr.per_enemy_cost(empty, full, enemies=240)
    assert cost["enemies"] == 240
    assert cost["gpuFrameDeltaUSec"] == 4000.0
    assert round(cost["gpuPerEnemyNanoseconds"], 1) == round(4_000_000 / 240, 1)
    assert round(cost["drawCallsPerEnemy"], 3) == round(600 / 240, 3)
    assert round(cost["verticesPerEnemy"], 1) == round(960_000 / 240, 1)
    assert round(cost["instancesPerEnemy"], 3) == round(240 / 240, 3)


def test_per_enemy_cost_handles_a_missing_gpu_number() -> None:
    empty = {"gpuFrameTotalUSec": None, "drawCalls": 10, "verticesSubmitted": 100, "instances": 10}
    full = {"gpuFrameTotalUSec": None, "drawCalls": 20, "verticesSubmitted": 200, "instances": 20}
    cost = rr.per_enemy_cost(empty, full, enemies=10)
    assert cost["gpuFrameDeltaUSec"] is None
    assert cost["gpuPerEnemyNanoseconds"] is None
    assert cost["drawCallsPerEnemy"] == 1.0


def test_per_enemy_cost_refuses_a_zero_population() -> None:
    import pytest

    with pytest.raises(ValueError):
        rr.per_enemy_cost({"drawCalls": 1}, {"drawCalls": 2}, enemies=0)


def make_lib(root, *segments: str) -> None:
    directory = root.joinpath(*segments)
    directory.mkdir(parents=True, exist_ok=True)
    directory.joinpath("renderdoc.so").write_bytes(b"\x7fELF")


def test_renderdoc_lib_finds_the_pymodule_beside_its_own_build(tmp_path) -> None:
    make_lib(tmp_path, "git", "renderdoc-build", "renderdoc", "build", "lib")
    make_lib(tmp_path, "git", "renderdoc-build", "renderdoc", "build3", "lib")
    assert rr.renderdoc_lib(home=str(tmp_path)).endswith("renderdoc-build/renderdoc/build3/lib")


def test_renderdoc_lib_skips_build_directories_without_a_pymodule(tmp_path) -> None:
    (tmp_path / "git" / "renderdoc-build" / "renderdoc" / "build2" / "lib").mkdir(parents=True)
    make_lib(tmp_path, "git", "renderdoc-build", "renderdoc", "build", "lib")
    assert rr.renderdoc_lib(home=str(tmp_path)).endswith("renderdoc-build/renderdoc/build/lib")


def test_renderdoc_lib_reports_when_nothing_is_built(tmp_path) -> None:
    import pytest

    with pytest.raises(FileNotFoundError):
        rr.renderdoc_lib(home=str(tmp_path))
