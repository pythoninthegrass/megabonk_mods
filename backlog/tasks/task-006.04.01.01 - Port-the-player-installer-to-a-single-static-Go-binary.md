---
id: TASK-006.04.01.01
title: Port the player installer to a single static Go binary
status: In Progress
assignee: []
created_date: '2026-10-31T08:14:00Z'
updated_date: '2026-11-03 03:53'
labels:
  - tooling
dependencies: []
references:
  - 'https://github.com/bitfield/script'
  - docs/player-installer.md
documentation:
  - docs/player-installer.md
modified_files:
  - go/
  - taskfiles/package.yml
  - docs/player-installer.md
parent_task_id: TASK-006.04.01
priority: medium
type: feature
ordinal: 128000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The Python installer works but still asks the player for an interpreter: the 3.11 floor is met by a system python3 on current distros, not on older ones, and install.sh exists only to pick and gate it. A single static binary - CGO_ENABLED=0, cross-compiled - removes the interpreter problem entirely: the player downloads one file and runs it. Keep the package/manifest contract exactly as docs/player-installer.md defines it (megabonk-player-package/1, the install record, exit codes 0/1/2/3/4/10) so existing packages install unmodified and the Windows and macOS ports can inherit the same shape. Use bitfield/script only where its pipeline sugar genuinely beats os/exec; everything else is stdlib (archive/zip, encoding/json, os, path/filepath). The Python installer stays the reference implementation: port module by module (vdf, steam, gamebuild, manifest, content, proton, plan, ui, cli), compare against it on the same synthetic fixtures, and do not make Go the default path until the binary reproduces the live checks on the AlmaLinux host (discovery of the relocated Flatpak root, native-build refusal with exit 4, full install/check/uninstall, headless text progress).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A clean checkout cross-compiles with CGO_ENABLED=0 to one static binary per target (at least linux/amd64 and linux/arm64); file/ldd confirm no dynamic dependency beyond libc-not-at-all, and the binary runs on a host with no Go and no Python
- [ ] #2 The manifest contract is byte-compatible: load of megabonk-player-package/1, refusal of every malformed manifest the Python loader refuses (naming the same bad key), and vendor kind lookup behave identically
- [ ] #3 Full lifecycle on the synthetic Windows-layout trees the Python tests use - install, --check no-drift, drift repair naming exactly the missing files with exit 10, uninstall - matches the Python installer's behaviour and exit codes 0/1/2/3/4/10
- [ ] #4 On the AlmaLinux host's real layout: the relocated Flatpak root is found through its grant, the unmounted library is skipped, and the native-Linux build is refused with exit 4 and the Windows-build steps
- [ ] #5 Headless runs print the same numbered plain-text progress as the Python TextProgress; GUI dialogs are out of scope here (TASK-006.04.01.02)
- [ ] #6 Third-party Go dependencies are limited to what is justified in writing: bitfield/script only where pipeline sugar beats stdlib, with the final dependency list recorded in the task
- [ ] #7 Parity tests run the Go binary and the Python installer against identical fixtures and compare stdout, the install record, and exit codes; Python remains the reference until the Go binary reproduces the live host checks, and no docs advertise Go as the default before then
- [ ] #8 docs/player-installer.md gains the Go section (build targets, contract inheritance) and taskfiles produce the binary alongside the zip
- [ ] #9 Interactive versus headless is decided by an attached tty probed at /dev/tty (os.OpenFile plus ModeCharDevice, stdlib only, no golang.org/x/term) together with the session environment, and --non-interactive or MEGABONK_NON_INTERACTIVE forces TextProgress; no prompt ever reads stdin
- [ ] #10 Failure output matches the Python installer the parity harness compares: discovery failures name the candidates tried, why each was rejected and the exact retry flag (--library, --game-dir, --prefix, --proton), and a skipped optional step prints the command that finishes it without changing the exit code
- [ ] #11 Any download checks the HTTP status before writing the body, pins the host across redirects and requires TLS 1.2 or newer, so a 404 or captive-portal page reads as a missing asset and never as a sha256 mismatch
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
- [ ] #5 task check passes
- [ ] #6 Tests written first for ported logic
- [ ] #7 Docs updated
- [ ] #8 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Adopted plan (user-approved 2026-11-02)

