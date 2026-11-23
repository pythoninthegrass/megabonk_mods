"""Every lifted PLT stub gets one definition: an image alias, an SDK-cleared host call, or a named abort."""

import lift_abi as abi
import lift_imports as li
import lift_sdk as sdk
import pytest


def view(tmp_path, *declarations, header="string.h"):
    (tmp_path / header).write_text("#include <stddef.h>\n" + "\n".join(declarations) + "\n")
    umbrella = tmp_path / "umbrella.c"
    umbrella.write_text(f'#include "{header}"\n')
    return sdk.Sdk([sdk._dump(umbrella)])


def test_a_scalar_import_binds_under_a_unique_name_and_names_the_host_symbol(tmp_path):
    plan = li.plan_stubs(view(tmp_path, "long twice(long a);"), {0x4000: "twice"}, {})
    assert plan.rows == [{"address": 0x4000, "name": "twice", "disposition": "bind", "reason": li.BOUND, "host": "twice"}]
    assert plan.imports == [abi.Binding(0x4000, "import_twice", abi.Signature(("i64",), "i64"), declared_name="twice")]
    assert plan.aliases == {}


def test_the_register_kinds_of_the_prototype_become_the_binding_signature(tmp_path):
    plan = li.plan_stubs(view(tmp_path, "double mix(double x, int n, void *p);"), {0x4000: "mix"}, {})
    assert plan.imports[0].signature == abi.Signature(("f64", "i32", "ptr"), "f64")


@pytest.mark.parametrize(
    "prototype, reason",
    [
        ("int f(struct widget *w);", "record parameter"),
        ("int f(const char *fmt, ...);", "variadic"),
        ("long double f(int n);", "long double result"),
    ],
)
def test_a_refused_import_becomes_a_named_abort_with_its_reason(tmp_path, prototype, reason):
    plan = li.plan_stubs(view(tmp_path, "struct widget { long w; };", prototype), {0x4000: "f"}, {})
    assert plan.rows[0]["disposition"] == "abort" and plan.rows[0]["reason"] == reason
    assert plan.imports == [] and plan.aliases == {}


def test_an_undeclared_import_aborts_naming_the_absence(tmp_path):
    plan = li.plan_stubs(view(tmp_path, "int other(void);"), {0x4000: "no_such_service"}, {})
    assert plan.rows[0]["disposition"] == "abort" and plan.rows[0]["reason"] == sdk.ABSENT


def test_a_stub_of_a_function_the_image_defines_aliases_that_body(tmp_path):
    plan = li.plan_stubs(view(tmp_path, "int il2cpp_thing(void);"), {0x4000: "il2cpp_thing"}, {"il2cpp_thing": 0x9000}, {0x9000})
    assert plan.rows[0]["disposition"] == "alias" and plan.aliases == {0x4000: 0x9000}
    assert plan.imports == []


def test_a_stub_whose_image_symbol_is_not_a_body_start_aborts_instead_of_aliasing_nothing(tmp_path):
    plan = li.plan_stubs(view(tmp_path, "int f(void);"), {0x4000: "f"}, {"f": 0x9003}, {0x9000})
    assert plan.rows[0]["disposition"] == "abort"
    assert plan.rows[0]["reason"] == "image symbol is not a lifted body start"
    assert plan.aliases == {}


def test_a_second_stub_of_one_bound_import_shares_the_first_definition(tmp_path):
    plan = li.plan_stubs(view(tmp_path, "long twice(long a);"), {0x4000: "twice", 0x4010: "twice"}, {})
    assert len(plan.imports) == 1 and plan.aliases == {0x4010: 0x4000}
    assert [row["disposition"] for row in plan.rows] == ["bind", "bind"]


def test_each_stub_of_a_refused_import_gets_its_own_abort(tmp_path):
    plan = li.plan_stubs(view(tmp_path, "int f(const char *fmt, ...);"), {0x4000: "f", 0x4010: "f"}, {})
    assert [row["disposition"] for row in plan.rows] == ["abort", "abort"]
    assert li.abort_stubs(plan.rows).count("void sub_") == 2
    assert li.abort_source(plan.rows).count("void lift_abort_f(void)") == 1


def test_the_abort_prints_the_import_name_and_the_reason_before_it_aborts(tmp_path):
    plan = li.plan_stubs(view(tmp_path, "int f(const char *fmt, ...);"), {0x4000: "f"}, {})
    source = li.abort_source(plan.rows)
    assert 'lift_import_refused: f: variadic' in source and "abort();" in source
    assert "void sub_4000(unsigned char *reg)" in li.abort_stubs(plan.rows)


