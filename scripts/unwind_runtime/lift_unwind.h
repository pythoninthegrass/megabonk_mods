#ifndef LIFT_UNWIND_H
#define LIFT_UNWIND_H
#include <stdint.h>

#define LU_REGS 17
#define LU_RA 16
#define LU_RSP 7
#define LU_PENDING_PAD 0x1F00
#define LU_PENDING_CFA 0x1F08

typedef struct {
  uint64_t pc;
  int32_t cfa_offset;
  uint8_t cfa_register;
  uint32_t saved_mask;
  int32_t saved[LU_REGS];
} lu_row;

typedef struct {
  uint64_t pc_begin;
  uint64_t pc_end;
  uint64_t lsda;
  uint64_t personality;
  uint32_t row_first;
  uint32_t row_count;
} lu_fde;

extern const lu_fde lu_fdes[];
extern const uint32_t lu_fde_count;
extern const lu_row lu_rows[];
extern unsigned char lu_lsda_bytes[];
extern const uint64_t lu_address_bias;
extern const uint64_t lu_lsda_va;
extern const uint64_t lu_lsda_size;

typedef struct {
  uint64_t lsda_offset;
  const void *cell;
  uint32_t size;
} lu_type_slot;

extern const lu_type_slot lu_type_slots[];
extern const uint32_t lu_type_slot_count;
#endif
