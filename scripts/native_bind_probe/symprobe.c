/* Reports which of the named symbols this macOS loader can actually resolve.
 *
 * Usage:
 *   symprobe [--lib <path>]... <sym>...
 *     ->  "<sym>\t0x<addr>\t<source>" per line, addr 0x0 when absent.
 *
 * Every RTLD_DEFAULT lookup runs before any --lib image is opened, so a "default"
 * source means the name was reachable without extra libraries and a library path
 * source means a recipe that needs that dlopen. Reordering those phases is the whole
 * point: dlopen puts symbols in the global scope, which would otherwise make a
 * "just dlopen it" claim impossible to distinguish from a free one.
 *
 * dyld's dlsym tolerates the Mach-O underscore on the way in, so both spellings are
 * tried and the one that worked is reported as the source.
 */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_LIBS 16
#define MAX_NAMES 4096

int main(int argc, char** argv) {
    void* libs[MAX_LIBS];
    char* lib_names[MAX_LIBS];
    int nlibs = 0;
    int i = 1;
    while (i < argc && strcmp(argv[i], "--lib") == 0) {
        if (i + 1 >= argc || nlibs >= MAX_LIBS) break;
        lib_names[nlibs] = argv[i + 1];
        nlibs++;
        i += 2;
    }

    static char addrs[MAX_NAMES][32];
    static char sources[MAX_NAMES][256];
    int nnames = argc - i;
    if (nnames > MAX_NAMES) nnames = MAX_NAMES;

    /* Phase 1: the default search scope, with no extra image loaded. */
    char scratch[1024];
    for (int n = 0; n < nnames; ++n) {
        const char* name = argv[i + n];
        void* addr = dlsym(RTLD_DEFAULT, name);
        const char* source = addr ? "default" : NULL;
        if (!addr) {
            snprintf(scratch, sizeof(scratch), "_%s", name);
            addr = dlsym(RTLD_DEFAULT, scratch);
            if (addr) source = "underscore";
        }
        snprintf(addrs[n], sizeof(addrs[n]), "%p", addr);
        snprintf(sources[n], sizeof(sources[n]), "%s", addr ? source : "none");
    }

    /* Phase 2: open the recipe images and retry only what is still missing. */
    for (int l = 0; l < nlibs; ++l) {
        libs[l] = dlopen(lib_names[l], RTLD_LAZY);
        if (!libs[l]) fprintf(stderr, "symprobe: dlopen %s failed: %s\n", lib_names[l], dlerror());
    }
    for (int n = 0; n < nnames; ++n) {
        if (strcmp(sources[n], "none") != 0) continue;
        const char* name = argv[i + n];
        for (int l = 0; l < nlibs; ++l) {
            if (!libs[l]) continue;
            void* addr = dlsym(libs[l], name);
            if (!addr) {
                snprintf(scratch, sizeof(scratch), "_%s", name);
                addr = dlsym(libs[l], scratch);
            }
            if (addr) {
                snprintf(addrs[n], sizeof(addrs[n]), "%p", addr);
                snprintf(sources[n], sizeof(sources[n]), "%s", lib_names[l]);
                break;
            }
        }
    }

    for (int n = 0; n < nnames; ++n) {
        printf("%s\t%s\t%s\n", argv[i + n], addrs[n], sources[n]);
    }
    fflush(stdout);
    return 0;
}
