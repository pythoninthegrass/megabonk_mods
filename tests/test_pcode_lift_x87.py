"""80-bit x87 semantics: the width-10 float ops the pinned image contains, checked against x87 itself.

The fixtures are the ops of sub_2121f26..f34 transcribed from the cached pcode, with the varnodes the
dump uses. Ground truth is the FPU: the same inputs go through FLD/FSTP/FUCOMI in an x86-64 binary
under Rosetta, and the lifted arm64 has to answer identically row for row.
"""

import pcode_lift as pl
import pytest
import subprocess
import test_pcode_lift as hp

pytestmark = hp.requires_llvm

ST0, ST1 = "register,1100,10", "register,1110,10"
NAN_A, NAN_B, EQ, LT = "unique,5e200,1", "unique,5e300,1", "unique,5e500,1", "unique,5e700,1"
I80_TMP, STORE_SRC = "unique,e5100,10", "unique,db00,10"
DATA, PTR = "const,1b1,4", "register,18,8"
def ret(addr):
    return hp.insn(addr, 1, hp.op("RETURN", None, "register,288,8"))
FLOAT_AT, INT_AT = "ram,1000,4", "ram,1008,4"
SECTIONS = [{"name": "pdata", "va": 0x1000, "size": 64, "exec": False}]

# The same tables drive both sides, so the two programs are asked exactly the same questions.
TABLES = r"""
static const unsigned int FLOATS[] = {
    0x00000000u, 0x80000000u, 0x3f800000u, 0xbf800000u, 0x3f000000u, 0xbf000000u, 0x00800000u, 0x00000001u,
    0x007fffffu, 0x7f7fffffu, 0xff7fffffu, 0x7f800000u, 0xff800000u, 0x7fc00000u, 0x7f800001u, 0x7f900000u,
    0xffc00000u, 0x7fffffffu, 0x40490fdu, 0xc1200000u, 0x38800000u, 0x00400000u, 0x33800000u, 0x00000003u,
};
static const int INTS[] = {
    0, 1, -1, 2, -2, 3, -3, 1 << 23, (1 << 23) + 1, 1 << 24, (1 << 24) + 1, 1 << 25, -16777217, 123456789,
    -123456789, 2147483647, -2147483647 - 1, 1 << 30, 1000000, -1000000,
};
/* Exponent class x integer bit x empty-or-not fraction, both signs: every encoding x87 can meet. */
static const unsigned char PATTERNS[][10] = {
    {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00},
    {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80},
    {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0xff, 0x3f},
    {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0xff, 0xbf},
    {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0xff, 0x7f},
    {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0xff, 0xff},
    {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0x7f},
    {0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0x7f},
    {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x40, 0x00, 0x00},
    {0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00},
    {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0xff, 0x3e},
    {0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x3f},
    {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x40},
    {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0xc0},
};
/* Fake NaN, SNaN, the two pseudo-denormals and the exponent-without-integer-bit pair. */
#define UNNORMAL "6 7 8 9 12 13"
#define NFLOATS (int) (sizeof FLOATS / sizeof *FLOATS)
#define NINTS (int) (sizeof INTS / sizeof *INTS)
#define NPATTERNS (int) (sizeof PATTERNS / sizeof *PATTERNS)
"""

