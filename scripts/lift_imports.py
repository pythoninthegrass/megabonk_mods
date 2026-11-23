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
# Linux services the SDK cannot bind but the image reaches at startup, implemented against the guest ABI instead.
COMPAT = {
    "__cxa_atexit": (abi.Signature(("ptr", "ptr", "ptr"), "i32"), "guest destructor registry, last registered runs first"),
    "__cxa_finalize": (abi.Signature(("ptr",), "void"), "drains the guest destructor registry"),
    "pthread_mutex_init": (abi.Signature(("ptr", "ptr"), "i32"), "guest mutex over a host mutex, Linux return codes"),
    "pthread_mutex_lock": (abi.Signature(("ptr",), "i32"), "host lock, Linux return codes"),
    "pthread_mutex_unlock": (abi.Signature(("ptr",), "i32"), "host unlock, Linux return codes"),
    "pthread_mutex_destroy": (abi.Signature(("ptr",), "i32"), "frees the host mutex when unlocked"),
    "pthread_mutexattr_init": (abi.Signature(("ptr",), "i32"), "guest attribute kind, zeroed"),
    "pthread_mutexattr_settype": (abi.Signature(("ptr", "i32"), "i32"), "sets the guest attribute kind"),
    "pthread_mutexattr_destroy": (abi.Signature(("ptr",), "i32"), "guest attribute has no resources to free"),
    "pthread_key_create": (abi.Signature(("ptr", "ptr"), "i32"), "guest thread key, values are host thread local"),
    "pthread_key_delete": (abi.Signature(("i32",), "i32"), "frees a guest thread key"),
    "pthread_getspecific": (abi.Signature(("i32",), "ptr"), "reads the calling host thread's value"),
    "pthread_setspecific": (abi.Signature(("i32", "ptr"), "i32"), "writes the calling host thread's value"),
    "clock_gettime": (abi.Signature(("i32", "ptr"), "i32"), "guest clock ids over host clocks, guest timespec layout"),
}


@dataclass
class StubPlan:
    rows: list[dict] = field(default_factory=list)
    imports: list[abi.Binding] = field(default_factory=list)
    aliases: dict[int, int] = field(default_factory=dict)
    compat: dict[str, int] = field(default_factory=dict)


def host_name(name: str) -> str:
    """The unique C name an adapter calls an import by, so it cannot clash with a prototype the headers declare."""
    return f"import_{name}"


def _row(address: int, name: str, disposition: str, reason: str, host: str | None = None) -> dict:
    return {"address": address, "name": name, "disposition": disposition, "reason": reason, "host": host}


def plan_stubs(
    sdk: lift_sdk.Sdk, stubs: dict[int, str], defined: dict[str, int] | None = None, entries=(), tls: abi.Tls | None = None
) -> StubPlan:
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
        if tls and name == "__tls_get_addr":
            plan.rows.append(_row(address, name, "compat", "single guest TLS module on host threads"))
            if address != tls.get_addr:
                plan.aliases[address] = tls.get_addr
            continue
        if name in COMPAT:
            plan.rows.append(_row(address, name, "compat", COMPAT[name][1]))
            if name in plan.compat:
                plan.aliases[address] = plan.compat[name]
            else:
                plan.compat[name] = address
                plan.imports.append(abi.Binding(address, host_name(name), COMPAT[name][0]))
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
    tally: dict = {"stubs": len(rows), "alias": 0, "bind": 0, "compat": 0, "abort": 0, "reasons": {}}
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


