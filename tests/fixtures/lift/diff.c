#include <stdint.h>
#ifdef __x86_64__
#include <xmmintrin.h>
#include <emmintrin.h>
#endif

uint64_t f_sum(uint64_t n) {
    uint64_t s = 0;
    for (uint64_t i = 0; i < n % 512; i++) s += (i * i) ^ (i >> 3);
    return s;
}

int32_t f_clamp(int32_t x, int32_t lo, int32_t hi) { return x < lo ? lo : (x > hi ? hi : x); }

uint32_t f_mix(uint32_t a, uint32_t b) {
    a ^= b << 7;
    a = (a >> 3) | (a << 29);
    return a * 2654435761u + (uint32_t)__builtin_popcount(b);
}

int64_t f_div(int64_t a, int64_t b) {
    if (b == 0 || (a == INT64_MIN && b == -1)) return -1;
    return a / b + a % b;
}

uint8_t f_u8(uint8_t a, uint8_t b) { return (uint8_t)(a * b + (a < b)); }

int32_t f_sat(int32_t a, int32_t b) {
    int32_t r;
    if (__builtin_add_overflow(a, b, &r)) return a < 0 ? INT32_MIN : INT32_MAX;
    return r;
}

uint64_t f_collatz(uint64_t n) {
    uint64_t c = 0;
    n = (n % 100000) + 1;
    while (n != 1 && c < 1000) {
        n = (n & 1) ? 3 * n + 1 : n / 2;
        c++;
    }
    return c;
}

int32_t f_switch(int32_t x) {
    switch (x & 7) {
    case 0: return x + 11;
    case 1: return x * 3;
    case 2: return x ^ 0x55;
    case 3: return -x;
    case 4: return x >> 2;
    case 5: return x << 3;
    case 6: return x | 9;
    default: return 7;
    }
}

double f_poly(double x, double y) { return x * x + 2 * x * y - y / 3.0; }

int32_t f_f2i(double x) { return (int32_t)(x > 1e6 ? 1e6 : (x < -1e6 ? -1e6 : x)); }

/* The x86 rule for cvttss2si/cvttsd2si: NaN or a magnitude the destination cannot hold
   gives the integer indefinite value, where arm64 saturates. These are the oracle for the
   unclamped conversions below; the native cast runs only where both ISAs truncate alike. */
int32_t r_d2i32(double x) {
    if (!(x >= -2147483648.0) || !(x < 2147483648.0)) return INT32_MIN;
    return (int32_t)x;
}

int64_t r_d2i64(double x) {
    if (!(x >= -9223372036854775808.0) || !(x < 9223372036854775808.0)) return INT64_MIN;
    return (int64_t)x;
}

int32_t r_f2i32(float x) {
    if (!(x >= -2147483648.0f) || !(x < 2147483648.0f)) return INT32_MIN;
    return (int32_t)x;
}

int64_t r_f2i64(float x) {
    if (!(x >= -9223372036854775808.0f) || !(x < 9223372036854775808.0f)) return INT64_MIN;
    return (int64_t)x;
}

int32_t f_d2i32(double x) { return (int32_t)x; }

int64_t f_d2i64(double x) { return (int64_t)x; }

int32_t f_f2i32(float x) { return (int32_t)x; }

int64_t f_f2i64(float x) { return (int64_t)x; }

uint32_t f_movmskps(__attribute__((vector_size(16))) float a) {
#ifdef __x86_64__
    return (uint32_t)_mm_movemask_ps(a);
#else
    uint32_t lanes[4];
    __builtin_memcpy(lanes, &a, 16);
    uint32_t mask = 0;
    for (int i = 0; i < 4; i++) mask |= (lanes[i] >> 31) << i;
    return mask;
#endif
}

__attribute__((vector_size(16))) uint16_t f_pshuflw(__attribute__((vector_size(16))) uint16_t a) {
#ifdef __x86_64__
    return (__attribute__((vector_size(16))) uint16_t)_mm_shufflelo_epi16((__m128i)a, 0xe0);
#else
    __attribute__((vector_size(16))) uint16_t r = a;
    for (unsigned i = 0; i < 4; i++) r[i] = a[(0xe0 >> (2 * i)) & 3];
    return r;
#endif
}

__attribute__((vector_size(16))) double f_divpd(__attribute__((vector_size(16))) double a,
                                                __attribute__((vector_size(16))) double b) {
    return a / b;
}

__attribute__((vector_size(16))) float f_divps(__attribute__((vector_size(16))) float a,
                                               __attribute__((vector_size(16))) float b) {
    return a / b;
}

__attribute__((vector_size(16))) float f_divps_mem(__attribute__((vector_size(16))) float a, const float *p) {
    __attribute__((vector_size(16))) float b;
    for (int i = 0; i < 4; i++) b[i] = p[i];
    return a / b;
}

/* The x86 pack min/max rule lane by lane. The pragma is what keeps -O1 on the packed
   minps/maxps; without it clang scalarizes the loop to minss/maxss. */
__attribute__((vector_size(16))) float f_minps(__attribute__((vector_size(16))) float a,
                                               __attribute__((vector_size(16))) float b) {
    float x[4], y[4], r[4];
    __builtin_memcpy(x, &a, 16);
    __builtin_memcpy(y, &b, 16);
#pragma clang loop vectorize(enable) interleave(enable)
    for (int i = 0; i < 4; i++) r[i] = x[i] < y[i] ? x[i] : y[i];
    __attribute__((vector_size(16))) float o;
    __builtin_memcpy(&o, r, 16);
    return o;
}

__attribute__((vector_size(16))) float f_maxps(__attribute__((vector_size(16))) float a,
                                               __attribute__((vector_size(16))) float b) {
    float x[4], y[4], r[4];
    __builtin_memcpy(x, &a, 16);
    __builtin_memcpy(y, &b, 16);
#pragma clang loop vectorize(enable) interleave(enable)
    for (int i = 0; i < 4; i++) r[i] = x[i] > y[i] ? x[i] : y[i];
    __attribute__((vector_size(16))) float o;
    __builtin_memcpy(&o, r, 16);
    return o;
}
