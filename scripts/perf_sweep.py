"""Frame-time sweep: one gated measurement window per enemy count, against a live run.

Every window is checked before it is kept: a run that was paused, starved of frames, vsync-locked, or thinned of
enemies is measured again rather than recorded. See docs/performance.md for what the numbers mean and
docs/development.md for the profiler verbs this drives.

Run on the machine hosting the game:

    uv run scripts/perf_sweep.py --out /tmp/perf
    uv run scripts/perf_sweep.py --count 0 --count 120 --count 240 --seconds 30
    uv run scripts/perf_sweep.py --count 0 --count 240 --physics-arms 3    # the kinematic-rigidbody A/B
    uv run scripts/perf_sweep.py --count 0 --count 240 --anim-arms 3       # the animation-stop A/B
"""

from __future__ import annotations

import argparse
import json
import run as hb
import shlex
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
DEFAULT_STRUNG_OFFSET = 150.0
DEFAULT_CAPTURE_DIR = Path("/tmp/RenderDoc")
RENDERDOC_ENV = "ENABLE_VULKAN_RENDERDOC_CAPTURE"


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


def render_suspect_reason(report: dict, *, target: int) -> str | None:
    """Why a render-arm window is not a clean A/B, or None. Kept but flagged, like suspect_reason."""
    arm = report.get("_renderArm")
    window = dict(report)
    window["_controlArm"] = {"on": "rendon", "off": "rendoff"}.get(arm, arm)
    window.setdefault("_controlState", {"renderersOff": report.get("_renderersOff")})
    return control_suspect_reason(window, control="render", target=target)


CONTROLS = ("render", "physics", "animation")
CONTROL_ARMS = {
    "render": ("rendon", "rendoff"),
    "physics": ("physbase", "physkin"),
    "animation": ("animbase", "animoff"),
}
CONTROL_TICKS = {"render": "RenderCull", "physics": "PhysicsFreeze", "animation": "AnimationCull"}
CONTROL_STATUS_KEYS = {"render": "renderCull", "physics": "physicsFreeze", "animation": "animationCull"}
CONTROL_COUNTERS = {"render": "renderersOff", "physics": "rigidbodiesKinematic", "animation": "behavioursOff"}
CONTROL_WORDS = {
    "render": ("render cull", "disabled", "renderers", "with rendering asked for"),
    "physics": ("physics freeze", "kinematicised", "rigidbodies", "with the solver asked for"),
    "animation": ("animation cull", "stopped", "animation components", "with animation asked for"),
}
FIDELITY_PROBES = (
    "Enemy.MyFixedUpdate",
    "EnemyMovementRb.MyFixedUpdate",
    "AnimatedMesh.Update",
    "EnemyManager.FixedUpdate",
)


def control_plan(counts: list[int] | tuple[int, ...], repeats: int, control: str) -> list[tuple[str, int, bool]]:
    """Two windows per count per repeat for one control, arms strictly alternating and the leading arm flipped every repeat.

    The first arm is the ordinary run; the second takes that control's work out with everything else still running. The
    window names carry the repeat so the two arms are never confused across sessions. Cost walks upward through a
    session, so an arm that is always measured second would absorb that drift alone.
    """
    if control not in CONTROLS:
        raise SystemExit(f"ABORT: unknown control '{control}'; expected one of {', '.join(CONTROLS)}")
    base, armed = CONTROL_ARMS[control]
    windows: list[tuple[str, int, bool]] = []
    for count in counts:
        for repeat in range(1, repeats + 1):
            for is_armed in ((False, True) if repeat % 2 else (True, False)):
                windows.append((f"count_{count}_{armed if is_armed else base}_r{repeat}", count, is_armed))
    return windows


def control_arm_payload(control: str, armed: bool) -> dict:
    """The perf payload for one arm: the verb is the control's name and `enabled` says whether its work is wanted."""
    if control not in CONTROLS:
        raise SystemExit(f"ABORT: unknown control '{control}'; expected one of {', '.join(CONTROLS)}")
    return {"action": control, "enabled": not armed}


def tick_ms_per_frame(report: dict, tick_name: str) -> float | None:
    """Per-frame cost of one harness tick, or None when the window never ran or the tick never did."""
    frames = report.get("frames") or 0
    tick = next((entry for entry in report.get("ticks") or [] if entry.get("name") == tick_name), None)
    if not frames or tick is None:
        return None
    return round((tick.get("ms") or 0) / frames, 6)