_ATEXIT_REGISTRY = """
#include <pthread.h>

typedef struct lift_atexit_entry { void *fn; void *arg; void *dso; struct lift_atexit_entry *next; } lift_atexit_entry;
static pthread_mutex_t lift_atexit_lock = PTHREAD_MUTEX_INITIALIZER;
static lift_atexit_entry *lift_atexit_head;

__attribute__((weak)) void *lift_atexit_alloc(size_t size) { return malloc(size); }

static void lift_atexit_invoke(void *fn, void *arg) {
  _Alignas(16) unsigned char reg[8192] = {0};
  _Alignas(16) unsigned char stack[65536] = {0};
  uintptr_t rsp = (uintptr_t)(stack + sizeof stack - 8);
  memcpy(reg + 32, &rsp, 8);
  memcpy(reg + 0x38, &arg, 8);
  ((void (*)(unsigned char *))(uintptr_t)fn)(reg);
  uintptr_t returned;
  memcpy(&returned, reg + 32, 8);
  if (returned != rsp + 8) {
    fputs("lift_compat: __cxa_finalize: guest stack imbalance\\n", stderr);
    abort();
  }
}

static int32_t lift_atexit_register(void *fn, void *arg, void *dso) {
  if (!fn) return 0;
  lift_atexit_entry *entry = lift_atexit_alloc(sizeof *entry);
  if (!entry) {
    fputs("lift_compat: __cxa_atexit: out of memory\\n", stderr);
    return 1;
  }
  *entry = (lift_atexit_entry){fn, arg, dso, 0};
  pthread_mutex_lock(&lift_atexit_lock);
  entry->next = lift_atexit_head;
  lift_atexit_head = entry;
  pthread_mutex_unlock(&lift_atexit_lock);
  return 0;
}

static void lift_atexit_drain(void *dso) {
  for (;;) {
    pthread_mutex_lock(&lift_atexit_lock);
    lift_atexit_entry **link = &lift_atexit_head;
    while (*link && dso && (*link)->dso != dso) link = &(*link)->next;
    lift_atexit_entry *entry = *link;
    if (!entry) {
      pthread_mutex_unlock(&lift_atexit_lock);
      return;
    }
    *link = entry->next;
    pthread_mutex_unlock(&lift_atexit_lock);
    lift_atexit_invoke(entry->fn, entry->arg);
  }
}
"""

# The 40-byte glibc guest pthread_mutex_t: our host pthread_mutex_t pointer lives at +16, the kind at +24.
# A zeroed struct is PTHREAD_MUTEX_INITIALIZER: the host mutex is created on first use, normal kind.
_MUTEX_REGISTRY = """
#include <errno.h>
#include <pthread.h>

#define LIFT_MUTEX_PTR 16
#define LIFT_MUTEX_KIND 24
#define LIFT_EPERM 1
#define LIFT_EBUSY 16
#ifndef LIFT_EINVAL
#define LIFT_EINVAL 22
#endif
#ifndef LIFT_ENOMEM
#define LIFT_ENOMEM 12
#endif
#define LIFT_EDEADLK 35

__attribute__((weak)) void *lift_mutex_alloc(size_t size) { return malloc(size); }
__attribute__((weak)) void lift_mutex_free(void *ptr) { free(ptr); }

static pthread_mutex_t lift_mutex_create_lock = PTHREAD_MUTEX_INITIALIZER;

static int lift_host_kind(int32_t kind) {
  if (kind == 1) return PTHREAD_MUTEX_RECURSIVE;
  if (kind == 2) return PTHREAD_MUTEX_ERRORCHECK;
  return PTHREAD_MUTEX_NORMAL;
}

static pthread_mutex_t *lift_mutex_get(void *mutex, int32_t kind) {
  pthread_mutex_t *host = *(pthread_mutex_t **)((unsigned char *)mutex + LIFT_MUTEX_PTR);
  if (host) return host;
  pthread_mutex_lock(&lift_mutex_create_lock);
  host = *(pthread_mutex_t **)((unsigned char *)mutex + LIFT_MUTEX_PTR);
  if (!host) {
    host = lift_mutex_alloc(sizeof *host);
    if (host) {
      pthread_mutexattr_t attr;
      pthread_mutexattr_init(&attr);
      pthread_mutexattr_settype(&attr, lift_host_kind(kind));
      if (pthread_mutex_init(host, &attr)) {
        lift_mutex_free(host);
        host = 0;
      }
      pthread_mutexattr_destroy(&attr);
      *(pthread_mutex_t **)((unsigned char *)mutex + LIFT_MUTEX_PTR) = host;
    }
  }
  pthread_mutex_unlock(&lift_mutex_create_lock);
  return host;
}

static int32_t lift_mutex_init(void *mutex, void *attr) {
  int32_t kind = attr ? *(int32_t *)attr & 3 : 0;
  pthread_mutex_t *stale = *(pthread_mutex_t **)((unsigned char *)mutex + LIFT_MUTEX_PTR);
  if (stale) {
    lift_mutex_free(stale);
    *(pthread_mutex_t **)((unsigned char *)mutex + LIFT_MUTEX_PTR) = 0;
  }
  *(int32_t *)((unsigned char *)mutex + LIFT_MUTEX_KIND) = kind;
  return lift_mutex_get(mutex, kind) ? 0 : LIFT_ENOMEM;
}

static int32_t lift_mutex_lock(void *mutex) {
  pthread_mutex_t *host = lift_mutex_get(mutex, *(int32_t *)((unsigned char *)mutex + LIFT_MUTEX_KIND));
  if (!host) return LIFT_ENOMEM;
  switch (pthread_mutex_lock(host)) {
    case 0: return 0;
    case EDEADLK: return LIFT_EDEADLK;
    default: return LIFT_EINVAL;
  }
}

static int32_t lift_mutex_unlock(void *mutex) {
  pthread_mutex_t *host = lift_mutex_get(mutex, *(int32_t *)((unsigned char *)mutex + LIFT_MUTEX_KIND));
  if (!host) return LIFT_EINVAL;
  switch (pthread_mutex_unlock(host)) {
    case 0: return 0;
    case EPERM: return LIFT_EPERM;
    default: return LIFT_EINVAL;
  }
}

static int32_t lift_mutex_destroy(void *mutex) {
  pthread_mutex_t *host = *(pthread_mutex_t **)((unsigned char *)mutex + LIFT_MUTEX_PTR);
  if (!host) {
    *(int32_t *)((unsigned char *)mutex + LIFT_MUTEX_KIND) = 0;
    return 0;
  }
  int failed = pthread_mutex_destroy(host);
  if (failed) return failed == EBUSY ? LIFT_EBUSY : LIFT_EINVAL;
  lift_mutex_free(host);
  *(pthread_mutex_t **)((unsigned char *)mutex + LIFT_MUTEX_PTR) = 0;
  *(int32_t *)((unsigned char *)mutex + LIFT_MUTEX_KIND) = 0;
  return 0;
}

static int32_t lift_mutexattr_init(void *attr) {
  *(int32_t *)attr = 0;
  return 0;
}

static int32_t lift_mutexattr_settype(void *attr, int32_t type) {
  if (type < 0 || type > 3) return LIFT_EINVAL;
  *(int32_t *)attr = type;
  return 0;
}

static int32_t lift_mutexattr_destroy(void *attr) {
  (void)attr;
  return 0;
}
"""

