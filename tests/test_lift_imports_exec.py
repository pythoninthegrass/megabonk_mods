"""Execute lifted bodies that call generated import stubs; every binary runs as a subprocess with a timeout."""

import lift_abi as abi
import lift_imports as li
import lift_probe as lp
import lift_sdk as sdk
import os
import pcode_lift as pl
import pytest
import signal
import subprocess
import sys
import test_pcode_lift as t

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin" or os.uname().machine != "arm64" or not (lp.LLVM / "clang").exists(),
    reason="needs native arm64 macOS and LLVM",
)

CALLER = 0x2000
STUB = 0x5000
IMAGE_BODY = 0x3000
IMAGE_STUB = 0x5800


@pytest.fixture(scope="module")
def measured():
    return sdk.load()


def caller(start, stub):
    """A lifted body that calls one stub and returns, the shape a PLT call has in lifted code."""
    return {
        **t.body(
            t.insn(start, 5, t.op("CALL", None, f"ram,{stub:x},8")),
            t.insn(start + 5, 1, t.op("RETURN", None, "register,288,8")),
            start=start,
        ),
        "undecoded": 0,
    }


def returns_seven(start):
    """An image function: rax = 7, then the pop of the return address a `ret` performs."""
    ops = [
        t.op("COPY", "register,0,8", "const,7,8"),
        t.op("INT_ADD", "register,20,8", "register,20,8", "const,8,8"),
        t.op("RETURN", None, "register,288,8"),
    ]
    return {**t.body(t.insn(start, 6, *ops), start=start), "undecoded": 0}


