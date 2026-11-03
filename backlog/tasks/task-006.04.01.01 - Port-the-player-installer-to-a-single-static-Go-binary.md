---
id: TASK-006.04.01.01
title: Port the player installer to a single static Go binary
status: In Progress
assignee: []
created_date: '2026-10-31T08:14:00Z'
updated_date: '2026-11-03 06:32'
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
  - taskfiles/installer.yml
  - taskfile.yml
  - tests/test_installer_parity.py
  - tests/test_player_installer_plan.py
  - tests/test_player_installer_steam.py
  - tests/test_player_installer_vdf.py
  - scripts/player_installer/cli.py
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
- [x] #1 A clean checkout cross-compiles with CGO_ENABLED=0 to one static binary per target (at least linux/amd64 and linux/arm64); file/ldd confirm no dynamic dependency beyond libc-not-at-all, and the binary runs on a host with no Go and no Python
- [x] #2 The manifest contract is behavior-compatible: load of megabonk-player-package/1, refusal of every malformed manifest the Python loader refuses while naming the same bad key, and vendor kind lookup behave identically. Refusal messages are compared on stable anchors, not bytes.
- [x] #3 Full lifecycle on the synthetic Windows-layout trees the Python tests use - install, --check no-drift, drift repair naming exactly the missing files with exit 10, uninstall - matches the Python installer's behaviour and exit codes 0/1/2/3/4/10
- [x] #4 On the AlmaLinux host's real layout: the relocated Flatpak root is found through its grant, the unmounted library is skipped, and the native-Linux build is refused with exit 4 and the Windows-build steps
- [x] #5 Headless runs print numbered plain-text progress in the reference's N/M label format; GUI dialogs are out of scope here (TASK-006.04.01.02)
- [x] #6 Third-party Go dependencies are limited to what is justified in writing: bitfield/script only where pipeline sugar beats stdlib, with the final dependency list recorded in the task
- [x] #7 Parity tests run the Go binary and the Python installer against identical fixtures and compare exit codes, the install record parsed as JSON, the installed file trees, and stdout/stderr on message anchors; Python remains the reference until the Go binary reproduces the live host checks, and no docs advertise Go as the default before then
- [x] #8 docs/player-installer.md gains the Go section (build targets, contract inheritance) and taskfiles produce the binary alongside the zip
- [x] #9 Interactive versus headless is decided by an attached tty probed at /dev/tty (os.OpenFile plus ModeCharDevice, stdlib only, no golang.org/x/term) together with the session environment, and --non-interactive or MEGABONK_NON_INTERACTIVE forces TextProgress; no prompt ever reads stdin
- [x] #10 Failure output names the candidates tried, why each was rejected and the exact retry flag (--library, --game-dir, --prefix, --proton), and a skipped optional step prints the command that finishes it without changing the exit code; compared on stable anchors rather than byte-for-byte
- [x] #11 Any download checks the HTTP status before writing the body, pins the host across redirects and requires TLS 1.2 or newer, so a 404 or captive-portal page reads as a missing asset and never as a sha256 mismatch
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
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

## Contract amendment (user-approved 2026-11-03): byte parity -> semantic parity

Amends AC #2/#5/#7/#10 and Phase 3. The Go binary is contract-compatible, not byte-compatible. Exact: exit codes 0/1/2/3/4/10, the installed/repaired/removed file trees, the progress line format N/M label, and the install record compared as parsed JSON. Anchored: refusal and discovery messages must name the same offending path/key/flag and a stable verb phrase (checksum mismatch, missing from the package, is not valid JSON, unsafe path, no AssetBundle file, expected a .mblevel.json file, the top level must be a JSON object, no usable Proton prefix, pass --prefix, no wine binary found in the Proton tools under, pass --proton, Steam clients considered, Libraries searched/skipped, the flatpak override --user --filesystem= finishing command, the exit-4 native-build refusal); quoting style may differ. Freed: Python repr() quoting -> %q, json.dumps byte layout -> encoding/json, Python JSONDecodeError and UnicodeDecodeError text -> Go error text.

Consequences: internal/pyjson and internal/pyrepr are deleted and the UTF-8 codec-message machinery in internal/ppath goes with them (~1.4k lines); manifest and content move onto plain structs plus encoding/json with DisallowUnknownFields; ppath keeps only the slash-separated path semantics so the record stays portable. The Go test suite is the parity harness over golden scenarios plus unit tests for tricky locals (vdf parsing, path normalization, refusal paths) instead of a mirror of every tests/test_player_installer_*.py. Dependency list stays empty: bitfield/script remains rejected, no library reproduces Python's repr/JSON-error bytes without reimplementing them, so this is a scope cut rather than a dependency.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Phase 1 (Python reference gap-fill, parent AC #10/#11 wording) implemented tests-first on this Linux maintainer host.

