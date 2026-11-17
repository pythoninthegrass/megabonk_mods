// Guest fixture: a minimal C++ exception runtime. The _Unwind_* and native_* functions are stubs the harness binds.
typedef unsigned long u64;
typedef unsigned char u8;
#define GUEST extern "C" __attribute__((noinline, visibility("hidden")))

struct UnwindException {
    u64 klass, cleanup, private_1, private_2;
} __attribute__((aligned(16)));

extern "C" {
int _Unwind_RaiseException(UnwindException *);
void _Unwind_Resume(UnwindException *);
int _Unwind_Resume_or_Rethrow(UnwindException *);
const u8 *_Unwind_GetLanguageSpecificData(void *);
u64 _Unwind_GetRegionStart(void *);
u64 _Unwind_GetIPInfo(void *, int *);
void _Unwind_SetGR(void *, int, u64);
void _Unwind_SetIP(void *, u64);
void native_note(int);
void native_abort();
}

static UnwindException g_exception;
static u8 g_payload[16];
static UnwindException *g_caught;
static int g_depth;

namespace std {
[[noreturn]] __attribute__((noinline, visibility("hidden"))) void terminate() {
    native_abort();
    __builtin_unreachable();
}
}

GUEST void abort() {
    native_abort();
    __builtin_unreachable();
}

GUEST void *__cxa_allocate_exception(u64) { return g_payload; }

GUEST void *__cxa_begin_catch(void *exception) {
    if (exception != &g_exception) native_abort();
    g_caught = (UnwindException *)exception;
    g_depth++;
    return g_payload;
}

GUEST void __cxa_end_catch() { g_depth--; }

GUEST void __cxa_throw(void *, void *, void (*)(void *)) {
    g_exception.klass = 0x4D42;
    g_exception.cleanup = g_exception.private_1 = g_exception.private_2 = 0;
    _Unwind_RaiseException(&g_exception);
    __cxa_begin_catch(&g_exception);
    std::terminate();
}

GUEST void __cxa_rethrow() {
    _Unwind_Resume_or_Rethrow(g_caught);
    __cxa_begin_catch(g_caught);
    std::terminate();
}

static u64 read_uleb(const u8 *&p) {
    u64 value = 0;
    int shift = 0;
    for (;;) {
        u8 byte = *p++;
        value |= (u64)(byte & 0x7F) << shift;
        shift += 7;
        if (!(byte & 0x80)) return value;
    }
}

static long read_sleb(const u8 *&p) {
    long value = 0;
    int shift = 0;
    for (;;) {
        u8 byte = *p++;
        value |= (long)(byte & 0x7F) << shift;
        shift += 7;
        if (!(byte & 0x80)) {
            if (byte & 0x40) value |= -(1L << shift);
            return value;
        }
    }
}

// Cleanups and catch(...) only: a typed filter or an exception specification stops the run.
GUEST int __gxx_personality_v0(int version, int actions, u64, UnwindException *exception, void *context) {
    if (version != 1) return 3;
    const u8 *p = _Unwind_GetLanguageSpecificData(context);
    if (!p) return 8;
    u64 start = _Unwind_GetRegionStart(context);
    int before = 0;
    u64 relative = _Unwind_GetIPInfo(context, &before) - 1 - start;
    if (*p++ != 0xFF) native_abort();
    if (*p++ != 0xFF) read_uleb(p);
    if (*p++ != 0x01) native_abort();
    u64 length = read_uleb(p);
    const u8 *end = p + length;
    while (p < end) {
        u64 site = read_uleb(p), size = read_uleb(p), pad = read_uleb(p), action = read_uleb(p);
        if (relative < site) break;
        if (relative >= site + size) continue;
        if (!pad) return 8;
        long selector = 0;
        bool catches = false;
        if (action) {
            const u8 *record = end + action - 1;
            for (;;) {
                long filter = read_sleb(record);
                const u8 *field = record;
                long next = read_sleb(record);
                if (filter < 0) native_abort();
                if (filter > 0) {
                    catches = true;
                    selector = filter;
                    break;
                }
                if (!next) break;
                record = field + next;
            }
        }
        if (actions & 1) return catches ? 6 : 8;
        _Unwind_SetGR(context, 0, (u64)exception);
        _Unwind_SetGR(context, 1, (u64)selector);
        _Unwind_SetIP(context, start + pad);
        return 7;
    }
    native_abort();
    return 3;
}


GUEST int f_depth_value() { return g_depth; }