def probes_ms_per_frame(report: dict) -> dict[str, float]:
    """ms/frame for the stock probes that show whether an arm changed work it was not meant to touch."""
    frames = report.get("frames") or 0
    if not frames:
        return {}
    by_name = {entry.get("name"): entry for entry in report.get("probes") or []}
    return {name: round((by_name[name].get("ms") or 0) / frames, 6) if name in by_name else 0.0 for name in FIDELITY_PROBES}


def control_suspect_reason(window: dict, *, control: str, target: int) -> str | None:
    """Why one control's window is not a clean A/B, or None. Kept but flagged, like suspect_reason."""
    if control not in CONTROL_ARMS:
        return None
    label, past, noun, baseline_words = CONTROL_WORDS[control]
    base, armed = CONTROL_ARMS[control]
    arm = window.get("_controlArm")
    if arm not in (base, armed):
        return None
    held = (window.get("_controlState") or {}).get(CONTROL_COUNTERS[control]) or 0
    if arm == base:
        return f"the {label} still {past} {held} {noun} {baseline_words}" if held else None
    if target and not held:
        return f"the {label} {past} no {noun} at {target} enemies"
    if not target and held:
        return f"the {label} {past} {held} {noun} with no enemies alive"
    return None


def other_control_suspect_reason(status: dict, control: str) -> str | None:
    """Why a window that should hold one control armed holds too many, or None.

    Two armed controls measure neither of them: the window is the A/B of both at once and neither figure can be
    attributed. This reads the harness's own account of what is armed rather than the sweep's intent.
    """
    strangers = [name for name in CONTROLS if name != control and (status.get(CONTROL_STATUS_KEYS[name]) or {}).get("armed")]
    if not strangers:
        return None
    return f"{', '.join(strangers)} armed as well as {control}"


def render_plan(counts: list[int] | tuple[int, ...], repeats: int) -> list[tuple[str, int, bool]]:
    """The render-only A/B: the render control of the same machinery, with its third element read as render-on."""
    return [(name, target, not armed) for name, target, armed in control_plan(counts, repeats, "render")]


def render_arm_payload(render_on: bool) -> dict:
    """The perf payload for one arm: `enabled` says whether enemy rendering is wanted, so the off arm sends false."""
    return control_arm_payload("render", not render_on)


def cull_ms_per_frame(report: dict) -> float | None:
    """Per-frame cost of the harness's own cull tick, or None when it never ran. The off arm pays it, so the split needs it."""
    return tick_ms_per_frame(report, CONTROL_TICKS["render"])


def player_start_suspect_reason(
    position: list[float] | None, origin: tuple[float, float, float] | None, tolerance: float = 8.0
) -> str | None:
    """Why a window did not start where it was told to, or None.

    The gate catches a teleport that did not land, which leaves the player hundreds of units from the swarm. It is
    not a gate on crowd shoving: 240 enemies piled on the standing point push the player a few units during the
    settle, and windows measured there have offsets of 2-5 units.
    """
    if not position or not origin:
        return None
    distance = sum((position[i] - origin[i]) ** 2 for i in range(3)) ** 0.5
    if distance <= tolerance:
        return None
    return f"the player was {distance:.1f} units from the fixed point at window start"


def plan(counts: list[int] | tuple[int, ...]) -> list[tuple[str, int, bool | None]]:
    """One window per count, then the two controls at the largest: every mod tick off, then back on."""
    windows = [(f"count_{count}", count, None) for count in counts]
    top = max(counts) if counts else 0
    windows.append((f"count_{top}_modoff", top, None))
    windows.append((f"count_{top}_reenabled", top, None))
    return windows


def render_plan(counts: list[int] | tuple[int, ...], repeats: int) -> list[tuple[str, int, bool]]:
    """Two windows per count per repeat, arms strictly alternating and the leading arm flipped every repeat.

    rendon is the ordinary run, rendoff hides only the enemy renderers with AI, physics and animation still
    running. The window names carry the repeat so the two arms are never confused across sessions. Cost walks
    upward through a session, so an arm that is always measured second would absorb that drift alone.
    """
    windows: list[tuple[str, int, bool]] = []
    for count in counts:
        for repeat in range(1, repeats + 1):
            for render_on in ((True, False) if repeat % 2 else (False, True)):
                arm = "rendon" if render_on else "rendoff"
                windows.append((f"count_{count}_{arm}_r{repeat}", count, render_on))
    return windows