# glibc keys are indices below PTHREAD_KEYS_MAX; values live on a list in one host pthread key, whose
# destructor runs the guest destructors when the host thread exits, glibc's four rounds included.
_KEY_REGISTRY = """
#include <errno.h>
#include <pthread.h>

#define LIFT_KEYS_MAX 1024
#define LIFT_DESTRUCTOR_ROUNDS 4
#define LIFT_EAGAIN 11
#ifndef LIFT_EINVAL
#define LIFT_EINVAL 22
#endif
#ifndef LIFT_ENOMEM
#define LIFT_ENOMEM 12
#endif

__attribute__((weak)) void *lift_key_alloc(size_t size) { return malloc(size); }
__attribute__((weak)) void lift_key_free(void *ptr) { free(ptr); }

typedef struct lift_key_value { int index; void *value; struct lift_key_value *next; } lift_key_value;

static pthread_mutex_t lift_key_lock = PTHREAD_MUTEX_INITIALIZER;
static void *lift_key_destructors[LIFT_KEYS_MAX];
static unsigned char lift_key_used[LIFT_KEYS_MAX];
static pthread_key_t lift_key_thread_slot;
static int lift_key_thread_slot_ready;

static void lift_key_invoke(void *fn, void *arg) {
  _Alignas(16) unsigned char reg[8192] = {0};
  _Alignas(16) unsigned char stack[65536] = {0};
  uintptr_t rsp = (uintptr_t)(stack + sizeof stack - 8);
  memcpy(reg + 32, &rsp, 8);
  memcpy(reg + 0x38, &arg, 8);
  ((void (*)(unsigned char *))(uintptr_t)fn)(reg);
  uintptr_t returned;
  memcpy(&returned, reg + 32, 8);
  if (returned != rsp + 8) {
    fputs("lift_compat: pthread key destructor: guest stack imbalance\\n", stderr);
    abort();
  }
}

static void lift_key_thread_fini(void *state) {
  lift_key_value *values = state;
  for (int round = 0; round < LIFT_DESTRUCTOR_ROUNDS; round++) {
    int ran = 0;
    for (lift_key_value *entry = values; entry; entry = entry->next) {
      if (!entry->value) continue;
      pthread_mutex_lock(&lift_key_lock);
      int live = entry->index >= 0 && entry->index < LIFT_KEYS_MAX && lift_key_used[entry->index];
      void *fn = live ? lift_key_destructors[entry->index] : 0;
      pthread_mutex_unlock(&lift_key_lock);
      if (!fn) continue;
      void *arg = entry->value;
      entry->value = 0;
      lift_key_invoke(fn, arg);
      ran = 1;
    }
    if (!ran) break;
  }
  while (values) {
    lift_key_value *next = values->next;
    lift_key_free(values);
    values = next;
  }
}

static int lift_key_live(int32_t index) {
  if (index < 0 || index >= LIFT_KEYS_MAX) return 0;
  pthread_mutex_lock(&lift_key_lock);
  int used = lift_key_used[index];
  pthread_mutex_unlock(&lift_key_lock);
  return used;
}

static int32_t lift_key_create(int32_t *key, void *destructor) {
  pthread_mutex_lock(&lift_key_lock);
  if (!lift_key_thread_slot_ready) {
    if (pthread_key_create(&lift_key_thread_slot, lift_key_thread_fini)) {
      pthread_mutex_unlock(&lift_key_lock);
      return LIFT_ENOMEM;
    }
    lift_key_thread_slot_ready = 1;
  }
  int32_t index = 0;
  while (index < LIFT_KEYS_MAX && lift_key_used[index]) index++;
  if (index == LIFT_KEYS_MAX) {
    pthread_mutex_unlock(&lift_key_lock);
    return LIFT_EAGAIN;
  }
  lift_key_used[index] = 1;
  lift_key_destructors[index] = destructor;
  pthread_mutex_unlock(&lift_key_lock);
  *key = index;
  return 0;
}

static int32_t lift_key_delete(int32_t index) {
  if (index < 0 || index >= LIFT_KEYS_MAX) return LIFT_EINVAL;
  pthread_mutex_lock(&lift_key_lock);
  if (!lift_key_used[index]) {
    pthread_mutex_unlock(&lift_key_lock);
    return LIFT_EINVAL;
  }
  lift_key_used[index] = 0;
  lift_key_destructors[index] = 0;
  pthread_mutex_unlock(&lift_key_lock);
  return 0;
}

static void *lift_key_get(int32_t index) {
  if (!lift_key_live(index)) return 0;
  lift_key_value *entry = pthread_getspecific(lift_key_thread_slot);
  while (entry) {
    if (entry->index == index) return entry->value;
    entry = entry->next;
  }
  return 0;
}

static int32_t lift_key_set(int32_t index, void *value) {
  if (!lift_key_live(index)) return LIFT_EINVAL;
  lift_key_value *values = pthread_getspecific(lift_key_thread_slot);
  for (lift_key_value *entry = values; entry; entry = entry->next) {
    if (entry->index == index) {
      entry->value = value;
      return 0;
    }
  }
  if (!value) return 0;
  lift_key_value *entry = lift_key_alloc(sizeof *entry);
  if (!entry) return LIFT_ENOMEM;
  entry->index = index;
  entry->value = value;
  entry->next = values;
  if (pthread_setspecific(lift_key_thread_slot, entry)) {
    lift_key_free(entry);
    return LIFT_ENOMEM;
  }
  return 0;
}
"""

