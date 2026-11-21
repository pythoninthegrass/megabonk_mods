"""Whether an imported Linux function may be forwarded to the host is read off the macOS SDK's own prototypes."""

import lift_sdk as sdk
import pytest


def synthetic(tmp_path, *declarations, header="string.h"):
    """An Sdk over one header, named so the family rule sees it, that declares exactly the given prototypes."""
    (tmp_path / header).write_text("#include <stddef.h>\n" + "\n".join(declarations) + "\n")
    umbrella = tmp_path / "umbrella.c"
    umbrella.write_text(f'#include "{header}"\n')
    return sdk.Sdk([sdk._dump(umbrella)])


@pytest.fixture(scope="module")
def measured():
    return sdk.load()


def test_a_scalar_prototype_binds_with_the_exact_register_kinds(tmp_path):
    view = synthetic(tmp_path, "long f(long a, int b, unsigned long c);", "double g(double x, float y);")
    first = view.decide("f")
    assert first.bound and first.args == ("i64", "i32", "u64") and first.result == "i64"
    second = view.decide("g")
    assert second.bound and second.args == ("f64", "f32") and second.result == "f64"


def test_a_pointer_to_a_scalar_binds_and_a_void_result_is_allowed(tmp_path):
    view = synthetic(tmp_path, "void *p(const char *s, void **out);", "void v(void);")
    assert view.decide("p").args == ("ptr", "ptr") and view.decide("p").result == "ptr"
    assert view.decide("v").bound and view.decide("v").args == () and view.decide("v").result == "void"


@pytest.mark.parametrize(
    "prototype, reason",
    [
        ("int f(const char *fmt, ...);", "variadic"),
        ("int f(struct widget *w);", "record parameter"),
        ("int f(void (*callback)(int));", "function pointer parameter"),
        ("int f(enum color c);", "enumerated parameter"),
        ("int f(char c);", "narrow integer parameter"),
        ("int f(unsigned short s);", "narrow integer parameter"),
        ("long double f(int n);", "long double result"),
        ("int f(long double x);", "long double parameter"),
        ("struct widget f(int n);", "record result"),
    ],
)
def test_a_prototype_that_cannot_pass_through_the_register_file_is_refused_with_its_reason(tmp_path, prototype, reason):
    view = synthetic(tmp_path, "struct widget { long w[4]; };", "enum color { RED, BLUE };", prototype)
    decision = view.decide("f")
    assert not decision.bound and decision.reason == reason


def test_an_array_parameter_decays_to_a_pointer_and_binds(tmp_path):
    decision = synthetic(tmp_path, "int f(int a[4]);").decide("f")
    assert decision.bound and decision.args == ("ptr",)


def test_more_integer_class_or_floating_point_arguments_than_registers_is_refused(tmp_path):
    view = synthetic(
        tmp_path,
        "int seven(long a, long b, long c, long d, long e, long f, long g);",
        "int six(long a, long b, long c, long d, long e, long f);",
        "int nine(double a, double b, double c, double d, double e, double f, double g, double h, double i);",
    )
    assert view.decide("seven").reason == "more than six integer-class arguments"
    assert view.decide("six").bound
    assert view.decide("nine").reason == "more than eight floating-point-class arguments"


def test_an_ordinary_function_in_a_header_that_defines_os_numbers_is_refused(tmp_path):
    view = synthetic(tmp_path, "int sleepish(int seconds);", header="unistd.h")
    decision = view.decide("sleepish")
    assert not decision.bound and decision.reason == "outside the value-only libc headers"


def test_a_function_whose_arguments_are_os_defined_numbers_is_refused_even_in_a_value_only_header(tmp_path):
    view = synthetic(tmp_path, "char *strerror(int errnum);")
    assert view.decide("strerror").reason == "OS-defined argument values"


def test_an_undeclared_name_is_refused(tmp_path):
    assert synthetic(tmp_path, "int f(void);").decide("g").reason == sdk.ABSENT


def test_the_declaring_header_is_tracked_across_the_dump_not_read_from_the_includer(tmp_path):
    (tmp_path / "unistd.h").write_text("int from_unistd(int n);\n")
    (tmp_path / "string.h").write_text('#include "unistd.h"\nint from_string(int n);\n')
    umbrella = tmp_path / "umbrella.c"
    umbrella.write_text('#include "string.h"\n')
    view = sdk.Sdk([sdk._dump(umbrella)])
    assert view.decide("from_string").bound
    assert view.decide("from_unistd").reason == "outside the value-only libc headers"


def test_the_measured_sdk_binds_pure_functions_with_the_kinds_their_prototypes_declare(measured):
    assert measured.decide("strlen").args == ("ptr",) and measured.decide("strlen").result == "u64"
    assert measured.decide("malloc").args == ("u64",) and measured.decide("malloc").result == "ptr"
    assert measured.decide("atan2").args == ("f64", "f64") and measured.decide("atan2").result == "f64"
    assert measured.decide("memchr").args == ("ptr", "i32", "u64")
    assert measured.decide("abs").args == ("i32",) and measured.decide("abs").result == "i32"
    assert measured.decide("sinf").args == ("f32",) and measured.decide("sinf").result == "f32"


@pytest.mark.parametrize(
    "name, reason",
    [
        ("sprintf", "variadic"),
        ("printf", "outside the value-only libc headers"),
        ("vsnprintf", "va_list parameter"),
        ("fseek", "record parameter"),
        ("fputs", "record parameter"),
        ("qsort", "function pointer parameter"),
        ("div", "record result"),
        ("sinl", "long double parameter"),
        ("pthread_mutex_lock", "outside the value-only libc headers"),
        ("read", "outside the value-only libc headers"),
        ("waitpid", "outside the value-only libc headers"),
        ("clock_gettime", "outside the value-only libc headers"),
        ("setlocale", "outside the value-only libc headers"),
        ("strerror", "OS-defined argument values"),
        ("__ctype_b_loc", sdk.ABSENT),
        ("__errno_location", sdk.ABSENT),
    ],
)
def test_the_measured_sdk_refuses_what_the_rule_says_with_the_reason_it_names(measured, name, reason):
    decision = measured.decide(name)
    assert not decision.bound and decision.reason == reason