def origin_from_state(state: dict) -> tuple[float, float, float]:
    """The player's position, to stand the swarm at and return them to between windows."""
    player = state.get("player")
    if not player or not player.get("position"):
        raise SystemExit("ABORT: no live player to stand the swarm around")
    x, y, z = player["position"][:3]
    return (x, y, z)


def strung_position(origin: tuple[float, float, float], offset: float) -> tuple[float, float, float]:
    """Where the strung-out density puts the player: a fixed walk away along +X, the swarm left behind at the origin."""
    x, y, z = origin
    return (x + offset, y, z)


def capture_trigger_batch() -> list:
    """The menu-driver input that fires RenderDoc's capture hotkey."""
    return [["key", "KEY_F12"]]


def startup_dismiss_batch() -> list:
    """The menu-driver input that clears the Photosensitivity Warning a Proton launch shows on every boot.

    A load-level sent while it is up returns no MapData, so the sweep drives Enter once after launch
    instead of burning load retries on it.
    """
    return [["key", "KEY_ENTER"]]


def pair_captures(before: dict[str, float], after: dict[str, float]) -> list[str]:
    """The capture files that appeared during a window, oldest first, so capture i maps to trigger i."""
    return sorted((name for name in after if name not in before and name.endswith(".rdc")), key=after.__getitem__)


def snapshot_captures(directory: Path) -> dict[str, float]:
    """Every capture file's mtime in a capture directory; a missing directory is an empty snapshot."""
    if not directory.is_dir():
        return {}
    return {entry.name: entry.stat().st_mtime for entry in directory.iterdir() if entry.is_file()}