# Linux and Darwin number clocks differently and disagree on suspend: glibc CLOCK_MONOTONIC excludes sleep
# (Darwin CLOCK_UPTIME_RAW), glibc CLOCK_BOOTTIME includes it (Darwin CLOCK_MONOTONIC). The guest struct
# timespec is two int64 fields; the host fields are copied positionally rather than through the host type.
_CLOCK_REGISTRY = """
#include <time.h>

#ifndef LIFT_EINVAL
#define LIFT_EINVAL 22
#endif

static int32_t lift_clock_gettime(int32_t clock_id, void *guest_timespec) {
  if (!guest_timespec) return LIFT_EINVAL;
  int host_id;
  switch (clock_id) {
    case 0: case 5: host_id = CLOCK_REALTIME; break;
    case 1: case 4: case 6: host_id = CLOCK_UPTIME_RAW; break;
    case 7: host_id = CLOCK_MONOTONIC; break;
    case 2: host_id = CLOCK_PROCESS_CPUTIME_ID; break;
    case 3: host_id = CLOCK_THREAD_CPUTIME_ID; break;
    default: return LIFT_EINVAL;
  }
  struct timespec ts;
  if (clock_gettime(host_id, &ts) != 0) return LIFT_EINVAL;
  int64_t sec = (int64_t)ts.tv_sec, nsec = (int64_t)ts.tv_nsec;
  memcpy(guest_timespec, &sec, 8);
  memcpy((unsigned char *)guest_timespec + 8, &nsec, 8);
  return 0;
}
"""

