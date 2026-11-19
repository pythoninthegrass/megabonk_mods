"""Executes the CALLOTHER host helpers on arm64: CPUID's leaf table, RDRAND's result flag, and the trap."""

import lift_abi as abi
import pcode_lift as pl
import pytest
import test_lift_unwind_exec as base
import test_pcode_lift as hp

pytestmark = base.requires_arm64

CPUID_BODY = "sub_2153d33"
RDRAND_BODY = "sub_2153ce9"
TRAP_BODY = "sub_208bb68"

DRIVER_HEAD = """
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>
static unsigned char reg[8192];
#define PEEK(OFFSET, TYPE) ({ TYPE v; memcpy(&v, reg + (OFFSET), sizeof v); v; })
#define POKE(OFFSET, VALUE) do { typeof(VALUE) v_ = (VALUE); memcpy(reg + (OFFSET), &v_, sizeof v_); } while (0)
"""


def link(tmp_path, name, bodies, driver):
    ir, shim, source = tmp_path / f"{name}.ll", tmp_path / f"{name}-shim.c", tmp_path / f"{name}.c"
    ir.write_text(pl.module_for(bodies, {}))
    shim.write_text(abi.generate([], []))
    source.write_text(driver)
    exe = tmp_path / name
    base.run([base.LLVM / "opt", "-passes=verify", "-disable-output", ir])
    base.run([base.LLVM / "clang", "-arch", "arm64", "-O2", ir, shim, source, "-o", exe])
    return exe


def lifted(function):
    return [pl.lift_body(function)]


def fields(exe):
    """The driver's printf output as a mapping."""
    words = base.execute(exe, "run").stdout.split()
    return dict(zip(words[::2], words[1::2]))


def cpuid_probe_body():
    """The dump's helper call and the four loads it feeds, minus the switch arms that guard it in place."""
    guarded = hp.cpuid_body()["insns"][0]["ops"]
    reachable = [op for op in guarded if op["op"] not in ("CBRANCH", "BRANCH")]
    return hp.body(
        hp.insn(0x2153D33, 4, *reachable),
        hp.insn(0x2153D37, 1, hp.op("RETURN", None, "register,288,8")),
        start=0x2153D33,
    )


def cpuid_driver(table=""):
    return (
        DRIVER_HEAD
        + f"""
extern void {CPUID_BODY}(unsigned char *reg);
{table}
int main(void) {{
  memset(reg, 0xa5, sizeof reg);
  POKE(0x00, (uint32_t)0xb);
  {CPUID_BODY}(reg);
  printf("eax %#llx ebx %#llx ecx %#llx edx %#llx\\n", PEEK(0x00, uint64_t), PEEK(0x18, uint64_t),
         PEEK(0x08, uint64_t), PEEK(0x10, uint64_t));
  return 0;
}}
"""
    )


CPUID_TABLE = """
typedef struct { uint32_t eax, ebx, ecx, edx; } lift_cpuid_leaf;
int lift_cpuid_leaf_at(uint64_t leaf, lift_cpuid_leaf *out) {
  if (leaf != 0xb) return 0;
  out->eax = 0x11111111u;
  out->ebx = 0x22222222u;
  out->ecx = 0x33333333u;
  out->edx = 0x44444444u;
  return 1;
}
"""

CPUID_ORDER = "eax 0x11111111 ebx 0x22222222 ecx 0x33333333 edx 0x44444444"

CPUID_TABLE_REFUSES_BUT_SCRIBBLES = """
typedef struct { uint32_t eax, ebx, ecx, edx; } lift_cpuid_leaf;
int lift_cpuid_leaf_at(uint64_t leaf, lift_cpuid_leaf *out) {
  (void)leaf;
  out->eax = out->ebx = out->ecx = out->edx = 0xdeadbeefu;
  return 0;
}
"""


def test_a_measured_leaf_reaches_the_four_registers_in_the_order_the_model_reads_them(tmp_path):
    """EAX, EBX, RDX, RCX: the order the dump's loads step through the helper's result block."""
    exe = link(tmp_path, "cpuid-table", lifted(cpuid_probe_body()), cpuid_driver(CPUID_TABLE))
    assert base.execute(exe, "run").stdout.strip() == CPUID_ORDER


