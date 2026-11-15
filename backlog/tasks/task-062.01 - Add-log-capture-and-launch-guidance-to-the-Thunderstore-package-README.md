---
id: TASK-062.01
title: Add log-capture and launch guidance to the Thunderstore package README
status: In Progress
assignee: []
created_date: '2026-11-09T23:55:00Z'
updated_date: '2026-11-14 23:33'
labels:
  - docs
  - thunderstore
dependencies: []
documentation:
  - pkg/README.md
  - docs/thunderstore.md
  - AGENTS.md
parent_task_id: TASK-062
priority: medium
ordinal: 214000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The README shown on the Thunderstore package page is the first place a player looks when the mod does not load, and it does not help with the failure seen in support. Install step 3 says only "Start the modded game", which does not say to launch through the mod manager. The troubleshooting paragraph says that no BepInEx log "usually means the loader/runtime or Wine override is missing", which is Wine-specific and misses the common Windows case: a profile-based manager keeps BepInEx in the profile folder, so a plain Steam launch boots the vanilla game and writes no BepInEx log. The README also never mentions Unity's Player.log or how to get the log out of r2modman or Thunderstore Mod Manager. The page README is separate from the downloadable ZIP and is changed through the authenticated Thunderstore markdown README update endpoint described in AGENTS.md, which does not upload a package or bump the version. The manager menu names and profile paths used must be confirmed on a real install of each manager, as in the parent task.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Install step 3 in pkg/README.md says to launch through the mod manager's modded launch, and says a direct Steam launch only works when the BepInEx files are also in the game folder
- [x] #2 The troubleshooting section covers the Windows case of no BepInEx log because the game was started outside the manager, alongside the existing Wine and runtime cause
- [x] #3 The troubleshooting section tells players how to get the profile's BepInEx LogOutput.log from r2modman and from Thunderstore Mod Manager, and where Unity's Player.log is on Windows and under Wine or Proton
- [x] #4 The new text follows the parent task's confirmed manager menu names and paths, with anything unconfirmed marked as such, and uses no personal paths or identifiers
- [x] #5 pkg/README.md renders correctly in Thunderstore's Markdown Preview tool, and the markdown passes the repository's markdownlint configuration
- [ ] #6 The live package page README matches pkg/README.md after the README-only update, with no package upload or version bump, and the token is read from the environment and never printed or placed in command arguments
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Scope: player-facing Thunderstore package README only (pkg/README.md) plus the README-only live update. Parent TASK-062's bug template, docs/player-guide.md and site wiki stay out of scope.