Added to steam.py: Candidate dataclass with REASON_MISSING/REASON_NO_STEAMAPPS/REASON_DUPLICATE/REASON_UNMOUNTED; client_candidates() and library_candidates() enumerate every probe with its accept/reject reason (client_roots/library_roots now filter the same enumeration, one source of truth); FlatpakProbe + flatpak_probe() report whether the persisted local-overrides file or the flatpak CLI answered, and flatpak_granted_paths delegates to it. cli._not_found_lines prints every client candidate with its reason, libraries searched/skipped with the reason and the exact --library retry flag (duplicates filtered out of the report), and the --game-dir/--home hints. A Flatpak-client library with granted != True now prints the finishing command: flatpak override --user --filesystem=<path> com.valvesoftware.Steam. A flatpak client found without any way to read grants prints the install-flatpak-or-pass---library note. ui.dialog_skip_note() returns the zenity/yad/kdialog install hint only on a desktop (display + controlling tty + no non-interactive force) with no backend; cli warns before progress starts. plan.build_plan names --prefix and the launch-once-to-create recipe when the prefix is unusable (and stops printing "at None" when there is no prefix at all); the wine-mode PlanError names --proton.

Real bug found on this host: Path.is_dir()/is_file()/exists() re-raise PermissionError for EACCES (not in pathlib's _ignore_error set), and an unreadable directory under /media crashed scan_for_libraries during every install. Discovery probes in steam.py now go through _is_dir/_is_file/_exists. The Go port must use os.Stat error-swallowing equivalents.

Test hygiene: test_player_installer_cli.py gains an autouse fixture pinning MOUNT_ROOTS=() and a neutral flatpak_probe; without it the real host's /media/steam grant and Flatpak overrides leaked into synthetic-tree tests and made the not-found test exit 4 against the real native Megabonk.

8 pytest failures (test_thps_attachments, test_build_thps_editable_level, two test_run wineserver cases) reproduce in a clean HEAD worktree without this change; at the time they looked like unrelated in-flight THPS/boss-spawn work, but that reading was wrong - see "Unblocking task check" below. Ruff clean; 128 installer tests pass.

Adopted the semantic-parity contract (see the amendment in the plan): deleted the Python-formatting layer (Go pyjson writer/parser, pyrepr, ppath codec-error machinery) after manifest/content moved onto encoding/json structs; ppath keeps slash joins, parents, suffix, and the EACCES-safe stat probes. Parity harness compares exit codes, the install record parsed as JSON, file trees, and anchored messages.

## Go port landed (2026-11-03)

11 packages under go/internal plus cmd/megabonk-installer: 27 files, ~9.1k lines,
gofmt/vet/test clean, `go list -m all` is one line (stdlib only), CGO_ENABLED=0, the linux
binary is not dynamically linked (`task installer:verify-static`).

`tests/test_installer_parity.py` is the Go test suite of record: 25 scenarios, twin fixture
trees, the same argv through `python -m player_installer` and the host-native binary,
comparing exit codes, both streams, the game and prefix trees by digest, and the install
record as parsed JSON. Go unit tests cover only the awkward-to-reach locals (ppath, vdf,
proton registry, jsonx, manifest, content, steam, ui, cli flag seam).

Hermeticity: the harness sets `MEGABONK_MOUNT_ROOTS=` (a new seam in cli.py honoured by both
implementations, so a maintainer's mounted library cannot turn a not-found scenario into an
install) and writes a grant-less `local-overrides` file into each fixture home so the
persisted-override path answers before the host's flatpak CLI is asked. Parity caught one
real divergence: Go read an empty `MEGABONK_MOUNT_ROOTS` as "use the defaults" where Python
read it as "scan nothing"; fixed and pinned by `TestMountRootsHonoursTheEnvironment`.

Docs: docs/player-installer.md gained "The Go port" (targets, contract inheritance, tasks,
what is exact versus anchored, Go is not the default) and a still-pending entry for the
un-executed darwin/windows binaries.

## Cross-environment evidence for AC #1 and AC #4 (2026-11-03)

Checks on the current tree: `task installer:build` + `installer:verify-static` (three
targets, ELF statically linked, PE32+ and Mach-O, `go list -m all` one line);
`task installer:test` (11 packages); `installer:parity` 25/25; the installer pytest suites
211 passed; `task lint` clean, and `task check` is green end to end (1007 passed, 56 skipped) once the
8 failures were fixed separately in `800dfa1` and `ba05d15`.

AC #1, "runs on a host with no Go and no Python", is measured rather than inferred. One
throwaway driver (`/tmp/opencode/installer-crosscheck/driver.py`) builds each scenario
fixture once and runs the full lifecycle - install, `--check` no-drift, drift `--check`
(exit 10), repair, uninstall - in seven environments: `host-python`, `host-go`,
`ubuntu:24.04`, `fedora:42`, `thevakhovske/holoiso` (SteamOS-based), and inside the
dockurr/windows Windows 11 guest both the `windows/amd64` binary and a
`python -m player_installer` reference. All seven agree on exit codes, on stdout and stderr
after the harness scrubber, on the install record parsed as JSON, and on the installed and
final trees; the five platform-independent trees also match across platforms. `command -v`
in each image reports no `python`, `python3`, `go`, `pip` or `pip3`, and a `FROM scratch` image whose whole filesystem is 46 entries - the binary plus the
fixture tree, no `/bin/sh`, no interpreter, no libc - runs the same five steps with the
same exits, because `docker commit` chains the writable layer between them
(`/tmp/opencode/installer-crosscheck/scratch_probe.py`).

Windows runs are compared per platform against the guest's own Python reference rather than
the Linux host run: `windows_path` keeps an existing drive letter and only prefixes `Z:` for
drive-less paths, so the `DOTNET_ROOT` launch option legitimately differs between a Linux
host run and a native Windows run.

Windows-only port bug found by the guest run and fixed test-first: `filepath.Abs` and
`filepath.EvalSymlinks` return backslash paths, which were compared against slash-separated
install paths, so every zip member was refused as escaping the game directory.
`plan.resolve` and `steam.resolve` are now thin wrappers over `resolveWith(path, abs,
toSlash, eval)` seams that normalise both `Abs` and `EvalSymlinks` output, and
`TestResolveKeepsSlashSemanticsOnWindows` in both packages injects a backslash-returning
`Abs`, a working `ToSlash` and a native-form `EvalSymlinks` - red before the fix, green
after. Capturing guest output needs `Start-Process -RedirectStandardOutput/-RedirectStandardError`
(PowerShell `2>` writes UTF-16 NativeCommandError records) and `PYTHONIOENCODING=utf-8` for
the reference run.

AC #4, maintainer-host checks on the AlmaLinux host's real layout: Flatpak Steam with its
root relocated to `/media/steam`, the stale unmounted `/mnt/games/GameLibrary/Steam` entry
still in `libraryfolders.vdf`, and the native install present. Python and Go printed
byte-identical output with exit 4 (`Flatpak Steam may only read: /media/steam` plus the
Windows-build steps) for the full discovery run and for the `--library` probe and fake-HOME
runs. A real mod install on that host cannot go through the Go binary today: the installed
build is native Linux, which the installer refuses by design with exit 4.

AC #11 stays open deliberately: neither implementation has HTTP download code (`net/http`
and `urllib.request` are absent from both), vendor archives are verified from cache, so
there is no download path to test.

