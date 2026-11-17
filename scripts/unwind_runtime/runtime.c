/* Guest-stack unwinder: the _Unwind_* layer for lifted x86-64 code, run natively on arm64. */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "lift_unwind.h"

extern void lift_dispatch(uint64_t target, unsigned char *reg);

enum { UA_SEARCH = 1, UA_CLEANUP = 2, UA_HANDLER_FRAME = 4 };
enum { URC_FATAL_PHASE2 = 2, URC_FATAL_PHASE1 = 3, URC_END_OF_STACK = 5, URC_HANDLER_FOUND = 6, URC_INSTALL_CONTEXT = 7, URC_CONTINUE = 8 };

typedef struct {
  uint64_t klass;
  uint64_t cleanup;
  uint64_t private_1;
  uint64_t private_2;
} lu_exception;

typedef struct {
  uint64_t regs[LU_REGS];
  uint64_t ip;
  uint64_t cfa;
  const lu_fde *fde;
} lu_ctx;

/* Register-file offset of each DWARF register number the unwinder restores. */
static const int reg_offset[16] = {0x0, 0x10, 0x8, 0x18, 0x30, 0x38, 0x28, 0x20, 0x80, 0x88, 0x90, 0x98, 0xA0, 0xA8, 0xB0, 0xB8};

static const lu_fde *find_fde(uint64_t pc) {
  uint32_t lo = 0, hi = lu_fde_count;
  while (lo < hi) {
    uint32_t mid = lo + (hi - lo) / 2;
    if (pc < lu_fdes[mid].pc_begin) hi = mid;
    else if (pc >= lu_fdes[mid].pc_end) lo = mid + 1;
    else return &lu_fdes[mid];
  }
  return NULL;
}

static const lu_row *row_at(const lu_fde *fde, uint64_t pc) {
  const lu_row *chosen = &lu_rows[fde->row_first];
  for (uint32_t i = 0; i < fde->row_count; i++)
    if (lu_rows[fde->row_first + i].pc <= pc) chosen = &lu_rows[fde->row_first + i];
  return chosen;
}

static uint64_t read_u64(uint64_t address) {
  uint64_t value;
  memcpy(&value, (const void *)(uintptr_t)address, 8);
  return value;
}

/* Fills the frame description for ctx->ip; false when no lifted frame owns the return address. */
static int frame_for(lu_ctx *ctx) {
  ctx->fde = find_fde(ctx->ip - 1);
  if (!ctx->fde) return 0;
  const lu_row *row = row_at(ctx->fde, ctx->ip - 1);
  ctx->cfa = ctx->regs[row->cfa_register] + (int64_t)row->cfa_offset;
  return 1;
}

static void unwind_to_caller(const lu_ctx *ctx, lu_ctx *caller) {
  const lu_row *row = row_at(ctx->fde, ctx->ip - 1);
  *caller = *ctx;
  for (int reg = 0; reg < LU_REGS; reg++)
    if (row->saved_mask & (1u << reg)) caller->regs[reg] = read_u64(ctx->cfa + (int64_t)row->saved[reg]);
  if (!(row->saved_mask & (1u << LU_RA))) abort();
  caller->regs[LU_RSP] = ctx->cfa;
  caller->ip = caller->regs[LU_RA] - lu_address_bias;
}

static int call_personality(const lu_ctx *ctx, int actions, lu_exception *exc) {
  _Alignas(16) unsigned char reg[8192] = {0};
  _Alignas(16) unsigned char stack[16384] = {0};
  uintptr_t rsp = (uintptr_t)(stack + sizeof stack - 8);
  uint64_t args[5] = {1, (uint64_t)actions, exc->klass, (uint64_t)(uintptr_t)exc, (uint64_t)(uintptr_t)ctx};
  const int order[5] = {0x38, 0x30, 0x10, 0x8, 0x80};
  memcpy(reg + 0x20, &rsp, 8);
  for (int i = 0; i < 5; i++) memcpy(reg + order[i], &args[i], 8);
  lift_dispatch(ctx->fde->personality, reg);
  uintptr_t returned;
  memcpy(&returned, reg + 0x20, 8);
  if (returned != rsp + 8) abort();
  int32_t result;
  memcpy(&result, reg, 4);
  return result;
}

static void start_context(const unsigned char *reg, lu_ctx *ctx) {
  memset(ctx, 0, sizeof *ctx);
  for (int i = 0; i < 16; i++) memcpy(&ctx->regs[i], reg + reg_offset[i], 8);
  uint64_t rsp = ctx->regs[LU_RSP];
  ctx->ip = read_u64(rsp) - lu_address_bias;
  ctx->regs[LU_RSP] = rsp + 8;
}