Stdlib-only Go port under go/ (module github.com/pythoninthegrass/megabonk_mods/installer); bitfield/script evaluated and rejected - every subprocess call is a single exec with no pipelines, so os/exec covers it. Final third-party dependency list: empty. golang.org/x/term stays out: tty probe is os.OpenFile("/dev/tty", O_RDONLY|O_NONBLOCK|O_NOCTTY) + ModeCharDevice.

Build targets (amends AC #1): darwin/arm64 (dev-box native, runs parity against synthetic trees), linux/amd64 (player fleet + live mf evidence), windows/amd64 (built so TASK-006.04.02 inherits a proven shape; not executed in parity). linux/arm64 dropped per user. installer:verify-static: ldd "not a dynamic executable" on linux, PE32+ check on windows, darwin asserts libSystem is the only dylib. Parity runs the host-native binary only.

Phases:
1. Python reference gap-fill (parent AC #10/#11 wording, tests first): discovery failures name every candidate, why rejected, and the exact retry flag; environment-skipped steps print the manual command and keep the exit code. Go mirrors these strings byte-for-byte.
2. Scaffold: go/ module, cmd/megabonk-installer, taskfiles/installer.yml (installer:build CGO_ENABLED=0 cross to .tools/installer/, installer:test, installer:verify-static), task check gains a Go-presence-guarded step.
3. Module-by-module port, Go tests first mirroring each tests/test_player_installer_*.py, in contract order vdf, gamebuild, manifest, content, steam, proton, plan, ui, cli. Message strings copied verbatim; AC #2/#5/#10 are byte-parity requirements.
4. Parity harness tests/test_installer_parity.py: session fixture builds the binary (skips without Go), runs Go and Python against identical synthetic fixtures, compares stdout, stderr, install record, exit codes 0/1/2/3/4/10.
5. Docs: player-installer.md Go section (build targets, contract inheritance, arm64-x86_64 caveats, Go not yet default). Binaries land in .tools/installer/ alongside the zip, never inside it.

Out of scope: GUI dialogs (TASK-006.04.01.02), wm2 discovery-identity fix (parent AC #2, Python first), package zip contents unchanged.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Phase 1 (Python reference gap-fill, parent AC #10/#11 wording) implemented tests-first on this Linux maintainer host.

Added to steam.py: Candidate dataclass with REASON_MISSING/REASON_NO_STEAMAPPS/REASON_DUPLICATE/REASON_UNMOUNTED; client_candidates() and library_candidates() enumerate every probe with its accept/reject reason (client_roots/library_roots now filter the same enumeration, one source of truth); FlatpakProbe + flatpak_probe() report whether the persisted local-overrides file or the flatpak CLI answered, and flatpak_granted_paths delegates to it. cli._not_found_lines prints every client candidate with its reason, libraries searched/skipped with the reason and the exact --library retry flag (duplicates filtered out of the report), and the --game-dir/--home hints. A Flatpak-client library with granted != True now prints the finishing command: flatpak override --user --filesystem=<path> com.valvesoftware.Steam. A flatpak client found without any way to read grants prints the install-flatpak-or-pass---library note. ui.dialog_skip_note() returns the zenity/yad/kdialog install hint only on a desktop (display + controlling tty + no non-interactive force) with no backend; cli warns before progress starts. plan.build_plan names --prefix and the launch-once-to-create recipe when the prefix is unusable (and stops printing "at None" when there is no prefix at all); the wine-mode PlanError names --proton.

Real bug found on this host: Path.is_dir()/is_file()/exists() re-raise PermissionError for EACCES (not in pathlib's _ignore_error set), and an unreadable directory under /media crashed scan_for_libraries during every install. Discovery probes in steam.py now go through _is_dir/_is_file/_exists. The Go port must use os.Stat error-swallowing equivalents.

Test hygiene: test_player_installer_cli.py gains an autouse fixture pinning MOUNT_ROOTS=() and a neutral flatpak_probe; without it the real host's /media/steam grant and Flatpak overrides leaked into synthetic-tree tests and made the not-found test exit 4 against the real native Megabonk.

8 pytest failures (test_thps_attachments, test_build_thps_editable_level, two test_run wineserver cases) reproduce in a clean HEAD worktree without this change; they belong to unrelated in-flight THPS/boss-spawn work in the tree. Ruff clean; 128 installer tests pass.
<!-- SECTION:NOTES:END -->