def test_a_leaf_no_table_answers_reports_no_features_at_all(tmp_path):
    """Fail-closed: a lift that cannot answer a leaf claims nothing, rather than arm64 host features."""
    exe = link(tmp_path, "cpuid-default", lifted(cpuid_probe_body()), cpuid_driver())
    assert base.execute(exe, "run").stdout.strip() == "eax 0 ebx 0 ecx 0 edx 0"


def test_a_leaf_the_table_declines_to_answer_is_zeros_even_if_it_wrote_something(tmp_path):
    """Only a table that says it answered gets believed; a declined leaf cannot leak host features."""
    exe = link(tmp_path, "cpuid-refused", lifted(cpuid_probe_body()), cpuid_driver(CPUID_TABLE_REFUSES_BUT_SCRIBBLES))
    assert base.execute(exe, "run").stdout.strip() == "eax 0 ebx 0 ecx 0 edx 0"


def rdrand_driver(helper=""):
    """Two draws from one body, so a helper that never writes the buffer shows up as the poison we left there."""
    return (
        DRIVER_HEAD
        + f"""
extern void {RDRAND_BODY}(unsigned char *reg);
{helper}
static unsigned long long draw(void) {{
  POKE(0x00, (uint32_t)0xa5a5a5a5u);
  POKE(0x200, (uint8_t)0xa5u);
  {RDRAND_BODY}(reg);
  return ((unsigned long long)PEEK(0x00, uint32_t) << 8) | PEEK(0x200, uint8_t);
}}
int main(void) {{
  memset(reg, 0xa5, sizeof reg);
  unsigned long long first = draw(), second = draw();
  printf("first %#llx/%u second %#llx/%u\\n", first >> 8, (unsigned)(first & 0xff), second >> 8, (unsigned)(second & 0xff));
  return 0;
}}
"""
    )


RDRAND_ANSWER = 0x1122334455667788

RDRAND_KNOWN_HELPER = f"""
_Bool lift_rdrand(uint64_t *out) {{ *out = UINT64_C({RDRAND_ANSWER}); return 1; }}
"""

RDRAND_EMPTY_HELPER = """
_Bool lift_rdrand(uint64_t *out) { (void)out; return 0; }
"""


def test_rdrand_writes_the_value_the_helper_produced_and_sets_the_flag(tmp_path):
    """The destination is the 32-bit register the dump writes, so only the low half of the host's word lands."""
    exe = link(tmp_path, "rdrand-known", lifted(hp.rdrand_body()), rdrand_driver(RDRAND_KNOWN_HELPER))
    assert base.execute(exe, "run").stdout.strip() == (
        f"first {RDRAND_ANSWER & 0xFFFFFFFF:#x}/1 second {RDRAND_ANSWER & 0xFFFFFFFF:#x}/1"
    )


def test_the_default_rdrand_helper_gives_bits_and_claims_success(tmp_path):
    """No RDRAND on arm64: the shim supplies the bits itself, and never leaves the flag falsely set."""
    exe = link(tmp_path, "rdrand-default", lifted(hp.rdrand_body()), rdrand_driver())
    _, first, _, second = base.execute(exe, "run").stdout.split()
    assert first.endswith("/1") and second.endswith("/1")
    assert int(first.split("/")[0], 16) != 0xA5A5A5A5
    assert first != second


def test_rdrand_reports_the_flag_as_the_helper_answered(tmp_path):
    """A host that cannot supply a random number must not leave the success flag set."""
    exe = link(tmp_path, "rdrand-empty", lifted(hp.rdrand_body()), rdrand_driver(RDRAND_EMPTY_HELPER))
    _, first, _, second = base.execute(exe, "run").stdout.split()
    assert first.endswith("/0") and second.endswith("/0")


TRAP_DRIVER = (
    DRIVER_HEAD
    + f"""
extern void {TRAP_BODY}(unsigned char *reg);
int main(void) {{
  memset(reg, 0, sizeof reg);
  pid_t child = fork();
  if (child == 0) {{
    {TRAP_BODY}(reg);
    _exit(0);
  }}
  int status = 0;
  waitpid(child, &status, 0);
  printf("signal %d\\n", WIFSIGNALED(status) ? WTERMSIG(status) : -1);
  return 0;
}}
"""
)


def test_an_undefined_opcode_traps_the_host(tmp_path):
    """The guest's ud2 becomes a brk on arm64: the process dies there instead of running the code after it."""
    exe = link(tmp_path, "trap", lifted(hp.invalid_body()), TRAP_DRIVER)
    assert base.execute(exe, "run").stdout.strip() == "signal 5"
