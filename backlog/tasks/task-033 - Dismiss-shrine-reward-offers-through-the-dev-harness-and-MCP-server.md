---
id: TASK-033
title: Dismiss shrine reward offers through the dev harness and MCP server
status: In Progress
assignee: []
created_date: '2026-11-02T06:18:00Z'
updated_date: '2026-11-02T06:27:00Z'
labels:
  - dev-harness
  - mcp
dependencies: []
documentation:
  - docs/development.md
priority: medium
type: enhancement
ordinal: 142000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Agents verifying shrine behaviour (e.g. the extra-shrine work in TASK-031) can open the Charge/Greed shrine reward window — "The shrine offers you a reward" with its Ignore Offers button — but nothing can close it without OS-level input. `dismiss-levelup` is hard-gated to `LevelupScreen.isLevelingUp` and returns `dialogWasOpen:false` while a shrine offer is visible; `key`/`mouse`/`type_text` inject into the editor's input queue and never reach stock Rewired UI, so Escape is ignored; `ui_tree`/`click_widget` only enumerate the mod's own `EditorWidgets()` (toolbar, palette, panels), not game UI; and `run.py menu drive` (real keyboard) is Linux-only, unavailable on the macOS/CrossOver dev hosts. An open modal therefore blocks every follow-up harness step and forces a relaunch.

The level-up window has the same class of gap for no-selection dismissal: its footer offers BANISH, SKIP and REFRESH buttons (confirmed in game with the window open), but `dismiss-levelup` can only pick an upgrade — there is no way to Skip. In `.tools/il2cpp_dump/dump.cs` (gitignored; search with `rg -u`), `LevelupScreen : BaseEncounterWindow` exposes `public void Skip()` plus `hasSkips`, `GetSkips()` and `GetSkipsUsed()`, so Skip is a real invokable action like `SelectUpgrade()`; skips are a limited per-run resource, so the harness must surface skip exhaustion rather than silently failing. The shrine reward flow lives in `ChargeShrine` (same dump, `rewardTime`/`lastRewardShrine` statics; shrine classes around line 334105) and its ignore path is a button onClick invocable the same way.

Precedents to follow: `dismiss-levelup` invokes the real selection path (`LevelupScreen.upgradePicker.buttons[i].SelectUpgrade()`) rather than faking input, and the music-probe `radio-next` command invokes the scene boombox's real Interact method. Wire new commands through harness_command.cs parsing, dev_harness.cs dispatch, a run.py subcommand, and an MCP tool mirroring the existing dismiss-levelup plumbing at every layer. Whether Skip lives on the existing dismiss-levelup command (e.g. a skip flag or sentinel choice) or the new no-selection command is the implementer's call, but both modals' no-selection paths must be reachable through run.py and the MCP server.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A new harness command dismisses the currently open shrine reward offer window (equivalent to pressing Ignore Offers) with no OS-level input, through run.py and the MCP server
- [ ] #2 The result reports whether an offer window was open; when none is open it returns a not-open result without throwing
- [ ] #3 An agent can close the upgrade offers window without choosing an upgrade through the game's own Skip action, via run.py and the MCP server; with no skips remaining it reports the reason clearly and leaves the window intact and still dismissable by choice
- [ ] #4 Each dismissal acts on its intended modal only, the existing dismiss-levelup choose-an-upgrade behaviour is unchanged, and which command targets which modal is documented
- [ ] #5 The shrine offer can also be accepted by index if it uses the same UpgradePicker path as level-ups; if it does not, the task records why in a note and acceptance stays ignore-only
- [ ] #6 Command parsing and payload building are covered by C# and Python tests written before the implementation
- [ ] #7 Verified in game through the MCP server: open a Charge shrine reward window and dismiss it with the new tool, and open a level-up window and Skip it, each with a screenshot showing the modal closed and the run responsive
- [ ] #8 docs/development.md documents the new command(s), their run.py subcommands and the MCP tools
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Research (dump.cs + live probe): reward modals are BaseEncounterWindow subclasses (dump.cs 360490): LevelupScreen (isLevelingUp static, Skip()/CloseLevelupScreen()/Leave(), upgradePicker), EncounterUi (two live instances 'EncounterWindow' and 'ItemPickWindow'; shrine offers, shady guy, moai, balance), ChestWindowUi, MicrowaveUi. Base class contract: Open(EEncounter), OnClose(), ChooseOffer(int). ChargeShrine.Reward() triggers the charge offer window. Live probe of the open UPGRADE OFFERS modal: upgradePicker.buttons.Length is 4 while 3 offers show, so choice validation mirrors dismiss-levelup's range error (reports buttons.Length) and ChooseOffer relies on the game's own out-of-range handling.

