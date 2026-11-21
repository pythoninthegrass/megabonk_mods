"""Define every lifted PLT stub of the linked image: an image alias, an SDK-cleared host call, or a named abort.

A stub is an alias when the image itself defines the name it jumps through, a host call only when the macOS SDK
declares that name with a prototype `lift_sdk` clears, and otherwise a stub that names the import and the reason
before it aborts, so no `sub_<address>` the lifted bodies call is left undefined.
"""

from __future__ import annotations

import lift_abi as abi
import lift_sdk
from dataclasses import dataclass, field

BOUND = "scalar prototype in a value-only libc header"
NOT_A_BODY = "image symbol is not a lifted body start"


@dataclass
class StubPlan:
    rows: list[dict] = field(default_factory=list)
    imports: list[abi.Binding] = field(default_factory=list)
    aliases: dict[int, int] = field(default_factory=dict)


def host_name(name: str) -> str:
    """The unique C name an adapter calls an import by, so it cannot clash with a prototype the headers declare."""
    return f"import_{name}"


def _row(address: int, name: str, disposition: str, reason: str, host: str | None = None) -> dict:
    return {"address": address, "name": name, "disposition": disposition, "reason": reason, "host": host}


def plan_stubs(sdk: lift_sdk.Sdk, stubs: dict[int, str], defined: dict[str, int] | None = None, entries=()) -> StubPlan:
    """One row per stub address (`stubs` maps it to the import it jumps through), the bindings and the aliases.

    `defined` maps each name the image itself defines to its address and `entries` holds the lifted body starts: a
    stub of a defined name aliases its body, and aborts when that address is not a body start. A second stub of
    one bound import aliases the first stub's definition, since the binding names must be unique.
    """
    plan, defined, entries, bound_at = StubPlan(), defined or {}, set(entries), {}
    for address in sorted(stubs):
        name = stubs[address]
        if name in defined:
            if defined[name] in entries:
                plan.aliases[address] = defined[name]
                plan.rows.append(_row(address, name, "alias", "image body"))
            else:
                plan.rows.append(_row(address, name, "abort", NOT_A_BODY))
            continue
        decision = sdk.decide(name)
        if not decision.bound:
            plan.rows.append(_row(address, name, "abort", decision.reason))
            continue
        plan.rows.append(_row(address, name, "bind", BOUND, host=name))
        if name in bound_at:
            plan.aliases[address] = bound_at[name]
            continue
        bound_at[name] = address
        signature = abi.Signature(decision.args, decision.result)
        plan.imports.append(abi.Binding(address, host_name(name), signature, declared_name=name))
    return plan


def import_report(sdk: lift_sdk.Sdk, rows: list[dict]) -> list[dict]:
    """One row per distinct import name, with how many stubs jump through it and the prototype the SDK declared."""
    seen: dict[str, dict] = {}
    for row in rows:
        if row["name"] in seen:
            seen[row["name"]]["stubs"] += 1
            continue
        prototype = sdk.decide(row["name"]).prototype if row["disposition"] == "bind" else None
        seen[row["name"]] = {
            "name": row["name"],
            "stubs": 1,
            "disposition": row["disposition"],
            "reason": row["reason"],
            "sdk_prototype": prototype,
        }
    return [seen[name] for name in sorted(seen)]


def counts(rows: list[dict]) -> dict:
    """Stub counts by disposition, with the refusals broken out by reason."""
    tally: dict = {"stubs": len(rows), "alias": 0, "bind": 0, "abort": 0, "reasons": {}}
    for row in rows:
        tally[row["disposition"]] += 1
        if row["disposition"] == "abort":
            tally["reasons"][row["reason"]] = tally["reasons"].get(row["reason"], 0) + 1
    return tally


def abort_source(rows: list[dict]) -> str:
    """One helper per refused import name: it prints `lift_import_refused: <name>: <reason>` and aborts."""
    reasons = {row["name"]: row["reason"] for row in rows if row["disposition"] == "abort"}
    lines: list[str] = []
    for name in sorted(reasons):
        lines += [
            f"void lift_abort_{name}(void) {{",
            f'  fprintf(stderr, "lift_import_refused: {name}: {reasons[name]}\\n");',
            "  abort();",
            "}",
        ]
    return "\n".join(lines)


def abort_stubs(rows: list[dict]) -> str:
    """A `sub_<address>` definition for every refused stub, each calling its named abort helper."""
    return "\n".join(
        f"void sub_{row['address']:x}(unsigned char *reg) {{ (void)reg; lift_abort_{row['name']}(); }}"
        for row in rows
        if row["disposition"] == "abort"
    )
