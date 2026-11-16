/*
 * Host for a lifted shipped body: models the runtime state the body reads, calls the body natively
 * and prints one "#JSON# {...}" line. Section globals, the entry symbol and its RVA come from the
 * driver as -D macros; stubs.c supplies a stub per callee that was not lifted.
 */
#include <setjmp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/sysctl.h>

#define REG_RAX 0x0
#define REG_RSP 0x20
#define MODEL_CLASS_SIZE 0x200
#define MODEL_CLASS_INIT_FLAG 0xe4
#define MODEL_CLASS_STATICS 0xb8
#define MODEL_STATICS_INSTANCE 0x8

unsigned char sec__bss[BSS_SIZE] __attribute__((aligned(32)));
unsigned char sec__got[GOT_SIZE] __attribute__((aligned(8)));
extern void ENTRY_SYM(unsigned char *reg);

static jmp_buf stub_escape;
static const char *stub_reached[8];
static size_t stub_count;

/* A stub means the body left the modelled state: record it and abandon the call. */
void stub_hit(const char *name) {
  if (stub_count < 8) stub_reached[stub_count++] = name;
  longjmp(stub_escape, 1);
}

static unsigned char stack[1 << 16] __attribute__((aligned(16)));
static unsigned char reg[8192];
static unsigned char statics[0x40];
static unsigned char klass[MODEL_CLASS_SIZE];
static unsigned char *klass_holder;

/* The three words the Linux control reads: init guard set, class initialised, static Instance null. */
static void model_state(void) {
  sec__bss[GUARD_OFFSET] = 1;
  *(uint32_t *)(klass + MODEL_CLASS_INIT_FLAG) = 1;
  *(unsigned char **)(klass + MODEL_CLASS_STATICS) = statics;
  *(uint64_t *)(statics + MODEL_STATICS_INSTANCE) = 0;
  klass_holder = klass;
  *(unsigned char ***)(sec__got + SLOT_OFFSET) = &klass_holder;
}

static int arch_translated(void) {
  int translated = 0;
  size_t length = sizeof(translated);
  if (sysctlbyname("sysctl.proc_translated", &translated, &length, NULL, 0) != 0) return -1;
  return translated;
}

int main(void) {
  model_state();
  memset(reg, 0, sizeof reg);
  *(uint64_t *)(reg + REG_RSP) = (uint64_t)(uintptr_t)(stack + sizeof stack - 64);
  int returned = 0;
  if (setjmp(stub_escape) == 0) {
    ENTRY_SYM(reg);
    returned = 1;
  }
  int32_t result = *(int32_t *)(reg + REG_RAX);
#if defined(__aarch64__)
  const char *arch = "arm64";
#else
  const char *arch = "x86_64";
#endif
  printf("#JSON# {\"arch\": \"%s\", \"proc_translated\": %d, \"rva\": \"0x%llx\", ", arch, arch_translated(),
         (unsigned long long)ENTRY_RVA);
  if (returned)
    printf("\"result\": %d, ", result);
  else
    printf("\"result\": null, ");
  printf("\"stubs_reached\": [");
  for (size_t i = 0; i < stub_count; i++) printf("%s\"%s\"", i ? ", " : "", stub_reached[i]);
  printf("], \"state\": {\"guard_set\": %s, \"class_initialised\": %s, \"instance_null\": %s}}\n",
         sec__bss[GUARD_OFFSET] != 0 ? "true" : "false",
         *(uint32_t *)(klass + MODEL_CLASS_INIT_FLAG) != 0 ? "true" : "false",
         *(uint64_t *)(*(unsigned char **)(klass + MODEL_CLASS_STATICS) + MODEL_STATICS_INSTANCE) == 0 ? "true" : "false");
  return returned ? 0 : 1;
}