def test_the_stub_report_counts_every_disposition_and_reason(tmp_path):
    plan = li.plan_stubs(
        view(tmp_path, "long twice(long a);", "int v(const char *s, ...);", "int il2cpp_x(void);"),
        {0x10: "twice", 0x20: "v", 0x30: "il2cpp_x", 0x40: "missing"},
        {"il2cpp_x": 0x99},
        {0x99},
    )
    assert li.counts(plan.rows) == {
        "stubs": 4,
        "alias": 1,
        "bind": 1,
        "compat": 0,
        "abort": 2,
        "reasons": {"variadic": 1, sdk.ABSENT: 1},
    }


def test_the_import_report_lists_one_row_per_distinct_name_with_its_stub_count(tmp_path):
    sdk_view = view(tmp_path, "long twice(long a);", "int v(const char *s, ...);")
    plan = li.plan_stubs(sdk_view, {0x10: "twice", 0x20: "twice", 0x30: "v"}, {})
    report = li.import_report(sdk_view, plan.rows)
    assert [(r["name"], r["stubs"], r["disposition"]) for r in report] == [("twice", 2, "bind"), ("v", 1, "abort")]
    assert report[0]["sdk_prototype"] == "long (long)"


def test_guest_atexit_and_finalize_plan_as_one_compat_definition_each(tmp_path):
    plan = li.plan_stubs(view(tmp_path), {0x4000: "__cxa_atexit", 0x4010: "__cxa_atexit", 0x4020: "__cxa_finalize"})
    assert [row["disposition"] for row in plan.rows] == ["compat", "compat", "compat"]
    assert plan.compat == {"__cxa_atexit": 0x4000, "__cxa_finalize": 0x4020}
    assert plan.aliases == {0x4010: 0x4000}
    assert plan.imports == [
        abi.Binding(0x4000, "import___cxa_atexit", abi.Signature(("ptr", "ptr", "ptr"), "i32")),
        abi.Binding(0x4020, "import___cxa_finalize", abi.Signature(("ptr",), "void")),
    ]
    assert li.counts(plan.rows)["compat"] == 3


def test_the_guest_mutex_family_plans_as_compat_with_glibc_prototypes(tmp_path):
    names = {
        0x4000: "pthread_mutex_init",
        0x4010: "pthread_mutex_lock",
        0x4020: "pthread_mutex_unlock",
        0x4030: "pthread_mutex_destroy",
        0x4040: "pthread_mutexattr_init",
        0x4050: "pthread_mutexattr_settype",
        0x4060: "pthread_mutexattr_destroy",
    }
    plan = li.plan_stubs(view(tmp_path), names)
    assert [row["disposition"] for row in plan.rows] == ["compat"] * 7
    assert plan.compat == {names[address]: address for address in names}
    assert {binding.name: binding.signature for binding in plan.imports} == {
        "import_pthread_mutex_init": abi.Signature(("ptr", "ptr"), "i32"),
        "import_pthread_mutex_lock": abi.Signature(("ptr",), "i32"),
        "import_pthread_mutex_unlock": abi.Signature(("ptr",), "i32"),
        "import_pthread_mutex_destroy": abi.Signature(("ptr",), "i32"),
        "import_pthread_mutexattr_init": abi.Signature(("ptr",), "i32"),
        "import_pthread_mutexattr_settype": abi.Signature(("ptr", "i32"), "i32"),
        "import_pthread_mutexattr_destroy": abi.Signature(("ptr",), "i32"),
    }


def test_compat_source_defines_the_registry_once_and_one_wrapper_per_name(tmp_path):
    plan = li.plan_stubs(view(tmp_path), {0x4000: "__cxa_atexit", 0x4010: "__cxa_finalize"})
    source = li.compat_source(plan.compat)
    assert source.count("static pthread_mutex_t lift_atexit_lock = PTHREAD_MUTEX_INITIALIZER;") == 1
    assert "int32_t import___cxa_atexit(void *a0, void *a1, void *a2) { return lift_atexit_register(a0, a1, a2); }" in source
    assert "void import___cxa_finalize(void *a0) { lift_atexit_drain(a0); }" in source
    assert 'fputs("lift_compat: __cxa_finalize: guest stack imbalance\\n", stderr);' in source
    assert "pthread_mutex_lock(&lift_atexit_lock);" in source
    assert li.compat_source({}) == ""


