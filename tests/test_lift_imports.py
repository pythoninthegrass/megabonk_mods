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
        "abort": 2,
        "reasons": {"variadic": 1, sdk.ABSENT: 1},
    }


def test_the_import_report_lists_one_row_per_distinct_name_with_its_stub_count(tmp_path):
    sdk_view = view(tmp_path, "long twice(long a);", "int v(const char *s, ...);")
    plan = li.plan_stubs(sdk_view, {0x10: "twice", 0x20: "twice", 0x30: "v"}, {})
    report = li.import_report(sdk_view, plan.rows)
    assert [(r["name"], r["stubs"], r["disposition"]) for r in report] == [("twice", 2, "bind"), ("v", 1, "abort")]
    assert report[0]["sdk_prototype"] == "long (long)"


def test_the_measured_sdk_binds_a_pure_function_and_refuses_one_with_a_layout_the_host_disagrees_on():
    measured = sdk.load()
    plan = li.plan_stubs(measured, {0x10: "strlen", 0x20: "pthread_mutex_lock", 0x30: "__ctype_b_loc"}, {})
    by_name = {row["name"]: row for row in plan.rows}
    assert by_name["strlen"]["disposition"] == "bind"
    assert by_name["pthread_mutex_lock"]["reason"] == sdk.OUTSIDE
    assert by_name["__ctype_b_loc"]["reason"] == sdk.ABSENT
