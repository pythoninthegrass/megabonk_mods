---
id: TASK-033
title: Dismiss shrine reward offers through the dev harness and MCP server
status: Done
assignee: []
created_date: '2026-11-02T06:18:00Z'
updated_date: '2026-11-02T07:31:00Z'
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
- [x] #1 A new harness command dismisses the currently open shrine reward offer window (equivalent to pressing Ignore Offers) with no OS-level input, through run.py and the MCP server
- [x] #2 The result reports whether an offer window was open; when none is open it returns a not-open result without throwing
- [x] #3 An agent can close the upgrade offers window without choosing an upgrade through the game's own Skip action, via run.py and the MCP server; with no skips remaining it reports the reason clearly and leaves the window intact and still dismissable by choice
- [x] #4 Each dismissal acts on its intended modal only, the existing dismiss-levelup choose-an-upgrade behaviour is unchanged, and which command targets which modal is documented
- [x] #5 The shrine offer can also be accepted by index if it uses the same UpgradePicker path as level-ups; if it does not, the task records why in a note and acceptance stays ignore-only
- [x] #6 Command parsing and payload building are covered by C# and Python tests written before the implementation
- [x] #7 Verified in game through the MCP server: open a Charge shrine reward window and dismiss it with the new tool, and open a level-up window and Skip it, each with a screenshot showing the modal closed and the run responsive
- [x] #8 docs/development.md documents the new command(s), their run.py subcommands and the MCP tools
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

created: 2026-11-02T07:31:00Z

---

Verified in game 2026-11-02 on the deployed build, Charge shrine fixture (levels/extra-shrines-charge.mblevel.json). Shrine offer window open (charge-offers-open.png) then dismissed via the MCP dismiss_offers tool: {"windowWasOpen":true,"window":"LevelupScreen (LevelupScreen)","action":"close","closed":true,"reason":null}; the follow-up frame showed the run live with the shrine standing where the player was (charge-offers-dismissed-run-running.png: clock 7:17 to 7:05, kills 96 to 108, coins 63 to 78). Repeating the call reported {"windowWasOpen":false,"window":null} with no throw, as did skip and choice with nothing open. Level-up window: skip reported closed:true and left the run live (levelup-offers-open.png, levelup-skipped-run-running.png); a skip the game refused reported closed:false reason "the game refused the skip; skip price 50, skips used 3" with the window intact (levelup-skip-refused.png) and still closable by --choice 1. --choice 0 on a level-up accepted and granted the Scythe (levelup-after-choice.png); --choice 99 was refused with the range error and the window left open; --choice 1 on a shrine window was refused with the ignore-only message (charge-choice-refused.png). dismiss-levelup afterwards still returned {"dialogWasOpen":true,"chosen":"Wireless Dagger"}.

---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Adds a dismiss-offers harness command that acts on whichever reward window is up, closing the gap where an open modal blocked every later harness step and forced a relaunch.

Layers (commits 0261088, 039ca2d, 929f9ee, d76302f): harness_command.cs parses dismiss-offers with optional choice (int) and skip (bool); dev_harness.cs implements DismissOffers; scripts/run.py adds build_dismiss_offers_command plus the dismiss-offers subcommand (--choice N, --skip); scripts/mcp_server.py exposes dismiss_offers(choice?, skip?). dismiss-levelup is untouched.

What the game turned out to do, all of it recorded in docs/development.md:
- The charge shrine's "The shrine offers you a reward" window is the single LevelupScreen instance (encounterType Levelup, utility buttons hidden), not EncounterUi. Finding the windows needs Resources.FindObjectsOfTypeAll over the Il2CppType; FindObjectsOfType<BaseEncounterWindow>() and C# type filters over a MonoBehaviour sweep both miss them under interop, so a visibly open window read as not open.
- Level-up picks must go through upgradePicker.buttons[N].SelectUpgrade(): LevelupScreen.ChooseOffer is a 16-byte empty override that leaves the window open. Non-level-up windows keep ChooseOffer(N).
- Shrine offers are ignore-only: their buttons carry no IUpgradable, so SelectUpgrade() throws NullReferenceException in PlayerInventory.AddUpgrade and ChooseOffer does nothing. choice there is now refused before anything is invoked with "offer N on '<window>' has no upgrade to select; a shrine reward window is dismissed with the default close, not chosen" (AC#5's recorded why).
- Detection requires LevelupScreen.isLevelingUp or EncounterWindows.encounterInProgress: after CloseLevelupScreen() the GameObject lingers active, and a second close threw NullReferenceException in EncounterWindows.RewardFinished().
- The closed read is the flag each action clears: !isLevelingUp for skip and choice, !encounterInProgress for the plain close (isLevelingUp is already false on a shrine window, so it was vacuous there). Reading encounterInProgress after Skip() reported an accepted-but-unaffordable skip as still open.
- A refused skip reports the game's own state in reason: "no skips left" from the private static hasSkips, otherwise "the game refused the skip; skip price 50, skips used 3" from GetSkipsUsed()/GetShopToolPrice(). Skips cost escalating shop currency, so refusals are usually price, not a hard cap.

Verification: task check green (1686 xUnit, 979 pytest, markdownlint and ruff clean). In game on levels/extra-shrines-charge.mblevel.json, driven through an MCP stdio client against scripts/mcp_server.py and through run.py: Charge shrine open -> close reported {"windowWasOpen":true,"window":"LevelupScreen (LevelupScreen)","action":"close","closed":true} and the run resumed (clock and kill count advancing in the follow-up frame); the same call again reported windowWasOpen:false with no throw. --choice 1 on that window was refused with the ignore-only message and left the window open and dismissable. A natural level-up accepted --choice 0 with closed:true and the Scythe appeared in the weapons bar; --choice 99 was refused with "choice 99 is out of range; the window offers 4 upgrades" and the window stayed open. Skips: four reported closed:true, the fifth reported closed:false reason "the game refused the skip; skip price 50, skips used 3" with the window visibly open (SKIP badge 50 against 33 held) and still closable by --choice 1. dismiss-levelup regression-checked afterwards: {"dialogWasOpen":true,"chosen":"Wireless Dagger"}.

Screenshots in .tools/evidence/: charge-offers-open.png, charge-offers-dismissed-run-running.png, levelup-offers-open.png, levelup-skipped-run-running.png, levelup-skip-refused.png, charge-choice-refused.png, levelup-after-choice.png.

Follow-ups: ChestWindowUi and MicrowaveUi are in the same sweep and were exercised only by the code path, not by a live chest or microwave window. The megabonk MCP server process in the dev session predates the dismiss_offers tool, so the live checks went through a fresh stdio MCP client and run.py; the next server start picks the tool up (it registers and validates correctly under the probe).
<!-- SECTION:FINAL_SUMMARY:END -->