ORACLE = (
    r"""
#include <stdint.h>
#include <stdio.h>
#include <string.h>
"""
    + TABLES
    + r"""
static void hex10(const unsigned char *b) {
  for (int i = 9; i >= 0; i--) printf("%02x", b[i]);
}

/* The loads the guest itself issues, so the widening is the FPU's own and not the compiler's. */
static void flds80(float f, unsigned char *b) {
  __asm__ volatile("finit\n\tflds %1\n\tfstpt %0" : "=m"(*b), "+m"(f) : : "st");
}

static void fild80(int v, unsigned char *b) {
  __asm__ volatile("finit\n\tfildl %1\n\tfstpt %0" : "=m"(*b), "+m"(v) : : "st");
}

static int unnormal(int index) {
  const char *set = UNNORMAL;
  char head[8];
  snprintf(head, sizeof head, "%d", index);
  for (const char *p = set; *p; p += strcspn(p, " ") + 1) {
    if (!strncmp(p, head, strlen(head)) && (p[strlen(head)] == ' ' || !p[strlen(head)])) return 1;
  }
  return 0;
}

int main(int argc, char **argv) {
  int only_unnormal = argc > 1 && !strcmp(argv[1], "unnormal");
  unsigned char b[16];
  for (int i = 0; i < NFLOATS; i++) {
    float f;
    memcpy(&f, &FLOATS[i], 4);
    flds80(f, b);
    printf("f2ld %08x ", FLOATS[i]);
    hex10(b);
    putchar('\n');
  }
  for (int i = 0; i < NINTS; i++) {
    fild80(INTS[i], b);
    printf("i2ld %d ", INTS[i]);
    hex10(b);
    putchar('\n');
  }
  for (int i = 0; i < NPATTERNS; i++) {
    for (int j = 0; j < NPATTERNS; j++) {
      if (only_unnormal && !(unnormal(i) || unnormal(j))) continue;
      long double x, y;
      memcpy(&x, PATTERNS[i], 10);
      memcpy(&y, PATTERNS[j], 10);
      printf("cmp %d %d %d %d %d %d %d\n", i, j, x != x, y != y, x == y, x < y, y < x);
    }
  }
  return 0;
}
"""
)

DRIVER = (
    r"""
#include <stdint.h>
#include <stdio.h>
#include <string.h>
"""
    + TABLES
    + r"""
static unsigned char reg[8192];
unsigned char sec_pdata[64];
extern void sub_2121f2c(unsigned char *reg);
extern void sub_2121f26(unsigned char *reg);
extern void sub_2121f34(unsigned char *reg);

#define PEEK(OFFSET, TYPE)                            \
  ({                                                  \
    TYPE v_;                                          \
    memcpy(&v_, reg + (OFFSET), sizeof v_);           \
    v_;                                               \
  })
#define POKE(OFFSET, VALUE)                             \
  do {                                                  \
    __typeof__(VALUE) v__ = (VALUE);                    \
    memcpy(reg + (OFFSET), &v__, sizeof v__);           \
  } while (0)

static void hex10(const unsigned char *b) {
  for (int i = 9; i >= 0; i--) printf("%02x", b[i]);
}

static void widen_float(unsigned int bits) {
  memcpy(&sec_pdata[0], &bits, 4);
  memset(reg, 0, 8192);
  POKE(0x18, (uintptr_t) &sec_pdata[16]);
  sub_2121f2c(reg);
}

static void widen_int(int value) {
  memcpy(&sec_pdata[8], &value, 4);
  memset(reg, 0, 8192);
  POKE(0x18, (uintptr_t) &sec_pdata[16]);
  sub_2121f26(reg);
}

static void compare(const unsigned char *a, const unsigned char *b, unsigned flags[4]) {
  memset(reg, 0, 8192);
  memcpy(reg + 0x1100, a, 10);
  memcpy(reg + 0x1110, b, 10);
  sub_2121f34(reg);
  flags[0] = PEEK(0x200, uint8_t);
  flags[1] = PEEK(0x201, uint8_t);
  flags[2] = PEEK(0x202, uint8_t);
  flags[3] = PEEK(0x203, uint8_t);
}

static int unnormal(int index) {
  const char *set = UNNORMAL;
  char head[8];
  snprintf(head, sizeof head, "%d", index);
  for (const char *p = set; *p; p += strcspn(p, " ") + 1) {
    if (!strncmp(p, head, strlen(head)) && (p[strlen(head)] == ' ' || !p[strlen(head)])) return 1;
  }
  return 0;
}

int main(int argc, char **argv) {
  int only_unnormal = argc > 1 && !strcmp(argv[1], "unnormal");
  for (int i = 0; i < NFLOATS; i++) {
    widen_float(FLOATS[i]);
    printf("f2ld %08x ", FLOATS[i]);
    hex10(&sec_pdata[16]);
    putchar('\n');
  }
  for (int i = 0; i < NINTS; i++) {
    widen_int(INTS[i]);
    printf("i2ld %d ", INTS[i]);
    hex10(&sec_pdata[16]);
    putchar('\n');
  }
  for (int i = 0; i < NPATTERNS; i++) {
    for (int j = 0; j < NPATTERNS; j++) {
      if (only_unnormal && !(unnormal(i) || unnormal(j))) continue;
      unsigned forward[4], backward[4];
      compare(PATTERNS[i], PATTERNS[j], forward);
      compare(PATTERNS[j], PATTERNS[i], backward);
      printf("cmp %d %d %u %u %u %u %u\n", i, j, forward[0], forward[1], forward[2], forward[3], backward[3]);
    }
  }
  return 0;
}
"""
)

