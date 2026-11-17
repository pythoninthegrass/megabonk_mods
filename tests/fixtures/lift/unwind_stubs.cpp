// Guest fixture: stand-ins for the native functions the harness binds by address. They live in their own
// translation unit so the optimizer cannot fold their results into the callers.
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
GUEST const u8 *_Unwind_GetLanguageSpecificData(void *) { STUB_BODY; return 0; }
GUEST u64 _Unwind_GetRegionStart(void *) { STUB_BODY; return 0; }
GUEST u64 _Unwind_GetIPInfo(void *, int *) { STUB_BODY; return 0; }
GUEST void _Unwind_SetGR(void *, int, u64) { STUB_BODY; }
GUEST void _Unwind_SetIP(void *, u64) { STUB_BODY; }
GUEST void native_note(int) { STUB_BODY; }
GUEST void native_abort() { STUB_BODY; }

GUEST void poison() { STUB_BODY; }
GUEST void *__tls_get_addr(void *) { STUB_BODY; return 0; }
