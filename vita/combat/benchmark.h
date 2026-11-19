#ifndef COMBAT_BENCHMARK_H
#define COMBAT_BENCHMARK_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

enum {
    BENCHMARK_BUDGET_US = 33300, BENCHMARK_HITCH_US = 50000,
    BENCHMARK_GATE_COUNT = 96, BENCHMARK_GATE_NEAR = 5,
    BENCHMARK_GATE_TRIALS = 6, BENCHMARK_TRIALS = 36,
};

typedef struct {
    unsigned count, repeat;
    bool scattered;
} BenchmarkTrial;

typedef struct {
    uint64_t duration_us;
    uint32_t p95_us, p99_us, max_us;
    size_t over_budget, hitches;
} BenchmarkSummary;

typedef struct {
    uint32_t target_live, live_min, live_max;
    uint32_t near_sum, samples, near_min;
} BenchmarkWorkload;

bool benchmark_summarize(const uint32_t *intervals, size_t count, uint32_t *scratch,
                         size_t capacity, uint64_t minimum_us, BenchmarkSummary *out);
bool benchmark_matched_pair(BenchmarkWorkload gathered, BenchmarkWorkload scattered);
bool benchmark_trial(unsigned index, BenchmarkTrial *trial);
bool benchmark_gate_trial(unsigned index, BenchmarkTrial *trial);
bool benchmark_gate_density(BenchmarkWorkload work);

#endif
