#ifndef VITA_SMOKE_METRICS_H
#define VITA_SMOKE_METRICS_H

#include <stdbool.h>
#include <stdint.h>

typedef struct {
    uint64_t count, min_us, max_us, total_us;
} FrameTimes;

static inline void frame_times_add(FrameTimes *times, uint64_t us)
{
    if (!times->count || us < times->min_us)
        times->min_us = us;
    if (us > times->max_us)
        times->max_us = us;
    times->count++;
    times->total_us += us;
}

typedef struct {
    bool sampled;
    uint8_t min_x, max_x, min_y, max_y;
} StickRange;

static inline void stick_range_add(StickRange *range, uint8_t x, uint8_t y)
{
    if (!range->sampled) {
        *range = (StickRange){true, x, x, y, y};
        return;
    }
    if (x < range->min_x)
        range->min_x = x;
    if (x > range->max_x)
        range->max_x = x;
    if (y < range->min_y)
        range->min_y = y;
    if (y > range->max_y)
        range->max_y = y;
}

static inline bool stick_range_exercised(const StickRange *range)
{
    return range->sampled && range->min_x <= 64 && range->max_x >= 192 &&
           range->min_y <= 64 && range->max_y >= 192;
}

typedef struct {
    unsigned initial_free, min_free;
} MemoryPeak;

static inline MemoryPeak memory_peak_start(unsigned free_bytes)
{
    return (MemoryPeak){free_bytes, free_bytes};
}

static inline void memory_peak_sample(MemoryPeak *peak, unsigned free_bytes)
{
    if (free_bytes < peak->min_free)
        peak->min_free = free_bytes;
}

static inline unsigned memory_peak_used(const MemoryPeak *peak)
{
    return peak->initial_free - peak->min_free;
}

#endif
