#include <dlfcn.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef void (*guest_hook)(unsigned char *);

static int invoke(guest_hook hook) {
    _Alignas(16) unsigned char reg[8192] = {0};
    _Alignas(16) unsigned char stack[65536] = {0};
    uintptr_t rsp = (uintptr_t)(stack + sizeof stack - 8);
    uintptr_t returned;
    memcpy(reg + 32, &rsp, sizeof rsp);
    hook(reg);
    memcpy(&returned, reg + 32, sizeof returned);
    return returned == rsp + 8;
}

static void report(const char *event, int index, uint64_t address) {
    printf("\n#STARTUP#{\"event\":\"%s\",\"index\":%d,\"address\":%" PRIu64 "}\n", event, index, address);
    fflush(stdout);
}

int main(int argc, char **argv) {
    if (argc < 2) return 2;
    void *image = dlopen(argv[1], RTLD_LOCAL | RTLD_NOW);
    if (!image) {
        fprintf(stderr, "dlopen: %s\n", dlerror());
        return 2;
    }
    for (int i = 2; i < argc; i++) {
        char symbol[32];
        uint64_t address = strtoull(argv[i], NULL, 16);
        snprintf(symbol, sizeof symbol, "sub_%" PRIx64, address);
        guest_hook hook = (guest_hook)dlsym(image, symbol);
        if (!hook) {
            fprintf(stderr, "missing hook: %s\n", symbol);
            return 2;
        }
        report("enter", i - 2, address);
        if (!invoke(hook)) {
            fprintf(stderr, "guest stack imbalance: %s\n", symbol);
            return 2;
        }
        report("return", i - 2, address);
    }
    return 0;
}
