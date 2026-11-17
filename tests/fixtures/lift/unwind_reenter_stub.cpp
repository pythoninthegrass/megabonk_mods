// Guest fixture: stand-in for the native import the re-entry fixture calls, in its own translation unit so the
// optimizer cannot fold its result into the caller.
extern "C" __attribute__((noinline, visibility("hidden"))) int native_reenter(int) {
    __asm__ volatile("ud2" ::: "memory");
    return 0;
}