Design: new harness command dismiss-offers with optional choice (int) and skip (bool). Find active window via Object.FindObjectsOfType<BaseEncounterWindow>() filtered by gameObject.activeInHierarchy; none -> {windowWasOpen:false} without throwing. Result reports runtime class and GameObject name. choice>=0 -> window.ChooseOffer(choice); LevelupScreen validated against upgradePicker.buttons.Length first with a dismiss-levelup-style range error. skip -> LevelupScreen only: call Skip(), then report skipped = !LevelupScreen.isLevelingUp; still open means skips exhausted, window left intact and still dismissable. Default (no choice/skip) -> close without selecting: LevelupScreen.CloseLevelupScreen() (public Leave path, same RVA as Leave()), other windows OnClose(). After any close action re-apply MyTime.Pause() when EditorMode.Active, mirroring DismissLevelUp. dismiss-levelup is not modified.

Layers: harness_command.cs gets HarnessCommandKind.DismissOffers + Skip flag parsing (reuse Choice field, add Skip bool to HarnessCommand); dev_harness.cs dispatch + implementation; run.py build_dismiss_offers_command(choice, skip) + dismiss-offers subparser (--choice N, --skip) + payload case; mcp_server.py dismiss_offers(choice: int | None = None, skip: bool = False) tool. docs/development.md documents all three layers next to dismiss-levelup.

Tests first: C# parsing tests in the harness_command tests file (dismiss-offers with/without choice, with skip, bad types rejected); Python build/payload tests in test_run.py and MCP tool test in test_mcp_server.py mirroring the dismiss-levelup tests. No testable pure logic beyond parsing (window interaction is runtime-only, verified in game).

Risks: OnClose() may expect game-internal state; if closing EncounterUi via OnClose() leaves the run frozen or errors, fall back to the window's own ignore button path (LevelupScreen.b_leave/b_skip are public MyButtonOffersUtility/MyButtonNormal). Skip() when exhausted: post-state check on isLevelingUp is the report, no private GetSkips access. Verification needs a relaunch (MelonLoader DLL loads once): reopen charge offer via teleport into a charge zone of levels/extra-shrines-charge.mblevel.json and a level-up via kills with spawns on.

Bonus: the generic BaseEncounterWindow sweep also covers ChestWindowUi and MicrowaveWindow; keep behaviour identical (report + close/choose), verify nothing crashes on those types.
<!-- SECTION:PLAN:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-11-02T06:23:00Z

---

Probe on a live UPGRADE OFFERS window (Forest, LVL 2, 2026-11-02): harness mouse click at the SKIP button centre and key Escape (correct-cased) both return ok but leave the modal open and the run frozen (EditorInput.Queue never reaches the Rewired UI); click_widget is refused with 'editor mode is off: the widgets only exist inside the editor'; key rejects ESCAPE as a case-mismatched name. dismiss-levelup only picks an offer — no no-selection path exists. Evidence: .tools/evidence/skip-attempt-result.png, skip-attempt-escape.png. Confirms all four dead ends in the description; OS-level input (user keyboard/mouse) closes the window normally.

---
<!-- COMMENTS:END -->