_COMPAT_WRAPPERS = {
    "__cxa_atexit": "int32_t import___cxa_atexit(void *a0, void *a1, void *a2) { return lift_atexit_register(a0, a1, a2); }",
    "__cxa_finalize": "void import___cxa_finalize(void *a0) { lift_atexit_drain(a0); }",
    "pthread_mutex_init": "int32_t import_pthread_mutex_init(void *a0, void *a1) { return lift_mutex_init(a0, a1); }",
    "pthread_mutex_lock": "int32_t import_pthread_mutex_lock(void *a0) { return lift_mutex_lock(a0); }",
    "pthread_mutex_unlock": "int32_t import_pthread_mutex_unlock(void *a0) { return lift_mutex_unlock(a0); }",
    "pthread_mutex_destroy": "int32_t import_pthread_mutex_destroy(void *a0) { return lift_mutex_destroy(a0); }",
    "pthread_mutexattr_init": "int32_t import_pthread_mutexattr_init(void *a0) { return lift_mutexattr_init(a0); }",
    "pthread_mutexattr_settype": "int32_t import_pthread_mutexattr_settype(void *a0, int32_t a1) { return lift_mutexattr_settype(a0, a1); }",
    "pthread_mutexattr_destroy": "int32_t import_pthread_mutexattr_destroy(void *a0) { return lift_mutexattr_destroy(a0); }",
    "pthread_key_create": "int32_t import_pthread_key_create(void *a0, void *a1) { return lift_key_create(a0, a1); }",
    "pthread_key_delete": "int32_t import_pthread_key_delete(int32_t a0) { return lift_key_delete(a0); }",
    "pthread_getspecific": "void *import_pthread_getspecific(int32_t a0) { return lift_key_get(a0); }",
    "pthread_setspecific": "int32_t import_pthread_setspecific(int32_t a0, void *a1) { return lift_key_set(a0, a1); }",
    "clock_gettime": "int32_t import_clock_gettime(int32_t a0, void *a1) { return lift_clock_gettime(a0, a1); }",
}

_ATEXIT_NAMES = ("__cxa_atexit", "__cxa_finalize")
_MUTEX_NAMES = tuple(name for name in _COMPAT_WRAPPERS if name.startswith("pthread_mutex"))
_KEY_NAMES = ("pthread_key_create", "pthread_key_delete", "pthread_getspecific", "pthread_setspecific")
_CLOCK_NAMES = ("clock_gettime",)
_REGISTRIES = [
    (set(_ATEXIT_NAMES), _ATEXIT_REGISTRY),
    (set(_MUTEX_NAMES), _MUTEX_REGISTRY),
    (set(_KEY_NAMES), _KEY_REGISTRY),
    (set(_CLOCK_NAMES), _CLOCK_REGISTRY),
]


def compat_source(compat: dict[str, int]) -> str:
    """The host implementation of every compat-disposition import: each registry it needs, then one wrapper per name."""
    if not compat:
        return ""
    names = set(compat)
    body = "".join(block for needed, block in _REGISTRIES if names & needed)
    return body + "\n".join(_COMPAT_WRAPPERS[name] for name in sorted(compat)) + "\n"