def build(tmp_path, view, imports, driver, shared=False):
    """Lift one caller per export, define every stub, and link them with a driver; returns the output path.

    `imports` is (export name, signature, import name); each gets its own caller body and stub address.
    """
    stubs = {STUB + 0x10 * i: name for i, (_, _, name) in enumerate(imports)}
    stubs[IMAGE_STUB] = "il2cpp_seven"
    plan = li.plan_stubs(view, stubs, {"il2cpp_seven": IMAGE_BODY}, {IMAGE_BODY})
    exports, bodies = [], [returns_seven(IMAGE_BODY)]
    for i, (export, signature, _) in enumerate(imports):
        exports.append(abi.Binding(CALLER + 0x10 * i, export, signature))
        bodies.append(caller(CALLER + 0x10 * i, STUB + 0x10 * i))
    exports.append(abi.Binding(CALLER + 0x10 * len(imports), "call_seven", abi.Signature((), "u64")))
    bodies.append(caller(CALLER + 0x10 * len(imports), IMAGE_STUB))
    lifted = [pl.lift_body(row) for row in bodies]
    ir, shim, source = tmp_path / "lifted.ll", tmp_path / "shim.c", tmp_path / "driver.c"
    ir.write_text(pl.module_for(lifted))
    shim.write_text(
        abi.generate(exports, plan.imports, callable_bodies=[IMAGE_BODY], aliases=plan.aliases)
        + li.abort_source(plan.rows)
        + "\n"
        + li.abort_stubs(plan.rows)
        + "\n"
    )
    source.write_text(driver)
    out = tmp_path / ("libimports.dylib" if shared else "imports")
    flags = ["-dynamiclib", "-Wl,-undefined,error"] if shared else []
    subprocess.run(
        [lp.LLVM / "clang", "-arch", "arm64", "-O2", *flags, ir, shim, source, "-o", out],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return out, plan


def run(exe, *args):
    return subprocess.run([str(exe), *args], capture_output=True, text=True, timeout=30)


FORWARDING = [
    ("call_abs", abi.Signature(("i32",), "i32"), "abs"),
    ("call_strlen", abi.Signature(("ptr",), "u64"), "strlen"),
    ("call_atan2", abi.Signature(("f64", "f64"), "f64"), "atan2"),
    ("call_memchr", abi.Signature(("ptr", "i32", "u64"), "ptr"), "memchr"),
    ("call_sinf", abi.Signature(("f32",), "f32"), "sinf"),
]
DRIVER = """
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
int32_t call_abs(int32_t);
uint64_t call_strlen(void *);
double call_atan2(double, double);
void *call_memchr(void *, int32_t, uint64_t);
float call_sinf(float);
uint64_t call_seven(void);
int main(void) {
  char text[] = "hello";
  printf("%d %llu %.6f %d %.6f %llu\\n", call_abs(-5), (unsigned long long)call_strlen(text), call_atan2(1.0, 1.0),
         (int)((char *)call_memchr(text, 'l', 5) - text), call_sinf(0.5f), (unsigned long long)call_seven());
  return 0;
}
"""


@pytest.fixture(scope="module")
def forwarding(tmp_path_factory, measured):
    exe, plan = build(tmp_path_factory.mktemp("forward"), measured, FORWARDING, DRIVER)
    return exe, plan


def test_a_bound_import_forwards_integer_pointer_double_and_float_arguments_and_results(forwarding):
    result = run(forwarding[0])
    assert result.returncode == 0, result.stderr
    assert result.stdout.split()[:5] == ["5", "5", "0.785398", "2", f"{__import__('math').sin(0.5):.6f}"]


def test_a_stub_of_a_function_the_image_defines_forwards_to_that_body(forwarding):
    assert run(forwarding[0]).stdout.split()[5] == "7"
    assert forwarding[1].aliases == {IMAGE_STUB: IMAGE_BODY}


REFUSED = [
    ("call_fseek", "fseek", "record parameter"),
    ("call_sprintf", "sprintf", "variadic"),
    ("call_read", "read", sdk.OUTSIDE),
    ("call_ctype", "__ctype_b_loc", sdk.ABSENT),
]
REFUSED_DRIVER = """
#include <stdint.h>
#include <string.h>
uint64_t call_fseek(void);
uint64_t call_sprintf(void);
uint64_t call_read(void);
uint64_t call_ctype(void);
uint64_t call_seven(void);
int main(int argc, char **argv) {
  if (!strcmp(argv[1], "fseek")) return (int)call_fseek();
  if (!strcmp(argv[1], "sprintf")) return (int)call_sprintf();
  if (!strcmp(argv[1], "read")) return (int)call_read();
  if (!strcmp(argv[1], "ctype")) return (int)call_ctype();
  return 0;
}
"""


@pytest.fixture(scope="module")
def refused(tmp_path_factory, measured):
    imports = [(export, abi.Signature((), "u64"), name) for export, name, _ in REFUSED]
    return build(tmp_path_factory.mktemp("refused"), measured, imports, REFUSED_DRIVER)[0]


@pytest.mark.parametrize(
    "mode, name, reason",
    [
        ("fseek", "fseek", "record parameter"),
        ("sprintf", "sprintf", "variadic"),
        ("read", "read", sdk.OUTSIDE),
        ("ctype", "__ctype_b_loc", sdk.ABSENT),
    ],
)
def test_a_refused_import_aborts_naming_the_symbol_and_the_reason(refused, mode, name, reason):
    result = run(refused, mode)
    assert result.returncode == -signal.SIGABRT
    assert f"lift_import_refused: {name}: {reason}" in result.stderr


def test_a_dylib_defines_every_stub_and_loads_in_a_fresh_process(tmp_path_factory, measured):
    work = tmp_path_factory.mktemp("dylib")
    dylib, _ = build(work, measured, FORWARDING, "int unused_main_marker;\n", shared=True)
    undefined = subprocess.run([lp.LLVM / "llvm-nm", "-u", dylib], capture_output=True, text=True, check=True).stdout
    assert not [line for line in undefined.split() if line.lstrip("_").startswith("sub_")]
    arch = subprocess.run(["lipo", "-archs", str(dylib)], capture_output=True, text=True, check=True).stdout.split()
    assert arch == ["arm64"]
    loader = work / "loader.c"
    loader.write_text(
        '#include <dlfcn.h>\n#include <stdio.h>\nint main(int c, char **v) { return dlopen(v[1], RTLD_NOW) ? 0 : (puts(dlerror()), 1); }\n'
    )
    program = work / "loader"
    subprocess.run([lp.LLVM / "clang", "-arch", "arm64", loader, "-o", program], check=True, capture_output=True, timeout=60)
    result = run(program, str(dylib))
    assert result.returncode == 0, result.stdout + result.stderr


ATEXIT_STUBS = {0x5000: "__cxa_atexit", 0x5010: "__cxa_finalize"}

ATEXIT_DRIVER = """
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int32_t import___cxa_atexit(void *, void *, void *);
void import___cxa_finalize(void *);

static atomic_int logged;
static int ids[256];
static uintptr_t args[256];

static void record(int id, unsigned char *reg) {
    uint64_t arg, rsp;
    memcpy(&arg, reg + 0x38, 8);
    int at = atomic_fetch_add(&logged, 1);
    ids[at] = id;
    args[at] = (uintptr_t)arg;
    memcpy(&rsp, reg + 32, 8);
    rsp += 8;
    memcpy(reg + 32, &rsp, 8);
}
#define DTOR(n) static void d##n(unsigned char *reg) { record(n, reg); }
DTOR(1)
DTOR(2)
DTOR(3)
DTOR(4)
static void bad(unsigned char *reg) { (void)reg; }

static int fail_next_alloc;
void *lift_atexit_alloc(size_t size) { return fail_next_alloc ? (fail_next_alloc = 0, NULL) : malloc(size); }

static void report(const char *label) {
    printf("%s ", label);
    for (int i = 0; i < atomic_load(&logged); i++) printf("%d:%llu ", ids[i], (unsigned long long)args[i]);
    printf("\\n");
}

static void *registerer(void *arg) {
    for (int i = 0; i < 50; i++) {
        if (import___cxa_atexit((void *)(uintptr_t)d1, (void *)(uintptr_t)(100 + i), (void *)(uintptr_t)1)) abort();
    }
    (void)arg;
    return NULL;
}

int main(int argc, char **argv) {
    void *a = (void *)0xAAAA, *b = (void *)0xBBBB;
    if (!strcmp(argv[1], "lifo")) {
        if (import___cxa_atexit((void *)(uintptr_t)d1, (void *)11, a)) return 1;
        if (import___cxa_atexit((void *)(uintptr_t)d2, (void *)22, a)) return 1;
        if (import___cxa_atexit((void *)(uintptr_t)d3, (void *)33, b)) return 1;
        if (import___cxa_atexit((void *)(uintptr_t)d4, (void *)44, NULL)) return 1;
        if (import___cxa_atexit(NULL, (void *)55, NULL)) return 1;
        import___cxa_finalize(a);
        if (atomic_load(&logged) != 2) return 2;
        import___cxa_finalize(a);
        if (atomic_load(&logged) != 2) return 2;
        import___cxa_finalize(NULL);
        report("lifo");
        return 0;
    }
    if (!strcmp(argv[1], "imbalance")) {
        import___cxa_atexit((void *)(uintptr_t)bad, NULL, NULL);
        import___cxa_finalize(NULL);
        return 0;
    }
    if (!strcmp(argv[1], "threads")) {
        pthread_t first, second;
        if (pthread_create(&first, NULL, registerer, NULL) || pthread_create(&second, NULL, registerer, NULL)) return 1;
        if (pthread_join(first, NULL) || pthread_join(second, NULL)) return 1;
        import___cxa_finalize(NULL);
        return atomic_load(&logged) == 100 ? 0 : 2;
    }
    if (!strcmp(argv[1], "oom")) {
        fail_next_alloc = 1;
        int first = import___cxa_atexit((void *)(uintptr_t)d1, (void *)11, NULL);
        import___cxa_finalize(NULL);
        printf("oom %d %d\\n", first, atomic_load(&logged));
        return 0;
    }
    return 3;
}
"""


def build_atexit(tmp_path):
    plan = li.plan_stubs(sdk.Sdk([]), ATEXIT_STUBS, {})
    shim = tmp_path / "atexit_shim.c"
    shim.write_text(abi.generate([], plan.imports, aliases=plan.aliases) + "\n" + li.compat_source(plan.compat) + "\n")
    driver = tmp_path / "atexit_driver.c"
    driver.write_text(ATEXIT_DRIVER)
    exe = tmp_path / "atexit"
    subprocess.run(
        [lp.LLVM / "clang", "-arch", "arm64", "-O2", shim, driver, "-o", exe],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return exe


@pytest.fixture(scope="module")
def atexit_exe(tmp_path_factory):
    return build_atexit(tmp_path_factory.mktemp("atexit"))


def test_atexit_registrations_drain_last_in_first_out_order_filtered_by_dso(atexit_exe):
    result = run(atexit_exe, "lifo")
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.split() == ["lifo", "2:22", "1:11", "4:44", "3:33"]


def test_a_destructor_that_leaves_the_guest_stack_imbalanced_aborts_by_name(atexit_exe):
    result = run(atexit_exe, "imbalance")
    assert result.returncode == -signal.SIGABRT
    assert "lift_compat: __cxa_finalize: guest stack imbalance" in result.stderr


def test_concurrent_registrations_all_drain_exactly_once(atexit_exe):
    result = run(atexit_exe, "threads")
    assert result.returncode == 0, result.stdout + result.stderr


def test_a_registration_that_cannot_allocate_returns_nonzero_without_storing_the_entry(atexit_exe):
    result = run(atexit_exe, "oom")
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.split() == ["oom", "1", "0"]


MUTEX_NAMES = [
    "pthread_mutex_init",
    "pthread_mutex_lock",
    "pthread_mutex_unlock",
    "pthread_mutex_destroy",
    "pthread_mutexattr_init",
    "pthread_mutexattr_settype",
    "pthread_mutexattr_destroy",
]

MUTEX_DRIVER = """
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int32_t import_pthread_mutex_init(void *, void *);
int32_t import_pthread_mutex_destroy(void *);
int32_t import_pthread_mutex_lock(void *);
int32_t import_pthread_mutex_unlock(void *);
int32_t import_pthread_mutexattr_init(void *);
int32_t import_pthread_mutexattr_settype(void *, int32_t);
int32_t import_pthread_mutexattr_destroy(void *);

#define L_EPERM 1
#define L_EBUSY 16
#define L_EINVAL 22
#define L_ENOMEM 12
#define L_EDEADLK 35

static int fail_next_alloc;
void *lift_mutex_alloc(size_t size) { return fail_next_alloc ? (fail_next_alloc = 0, NULL) : malloc(size); }
void lift_mutex_free(void *ptr) { free(ptr); }

static _Alignas(8) unsigned char mutex[40];
static _Alignas(4) unsigned char attr[4];

static long counter;
static void *worker(void *arg) {
    for (int i = 0; i < 10000; i++) {
        if (import_pthread_mutex_lock(arg)) abort();
        counter += 1;
        if (import_pthread_mutex_unlock(arg)) abort();
    }
    return NULL;
}

int main(int argc, char **argv) {
    const char *mode = argv[1];
    memset(mutex, 0, sizeof mutex);
    memset(attr, 0x5A, sizeof attr);
    if (!strcmp(mode, "basic")) {
        if (import_pthread_mutex_init(mutex, NULL)) return 1;
        if (import_pthread_mutex_lock(mutex)) return 2;
        if (import_pthread_mutex_unlock(mutex)) return 3;
        if (import_pthread_mutex_destroy(mutex)) return 4;
        return 0;
    }
    if (!strcmp(mode, "static")) {
        if (import_pthread_mutex_lock(mutex)) return 1;
        if (import_pthread_mutex_unlock(mutex)) return 2;
        if (import_pthread_mutex_destroy(mutex)) return 3;
        return 0;
    }
    if (!strcmp(mode, "kinds")) {
        if (import_pthread_mutexattr_init(attr)) return 1;
        if (*(int *)attr != 0) return 1;
        if (import_pthread_mutexattr_settype(attr, 2)) return 2;
        if (import_pthread_mutex_init(mutex, attr)) return 3;
        if (*(int *)(mutex + 24) != 2) return 3;
        if (import_pthread_mutex_lock(mutex)) return 4;
        if (import_pthread_mutex_lock(mutex) != L_EDEADLK) return 5;
        if (import_pthread_mutex_unlock(mutex)) return 6;
        if (import_pthread_mutex_unlock(mutex) != L_EPERM) return 7;
        if (import_pthread_mutex_destroy(mutex)) return 8;
        memset(mutex, 0, sizeof mutex);
        if (import_pthread_mutexattr_settype(attr, 1)) return 9;
        if (import_pthread_mutex_init(mutex, attr)) return 10;
        if (import_pthread_mutex_lock(mutex)) return 11;
        if (import_pthread_mutex_lock(mutex)) return 12;
        if (import_pthread_mutex_unlock(mutex)) return 13;
        if (import_pthread_mutex_unlock(mutex)) return 14;
        if (import_pthread_mutexattr_destroy(attr)) return 15;
        return 0;
    }
    if (!strcmp(mode, "contend")) {
        pthread_t first, second;
        if (pthread_create(&first, NULL, worker, mutex) || pthread_create(&second, NULL, worker, mutex)) return 1;
        if (pthread_join(first, NULL) || pthread_join(second, NULL)) return 2;
        return counter == 20000 ? 0 : 3;
    }
    if (!strcmp(mode, "destroy-locked")) {
        if (import_pthread_mutex_init(mutex, NULL)) return 1;
        if (import_pthread_mutex_lock(mutex)) return 2;
        if (import_pthread_mutex_destroy(mutex) != L_EBUSY) return 3;
        if (import_pthread_mutex_unlock(mutex)) return 4;
        if (import_pthread_mutex_destroy(mutex)) return 5;
        return 0;
    }
    if (!strcmp(mode, "badtype")) {
        if (import_pthread_mutexattr_init(attr)) return 1;
        if (import_pthread_mutexattr_settype(attr, 4) != L_EINVAL) return 2;
        if (import_pthread_mutexattr_settype(attr, -1) != L_EINVAL) return 3;
        if (import_pthread_mutexattr_settype(attr, 0)) return 4;
        if (import_pthread_mutexattr_settype(attr, 3)) return 5;
        if (import_pthread_mutexattr_destroy(attr)) return 6;
        return 0;
    }
    if (!strcmp(mode, "oom")) {
        fail_next_alloc = 1;
        if (import_pthread_mutex_init(mutex, NULL) != L_ENOMEM) return 1;
        return 0;
    }
    return 3;
}
"""


def build_mutex(tmp_path):
    stubs = {0x5000 + 0x10 * i: name for i, name in enumerate(MUTEX_NAMES)}
    plan = li.plan_stubs(sdk.Sdk([]), stubs, {})
    shim = tmp_path / "mutex_shim.c"
    shim.write_text(abi.generate([], plan.imports, aliases=plan.aliases) + "\n" + li.compat_source(plan.compat) + "\n")
    driver = tmp_path / "mutex_driver.c"
    driver.write_text(MUTEX_DRIVER)
    exe = tmp_path / "mutex"
    subprocess.run(
        [lp.LLVM / "clang", "-arch", "arm64", "-O2", shim, driver, "-o", exe],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return exe


@pytest.fixture(scope="module")
def mutex_exe(tmp_path_factory):
    return build_mutex(tmp_path_factory.mktemp("mutex"))


@pytest.mark.parametrize("mode", ["basic", "static", "kinds", "contend", "destroy-locked", "badtype", "oom"])
def test_guest_mutexes_keep_glibc_lock_semantics_and_return_codes(mutex_exe, mode):
    result = run(mutex_exe, mode)
    assert result.returncode == 0, f"{mode}: rc={result.returncode} out={result.stdout} err={result.stderr}"


KEY_NAMES = [
    "pthread_key_create",
    "pthread_key_delete",
    "pthread_getspecific",
    "pthread_setspecific",
]

KEY_DRIVER = """
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int32_t import_pthread_key_create(void *, void *);
int32_t import_pthread_key_delete(int32_t);
void *import_pthread_getspecific(int32_t);
int32_t import_pthread_setspecific(int32_t, void *);

#define L_EAGAIN 11
#define L_EINVAL 22
#define L_ENOMEM 12
#define LIFT_KEYS_MAX 1024

static int fail_next_alloc;
void *lift_key_alloc(size_t size) { return fail_next_alloc ? (fail_next_alloc = 0, NULL) : malloc(size); }
void lift_key_free(void *ptr) { free(ptr); }

static atomic_int dtor_runs;
static atomic_uintptr_t dtor_value;

static void dtor(unsigned char *reg) {
    uint64_t arg, rsp;
    memcpy(&arg, reg + 0x38, 8);
    memcpy(&rsp, reg + 32, 8);
    rsp += 8;
    memcpy(reg + 32, &rsp, 8);
    atomic_store(&dtor_value, (uintptr_t)arg);
    atomic_fetch_add(&dtor_runs, 1);
}

static int key;
static void *const marker = (void *)0xF00D;

static void *setter(void *arg) {
    if (import_pthread_setspecific(key, arg)) abort();
    for (int i = 0; i < 10000; i++) {
        if (import_pthread_getspecific(key) != arg) abort();
    }
    return NULL;
}

int main(int argc, char **argv) {
    const char *mode = argv[1];
    if (!strcmp(mode, "basic")) {
        int k;
        if (import_pthread_key_create(&k, NULL)) return 1;
        if (k < 0 || k >= LIFT_KEYS_MAX) return 1;
        if (import_pthread_setspecific(k, marker)) return 2;
        if (import_pthread_getspecific(k) != marker) return 3;
        if (import_pthread_setspecific(k, NULL)) return 4;
        if (import_pthread_key_delete(k)) return 5;
        return 0;
    }
    if (!strcmp(mode, "invalid")) {
        if (import_pthread_getspecific(-1)) return 1;
        if (import_pthread_getspecific(LIFT_KEYS_MAX)) return 2;
        if (import_pthread_setspecific(LIFT_KEYS_MAX, marker) != L_EINVAL) return 3;
        if (import_pthread_key_delete(LIFT_KEYS_MAX) != L_EINVAL) return 4;
        if (import_pthread_key_delete(-1) != L_EINVAL) return 5;
        return 0;
    }
    if (!strcmp(mode, "isolation")) {
        if (import_pthread_key_create(&key, NULL)) return 1;
        pthread_t first, second;
        if (pthread_create(&first, NULL, setter, (void *)0x1000) || pthread_create(&second, NULL, setter, (void *)0x2000)) return 2;
        if (pthread_join(first, NULL) || pthread_join(second, NULL)) return 3;
        if (import_pthread_key_delete(key)) return 4;
        return 0;
    }
    if (!strcmp(mode, "destructor")) {
        if (import_pthread_key_create(&key, (void *)dtor)) return 1;
        pthread_t thread;
        if (pthread_create(&thread, NULL, setter, marker)) return 2;
        if (pthread_join(thread, NULL)) return 3;
        if (atomic_load(&dtor_runs) != 1) return 4;
        if (atomic_load(&dtor_value) != (uintptr_t)marker) return 5;
        if (import_pthread_key_delete(key)) return 6;
        return 0;
    }
    if (!strcmp(mode, "exhaustion")) {
        static int keys[LIFT_KEYS_MAX];
        for (int i = 0; i < LIFT_KEYS_MAX; i++) {
            if (import_pthread_key_create(&keys[i], NULL)) return 1;
            if (keys[i] < 0 || keys[i] >= LIFT_KEYS_MAX) return 1;
        }
        int extra;
        if (import_pthread_key_create(&extra, NULL) != L_EAGAIN) return 2;
        for (int i = 0; i < LIFT_KEYS_MAX; i++) {
            if (import_pthread_key_delete(keys[i])) return 3;
        }
        if (import_pthread_key_create(&extra, NULL)) return 4;
        if (import_pthread_key_delete(extra)) return 5;
        return 0;
    }
    if (!strcmp(mode, "oom")) {
        int k;
        if (import_pthread_key_create(&k, NULL)) return 1;
        fail_next_alloc = 1;
        if (import_pthread_setspecific(k, marker) != L_ENOMEM) return 2;
        fail_next_alloc = 0;
        if (import_pthread_setspecific(k, marker)) return 3;
        if (import_pthread_getspecific(k) != marker) return 4;
        if (import_pthread_key_delete(k)) return 5;
        return 0;
    }
    return 3;
}
"""


def build_key(tmp_path):
    stubs = {0x5000 + 0x10 * i: name for i, name in enumerate(KEY_NAMES)}
    plan = li.plan_stubs(sdk.Sdk([]), stubs, {})
    shim = tmp_path / "key_shim.c"
    shim.write_text(abi.generate([], plan.imports, aliases=plan.aliases) + "\n" + li.compat_source(plan.compat) + "\n")
    driver = tmp_path / "key_driver.c"
    driver.write_text(KEY_DRIVER)
    exe = tmp_path / "key"
    subprocess.run(
        [lp.LLVM / "clang", "-arch", "arm64", "-O2", shim, driver, "-o", exe],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return exe


@pytest.fixture(scope="module")
def key_exe(tmp_path_factory):
    return build_key(tmp_path_factory.mktemp("key"))


@pytest.mark.parametrize("mode", ["basic", "invalid", "isolation", "destructor", "exhaustion", "oom"])
def test_guest_thread_keys_are_independent_per_host_thread(key_exe, mode):
    result = run(key_exe, mode)
    assert result.returncode == 0, f"{mode}: rc={result.returncode} out={result.stdout} err={result.stderr}"


CLOCK_DRIVER = """
#include <stdint.h>
#include <stdio.h>
#include <string.h>

int32_t import_clock_gettime(int32_t, void *);

#define L_EINVAL 22

static void spin(void) {
    volatile long sink = 0;
    for (long i = 0; i < 20000000L; i++) sink += i;
}

int main(int argc, char **argv) {
    const char *mode = argv[1];
    int64_t ts[2], later[2];
    if (!strcmp(mode, "realtime")) {
        ts[0] = ts[1] = -7;
        if (import_clock_gettime(0, ts)) return 1;
        if (ts[0] < 1700000000LL || ts[0] > 4000000000LL) return 2;
        if (ts[1] < 0 || ts[1] >= 1000000000LL) return 3;
        return 0;
    }
    if (!strcmp(mode, "monotonic")) {
        if (import_clock_gettime(1, ts)) return 1;
        if (ts[0] < 0 || ts[0] > 1000000000LL) return 2;
        if (ts[1] < 0 || ts[1] >= 1000000000LL) return 3;
        spin();
        if (import_clock_gettime(1, later)) return 4;
        if (later[0] * 1000000000LL + later[1] <= ts[0] * 1000000000LL + ts[1]) return 5;
        return 0;
    }
    if (!strcmp(mode, "ids")) {
        int ids[] = {2, 3, 4, 5, 6, 7};
        for (unsigned i = 0; i < sizeof ids / sizeof ids[0]; i++) {
            if (import_clock_gettime(ids[i], ts)) return 1 + (int)i;
        }
        return 0;
    }
    if (!strcmp(mode, "invalid")) {
        memset(ts, 0xAA, sizeof ts);
        if (import_clock_gettime(99, ts) != L_EINVAL) return 1;
        int64_t poison = (int64_t)0xAAAAAAAAAAAAAAAALL;
        if (ts[0] != poison || ts[1] != poison) return 2;
        if (import_clock_gettime(0, NULL) != L_EINVAL) return 3;
        return 0;
    }
    return 3;
}
"""


def build_clock(tmp_path):
    plan = li.plan_stubs(sdk.Sdk([]), {0x5000: "clock_gettime"}, {})
    shim = tmp_path / "clock_shim.c"
    shim.write_text(abi.generate([], plan.imports, aliases=plan.aliases) + "\n" + li.compat_source(plan.compat) + "\n")
    driver = tmp_path / "clock_driver.c"
    driver.write_text(CLOCK_DRIVER)
    exe = tmp_path / "clock"
    subprocess.run(
        [lp.LLVM / "clang", "-arch", "arm64", "-O2", shim, driver, "-o", exe],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return exe


@pytest.fixture(scope="module")
def clock_exe(tmp_path_factory):
    return build_clock(tmp_path_factory.mktemp("clock"))


@pytest.mark.parametrize("mode", ["realtime", "monotonic", "ids", "invalid"])
def test_guest_clock_ids_keep_glibc_semantics_and_write_the_guest_timespec(clock_exe, mode):
    result = run(clock_exe, mode)
    assert result.returncode == 0, f"{mode}: rc={result.returncode} out={result.stdout} err={result.stderr}"
