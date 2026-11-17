// Reference driver: links unwind.cpp against a stock libstdc++ and prints the notes in the same format as the lifted harness.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <exception>

extern "C" {
int f_catch(int);
int f_nested(int);
int f_rethrow(int);
long f_regs(long);
int f_uncaught();
}

static int notes[64], count;
extern "C" void native_note(int id) { notes[count++] = id; }
extern "C" void poison() {}
extern "C" int f_depth_value() { return 0; }

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
    if (!strcmp(mode, "catch0")) result = f_catch(0);
    else if (!strcmp(mode, "catch1")) result = f_catch(1);
    else if (!strcmp(mode, "nested0")) result = f_nested(0);
    else if (!strcmp(mode, "nested1")) result = f_nested(1);
    else if (!strcmp(mode, "rethrow1")) result = f_rethrow(1);
    else if (!strcmp(mode, "regs")) result = f_regs(7);
    else if (!strcmp(mode, "uncaught")) result = f_uncaught();
    else return 2;
    printf("R %ld N ", result);
    print_notes();
    printf(" D 0\n");
    return 0;
}
