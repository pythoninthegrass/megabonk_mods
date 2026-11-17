// Guest fixture: functions that throw, catch and clean up. The runtime they call is in another translation unit.
typedef unsigned long u64;
#define GUEST extern "C" __attribute__((noinline, visibility("hidden")))

extern "C" {
void native_note(int);
void poison();
void *__cxa_allocate_exception(u64);
[[noreturn]] void __cxa_throw(void *, void *, void (*)(void *));
int f_depth_value();
}

struct Guard {
    int id;
    ~Guard() { native_note(id); }
};

GUEST void thrower(int x) {
    if (x) {
        void *object = __cxa_allocate_exception(4);
        __cxa_throw(object, 0, 0);
    }
}

GUEST int f_catch(int x) {
    Guard a{1};
    try {
        Guard b{2};
        thrower(x);
        native_note(100);
    } catch (...) {
        native_note(200);
        return 5;
    }
    return 7;
}

GUEST void inner(int x) {
    Guard g{20};
    thrower(x);
    native_note(21);
}

GUEST void middle(int x) {
    Guard g{10};
    inner(x);
    native_note(11);
}

GUEST int f_nested(int x) {
    try {
        middle(x);
    } catch (...) {
        native_note(99);
        return 1;
    }
    return 0;
}

GUEST int f_rethrow(int x) {
    Guard a{3};
    try {
        try {
            thrower(x);
        } catch (...) {
            native_note(300);
            throw;
        }
    } catch (...) {
        native_note(301);
        return 9;
    }
    return 0;
}

GUEST long f_regs(long x) {
    long a = x * 3, b = x * 5, c = x * 7, d = x * 11, e = x * 13;
    try {
        thrower(1);
    } catch (...) {
    }
    return a + b + c + d + e;
}

GUEST int f_uncaught() {
    Guard g{40};
    thrower(1);
    return 0;
}

GUEST int f_depth() { return f_depth_value(); }

GUEST int f_leak() {
    poison();
    return 0;
}