def test_compat_source_defines_the_guest_mutex_family_once(tmp_path):
    plan = li.plan_stubs(
        view(tmp_path), {0x4000: "pthread_mutex_init", 0x4010: "pthread_mutex_lock", 0x4020: "pthread_mutexattr_settype"}
    )
    source = li.compat_source(plan.compat)
    assert "int32_t import_pthread_mutex_init(void *a0, void *a1) { return lift_mutex_init(a0, a1); }" in source
    assert "int32_t import_pthread_mutex_lock(void *a0) { return lift_mutex_lock(a0); }" in source
    assert "int32_t import_pthread_mutexattr_settype(void *a0, int32_t a1) { return lift_mutexattr_settype(a0, a1); }" in source
    assert "static pthread_mutex_t *lift_mutex_get(void *mutex, int32_t kind)" in source


def test_guest_thread_key_family_plans_as_compat_with_glibc_prototypes(tmp_path):
    names = {
        0x4000: "pthread_key_create",
        0x4010: "pthread_key_delete",
        0x4020: "pthread_getspecific",
        0x4030: "pthread_setspecific",
    }
    plan = li.plan_stubs(view(tmp_path), names)
    assert [row["disposition"] for row in plan.rows] == ["compat"] * 4
    assert {binding.name: binding.signature for binding in plan.imports} == {
        "import_pthread_key_create": abi.Signature(("ptr", "ptr"), "i32"),
        "import_pthread_key_delete": abi.Signature(("i32",), "i32"),
        "import_pthread_getspecific": abi.Signature(("i32",), "ptr"),
        "import_pthread_setspecific": abi.Signature(("i32", "ptr"), "i32"),
    }


def test_compat_source_defines_the_thread_key_registry_only_for_key_names(tmp_path):
    keys = li.plan_stubs(view(tmp_path), {0x4000: "pthread_key_create", 0x4010: "pthread_getspecific"})
    source = li.compat_source(keys.compat)
    assert "static void *lift_key_destructors[LIFT_KEYS_MAX];" in source
    assert "int32_t import_pthread_key_create(void *a0, void *a1) { return lift_key_create(a0, a1); }" in source
    assert "void *import_pthread_getspecific(int32_t a0) { return lift_key_get(a0); }" in source
    assert "static void lift_key_thread_fini(void *state)" in source
    atexit_only = li.plan_stubs(view(tmp_path), {0x4000: "__cxa_atexit"})
    assert "lift_key_create" not in li.compat_source(atexit_only.compat)


def test_guest_clock_gettime_plans_as_compat_with_the_guest_prototype(tmp_path):
    plan = li.plan_stubs(view(tmp_path), {0x4000: "clock_gettime", 0x4010: "clock_gettime"})
    assert [row["disposition"] for row in plan.rows] == ["compat", "compat"]
    assert plan.imports == [abi.Binding(0x4000, "import_clock_gettime", abi.Signature(("i32", "ptr"), "i32"))]
    assert plan.aliases == {0x4010: 0x4000}


def test_compat_source_defines_the_clock_service_only_when_clock_gettime_is_planned(tmp_path):
    plan = li.plan_stubs(view(tmp_path), {0x4000: "clock_gettime"})
    source = li.compat_source(plan.compat)
    assert "static int32_t lift_clock_gettime(int32_t clock_id, void *guest_timespec)" in source
    assert "int32_t import_clock_gettime(int32_t a0, void *a1) { return lift_clock_gettime(a0, a1); }" in source
    atexit_only = li.plan_stubs(view(tmp_path), {0x4000: "__cxa_atexit"})
    assert "lift_clock_gettime" not in li.compat_source(atexit_only.compat)


def test_the_measured_sdk_binds_a_pure_function_and_refuses_one_with_a_layout_the_host_disagrees_on():
    measured = sdk.load()
    plan = li.plan_stubs(measured, {0x10: "strlen", 0x20: "pthread_cond_wait", 0x30: "__ctype_b_loc"}, {})
    by_name = {row["name"]: row for row in plan.rows}
    assert by_name["strlen"]["disposition"] == "bind"
    assert by_name["pthread_cond_wait"]["reason"] == sdk.OUTSIDE
    assert by_name["__ctype_b_loc"]["reason"] == sdk.ABSENT
