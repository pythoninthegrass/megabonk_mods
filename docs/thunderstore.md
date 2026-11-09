# Thunderstore packaging and releases

The public product is **Megabonk Level Editor**; its package identifier is
`Megabonk_Level_Editor`. The repository remains `megabonk_mods`, the assembly is
`MegabonkLevels.Mod.dll` and the stable BepInEx GUID is `megabonklevels.runtime`.
The team namespace is configured in the root `thunderstore.toml`.

## Package source and build

`pkg/` contains the package's player-facing README, reference manifest, icon and
NLayer license. The root README describes the repository, not the package page.
The 256×256 icon is a rasterization of `site/public/favicon.svg`; regenerate it
with `rsvg-convert -w 256 -h 256 -o pkg/icon.png site/public/favicon.svg`.

From the repository root:

```sh
task package:thunderstore
task package:thunderstore:check
```

The build installs tcli 0.2.4 locally in `.tools/tcli/` if missing, builds the
Release DLLs (with Task's `.env` loading), runs package tests, invokes `tcli build`
and validates the resulting `.tools/thunderstore/<team>-Megabonk_Level_Editor-<version>.zip`.
It never publishes. After CLI installation and a Release build,
`.tools/tcli/tcli build` also builds the ZIP directly.

tcli generates the ZIP's `manifest.json` from `thunderstore.toml`; `pkg/manifest.json`
is a reviewable reference, checked against that generated manifest. tcli adds
`namespace` and `FullName` fields; the ZIP checker permits those only with the
configured identity. Update both metadata sources and the BepInPlugin display
version together for each release.

The ZIP has exactly these files, with no enclosing directory:

```text
manifest.json
README.md
icon.png
BepInEx/plugins/MegabonkLevels/MegabonkLevels.Mod.dll
BepInEx/plugins/MegabonkLevels/NLayer.dll
BepInEx/plugins/MegabonkLevels/NLayer.LICENSE.txt
```

The dependency is `BepInEx-BepInExPack_IL2CPP-6.0.788`. The package does not
redistribute BepInEx, its .NET runtime, Harmony, generated game/Unity interop,
game assets, PDBs, installers or developer test data. The ZIP checker,
`scripts/check_thunderstore_package.py`, rejects unexpected files and DLLs that
differ from the current Release output.
The older `package:windows`, `package:linux` and `package:macos` tasks describe
the legacy MelonLoader installer format and are internal: Task hides them from
listings and rejects direct CLI invocation. Do not expose a wrapper that combines
them with this BepInEx DLL. Use a separate worktree at `melonloader-final` for
legacy packages.

## Shared release version

`release-please-config.json` defines one root release, with Git tags such as
`v0.1.0`. The Python release strategy updates `pyproject.toml`; targeted
`extra-files` keep the other product-version fields synchronized:

- the root project entry in `uv.lock`, selected by name rather than array index
- the mod project's `<Version>` and the BepInPlugin display version
- Thunderstore's `versionNumber` and the reference manifest's `version_number`
- the site's `package.json` and both root version fields in `package-lock.json`

The Go installer has no embedded product-version field: its source follows the
same Git tag. Do not change the `go` toolchain directive to a product version.
Dependencies, game builds, level/pack schemas and the standalone boot spike have
their own versions and are not part of this synchronization.

Keep the plugin's inline `x-release-please-version` annotation; the generic
updater uses it to change only that line. The `uv.lock` selector accepts both
plain names and the tagged-value objects used by Release Please's TOML parser,
without updating third-party package versions. Two JSON updaters target the npm
lockfile's top-level version and `packages[""].version`; no dependency entries
are selected. Version examples in player documentation use placeholders so they
do not become stale on the next release.

### First release and subsequent bumps

`.release-please-manifest.json` is Release Please's current/last-released version
ledger, not the requested next version. It is bootstrapped at `0.1.0`; the
temporary `"release-as": "0.1.0"` override ensures the first release PR targets
exactly that version instead of deriving a higher one from existing commits.
Remove the override after the first release PR is merged and the GitHub release
exists. Otherwise later runs remain pinned at `0.1.0`. The option is supported
but deprecated upstream; use it only for this bootstrap, not normal releases.

After that, let conventional commits and Release Please advance the ledger and
all version files together. Do not independently release the website or add
separate language packages to the manifest unless their release lifecycles are
intentionally being split.

`.github/workflows/release-please.yml` runs on pushes to `main`. It reads the
repository Actions secret `RELEASE_PLEASE_TOKEN` with contents and pull-request
write permissions. The optional placeholder in `.env.example` is for local
tooling only: Actions does not read `.env`. Keep the real token out of Git,
command arguments and logs. This workflow creates release PRs and GitHub
releases; it does **not** publish to Thunderstore, npm, NuGet or PyPI, build a
player package, or deploy the website. A push that adds the workflow can start
release automation, so review the configuration before pushing.

Check current version consistency with:

```sh
uv run pytest tests/test_release_versions.py -n 0
```

For the optional offline future-bump integration test, install the upstream
updaters locally first; this does not contact GitHub or create a release:

```sh
npm install --prefix .tools/release-please --no-save --ignore-scripts release-please@17.11.2
uv run pytest tests/test_release_versions.py -n 0
```

The integration test applies Release Please's actual updaters and composite
update handling to temporary copies at a different version, then checks that
all product fields moved and dependency/toolchain versions did not.

### Dependency updates

`.github/renovate.json5` groups npm, NuGet, Go modules and Python dependencies.
Python uses `pep621` for `pyproject.toml`/`uv.lock` and an explicit `pep723` file
pattern for inline script metadata under `scripts/`. There is no Cargo project,
so no Rust rule is configured. Other default Renovate managers are not disabled.

The schedule permits new update branches during **Saturday 10–11 AM
America/Chicago**, including lockfile maintenance. It is an allowed window, not
a guarantee that the bot will run at exactly 10:00. Validate without running
dependency updates:

```sh
npx --yes --package renovate@44.222.5 -- renovate-config-validator --strict .github/renovate.json5
```

## Validate a manifest offline

`scripts/validate_thunderstore_manifest.py` reimplements
[the site's Manifest Validator](https://thunderstore.io/tools/manifest-v1-validator/),
which needs a logged-in account and a team you belong to. It ports
`ManifestV1Serializer` and the Django 4.2 / DRF validators behind it, including their
message text, so a line printed here matches the line the site prints.

```sh
uv run scripts/validate_thunderstore_manifest.py                      # pkg/manifest.json
uv run scripts/validate_thunderstore_manifest.py --online             # plus thunderstore.io
uv run scripts/validate_thunderstore_manifest.py .tools/thunderstore/<team>-<package>.zip
task package:thunderstore:manifest            # same, via Task
task package:thunderstore:manifest ONLINE=true
```

It takes a `manifest.json` or a built package ZIP, and the team defaults to
`thunderstore.toml`'s `[package].namespace`; `--team` picks another, `--json` emits
machine-readable output. Exit 1 means the manifest would be rejected, exit 2 means the
input could not be read. `task package:thunderstore` runs it on `pkg/manifest.json`
before building, and `task package:thunderstore:check` runs it on the built ZIP.

Offline it checks everything the serializer can decide from the document alone: required
fields, the name and version patterns and length caps, a version that is not written in
its canonical form, the URL rules, dependency strings, self-dependency, duplicate
dependencies, the dependency and installer list caps, installer identifier shape and
reuse, and the team name's shape. The four checks that read the site's database run only
with `--online`, and only once the offline rules pass -- as on the site, where they are
serializer-level checks that valid fields must reach:

- each dependency resolves to a published package version
- this `namespace-name-version` is not already published
- no package exists with the same name in a different capitalization
- installer identifiers exist, which stays a note because that table is not public

`--online` uses the public read-only JSON API through `scripts/asset_download.py`, so no
token is involved: `/api/experimental/package/<ns>/<name>/<version>/` and
`/api/cyberstorm/listing/<community>/<ns>/` for the team's package list. The
`api/v1/package/...` detail paths return 404 for the same package, so those two are
deliberate. An unreachable host is a note, not a failure.

Behaviours worth knowing before debugging a disagreement with the site:

- Extra keys are ignored, which is why tcli's `namespace` and `FullName` are harmless.
- `PackageReference.parse` takes the version and then the name from the right, so
  `Dash-Ed-Team-Mythic-TestMod-1.1.0` is one reference and a version with two dots is
  mandatory.
- A bare `mailto:` address is rejected while `mailto://anything` passes, and `ipfs://`
  needs something that looks like a host: `ipfs://CID` fails.

## Content and licensing

The Thunderstore package is runtime-only: **no levels, third-party packs or
music** are included. In particular, extracted THPS assets and music must not
be published with it. Screenshots in the README are publicly hosted links, not
bundled game assets. NLayer 1.16.0 is redistributed under MIT with its upstream
license notice preserved in `pkg/NLayer.LICENSE.txt`.

The repository currently has no project-wide license file. Packaging does not
choose a code/content license on the maintainer's behalf. Confirm the intended
release terms and rights to any newly added content before first publication;
adding a level or pack is a separate licensing and manager-layout review.

## Test the final ZIP, not the build folder

1. Quit the game. Back up the manager's settings/profile metadata and inventory
   the affected game files. Preserve the existing profile and manual development
   DLLs outside the manager's sync tree.
2. Create a **new Megabonk profile** with only the declared BepInEx dependency.
   Do not reuse a development profile or another plugin's configuration files.
3. Import the built ZIP with the manager's local/custom mod import, then Apply.
   Do not copy the plugin DLL manually as a substitute for this test.
4. Check that the installed plugin and NLayer hashes match the ZIP, and that only
   one copy of `megabonklevels.runtime` can load. The manager may wrap or flatten
   the package's plugin subfolder; inspect the actual installed paths.
5. Launch and check `BepInEx/LogOutput.log` for
   `Loading [Megabonk Level Editor <version>]`, `MegabonkLevels mod initialized.`
   and `Chainloader startup complete`. Check errors associated with this plugin,
   not just the chainloader's own `ErrorLog.log`.
6. Confirm the console opens and a separately supplied, pack-free level appears
   on Map Selection and plays. Enter the editor, make and undo an edit, and save
   a copy. No mod-specific BepInEx config is expected; developer tools require
   `MEGABONK_DEV=true` in the launch environment.
7. Review `pkg/README.md` using Thunderstore's
   [Markdown Preview](https://thunderstore.io/tools/markdown-preview/), including
   both externally hosted screenshots. Validate the generated manifest with
   `task package:thunderstore:manifest ONLINE=true`, and confirm it with the
   [Manifest Validator](https://thunderstore.io/tools/manifest-v1-validator/), which
   is the final word.
   The screenshots use the public showcase site, not private-repository raw URLs.
   Recheck the editor image URL after a website rebuild changes its asset hash.
8. Record the ZIP SHA-256, profile, installed hashes, log evidence and screenshots.
   Rebuild and repeat the import test if any packaged file changes afterward.

On the tested macOS setup, r2modmac 1.1.0 manages files but does not successfully
launch the Windows game through plain Wine. Use the existing Wine launch path.
Its Apply omits the loader pack's `dotnet/`, `.doorstop_version` and `changelog.txt`;
supply these from the dependency ZIP, not from this mod package. Set the prefix's
`winhttp=native,builtin` override (the repo launcher passes it in the environment).
Park the MelonLoader `version.dll`; both proxies must not be active together.
See [Running BepInEx under Wine](development.md#running-bepinex-under-wine).

For an isolated test game outside the Wine prefix, inspect the manager-written
`doorstop_config.ini` before launching. r2modmac may write a host path such as
`\Users\...` without a Windows drive letter. Back up that file, then use paths
relative to the game folder instead:

```ini
[General]
target_assembly=BepInEx\core\BepInEx.Unity.IL2CPP.dll

[UnityMono]
dll_search_path_override=BepInEx\core
```

Keep the existing sections and other settings, including the relative
`dotnet\coreclr.dll` runtime path. Re-Apply may overwrite these changes. Launch
with the game folder as the working directory and the **test copy's executable**
explicitly; the repo's current plain-Wine launcher still names the default Steam
executable even when `MEGABONK_GAME_DIR` changes its working/log directory.
Use an explicit `Z:\...\Megabonk.exe` path for a host-side test copy, and point
`MEGABONK_GAME_DIR` at that same folder for harness commands. Do not mistake a
successful launch of the development install for a manager-install test.

The manager's sync is bidirectional: deleting installed mod files can also remove
them from its profile at the next sync. Restore backups with the manager stopped;
do not delete an installed tree to simulate disabling a mod.

With r2modmac 1.1.0, local ZIP imports appear as
`Local-Megabonk_Level_Editor-<version>`. Apply preserves the plugin's nested folder:
`BepInEx/plugins/Local-Megabonk_Level_Editor-<version>/MegabonkLevels/` contains the
DLL, NLayer and its license. That layout loads correctly; do not flatten it by
hand. A clean-profile install was verified under Wine 11.18 with the omitted
runtime supplied from the dependency ZIP and relative Doorstop paths. Console,
pack-free level loading/gameplay, terrain editing, undo and save-copy all work.

## Release gate and publishing

Before the first publish:

- Keep work on the port branch; main stays MelonLoader until an approved cutover.
- The annotated `melonloader-final` tag preserves the final MelonLoader-only
  revision. Keep it and the rollback files; ensure the tag is available remotely
  before publication. Creating it locally does not push it or merge the port.
- Confirm the team's service account has package-upload permission. Read
  [Global Rules](https://wiki.thunderstore.io/moderation/global-rules) and any
  Megabonk-specific rules. Do not distribute game assemblies or unlicensed assets.
- Confirm all linked documentation and feedback destinations are publicly
  accessible. A private GitHub repository's source/docs/issues links do not work
  for players without access; make them public or replace them before release.
- Complete the clean-profile ZIP test, manifest validation and README preview.
  Record rights/licensing decisions and the exact tested archive hash.
- Confirm community `megabonk`, categories `mods` and `tools`, and NSFW **false**
  for every upload. The category API currently exposes no AI Generated category;
  check again before uploading and apply it if it becomes available and applies.
- Obtain explicit publication approval. Building a package is not approval to
  upload it or to merge the cutover.

Create a **team service account**, not a personal token, at Thunderstore's team
settings. Supply its token only through `TCLI_AUTH_TOKEN` in the shell environment
or a gitignored local environment file. Never put it in TOML, command arguments,
task notes or logs. After approval, validate and publish the already tested ZIP:

```sh
task package:thunderstore:check
.tools/tcli/tcli publish --file .tools/thunderstore/<team>-Megabonk_Level_Editor-<version>.zip
```

Do not use bare `tcli publish`: it rebuilds by default and could upload a ZIP that
was not tested. Recheck the stored SHA-256 immediately before the upload.
After publishing, verify the page's title, icon, screenshots, dependency, category
and NSFW settings, then install the published version in another clean profile.
That last download check cannot be performed before publication.

Package versions are immutable. Updates require a higher version with the same
team/name identity. Retain superseded releases; after a soak period and approval,
**deprecate, never delete** an obsolete package. Do not automatically deprecate
anything during the initial upload.

## Rollback

Quit the game and disable the package in the manager; Apply and verify the plugin
is no longer in the active plugin tree. Keep user-authored `UserData/` files.
For a loader rollback, park `winhttp.dll` and `doorstop_config.ini`, restore the
preserved MelonLoader `version.dll`, and deploy the DLL from the final legacy tag,
not this BepInEx package. Leave inactive loader trees intact. Reverse the proxy
renames to return to BepInEx. Restore the original manager profile/settings and
manual development artifacts from the pre-test inventory if required.