class Sweeper:
    """Drives one game instance through launch, load, and the window sequence."""

    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.game = hb.resolve_game_dir(hb.load_lookup())
        self.harness = self.game / "harness"
        self.log = hb.latest_log_path(self.game)
        self.menu_service_started = False

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

    def game_pid(self) -> int | None:
        for name in PROCESSES:
            proc = subprocess.run(["pgrep", "-x", name], capture_output=True, text=True)
            if proc.returncode == 0:
                return int(proc.stdout.split()[0])
        return None

    def require_renderdoc_armed(self) -> None:
        """Captures only ever land if the game was launched with the RenderDoc Vulkan layer enabled."""
        pid = self.game_pid()
        environ = Path(f"/proc/{pid}/environ") if pid else None
        armed = environ and environ.exists() and RENDERDOC_ENV.encode() + b"=1" in environ.read_bytes().split(b"\0")
        self.require(bool(armed), f"the game (pid {pid}) was not launched with {RENDERDOC_ENV}=1, captures would never land")

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
            if self.args.launch_cmd:
                self.sh(*shlex.split(self.args.launch_cmd))
            else:
                self.sh("task", "game:run", timeout=180)
        self.require(self.wait_for_log("DevHarness: enabled", 300), "the harness never came up after launch")
        self.require(self.game_alive(), "the game is not running after launch")
        verdict = hb.wait_for_steamworks_ready(lambda: hb.steam_ready_verdict(self.harness, 2.0), 180, alive=self.game_alive)
        self.require(verdict in ("ready", "offline"), f"Steamworks never became ready ({verdict})")
        self.log_line(f"harness up, Steamworks {verdict}")

    def load_with_retries(self) -> None:
        """Send the load until the kill floor arms: a load the game drops leaves no trace but a missing run.

        A Proton launch parks the Photosensitivity Warning over the main menu, and a load sent while it is up is
        refused with no MapData, so that refusal earns an Enter through the menu driver before the retry.
        """
        command = hb.build_load_level_command(
            hb.to_game_path(Path(self.args.level).resolve()), map=self.args.map, tier=self.args.tier, seed=self.args.seed
        )
        for attempt in range(1, 6):
            offset = self.log.stat().st_size if self.log.exists() else 0
            try:
                self.send(command, timeout=120.0)
            except SystemExit as rejected:
                self.log_line(f"load attempt {attempt} rejected: {rejected}")
                if "no MapData" in str(rejected):
                    self.dismiss_startup_warning()
            if self.wait_for_log("KillFloor: armed", 75, offset):
                self.log_line(f"run started on load attempt {attempt}")
                return
            self.log_line(f"load attempt {attempt} did not arm the kill floor, retrying")
        raise SystemExit("ABORT: the run never started, the game is probably sitting at the main menu")

    def live(self, label: str) -> dict:
        """Gate a measurement on a real, unpaused, playing run, dismissing whatever reward screen got in the way.

        A level-up storm (several rewards queued from one burst of kills) re-pauses the run the moment it is resumed,
        so the dismiss-and-resume cycle gets a few tries before the gate gives up on this window.
        """
        state = self.verb("state")
        self.require(state["levelLoaded"], f"{label}: no level loaded")
        self.require(state["killFloorArmed"], f"{label}: kill floor not armed")
        self.require(not state["editor"], f"{label}: still in editor mode")
        self.require(not state["frozen"], f"{label}: run is frozen")
        status = self.perf("status")
        for _ in range(4):
            if not status["paused"]:
                return status
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

    def trigger_capture(self) -> None:
        """Fire RenderDoc's capture hotkey through the stock-menu input driver."""
        proc = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "run.py"), "menu", "drive", json.dumps(capture_trigger_batch())],
            cwd=REPO,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.require(proc.returncode == 0, f"capture trigger failed: {proc.stdout} {proc.stderr}")

    def ensure_menu_service(self) -> None:
        """A menu service left over from an earlier session is fine to reuse; anything else is fatal."""
        proc = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "run.py"), "menu", "start"],
            cwd=REPO,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode != 0 and "already running" not in proc.stdout + proc.stderr:
            self.require(False, f"menu service start failed: {proc.stdout} {proc.stderr}")
        self.menu_service_started = True

    def dismiss_startup_warning(self) -> None:
        """Best-effort Enter for the Photosensitivity Warning; a host without the menu driver only logs and moves on.

        The load retries remain the backstop, so nothing here is fatal.
        """
        try:
            start = subprocess.run(
                [sys.executable, str(REPO / "scripts" / "run.py"), "menu", "start"],
                cwd=REPO,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if start.returncode != 0 and "already running" not in start.stdout + start.stderr:
                self.log_line(f"startup Enter skipped: menu start failed: {start.stdout} {start.stderr}")
                return
            self.menu_service_started = True
            drive = subprocess.run(
                [sys.executable, str(REPO / "scripts" / "run.py"), "menu", "drive", json.dumps(startup_dismiss_batch())],
                cwd=REPO,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if drive.returncode != 0:
                self.log_line(f"startup Enter failed: {drive.stdout} {drive.stderr}")
            else:
                self.log_line("drove Enter for the Photosensitivity Warning")
        except subprocess.TimeoutExpired:
            self.log_line("startup Enter timed out, the load retries will cover it")

    def collect_captures(self, name: str, attempt: int, before: dict[str, float]) -> list[str]:
        """Move the window's new capture files under the sweep's out directory and name them in the window JSON."""
        after = snapshot_captures(self.args.capture_dir)
        captured = pair_captures(before, after)
        if len(captured) < self.args.captures:
            self.log_line(f"  {name}: only {len(captured)} of {self.args.captures} captures landed")
        destination = self.args.out / "captures"
        destination.mkdir(parents=True, exist_ok=True)
        paths = []
        for index, path in enumerate(captured):
            label = f"{name}#{attempt}" if attempt > 1 else name
            moved = destination / f"{label}_{index}.rdc"
            shutil.move(self.args.capture_dir / path, moved)
            paths.append(moved.name)
        return paths

    def measure(
        self,
        name: str,
        target: int,
        attempt: int,
        origin: tuple[float, float, float],
        render_on: bool | None = None,
        control: str | None = None,
        armed: bool | None = None,
    ) -> dict | None:
        """One window, or None when the gates say to take it again.

        The spawn stays outside the window. The teleport before it keeps the run alive and the swarm's shape
        comparable: a player knocked off the map is killed through PlayerHealth.KillPlayer, which bypasses both the
        Mirror stacks and the hit points the health verb sets, and a swarm left to spread out across the map is a
        different benchmark than one gathered at a point.
        """
        control = control or ("render" if render_on is not None else None)
        if control is not None and armed is None:
            armed = not render_on
        self.live(f"before {name}")
        self.send(hb.build_teleport_command(position=origin))
        time.sleep(0.5)
        player_start = (self.verb("state").get("player") or {}).get("position")
        self.perf("health", hp=self.args.hp)
        current = self.perf("status")["enemiesLast"]
        if target - current > 0:
            spawned = self.perf("spawn", count=target - current)
            self.log_line(f"  spawn: asked={spawned['requested']} got={spawned['spawned']} pool={spawned['enemies']}/{spawned['poolMax']}")
        if self.args.density == "strung":
            self.send(hb.build_teleport_command(position=list(strung_position(origin, self.args.strung_offset))))
            time.sleep(0.5)
        control_info = None
        if control is not None:
            control_info = self.perf(**control_arm_payload(control, bool(armed)))
        position_before = self.perf("status").get("enemyPositionSum")
        before = snapshot_captures(self.args.capture_dir) if self.args.captures else {}
        self.perf("start")
        dismissed = 0
        triggers = [self.args.seconds * (i + 1) / (self.args.captures + 1) for i in range(self.args.captures)]
        started = time.time()
        deadline = started + self.args.seconds
        while time.time() < deadline:
            time.sleep(1.0)
            while triggers and time.time() - started >= triggers[0]:
                triggers.pop(0)
                self.trigger_capture()
            closed = self.dismiss_reward()
            if closed.get("windowWasOpen"):
                dismissed += 1
                self.log_line(f"  skipped a reward window inside {name}")
        report = self.perf("report")
        status_after = self.perf("status")
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
        report["_density"] = self.args.density
        if self.args.density == "strung":
            report["_strungOffset"] = self.args.strung_offset
        if control is not None:
            report["_control"] = control
            report["_controlArm"] = CONTROL_ARMS[control][1] if armed else CONTROL_ARMS[control][0]
            report["_controlState"] = {k: v for k, v in (control_info or {}).items() if k != "enabled"}
            report["_controlMsPerFrame"] = tick_ms_per_frame(report, CONTROL_TICKS[control])
            report["_probesMsPerFrame"] = probes_ms_per_frame(report)
            if control == "render":
                report["_renderArm"] = "off" if armed else "on"
                report["_renderersOff"] = (control_info or {}).get("renderersOff")
                report["_cullMsPerFrame"] = cull_ms_per_frame(report)
        report["_positionSumBefore"] = position_before
        report["_positionSumAfter"] = status_after.get("enemyPositionSum")
        report["_playerAtOrigin"] = player_start
        report["_origin"] = list(origin)
        if self.args.captures:
            report["_captures"] = self.collect_captures(name, attempt, before)
        suspects = [
            reason
            for reason in (
                suspect_reason(report, target=target),
                control_suspect_reason(report, control=control, target=target) if control else None,
                other_control_suspect_reason(status_after, control) if control else None,
                player_start_suspect_reason(player_start, origin),
            )
            if reason
        ]
        report["_suspect"] = "; ".join(suspects) if suspects else None
        (self.args.out / f"{name}.json").write_text(json.dumps(report, indent=1))
        render_suffix = ""
        if "_renderArm" in report:
            cull = report["_cullMsPerFrame"]
            render_suffix = f" render={report['_renderArm']} renderersOff={report['_renderersOff']}" + (
                f" cull={cull:.3f}ms/f" if cull is not None else ""
            )
        elif "_controlArm" in report:
            cost = report["_controlMsPerFrame"]
            counters = " ".join(f"{k}={v}" for k, v in sorted((report["_controlState"] or {}).items()) if isinstance(v, int))
            render_suffix = f" {report['_control']}={report['_controlArm']} {counters}" + (
                f" control={cost:.3f}ms/f" if cost is not None else ""
            )
        self.log_line(
            f"{tag:>23} target={target:3d} alive={report['enemiesMin']:3d}..{report['enemiesMax']:3d} "
            f"frames={report['frames']:5d} mean={report['meanMs']:6.2f} p50={report['p50Ms']:6.2f} "
            f"p90={report['p90Ms']:6.2f} p99={report['p99Ms']:7.2f} max={report['maxMs']:7.2f} "
            f"mod={report['modMsPerFrame']:6.3f} gc={report['gcPauseMsPerFrame']:6.3f}"
            + (f" density={self.args.density}" if self.args.density != "gathered" else "")
            + render_suffix
            + (f"  SUSPECT: {report['_suspect']}" if report["_suspect"] else "")
        )
        return report

    def window(
        self,
        name: str,
        target: int,
        origin: tuple[float, float, float],
        render_on: bool | None = None,
        control: str | None = None,
        armed: bool | None = None,
    ) -> dict:
        for attempt in range(1, self.args.attempts + 1):
            report = self.measure(name, target, attempt, origin, render_on=render_on, control=control, armed=armed)
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

        if self.args.captures:
            self.require_renderdoc_armed()
            self.ensure_menu_service()
            self.log_line(
                f"capture mode: {self.args.captures} RenderDoc frames per window; capture runs perturb frame times, "
                "so timing tables come from capture-free runs"
            )

        repeats = self.args.render_arms or self.args.physics_arms or self.args.anim_arms
        windows = (
            control_plan(self.args.counts, repeats, self.args.control)
            if self.args.control
            else plan(self.args.counts)
        )
        if self.args.control:
            for other in CONTROLS:
                if other != self.args.control:
                    self.perf(**control_arm_payload(other, False))
            self.log_line(f"control A/B: {self.args.control}, {repeats} repeats per arm, other controls left disarmed")
        try:
            for name, target, is_armed in windows:
                if name.endswith("_modoff"):
                    self.perf("toggle", target="all", enabled=False)
                elif name.endswith("_reenabled"):
                    self.perf("toggle", target="all", enabled=True)
                self.window(
                    name,
                    target,
                    origin,
                    control=self.args.control,
                    armed=is_armed if self.args.control else None,
                )
                self.log_line(f"  player at {(self.verb('state').get('player') or {}).get('position')} after {name}")
        finally:
            for control in CONTROLS:
                try:
                    self.perf(**control_arm_payload(control, False))
                except SystemExit as failure:
                    self.log_line(f"{control} restore failed: {failure}")
            if self.args.captures or self.menu_service_started:
                subprocess.run([sys.executable, str(REPO / "scripts" / "run.py"), "menu", "stop"], cwd=REPO, capture_output=True)

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
    parser.add_argument(
        "--density",
        choices=["gathered", "strung"],
        default="gathered",
        help="gathered stands the swarm at the player; strung spawns it there and walks the player --strung-offset "
        "away before the window, so contact-dependent cost falls out of the A/B",
    )
    parser.add_argument("--strung-offset", type=float, default=DEFAULT_STRUNG_OFFSET, help="world units along +X for --density strung")
    parser.add_argument("--captures", type=int, default=0, help="RenderDoc frames to trigger inside each window (0 = none)")
    parser.add_argument("--capture-dir", type=Path, default=DEFAULT_CAPTURE_DIR, help="where RenderDoc writes .rdc files")
    parser.add_argument(
        "--launch-cmd",
        default=None,
        help="how to relaunch the game between sweeps instead of 'task game:run', e.g. a systemd unit on a "
        "direct-Proton host; only used when --relaunch is on (the default)",
    )
    parser.add_argument("--map", type=int, default=None, help="eMap value to load instead of the level file's")
    parser.add_argument("--tier", type=int, default=None, help="tier to load")
    parser.add_argument("--seed", type=int, default=None, help="seed to load, so a sweep is reproducible")
    parser.add_argument("--no-relaunch", dest="relaunch", action="store_false", help="measure the run already loaded")
    parser.add_argument(
        "--render-arms",
        type=int,
        default=None,
        metavar="N",
        help="replace the count ladder with the render-only A/B: per count, N alternating rendon/rendoff window pairs "
        "with the enemy renderers culled in the off arm",
    )
    parser.add_argument(
        "--physics-arms",
        type=int,
        default=None,
        metavar="N",
        help="replace the count ladder with the physics A/B: per count, N alternating physbase/physkin window pairs "
        "with the live enemies' rigidbodies made kinematic in the kinematic arm",
    )
    parser.add_argument(
        "--anim-arms",
        type=int,
        default=None,
        metavar="N",
        help="replace the count ladder with the animation A/B: per count, N alternating animbase/animoff window pairs "
        "with the live enemies' animation components stopped in the off arm",
    )
    parser.set_defaults(counts=None, relaunch=True)
    args = parser.parse_args(argv)
    if args.counts is None:
        args.counts = list(DEFAULT_COUNTS)
    if any(count < 0 for count in args.counts):
        parser.error("counts must be 0 or greater")
    if args.seconds <= 0:
        parser.error("--seconds must be positive")
    if args.strung_offset < 0:
        parser.error("--strung-offset must be 0 or greater")
    arm_flags = (("--render-arms", "render", args.render_arms), ("--physics-arms", "physics", args.physics_arms), ("--anim-arms", "animation", args.anim_arms))
    for flag, _, value in arm_flags:
        if value is not None and value < 1:
            parser.error(f"{flag} must be 1 or more")
    args.control = next((name for _, name, value in arm_flags if value), None)
    if sum(1 for _, _, value in arm_flags if value) > 1:
        parser.error("--render-arms, --physics-arms and --anim-arms are mutually exclusive: two armed controls measure neither")
    if not 0 <= args.captures <= 8:
        parser.error("--captures must be between 0 and 8")
    return args


def main(argv: list[str] | None = None) -> int:
    return Sweeper(parse_args(argv)).run()


if __name__ == "__main__":
    sys.exit(main())
