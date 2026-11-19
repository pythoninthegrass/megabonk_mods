#include "benchmark.h"

#include <stdlib.h>

static BenchmarkTrial scheduled_trial(unsigned index, unsigned count)
{
    return (BenchmarkTrial){count, index / 2 % 3 + 1, (index % 2) != (index / 2 % 2)};
}

bool benchmark_trial(unsigned index, BenchmarkTrial *trial)
{
    static const unsigned counts[] = {24, 48, 96, 144, 192, 240};
    if (index >= BENCHMARK_TRIALS)
        return false;
    *trial = scheduled_trial(index, counts[index / BENCHMARK_GATE_TRIALS]);
    return true;
}

bool benchmark_gate_trial(unsigned index, BenchmarkTrial *trial)
{
    if (index >= BENCHMARK_GATE_TRIALS)
        return false;
    *trial = scheduled_trial(index, BENCHMARK_GATE_COUNT);
    return true;
}

static int compare_intervals(const void *left, const void *right)
{
    const uint32_t a = *(const uint32_t *)left, b = *(const uint32_t *)right;
    return (a > b) - (a < b);
}

static size_t percentile_index(size_t count, unsigned percentile)
{
    return count / 100 * percentile + (count % 100 * percentile + 99) / 100 - 1;
}

bool benchmark_summarize(const uint32_t *intervals, size_t count, uint32_t *scratch,
                         size_t capacity, uint64_t minimum_us, BenchmarkSummary *out)
{
    if (!count || count > capacity || scratch == intervals)
        return false;
    BenchmarkSummary summary = {0};
    for (size_t i = 0; i < count; ++i) {
        uint32_t interval = intervals[i];
        if (!interval)
            return false;
        summary.duration_us += interval;
        summary.over_budget += interval > BENCHMARK_BUDGET_US;
        summary.hitches += interval > BENCHMARK_HITCH_US;
        scratch[i] = interval;
    }
    if (summary.duration_us < minimum_us)
        return false;
    qsort(scratch, count, sizeof(*scratch), compare_intervals);
    summary.p95_us = scratch[percentile_index(count, 95)];
    summary.p99_us = scratch[percentile_index(count, 99)];
    summary.max_us = scratch[count - 1];
    *out = summary;
    return true;
}

static bool valid_workload(BenchmarkWorkload work)
{
    return work.target_live && work.samples && work.live_min == work.target_live &&
           work.live_max == work.target_live && work.near_sum <= (uint64_t)work.target_live * work.samples;
}

bool benchmark_matched_pair(BenchmarkWorkload gathered, BenchmarkWorkload scattered)
{
    return valid_workload(gathered) && valid_workload(scattered) &&
           gathered.target_live == scattered.target_live &&
           (uint64_t)gathered.near_sum * scattered.samples > (uint64_t)scattered.near_sum * gathered.samples;
}

bool benchmark_gate_density(BenchmarkWorkload work)
{
    return valid_workload(work) && work.target_live == BENCHMARK_GATE_COUNT &&
           work.near_min >= BENCHMARK_GATE_NEAR &&
           (uint64_t)work.near_min * work.samples <= work.near_sum;
}