static void install(unsigned char *reg, const lu_ctx *ctx) {
  for (int i = 0; i < 16; i++) memcpy(reg + reg_offset[i], &ctx->regs[i], 8);
  memcpy(reg + LU_PENDING_PAD, &ctx->ip, 8);
  memcpy(reg + LU_PENDING_CFA, &ctx->cfa, 8);
}

static int phase1(const lu_ctx *start, lu_exception *exc) {
  lu_ctx ctx = *start, next;
  for (;;) {
    if (!frame_for(&ctx)) return URC_END_OF_STACK;
    if (ctx.fde->personality) {
      int rc = call_personality(&ctx, UA_SEARCH, exc);
      if (rc == URC_HANDLER_FOUND) {
        exc->private_2 = ctx.cfa;
        return URC_HANDLER_FOUND;
      }
      if (rc != URC_CONTINUE) return URC_FATAL_PHASE1;
    }
    unwind_to_caller(&ctx, &next);
    ctx = next;
  }
}

static int phase2(unsigned char *reg, const lu_ctx *start, lu_exception *exc) {
  lu_ctx ctx = *start, next;
  for (;;) {
    if (!frame_for(&ctx)) return URC_FATAL_PHASE2;
    if (ctx.fde->personality) {
      int actions = UA_CLEANUP | (ctx.cfa == exc->private_2 ? UA_HANDLER_FRAME : 0);
      int rc = call_personality(&ctx, actions, exc);
      if (rc == URC_INSTALL_CONTEXT) {
        install(reg, &ctx);
        return URC_INSTALL_CONTEXT;
      }
      if (rc != URC_CONTINUE) return URC_FATAL_PHASE2;
    }
    unwind_to_caller(&ctx, &next);
    ctx = next;
  }
}

static void return_value(unsigned char *reg, int value, int installed) {
  if (installed) return;
  uint64_t result = (uint32_t)value;
  memcpy(reg, &result, 8);
  uint64_t rsp;
  memcpy(&rsp, reg + 0x20, 8);
  rsp += 8;
  memcpy(reg + 0x20, &rsp, 8);
}

/* Raw imports: they run on the guest register file and own its RSP, because landing rewrites it. */
void lu_raise_exception(unsigned char *reg) {
  lu_exception *exc;
  uint64_t arg;
  memcpy(&arg, reg + 0x38, 8);
  exc = (lu_exception *)(uintptr_t)arg;
  lu_ctx start;
  start_context(reg, &start);
  int rc = phase1(&start, exc);
  if (rc != URC_HANDLER_FOUND) return_value(reg, rc, 0);
  else {
    rc = phase2(reg, &start, exc);
    return_value(reg, rc, rc == URC_INSTALL_CONTEXT);
  }
}

void lu_resume(unsigned char *reg) {
  uint64_t arg;
  memcpy(&arg, reg + 0x38, 8);
  lu_exception *exc = (lu_exception *)(uintptr_t)arg;
  lu_ctx start;
  start_context(reg, &start);
  int rc = phase2(reg, &start, exc);
  if (rc != URC_INSTALL_CONTEXT) abort();
  return_value(reg, rc, 1);
}

/* Points each type-table entry of the LSDA copy at the cell that holds its relocated typeinfo pointer. */
__attribute__((constructor)) static void lu_patch_type_slots(void) {
  for (uint32_t i = 0; i < lu_type_slot_count; i++) {
    unsigned char *entry = lu_lsda_bytes + lu_type_slots[i].lsda_offset;
    int64_t distance = (int64_t)((const unsigned char *)lu_type_slots[i].cell - entry);
    if (lu_type_slots[i].size == 4) {
      if (distance != (int32_t)distance) abort();
      int32_t narrow = (int32_t)distance;
      memcpy(entry, &narrow, 4);
    } else {
      memcpy(entry, &distance, 8);
    }
  }
}

/* Typed imports used by the lifted personality routine. */
const void *lu_get_language_specific_data(lu_ctx *ctx) {
  if (!ctx->fde->lsda) return NULL;
  return lu_lsda_bytes + (ctx->fde->lsda - lu_lsda_va);
}
uint64_t lu_get_region_start(lu_ctx *ctx) { return ctx->fde->pc_begin; }
uint64_t lu_get_ip_info(lu_ctx *ctx, int *ip_before_insn) {
  *ip_before_insn = 0;
  return ctx->ip;
}
void lu_set_gr(lu_ctx *ctx, int index, uint64_t value) { ctx->regs[index] = value; }
void lu_set_ip(lu_ctx *ctx, uint64_t value) { ctx->ip = value; }
uint64_t lu_get_cfa(lu_ctx *ctx) { return ctx->cfa; }

/* A rethrow of an exception that is not being force-unwound is a fresh two-phase raise. */
void lu_resume_or_rethrow(unsigned char *reg) { lu_raise_exception(reg); }
