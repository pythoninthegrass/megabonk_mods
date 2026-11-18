#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef uint32_t (*thunk)(void *, const void *, uint64_t);
typedef uint8_t (*switch_fn)(uint32_t);

#ifdef SHIPPED_REFERENCE
#include <dlfcn.h>
#include <link.h>

static uintptr_t image_base(const char *path) {
    struct link_map *map;
    void *so = dlopen(path, RTLD_NOW | RTLD_LOCAL);
    if (!so) {
        fprintf(stderr, "%s\n", dlerror());
        return 0;
    }
    return dlinfo(so, RTLD_DI_LINKMAP, &map) == 0 ? map->l_addr : 0;
}
#else
uint32_t lifted_thunk(void *, const void *, uint64_t);
uint8_t lifted_switch(uint32_t);
#endif

int main(int argc, char **argv) {
    thunk invoke;
    switch_fn choose;
    uintptr_t target = 0x1d41db0;
#ifdef SHIPPED_REFERENCE
    if (argc != 2) return 2;
    uintptr_t base = image_base(argv[1]);
    if (!base) return 3;
    invoke = (thunk)(base + 0x1d35190);
    choose = (switch_fn)(base + 0x4bd70f0);
    target += base;
#else
    if (argc != 2) return 2;
    invoke = lifted_thunk;
    choose = lifted_switch;
    if (strcmp(argv[1], "unknown") == 0) target = 0;
    if (strcmp(argv[1], "interior") == 0) target++;
#endif
    unsigned char slot[24] = {0}, object[24] = {0};
    memcpy(slot + 16, &target, sizeof target);
    uint32_t values[] = {0, 42, 0x80000001};
    for (unsigned i = 0; i < sizeof values / sizeof *values; ++i) {
        memcpy(object + 20, &values[i], sizeof values[i]);
        printf("%u\n", invoke(slot, object, 0));
    }
    for (uint32_t i = 0; i <= 83; ++i) printf("%u", choose(i));
    printf("\n");
}