## Unblocking task check (2026-11-03)

The 8 failures were not all "someone else's in-flight work": the repo's own rule is that a
missing gitignored build product skips with a reason and failures are not expected, so the 6
in `test_thps_attachments.py` and `test_build_thps_editable_level.py` were a real gap - both
files read `.tools/thps1/warehouse/warehouse.obj` with no guard, while four sibling THPS
files carry `needs_extract` skipifs. Fixed centrally rather than file by file:
`tests/conftest.py` now declares `GENERATED_ARTIFACTS` (each product as `module.ATTRIBUTE` or
a repo-relative path) and a `pytest_runtest_makereport` wrapper turns a `FileNotFoundError`
whose `filename` resolves to an absent entry into a skip, so a test that forgets a local
guard still skips. It keys on the filename, so a product that exists but is malformed still
fails, and an unrelated missing file still fails - checked with a throwaway probe.

The 2 `test_run.py` wineserver failures were a different pair of problems: both inject a
fake server pid (`running_wineserver_pids -> [7]`) and never stub `os.kill`, unlike the
sibling test that records kills, and `wait_for_wineserver_to_exit` only caught
`ProcessLookupError` around the SIGKILL. On this host pid 7 is a root kworker, so the real
`os.kill` raised `PermissionError` and the "force-killed N" line claimed servers never
signalled. run.py now counts killed and refused pids separately and treats `EPERM` as a
server it cannot kill (pinned by a new test), and an autouse conftest fixture stubs `os.kill`
to raise, so a test that reaches a real kill fails with instructions instead of signalling a
live process. That tripwire flagged exactly those two tests across 1005 others.

