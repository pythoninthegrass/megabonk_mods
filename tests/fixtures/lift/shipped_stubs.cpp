// Guest fixture: stand-ins for the libsupc++ entry points and natives that the shipped runtime lifted from the image replaces.
typedef unsigned long u64;
typedef unsigned char u8;
#define GUEST extern "C" __attribute__((noinline, visibility("hidden")))
#define STUB_BODY __asm__ volatile("ud2" ::: "memory")
struct UnwindException {
    u64 klass, cleanup, private_1, private_2;
} __attribute__((aligned(16)));

GUEST int _Unwind_RaiseException(UnwindException *) { STUB_BODY; return 0; }
GUEST void _Unwind_Resume(UnwindException *) { STUB_BODY; }
GUEST int _Unwind_Resume_or_Rethrow(UnwindException *) { STUB_BODY; return 0; }
GUEST void native_note(int) { STUB_BODY; }
GUEST void native_abort() { STUB_BODY; }
GUEST void poison() { STUB_BODY; }

GUEST void *__cxa_allocate_exception(u64) { STUB_BODY; return 0; }
GUEST void *__cxa_begin_catch(void *) { STUB_BODY; return 0; }
GUEST void __cxa_end_catch() { STUB_BODY; }
GUEST void __cxa_throw(void *, void *, void (*)(void *)) { STUB_BODY; }
GUEST void __cxa_rethrow() { STUB_BODY; }
GUEST int __gxx_personality_v0(int, int, u64, UnwindException *, void *) { STUB_BODY; return 0; }
GUEST int f_depth_value() { return 0; }
namespace std {
[[noreturn]] __attribute__((noinline, visibility("hidden"))) void terminate() {
    STUB_BODY;
    __builtin_unreachable();
}
}
