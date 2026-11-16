#include <stdint.h>

typedef float v4f32 __attribute__((vector_size(16)));

#define MIX_ARGS uint64_t a, uint64_t b, uint64_t c, uint64_t d, uint64_t e, uint64_t f, uint64_t g, \
    double h, double i, double j, double k, double l, double m, double n, double o, double p, v4f32 v, void *q
#define MIX_PASS a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, v, q
#define NOINLINE __attribute__((noinline, visibility("hidden")))

NOINLINE double native_mix(MIX_ARGS) {
    return a + 2*b + 3*c + 4*d + 5*e + 6*f + 7*g +
        h + 2*i + 3*j + 4*k + 5*l + 6*m + 7*n + 8*o + 9*p +
        v[0] + 2*v[1] + 3*v[2] + 4*v[3] + *(uint64_t *)q;
}

NOINLINE double f_mix(MIX_ARGS) {
    return a + 2*b + 3*c + 4*d + 5*e + 6*f + 7*g +
        h + 2*i + 3*j + 4*k + 5*l + 6*m + 7*n + 8*o + 9*p +
        v[0] + 2*v[1] + 3*v[2] + 4*v[3] + *(uint64_t *)q;
}

NOINLINE double f_import_mix(MIX_ARGS) {
    return native_mix(MIX_PASS) + 1;
}

NOINLINE v4f32 native_vector(v4f32 a, v4f32 b) {
    return a + b;
}

NOINLINE v4f32 f_vector(v4f32 a, v4f32 b) {
    return native_vector(a, b) * (v4f32){2, 2, 2, 2};
}

NOINLINE void *native_pointer(void *p) {
    return (uint64_t *)p + 1;
}

NOINLINE void *f_pointer(uint64_t *p) {
    return native_pointer(p);
}

NOINLINE uint64_t f_inner(uint64_t x) {
    return x * 3 + 7;
}

NOINLINE uint64_t f_nested(uint64_t x) {
    return f_inner(x) + f_inner(x + 1);
}

#ifdef ABI_HOST
extern uint64_t e_inner(uint64_t);
#define CALLBACK e_inner
#else
#define CALLBACK f_inner
#endif

NOINLINE uint64_t native_callback(uint64_t x) {
    return CALLBACK(x + 2) + 11;
}

NOINLINE uint64_t f_callback(uint64_t x) {
    return native_callback(x) + f_inner(x);
}

NOINLINE uint64_t f_indirect(uint64_t (*fn)(uint64_t), uint64_t x) {
    return fn(x) + 3;
}

NOINLINE uint64_t f_indirect_tail(uint64_t (**fn)(uint64_t), uint64_t x) {
    return (*fn)(x);
}

#define ROUNDTRIP(name, type) \
    NOINLINE type native_##name(type x) { return x; } \
    NOINLINE type f_##name(type x) { return native_##name(x); }

ROUNDTRIP(i8, int8_t)
ROUNDTRIP(u8, uint8_t)
ROUNDTRIP(i16, int16_t)
ROUNDTRIP(u16, uint16_t)
ROUNDTRIP(i32, int32_t)
ROUNDTRIP(u32, uint32_t)
ROUNDTRIP(i64, int64_t)
ROUNDTRIP(u64, uint64_t)
ROUNDTRIP(f32, float)
ROUNDTRIP(f64, double)

typedef double v2f64 __attribute__((vector_size(16)));
typedef uint32_t v4u32 __attribute__((vector_size(16)));
ROUNDTRIP(v2f64, v2f64)
ROUNDTRIP(v4u32, v4u32)

NOINLINE void native_store(void *p, uint64_t x) {
    *(uint64_t *)p = x;
}

NOINLINE void f_store(void *p, uint64_t x) {
    native_store(p, x);
}
