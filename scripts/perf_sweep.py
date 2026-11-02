"""Frame-time sweep: one gated measurement window per enemy count, against a live run.

Every window is checked before it is kept: a run that was paused, starved of frames, vsync-locked, or thinned of
enemies is measured again rather than recorded. See docs/performance.md for what the numbers mean and
docs/development.md for the profiler verbs this drives.

Run on the machine hosting the game:

    uv run scripts/perf_sweep.py --out /tmp/perf
    uv run scripts/perf_sweep.py --count 0 --count 120 --count 240 --seconds 30
"""

from __future__ import annotations

import argparse
import json
import run as hb
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_LEVEL = REPO / "levels" / "example-forest.mblevel.json"
DEFAULT_COUNTS = (0, 40, 80, 120, 160, 200, 240)
DEFAULT_MIN_FPS = 30
DEFAULT_ATTEMPTS = 4
PROCESSES = ("Megabonk.exe", "Megabonk.x86_64", "Megabonk")
LOW_POPULATION_FRACTION = 0.8


def discard_reasons(report: dict, *, window_seconds: float, min_fps: int) -> list[str]:
    """Why this window must be measured again; empty means it is usable.

    Paused frames are UI frames: while a reward or death screen holds the run, Unity renders at a rate unrelated to
    gameplay and those frames are long, so a window containing any is diluted rather than measured.
    """
    reasons: list[str] = []
    if report["pausedFrames"]:
        reasons.append(f"{report['pausedFrames']} paused frames were UI frames")
    if report["frames"] < int(0.8 * window_seconds * min_fps):
        reasons.append(f"only {report['frames']} sampled frames in {window_seconds} s at {min_fps} fps minimum")
    if report["vSyncCount"] != 0:
        reasons.append("vsync came back on")
    if report["paused"]:
        reasons.append("the run is paused but no paused frames were recorded")
    return reasons


def suspect_reason(report: dict, *, target: int) -> str | None:
    """Why a kept window understates its enemy count, or None. Kept but flagged: a thinned population is still data."""
    if target and report["enemiesMax"] < LOW_POPULATION_FRACTION * target:
        return f"only {report['enemiesMax']} of {target} enemies were alive"
    return None


def plan(counts: list[int] | tuple[int, ...]) -> list[tuple[str, int]]:
    """One window per count, then the two controls at the largest: every mod tick off, then back on."""
    windows = [(f"count_{count}", count) for count in counts]
    top = max(counts) if counts else 0
    windows.append((f"count_{top}_modoff", top))
    windows.append((f"count_{top}_reenabled", top))
    return windows


def origin_from_state(state: dict) -> tuple[float, float, float]:
    """The player's position, to stand the swarm at and return them to between windows."""
    player = state.get("player")
    if not player or not player.get("position"):
        raise SystemExit("ABORT: no live player to stand the swarm around")
    x, y, z = player["position"][:3]
    return (x, y, z)