Go mirror of the discovery-identity and prefix-selection change (parent AC #2, commit e7c3b0f): steam.GameCandidates / FindGameDir, isMegabonk/isIl2Cpp, commonChildren, PrefixCandidates and FindPrefix in go/internal/steam, reportPrefix and the Il2Cpp section of notFoundLines in go/internal/cli, with ReasonNotMegabonk, ReasonNoPrefix and ReasonNoDriveC as the anchored strings Python and Go share. FindInstall gained a prefixChosen argument so an explicit --prefix suppresses the ambiguity nag, matching the Python flag.

installDirFromManifests had the same manifest-matching bug as the Python side (it looked up appid/installdir as nested keys instead of searching the manifest's own section) and is fixed the same way, with the appid check skipping only manifests that state a different id.

Go tests: nine new cases in internal/steam (decoy rejected, manifest candidate ordering and ReasonMissing, manifest beats a folder merely named Megabonk, native build accepted, own-library prefix, only-other-usable prefix, two prefixes refused, drive_c reason) and four in internal/cli, plus four parity scenarios in tests/test_installer_parity.py. task installer:build/test/parity green (29 scenarios), task check green (1034 passed, 56 skipped).

AC #11 (download hardening) closed in scripts/asset_download.py (commit 5e2981a), the one stdlib fetcher both download call sites now use (build_player_package.fetch, install_melonloader._download); a test pins that no other file under scripts/ calls urlopen. Status is checked before the body is touched, so a 404, a login/captive-portal content type or an empty body reads as MissingAsset and never as a sha256 mismatch; https-only with a TLS 1.2 floor and certificate verification; oversized bodies refused from Content-Length and while reading; the digest verified against the pin before anything reaches the cache. Redirects stay on the original host except for the CDNs the known vendors hand off to (github.com -> githubusercontent.com, dotnetcli -> azureedge/microsoft), matched on subdomain boundaries so lookalikes are refused. The Go installer contains no network code - archives come from the package's vendor/ - so there was nothing to mirror on the port side. 29 unit tests drive the fetcher through fake openers plus integration tests at both call sites; live evidence: both real vendor URLs downloaded through their cross-host redirects with digests matching the pins, a real GitHub 404 read as MissingAsset, plain http and an off-list redirect host were refused, nothing was cached on failure, and a cold-cache --allow-download rebuilt the package from scratch. Real bug fixed in taskfiles/package.yml on the way: the documented ALLOW_DOWNLOAD=true never reached the script (Task CLI vars are not shell env, so the ${ALLOW_DOWNLOAD:-} test was always empty); it is now a declared task var rendered into the command, pinned by a task --dry test.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-11-03 05:18
---
AC #1 and AC #4 are now evidenced, not assumed. The same fixture and the same expected tree go through the full lifecycle (install, `--check` no-drift, drift `--check` with exit 10, repair, uninstall) in seven environments: the host's Python reference, the host Go binary, `ubuntu:24.04`, `fedora:42`, the SteamOS-based `thevakhovske/holoiso`, and in the Windows 11 Docker guest both the `windows/amd64` binary and a `python -m player_installer` reference. All seven agree on exit codes, both streams, the install record as parsed JSON, and the installed and final trees; the images have no `python`, `python3`, `go`, `pip` or `pip3`, and a `FROM scratch` image whose entire filesystem is 46 entries - the binary plus the fixture tree, no `/bin/sh`, no interpreter, no libc - runs the same five steps with the same exits. On the AlmaLinux maintainer host the Go binary prints byte-identical output to the Python reference (exit 4, relocated Flatpak root, stale unmounted library) on the real layout.

The Windows guest run caught one real port bug: `filepath.Abs` and `filepath.EvalSymlinks` return backslash paths there, and comparing them against slash-separated install paths made every zip member look like it escaped the game directory. `plan.resolve` and `steam.resolve` now normalise both through a `resolveWith` seam, pinned by a new test in each package that injects a backslash-returning `Abs` and a native-form `EvalSymlinks`.

`task check` is green (1007 passed, 56 skipped). The 8 failures this comment originally called pre-existing turned out to be two real defects, now fixed: six tests read a gitignored build product with no guard (the repo rule is that they skip), and two wineserver tests reached a real `os.kill` on an injected pid while `wait_for_wineserver_to_exit` caught only `ProcessLookupError` - see the "Unblocking task check" notes.

Open: AC #11, which has nothing to test until either implementation downloads anything (neither has HTTP code, vendor archives are verified from cache), so it needs either a download path or a scope cut; and switching the default install path to the Go binary, which is a maintainer decision, not a port gap.
---
<!-- COMMENTS:END -->
