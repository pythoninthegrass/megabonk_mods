#include "benchmark.h"

#include <assert.h>
#include <string.h>

int main(void)
{
    uint32_t intervals[100];
    for (unsigned i = 0; i < 100; ++i)
        intervals[i] = 100000 - 1000 * i;
    uint32_t original[100], scratch[100];
    memcpy(original, intervals, sizeof intervals);
    BenchmarkSummary result;
    assert(benchmark_summarize(intervals, 100, scratch, 100, 5000000, &result));
    assert(!memcmp(intervals, original, sizeof intervals));
    assert(result.duration_us == 5050000);
    assert(result.p95_us == 95000 && result.p99_us == 99000 && result.max_us == 100000);
    assert(result.over_budget == 67 && result.hitches == 50);
    assert(!benchmark_summarize(intervals, 100, scratch, 99, 5000000, &result));
    assert(!benchmark_summarize(intervals, 100, scratch, 100, 5050001, &result));
    assert(!benchmark_summarize(intervals, 0, scratch, 100, 1, &result));

    uint32_t edges[] = {33300, 33301, 50000, 50001};
    assert(benchmark_summarize(edges, 4, scratch, 100, 1, &result));
    assert(result.over_budget == 3 && result.hitches == 1);
    edges[0] = 0;
    assert(!benchmark_summarize(edges, 4, scratch, 100, 1, &result));

    BenchmarkWorkload gathered = {.target_live = 48, .live_min = 48, .live_max = 48,
                                  .near_sum = 450, .samples = 10};
    BenchmarkWorkload scattered = {.target_live = 48, .live_min = 48, .live_max = 48,
                                   .near_sum = 90, .samples = 3};
    assert(benchmark_matched_pair(gathered, scattered));
    scattered.near_sum = 135;
    assert(!benchmark_matched_pair(gathered, scattered));
    scattered.near_sum = 90;
    scattered.live_min = 47;
    assert(!benchmark_matched_pair(gathered, scattered));

    for (unsigned i = 0; i < BENCHMARK_TRIALS; i += 2) {
        BenchmarkTrial a, b;
        assert(benchmark_trial(i, &a) && benchmark_trial(i + 1, &b));
        assert(a.count == b.count && a.repeat == b.repeat && a.scattered != b.scattered);
        assert(a.scattered == (i / 2 % 2 != 0));
    }
    BenchmarkTrial last;
    assert(benchmark_trial(BENCHMARK_TRIALS - 1, &last));
    assert(last.count == 240 && last.repeat == 3);
    assert(!benchmark_trial(BENCHMARK_TRIALS, &last));
    for (unsigned i = 0; i < BENCHMARK_GATE_TRIALS; ++i) {
        BenchmarkTrial gate;
        assert(benchmark_gate_trial(i, &gate));
        assert(gate.count == 96 && gate.repeat == i / 2 + 1);
        assert(gate.scattered == ((i % 2) != (i / 2 % 2)));
    }
    assert(!benchmark_gate_trial(BENCHMARK_GATE_TRIALS, &last));
    assert(benchmark_gate_density((BenchmarkWorkload){.target_live = 96, .live_min = 96, .live_max = 96,
                                                       .near_sum = 12, .samples = 2, .near_min = 5}));
    assert(!benchmark_gate_density((BenchmarkWorkload){.target_live = 96, .live_min = 96, .live_max = 96,
                                                        .near_sum = 12, .samples = 2, .near_min = 4}));
}
