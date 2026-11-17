---
id: TASK-083
title: Lower code address constants to dispatchable file addresses in lifted bodies
status: To Do
assignee: []
created_date: '2026-11-17T02:19:00Z'
labels:
  - native-macos
  - arm64
dependencies: []
references:
  - scripts/pcode_lift.py
  - tests/test_lift_code_address.py
  - docs/development.md
priority: medium
type: bug
ordinal: 284000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A code address a lifted body materialises itself, such as a lea of a function, lowers through pcode_lift.address_value to ptrtoint of the host @sub_X. With call_dispatch on, every indirect call goes through lift_dispatch, which switches on the ELF file address X, so such a pointer aborts as an unregistered target. Relocated data words (vtables, typeinfo) already carry file addresses and are unaffected. The same pointer passed to native code as a callback is a separate question: native code cannot call a file address, so it needs a trampoline or a rejection. tests/test_lift_code_address.py holds the dispatch half as a strict expected failure. Changing the lowering alters existing lifted IR for any body that takes a function address, so the effect on per-body hole lists and IR must be measured and reported, not adjusted.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 With call_dispatch, a code address constant lowers to the file address, and a lifted call through it reaches the target body natively on arm64.
- [ ] #2 A code address that escapes to native code (stored to data native code reads, or passed to an import) is either given a callable trampoline or rejected by name; none is emitted as a file address a native caller would jump to.
- [ ] #3 The strict xfail in tests/test_lift_code_address.py is replaced by passing tests, and the change to existing lifted output is measured over the cached seed samples and reported.
- [ ] #4 docs/development.md states the verified contract for code addresses and drops the callback-pointer exclusion it covers.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