CONST_DRIVER = r"""
#include <stdio.h>
#include <string.h>
static unsigned char reg[8192];
extern void sub_2121f26(unsigned char *reg);
int main(void) {
  static unsigned char out[16];
  memset(reg, 0xa5, sizeof reg);
  unsigned long long address = (unsigned long long)(unsigned char *) out;
  memcpy(reg + 0x18, &address, 8);
  sub_2121f26(reg);
  for (int i = 9; i >= 0; i--) printf("%02x", out[i]);
  putchar('\n');
  return 0;
}
"""


def f2ld_body():
    """sub_2121f2c's widening, written out the way the dump's own STORE does it."""
    return hp.body(
        hp.insn(
            0x2121F2C,
            6,
            hp.op("FLOAT2FLOAT", ST0, FLOAT_AT),
            hp.op("COPY", STORE_SRC, ST0),
            hp.op("STORE", None, DATA, PTR, STORE_SRC),
        ),
        ret(0x2121F32),
        start=0x2121F2C,
    )


def i2ld_body(source=INT_AT):
    """sub_2121f26's INT2FLOAT: the dump's own constant, or a ram slot when the test drives it."""
    return hp.body(
        hp.insn(
            0x2121F26,
            2,
            hp.op("INT2FLOAT", I80_TMP, source),
            hp.op("COPY", STORE_SRC, I80_TMP),
            hp.op("STORE", None, DATA, PTR, STORE_SRC),
        ),
        ret(0x2121F28),
        start=0x2121F26,
    )


def cmp_body():
    """sub_2121f34's four predicates over the two 80-bit stack slots, with the answers copied out."""
    return hp.body(
        hp.insn(
            0x2121F34,
            2,
            hp.op("FLOAT_NAN", NAN_A, ST0),
            hp.op("FLOAT_NAN", NAN_B, ST1),
            hp.op("FLOAT_EQUAL", EQ, ST0, ST1),
            hp.op("FLOAT_LESS", LT, ST0, ST1),
            hp.op("COPY", "register,200,1", NAN_A),
            hp.op("COPY", "register,201,1", NAN_B),
            hp.op("COPY", "register,202,1", EQ),
            hp.op("COPY", "register,203,1", LT),
        ),
        ret(0x2121F36),
        start=0x2121F34,
    )


def differential_bodies():
    return [pl.lift_body(fn, SECTIONS) for fn in (f2ld_body(), i2ld_body(), cmp_body())]