1. pkg/README.md install step 3: launch from the manager's modded launch (Start modded); state that a direct Steam launch boots the unmodded game and writes no BepInEx log, and works only when the BepInEx files are also in the game folder.
2. pkg/README.md troubleshooting: split into 'Where the logs are' and 'If the mod does not appear'. Profile-based managers keep BepInEx, and LogOutput.log, in the profile folder; reach it from Settings via Browse profile folder, or Copy log file contents to clipboard. Cover the Windows no-log case (started outside the manager) alongside the existing Wine/runtime-override cause. Add Unity Player.log/Player-prev.log locations for Windows and Wine/Proton.
3. Evidence for manager labels: r2modman upstream source (ebkr/r2modmanPlus master) - NavigationMenu.vue 'Start modded'/'Start vanilla' split button; SettingsView.vue 'Browse profile folder' and 'Copy log file contents to clipboard'; LogOutputProvider documents LogOutput.log under <profile>/BepInEx; Manager.vue copyLogToClipboard reads <profilePath>/BepInEx/LogOutput.log; BepInExGameInstructions passes --doorstop-enable true --doorstop-target <profile>/... for modded and --doorstop-enable false for vanilla. Thunderstore Mod Manager is an r2modman-derived shell and community guides/video show the same Settings entries; NOT verified on a real install of that manager (parent TASK-062 AC #5 still open), so the README adds one sentence that menu names shift between manager versions.
4. Validate: markdownlint -c .markdownlint.jsonc pkg/README.md, then Thunderstore Markdown Preview tool in Chrome with a screenshot.
5. Publish README-only: authenticated PATCH /api/cyberstorm/package/pythoninthegrass/Megabonk_Level_Editor/v/0.2.0/markdown/readme/update/ with JSON {"content":...}. Token from .env TCLI_AUTH_TOKEN loaded into the environment only; never printed or passed as an argument. Afterwards confirm the displayed README matches pkg/README.md and version_number is still 0.2.0 with no new upload.
6. docs/thunderstore.md: one line in the README-update paragraph noting the page README carries the player log-capture guidance so future edits keep it.
7. Finalize: check acceptance criteria as met, notes + final summary, conventional commit docs(thunderstore): ... with no attribution.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Manager wording evidence: r2modman upstream (ebkr/r2modmanPlus master) - NavigationMenu.vue split button 'Start modded'/'Start vanilla'; SettingsView.vue 'Browse profile folder' and 'Copy log file contents to clipboard' with a Log file exists/does not exist status; LogOutputProvider documents LogOutput.log under <profile>/BepInEx; Manager.vue copyLogToClipboard reads <profilePath>/BepInEx/LogOutput.log; BepInExGameInstructions passes --doorstop-enable true --doorstop-target <profile>/... for modded and --doorstop-enable false for vanilla, which is why a plain Steam launch boots vanilla and writes no log.

Thunderstore Mod Manager labels were NOT verified on a real install (parent TASK-062 AC #5 still open). It is an r2modman-derived shell and community guides plus a tutorial video show the same Settings entries, so the README names both managers with the r2modman-verified labels and adds one sentence that menu names shift between versions and platforms.

Validation: markdownlint clean on pkg/README.md, docs/thunderstore.md and AGENTS.md; task check green (1552 passed, 6 skipped); Thunderstore Markdown Preview at /tools/markdown-preview/ rendered both new H3s, all H1/H2, 2 tables, no raw fences, and every key string (Start modded, Browse profile folder, Copy log file contents to clipboard, Player-prev.log, both Player.log paths).

AC #5 caveat: the two megabonkmod.party screenshots do not paint on Thunderstore. net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin, caused by site/server.mjs sending Cross-Origin-Resource-Policy: same-origin on every response. Pre-existing (the live page today shows the same broken images), not a markdown defect. Filed as TASK-068.

AC #6 blocked: PATCH /api/cyberstorm/package/pythoninthegrass/Megabonk_Level_Editor/v/0.2.0/markdown/readme/update/ with the TCLI_AUTH_TOKEN Bearer token returns 403 {"non_field_errors":["Service accounts are unable to perform this action"]}. Upstream: the view calls update_markdown_override(agent=request.user) -> package.ensure_user_can_manage_wiki -> owner.ensure_user_can_manage_packages, which excludes service accounts; supported auth classes are ServiceAccountTokenAuthentication (Bearer, banned here) and UserSessionTokenAuthentication (Authorization: Session <session key>); the upstream tests use a logged-in human client. AGENTS.md and docs/thunderstore.md both claimed the service-account token works and have been corrected.

Nothing changed on the live page: readme GET returned 200 and matched git HEAD before the attempt, and latest remains 0.2.0 with an unchanged date_created. Remaining step for AC #6: apply pkg/README.md through the site's README editor signed in as the pythoninthegrass owner (or Session auth), then re-verify with GET /api/experimental/package/pythoninthegrass/Megabonk_Level_Editor/0.2.0/readme/ and confirm version_number stays 0.2.0.

Committed as 032e5c4 docs(thunderstore): add manager launch and log-capture guidance to the package README
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
pkg/README.md now tells players to launch through the manager and where the logs live.

- Install step 3: start the game from the manager's modded launch (Start modded); a direct Steam launch boots the unmodded game and writes no BepInEx log, and works only when the BepInEx files are also in the game folder.
- New 'Where the logs are' subsection: profile-based managers keep BepInEx and LogOutput.log in the profile folder, reached via Settings -> Browse profile folder, with Copy log file contents to clipboard as the quick path; plus Unity's Player.log and Player-prev.log locations for Windows and for Wine/Proton.
- New 'If the mod does not appear' subsection splits the causes: no log at all on Windows because the game was started outside the manager; still no log after a modded launch pointing at the .NET runtime or Wine winhttp override; a log with no MegabonkLevels line pointing at duplicate DLLs.
- docs/thunderstore.md records that the page README carries this troubleshooting guidance, and both it and AGENTS.md now state that the cyberstorm markdown README endpoint rejects the team service account and needs a signed-in human owner.

Validation: markdownlint clean, task check green (1552 passed, 6 skipped), and the Thunderstore Markdown Preview tool renders the markdown correctly - both new headings, both tables, no raw fences, all key strings present.

Open: AC #6. The service-account token is refused with 403 'Service accounts are unable to perform this action', so the displayed README still matches the previous text; the update needs the site's README editor as the package owner. Nothing was published and the package version is unchanged at 0.2.0.

Related: TASK-068 tracks the megabonkmod.party Cross-Origin-Resource-Policy: same-origin header that blocks the README's two screenshots from rendering on Thunderstore.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
