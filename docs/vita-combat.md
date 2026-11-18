# PS Vita Forest combat prototype

**Megabonk Vita Combat** (`MBVK00002`) is a standalone feasibility build, not a port of the shipped Unity player. It renders an orthographic 3D Forest graybox as a depth-tested triangle batch through GXM and [libvita2d](https://github.com/xerpi/libvita2d) at 960×544 with no MSAA. It uses original geometry and the Vita system font. The VPK does not bundle commercial game assets or Sony modules and requires no runtime plugins, shader compiler installation, or clock override.

## Build and install

Use VitaSDK 2026.08 with ARM GCC 15.2.0 and the VitaSDK `libvita2d` package. From the repository root, `mise exec -- task vita:combat` builds and validates `.tools/vita-combat/megabonk-vita-combat.vpk`. Override the SDK path with `VITASDK` or the build directory with `VITA_COMBAT_BUILD_DIR`. Run the portable simulation tests with `mise exec -- uv run pytest -n0 tests/test_vita_combat.py`.

Install the VPK with VitaShell or stage it and install it with a development SSH server that supports third-party VPKs. Launch **Megabonk Vita Combat** from LiveArea. This developer-only build uses the SDK's precompiled libvita2d shaders; review linked library distribution requirements before distributing a VPK.

## Physical play check

1. Press Cross at the title. The left stick moves the character; the right stick aims without changing movement. Releasing the right stick retains the most recent aim. The weapon fires automatically.
2. Defeat enemies and move over four cyan XP drops. Combat stops while the upgrade menu is open. Use D-pad Up or Down to highlight **Power** or **Haste**, then press and hold Cross. Level should change from 1 to 2 exactly once, and only the selected stat should change: damage rises from 1 to 2, or the shot interval drops from 18 to 15 simulation ticks. Movement, enemy pursuit, and firing should resume.
3. Start returns to the title. Square and Triangle do not enable benchmark controls during an ordinary run.

## Benchmark setup

Press Triangle at the title. D-pad Left or Right adjusts the live count in increments of 24 (24–240); Up selects **Gathered**, Down selects **Scattered**. Cross starts the run; Square resets it to the same initial state. Start returns to the title. To repeat a matched pair, keep the count unchanged and leave both sticks neutral.

Both layouts use the same enemy geometry, initial HP, AI, weapon targeting and viewport scale. Scattered starts with three times the spacing along both axes. Enemies pursue the player in both cases; the labels describe the initial layouts, not the spacing after pursuit. Benchmark runs do not take player damage or accumulate XP, and a defeated enemy is replaced at its initial position so the selected live count remains constant. Normal Play does not use these rules. This app provides the workload, not a measurement or a full-port viability verdict.

## PCH-2000 verification

Version 01.00 installed and launched on a physical PCH-2000. The playtest confirmed independent movement and aim, a single upgrade application, and resumed combat. Both benchmark layouts ran, and Square restored their starting positions. The tested enemy count was not recorded. This version does not capture timing or memory telemetry.