def run_builtin(tmp_path, name, source, arch, argv=()):
    path, exe = tmp_path / f"{name}.c", tmp_path / name
    path.write_text(source)
    proc = subprocess.run(
        [hp.LLVM / "clang", "-O0", "-arch", arch, "-o", str(exe), str(path)], text=True, capture_output=True
    )
    assert proc.returncode == 0, proc.stderr
    prefix = [] if arch == "arm64" else ["arch", "-x86_64"]
    result = subprocess.run([*prefix, str(exe), *argv], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    return result.stdout


def build_lifted(tmp_path, bodies, name, source):
    ir_path, source_path, exe = tmp_path / f"{name}.ll", tmp_path / f"{name}.c", tmp_path / name
    ir_path.write_text(pl.module_for(bodies, {"pdata": None}))
    checked = hp.verify(ir_path.read_text())
    assert checked.returncode == 0, checked.stderr
    source_path.write_text(source)
    proc = subprocess.run(
        [hp.LLVM / "clang", "-O0", "-arch", "arm64", str(ir_path), str(source_path), "-o", str(exe)],
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr
    return exe


@pytest.fixture(scope="module")
def oracle(tmp_path_factory):
    """x87's own answers, computed once by an x86-64 binary."""
    workdir = tmp_path_factory.mktemp("x87-oracle")
    run_builtin(workdir, "oracle", ORACLE, "x86_64")
    return lambda *argv: run_builtin(workdir, "oracle", ORACLE, "x86_64", argv)


@pytest.fixture(scope="module")
def lifted(tmp_path_factory):
    """The same questions, answered by the lifted bodies running as arm64."""
    workdir = tmp_path_factory.mktemp("x87-lifted")
    exe = build_lifted(workdir, differential_bodies(), "lifted", DRIVER)
    return lambda *argv: subprocess.run([str(exe), *argv], text=True, capture_output=True).stdout


def rows(output, kind):
    return {tuple(line.split()[1:]) for line in output.splitlines() if line.startswith(kind)}


def test_every_x87_op_in_the_dump_lifts_without_a_hole():
    for lifted_body in differential_bodies():
        assert lifted_body.holes == []
        assert "f80" not in lifted_body.ir and "fp80" not in lifted_body.ir
    assert pl.lift_body(i2ld_body()).holes == []


def test_the_widened_floats_are_the_encodings_flds_pushes(lifted, oracle):
    assert rows(lifted(), "f2ld") == rows(oracle(), "f2ld")


def test_the_widened_integers_are_the_encodings_fild_pushes(lifted, oracle):
    assert rows(lifted(), "i2ld") == rows(oracle(), "i2ld")


def test_the_predicates_answer_what_x87_answers(lifted, oracle):
    assert rows(lifted(), "cmp") == rows(oracle(), "cmp")


def test_an_unnormal_encoding_is_neither_ordered_nor_equal(lifted, oracle):
    """The fake NaN, the pseudo-denormals and a set exponent with a clear integer bit: x87 refuses to order them."""
    assert rows(lifted("unnormal"), "cmp") == rows(oracle("unnormal"), "cmp")
    assert len(rows(oracle("unnormal"), "cmp")) > 40


def test_the_dump_s_constant_conversion_stores_the_zero_encoding(tmp_path):
    exe = build_lifted(tmp_path, [pl.lift_body(i2ld_body("const,0,4"), SECTIONS)], "const", CONST_DRIVER)
    assert subprocess.run([str(exe)], text=True, capture_output=True).stdout.strip() == "00" * 10


def test_eighty_bit_arithmetic_stays_a_hole():
    """No FLOAT_ADD at width 10 exists in the image, so there is no rounding mode to invent."""
    fn = hp.body(hp.insn(0x1000, 2, hp.op("FLOAT_ADD", ST0, ST0, ST1)), ret(0x1002))
    assert pl.lift_body(fn).holes == ["FLOAT_ADD:float width 10"]


def test_narrowing_to_single_precision_stays_a_hole():
    fn = hp.body(hp.insn(0x1000, 2, hp.op("FLOAT2FLOAT", "register,20,4", ST0)), ret(0x1002))
    assert pl.lift_body(fn).holes == ["FLOAT2FLOAT:float width 10"]