class Sweeper:
    """Drives one game instance through launch, load, and the window sequence."""

    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.game = hb.resolve_game_dir(hb.load_lookup())
        self.harness = self.game / "harness"
        self.log = self.game / "MelonLoader" / "Latest.log"

    def log_line(self, message: str) -> None:
        print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)

    def require(self, condition: bool, message: str) -> None:
        if not condition:
            raise SystemExit(f"ABORT: {message}")

    def sh(self, *command: str, timeout: int = 300) -> None:
        mise = shutil.which("mise")
        argv = [mise, "exec", "--", *command] if mise else list(command)
        proc = subprocess.run(argv, cwd=REPO, capture_output=True, text=True, timeout=timeout)
        self.require(proc.returncode == 0, f"{' '.join(argv)} failed: {proc.stdout} {proc.stderr}")

    def game_alive(self) -> bool:
        return any(subprocess.run(["pgrep", "-x", name], capture_output=True).returncode == 0 for name in PROCESSES)

    def send(self, payload: dict, timeout: float = 60.0) -> dict:
        outcome, result = hb.request_result(self.harness, payload, timeout)
        self.require(outcome == "done" and result is not None, f"{payload['command']}: {outcome}")
        self.require(result.get("ok") is not False, f"{payload['command']}: {result.get('error')}")
        return result.get("result") or {}

    def perf(self, action: str, **fields) -> dict:
        return self.send(hb.build_perf_command(action, **fields), timeout=120.0)

    def verb(self, command: str, **fields) -> dict:
        return self.send({"command": command, **fields})

    def wait_for_log(self, needle: str, timeout: float, start_offset: int = 0) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.log.exists():
                with self.log.open(errors="replace") as handle:
                    handle.seek(start_offset)
                    if needle in handle.read():
                        return True
            time.sleep(1)
        return False

    def launch_fresh(self) -> None:
        """Quit whatever is running and bring up a session with the harness and Steamworks answering."""
        if self.game_alive():
            try:
                self.send({"command": "quit"})
            except SystemExit:
                pass
            for _ in range(30):
                if not self.game_alive():
                    break
                time.sleep(1)
            for name in PROCESSES:
                subprocess.run(["pkill", "-x", name], capture_output=True)
            time.sleep(2)
        if self.args.relaunch:
            self.log.unlink(missing_ok=True)
            self.sh("task", "game:run", timeout=180)
        self.require(self.wait_for_log("DevHarness: enabled", 300), "the harness never came up after launch")
        self.require(self.game_alive(), "the game is not running after launch")
        verdict = hb.wait_for_steamworks_ready(lambda: hb.steam_ready_verdict(self.harness, 2.0), 180, alive=self.game_alive)
        self.require(verdict in ("ready", "offline"), f"Steamworks never became ready ({verdict})")
        self.log_line(f"harness up, Steamworks {verdict}")

    def load_with_retries(self) -> None:
        """Send the load until the kill floor arms: a load the game drops leaves no trace but a missing run."""
        command = hb.build_load_level_command(
            hb.to_game_path(Path(self.args.level).resolve()), map=self.args.map, tier=self.args.tier, seed=self.args.seed
        )
        for attempt in range(1, 6):
            offset = self.log.stat().st_size if self.log.exists() else 0
            try:
                self.send(command, timeout=120.0)
            except SystemExit as rejected:
                self.log_line(f"load attempt {attempt} rejected: {rejected}")
            if self.wait_for_log("KillFloor: armed", 75, offset):
                self.log_line(f"run started on load attempt {attempt}")
                return
            self.log_line(f"load attempt {attempt} did not arm the kill floor, retrying")
        raise SystemExit("ABORT: the run never started, the game is probably sitting at the main menu")

    def live(self, label: str) -> dict:
        """Gate a measurement on a real, unpaused, playing run, dismissing whatever reward screen got in the way."""
        state = self.verb("state")
        self.require(state["levelLoaded"], f"{label}: no level loaded")
        self.require(state["killFloorArmed"], f"{label}: kill floor not armed")
        self.require(not state["editor"], f"{label}: still in editor mode")
        self.require(not state["frozen"], f"{label}: run is frozen")
        status = self.perf("status")
        if status["paused"]:
            if self.dismiss_reward().get("windowWasOpen"):
                self.log_line(f"{label}: a reward window had the run paused")
            self.send({"command": "resume"})
            time.sleep(1)
            status = self.perf("status")
        self.require(not status["paused"], f"{label}: gameplay is paused")
        return status

    def dismiss_reward(self) -> dict:
        """Skip the open level-up without taking an upgrade, so XP from kill-floor deaths neither pauses the run nor drifts the build.

        An empty dict means nothing skippable was open, or a window the harness cannot skip is.
        """
        outcome, result = hb.request_result(self.harness, hb.build_dismiss_offers_command(None, True), 20.0)
        if outcome != "done" or result is None or result.get("ok") is False:
            return {}
        return result.get("result") or {}

    def measure(self, name: str, target: int, attempt: int, origin: tuple[float, float, float]) -> dict | None:
        """One window, or None when the gates say to take it again.

        The spawn stays outside the window. The teleport before it keeps the run alive and the swarm's shape
        comparable: a player knocked off the map is killed through PlayerHealth.KillPlayer, which bypasses both the
        Mirror stacks and the hit points the health verb sets, and a swarm left to spread out across the map is a
        different benchmark than one gathered at a point.
        """
        self.live(f"before {name}")
        self.send(hb.build_teleport_command(position=origin))
        time.sleep(0.5)
        self.perf("health", hp=self.args.hp)
        current = self.perf("status")["enemiesLast"]
        if target - current > 0:
            spawned = self.perf("spawn", count=target - current)
            self.log_line(f"  spawn: asked={spawned['requested']} got={spawned['spawned']} pool={spawned['enemies']}/{spawned['poolMax']}")
        self.perf("start")
        dismissed = 0
        deadline = time.time() + self.args.seconds
        while time.time() < deadline:
            time.sleep(1.0)
            closed = self.dismiss_reward()
            if closed.get("windowWasOpen"):
                dismissed += 1
                self.log_line(f"  skipped a reward window inside {name}")
        report = self.perf("report")
        tag = name if attempt == 1 else f"{name}#{attempt}"
        reasons = discard_reasons(report, window_seconds=self.args.seconds, min_fps=self.args.min_fps)
        if reasons:
            self.log_line(f"  {tag}: {'; '.join(reasons)}, measuring again")
            if self.dismiss_reward().get("windowWasOpen"):
                self.log_line(f"  {tag}: skipped the reward window that was still open")
            self.send({"command": "resume"})
            return None
        report["_target"] = target
        report["_window_seconds"] = self.args.seconds
        report["_rewardsSkipped"] = dismissed
        report["_attempt"] = attempt
        report["_suspect"] = suspect_reason(report, target=target)
        (self.args.out / f"{name}.json").write_text(json.dumps(report, indent=1))
        self.log_line(
            f"{tag:>23} target={target:3d} alive={report['enemiesMin']:3d}..{report['enemiesMax']:3d} "
            f"frames={report['frames']:5d} mean={report['meanMs']:6.2f} p50={report['p50Ms']:6.2f} "
            f"p90={report['p90Ms']:6.2f} p99={report['p99Ms']:7.2f} max={report['maxMs']:7.2f} "
            f"mod={report['modMsPerFrame']:6.3f}" + (f"  SUSPECT: {report['_suspect']}" if report["_suspect"] else "")
        )
        return report

    def window(self, name: str, target: int, origin: tuple[float, float, float]) -> dict:
        for attempt in range(1, self.args.attempts + 1):
            report = self.measure(name, target, attempt, origin)
            if report is not None:
                return report
        raise SystemExit(f"ABORT: {name} was unusable on all {self.args.attempts} attempts")

    def run(self) -> int:
        self.args.out.mkdir(parents=True, exist_ok=True)
        for stale in self.args.out.glob("*.json"):
            stale.unlink()

        self.log_line(f"game dir {self.game}")
        self.launch_fresh()
        self.load_with_retries()
        self.send(hb.build_spawns_command(False))
        self.send({"command": "invulnerable"})
        self.send(hb.build_editor_command(False))
        self.send({"command": "resume"})
        vsync = self.perf("vsync", enabled=False)
        self.require(vsync["vSyncCount"] == 0, f"vsync stayed on: {vsync}")
        self.perf("reset")
        time.sleep(3)
        self.log_line(f"run live: enemies={self.live('after setup')['enemiesLast']}")
        origin = origin_from_state(self.verb("state"))
        self.log_line(f"  standing at {origin}")

        for name, target in plan(self.args.counts):
            if name.endswith("_modoff"):
                self.perf("toggle", target="all", enabled=False)
            elif name.endswith("_reenabled"):
                self.perf("toggle", target="all", enabled=True)
            self.window(name, target, origin)
            self.log_line(f"  player at {(self.verb('state').get('player') or {}).get('position')} after {name}")

        (self.args.out / "status.json").write_text(json.dumps(self.perf("status"), indent=1))
        (self.args.out / "final_state.json").write_text(json.dumps(self.verb("state"), indent=1))
        self.log_line(f"sweep complete: {len(list(self.args.out.glob('count_*.json')))} windows in {self.args.out}")
        return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=Path("/tmp/perf"), help="where to write one JSON per window")
    parser.add_argument("--level", default=str(DEFAULT_LEVEL), help="level file to load and measure in")
    parser.add_argument(
        "--count",
        dest="counts",
        type=int,
        action="append",
        metavar="N",
        help=f"enemies to measure at, repeatable (0-{hb.PERF_MAX_ENEMIES}); defaults to {list(DEFAULT_COUNTS)}",
    )
    parser.add_argument("--seconds", type=float, default=20.0, help="length of each window")
    parser.add_argument("--min-fps", type=int, default=DEFAULT_MIN_FPS, help="below this average a window is retaken")
    parser.add_argument("--attempts", type=int, default=DEFAULT_ATTEMPTS, help="tries per window before giving up")
    parser.add_argument("--hp", type=int, default=None, help=f"hit points to park the player at (1-{hb.PERF_MAX_PLAYER_HP})")
    parser.add_argument("--map", type=int, default=None, help="eMap value to load instead of the level file's")
    parser.add_argument("--tier", type=int, default=None, help="tier to load")
    parser.add_argument("--seed", type=int, default=None, help="seed to load, so a sweep is reproducible")
    parser.add_argument("--no-relaunch", dest="relaunch", action="store_false", help="measure the run already loaded")
    parser.set_defaults(counts=list(DEFAULT_COUNTS), relaunch=True)
    args = parser.parse_args(argv)
    if any(count < 0 for count in args.counts):
        parser.error("counts must be 0 or greater")
    if args.seconds <= 0:
        parser.error("--seconds must be positive")
    return args


def main(argv: list[str] | None = None) -> int:
    return Sweeper(parse_args(argv)).run()


if __name__ == "__main__":
    sys.exit(main())
