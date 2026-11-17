// Guest fixture: typed catches over real RTTI. The type_info vtables are undefined symbols that the test binds to the shipped image's own.
#define GUEST extern "C" __attribute__((noinline, visibility("hidden")))

extern "C" void native_note(int);

struct Base {
    int x;
};
struct Derived : Base {
    int y;
};
struct Other {
    int z;
};

struct Guard {
    int id;
    ~Guard() { native_note(id); }
};

GUEST void raise_derived(int a) { throw Derived{{a}, a + 1}; }
GUEST void raise_base(int a) { throw Base{a}; }
GUEST void raise_other(int a) { throw Other{a}; }

GUEST int f_upcast(int a) {
    Guard g{1};
    try {
        raise_derived(a);
    } catch (Base &b) {
        native_note(100 + b.x);
        return b.x * 10;
    }
    return -1;
}

GUEST int f_exact(int a) {
    try {
        raise_derived(a);
    } catch (Derived &d) {
        return d.y;
    }
    return -1;
}

GUEST int f_same(int a) {
    try {
        raise_base(a);
    } catch (Base &b) {
        return b.x + 1000;
    }
    return -1;
}

GUEST int f_skip(int a) {
    try {
        Guard g{2};
        try {
            Guard h{3};
            raise_base(a);
        } catch (Other &) {
            native_note(900);
            return -2;
        }
    } catch (Base &b) {
        native_note(200 + b.x);
        return b.x;
    }
    return -1;
}

GUEST int f_downcast_misses(int a) {
    try {
        raise_base(a);
    } catch (Derived &) {
        return -4;
    } catch (...) {
        native_note(300);
        return 77;
    }
    return -1;
}

GUEST int f_unmatched(int a) {
    Guard g{4};
    try {
        raise_other(a);
    } catch (Base &) {
        return -5;
    }
    return -1;
}
