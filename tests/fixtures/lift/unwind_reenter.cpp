// Guest fixture: a lifted frame that calls a native import which re-enters an export. Only the re-entry test builds it.
#define GUEST extern "C" __attribute__((noinline, visibility("hidden")))

extern "C" {
void native_note(int);
void thrower(int);
int native_reenter(int);
}

struct ReenterGuard {
    int id;
    ~ReenterGuard() { native_note(id); }
};

GUEST int f_reenter(int x) {
    ReenterGuard a{60};
    int r = 0;
    try {
        r = native_reenter(x);
        native_note(r);
        thrower(x);
        native_note(101);
    } catch (...) {
        native_note(61);
        return r + 100;
    }
    return r;
}
