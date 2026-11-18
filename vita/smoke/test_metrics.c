#include <assert.h>

#include "metrics.h"

int main(void)
{
    FrameTimes times = {0};
    assert(times.count == 0);
    frame_times_add(&times, 17000);
    frame_times_add(&times, 16000);
    frame_times_add(&times, 18000);
    assert(times.count == 3);
    assert(times.min_us == 16000);
    assert(times.max_us == 18000);
    assert(times.total_us == 51000);

    StickRange left = {0}, right = {0};
    stick_range_add(&left, 128, 128);
    stick_range_add(&right, 125, 129);
    assert(!stick_range_exercised(&left));
    stick_range_add(&left, 20, 128);
    stick_range_add(&left, 230, 128);
    assert(!stick_range_exercised(&left));
    stick_range_add(&left, 128, 20);
    stick_range_add(&left, 128, 230);
    assert(stick_range_exercised(&left));
    assert(!stick_range_exercised(&right));
    assert(left.min_x == 20 && left.max_x == 230);
    assert(left.min_y == 20 && left.max_y == 230);

    MemoryPeak memory = memory_peak_start(10000);
    memory_peak_sample(&memory, 9000);
    memory_peak_sample(&memory, 9500);
    memory_peak_sample(&memory, 11000);
    assert(memory.min_free == 9000);
    assert(memory_peak_used(&memory) == 1000);
}
