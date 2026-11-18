#include <stdint.h>
#include <stdio.h>

extern void sub_90000000(unsigned char *reg);
uint64_t lifted_handover(void *, uint64_t, uint64_t);

/* The guest target of the handover: it sees the register file after the two moves, so the value
   printed here is what the jump carried, and the return value is what the callee leaves in rax. */
uint64_t handover_callee(uint64_t first) {
    printf("callee %#llx\n", (unsigned long long)first);
    return first * 3 + 1;
}

int main(void) {
    uint64_t result = lifted_handover((void *)sub_90000000, 0x1122334455667788ULL, 0x99aabbccULL);
    printf("result %#llx\n", (unsigned long long)result);
    return 0;
}
