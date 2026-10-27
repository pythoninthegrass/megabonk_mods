#!/usr/bin/env bash
# Offline-launch test harness: run exactly one game instance with a given
# MEGABONK_STEAM_FAIL_INIT setting, probe Steamworks readiness, and report.
#   tools/steamstub/offline_test.sh fail     # stub Init fails -> expect ready:false
#   tools/steamstub/offline_test.sh ok       # stub Init succeeds -> expect ready:true
set -uo pipefail
cd "$(dirname "$0")/../.."

MODE="${1:-ok}"
GAMEROOT="$(python3 scripts/game_paths.py | python3 -c 'import json,sys; print(json.load(sys.stdin)["game_dir"])')"
LOG="$GAMEROOT/MelonLoader/Latest.log"
HARNESS="$GAMEROOT/harness"
DEBUGLOG="$GAMEROOT/init_debug.log"

kill_all() {
  for pid in $(ps -axo pid,comm 2>/dev/null | grep -E 'Megabonk\.exe|wineserver|UnityCrashHandler64|winedevice' | awk '{print $1}'); do kill -9 "$pid" 2>/dev/null; done
  sleep 3
  pgrep -a Megabonk >/dev/null 2>&1 && { echo "WARN: game still alive"; }
}

if [ "$MODE" = "fail" ]; then export MEGABONK_STEAM_FAIL_INIT=1; else unset MEGABONK_STEAM_FAIL_INIT; fi

kill_all
rm -f "$DEBUGLOG"
log_lines_before=$(wc -l < "$LOG")

echo "== launching (MODE=$MODE, MEGABONK_STEAM_FAIL_INIT=${MEGABONK_STEAM_FAIL_INIT:-<unset>}) =="
task game:run >/dev/null 2>&1

for _ in $(seq 1 20); do
  grep -q 'DevHarness: enabled' "$LOG" && break
  sleep 2
done

echo "== stub Init branch log =="
if [ -f "$DEBUGLOG" ]; then sort "$DEBUGLOG" | uniq -c; else echo "(no init_debug.log written)"; fi

echo "== steam-ready probe =="
uv run scripts/run.py steam-ready >/dev/null 2>&1
latest=$(ls -t "$HARNESS/results"/*-steam-ready.json 2>/dev/null | head -1)
cat "$latest"; echo

echo "== state =="
uv run scripts/run.py state 2>/dev/null | tail -1

echo "== log tail =="
tail -n +$((log_lines_before + 1)) "$LOG" | grep -iE 'DevHarness|Steamworks|degrad|not initialized' | tail -10

echo "== process =="
ps -axo pid=,command= 2>/dev/null | grep 'Megabonk.exe' | grep -v grep || echo "NO GAME PROCESS"
