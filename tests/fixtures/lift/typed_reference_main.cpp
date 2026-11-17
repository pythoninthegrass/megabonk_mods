// Reference driver: links typed.cpp against a stock libstdc++ and prints the notes in the same format as the lifted harness.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <exception>

extern "C" {
int f_upcast(int);
int f_exact(int);
int f_same(int);
int f_skip(int);
int f_downcast_misses(int);
int f_unmatched(int);
}

static int notes[64], count;
extern "C" void native_note(int id) { notes[count++] = id; }

static void print_notes() {
    for (int i = 0; i < count; i++) printf("%s%d", i ? "," : "", notes[i]);
}

static void on_terminate() {
    printf("ABORT N ");
    print_notes();
    printf("\n");
    fflush(stdout);
    abort();
}

int main(int argc, char **argv) {
    std::set_terminate(on_terminate);
    const char *mode = argc > 1 ? argv[1] : "";
    long result = 0;
    if (!strcmp(mode, "upcast")) result = f_upcast(5);
    else if (!strcmp(mode, "exact")) result = f_exact(5);
    else if (!strcmp(mode, "same")) result = f_same(5);
    else if (!strcmp(mode, "skip")) result = f_skip(5);
    else if (!strcmp(mode, "downcast_misses")) result = f_downcast_misses(5);
    else if (!strcmp(mode, "unmatched")) result = f_unmatched(5);
    else return 2;
    printf("R %ld N ", result);
    print_notes();
    printf("\n");
    return 0;
}
