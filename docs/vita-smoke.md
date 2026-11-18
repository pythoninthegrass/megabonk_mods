# PS Vita hardware smoke test

The smoke test is a standalone VitaSDK app (`MBVK00001`), not a Megabonk build. It uses two software-drawn framebuffers, no Unity or game data, and no runtime plugins or clock overrides.

## Build

Use VitaSDK release 2026.08 with ARM GCC 15.2.0, CMake 3.20 or newer, and the repo's `mise`, `task`, and `uv` tools. Set `VITASDK` if it is not at `$HOME/.local/opt/vitasdk`. Run `mise exec -- task vita:smoke` from the repo root. It builds and validates `.tools/vita-smoke/megabonk-vita-smoke.vpk`. Set `VITA_SMOKE_BUILD_DIR` to a fresh directory to verify a clean build; compare the extracted entries rather than the archive hash because VitaSDK's packer stores entry timestamps. The host metrics test is `mise exec -- uv run pytest -n0 tests/test_vita_smoke.py`.

## Physical console

1. On the PCH-2000, note the firmware and disable any per-title or global clock overrides before booting the app. The app records actual ARM, bus, GPU and GPU crossbar clocks in MHz; confirm they are stock rather than inferring it from the absence of clock setters.
2. Copy the VPK into the console's downloads directory through VitaShell USB mode, or stage it over SFTP if the development SSH server is running. Install it in VitaShell, then launch **Megabonk Vita Smoke** from LiveArea. The package does not require the development SSH server to run.
3. Leave the app in the foreground for at least 10 seconds, without suspending or opening an overlay. Rotate the left and right physical sticks separately through their full travel. Check that each square's cursor moves independently and that each square turns green after crossing the low and high thresholds on both axes.
4. Press Cross to write `ux0:data/megabonk-vita-smoke/result.txt`. A green bar means the report was saved; a red bar means the write failed. Press Start to exit. Copy the report back and record the observed stick behavior with it.

Frame times are intervals between completed vblank waits, including display pacing, not CPU or GPU execution times. The report includes sample count and min/mean/max in microseconds. MAIN and CDRAM free-pool deltas are sampled peaks relative to the first in-process query, before framebuffer allocation but after process startup; they are not total process memory. The report also gives the explicit 1 MiB newlib reservation and allocated CDRAM framebuffer block separately. A failed free-memory query is reported as missing data, not zero usage.

## PCH-2000 sample

The app booted on firmware 3.74, and both physical sticks independently exercised their on-screen squares. The controller reported left X/Y and right X at 0–255, and right Y at 0–232. Over 253 frame intervals (about 4.2 seconds, shorter than the 10-second checklist), frame times were 16.635 ms minimum, 16.683 ms mean, and 16.729 ms maximum. The peak free-pool decrease was 0 bytes for MAIN after startup and 4 MiB for CDRAM; the separate newlib heap reservation was 1 MiB. The report captured 333/222/41/111 MHz for ARM/bus/GPU/crossbar. The app does not set clocks, but the report alone does not verify that system or per-title overrides were disabled.

A second run captured 1,435 intervals (about 24 seconds) at 16.611 ms minimum, 16.683 ms mean, and 16.756 ms maximum. Both sticks passed again, and the memory and clock readings matched the first run. The PSVshell overlay displayed the same clocks in white (Default mode) for all four domains, confirming that PSVshell was not forcing a clock during this check. There was no saved global or smoke-app profile. This run included the overlay check and does not establish behavior with plugins disabled.
