#include "sweep.h"
#include "benchmark.h"

#include <inttypes.h>
#include <stdatomic.h>
#include <stdio.h>
#include <sys/stat.h>
#include <time.h>

#include <psp2/display.h>
#include <psp2/gxm.h>
#include <psp2/kernel/processmgr.h>
#include <psp2/kernel/sysmem.h>
#include <psp2/power.h>

enum { WARMUP_US = 500000, WINDOW_US = 5000000, CAPACITY = 600 };

static const char root[] = "ux0:data/megabonk-vita-combat";
static char directory[112], status[96];
static unsigned index, trial_count;
static bool active, measuring, gate_mode;
static uint64_t trial_start, window_start, next_sample;
static BenchmarkTrial trial;
static BenchmarkWorkload workload;
static SceKernelFreeMemorySizeInfo baseline, minimum;
static bool memory_valid, baseline_valid;
static int first_clocks[4], last_clocks[4];
static atomic_bool capture;
static unsigned frame_count, display_errors;
static uint64_t timestamps[CAPACITY];
static uint32_t vcounts[CAPACITY], intervals[CAPACITY], scratch[CAPACITY];
static void *queued_base;

int __real_sceDisplaySetFrameBuf(const SceDisplayFrameBuf *, SceDisplaySetBufSync);
int __real_sceDisplayWaitVblankStart(void);

int __wrap_sceDisplaySetFrameBuf(const SceDisplayFrameBuf *frame, SceDisplaySetBufSync sync)
{
    int result = __real_sceDisplaySetFrameBuf(frame, sync);
    queued_base = result >= 0 && frame && sync == SCE_DISPLAY_SETBUF_NEXTFRAME ? frame->base : NULL;
    return result;
}

int __wrap_sceDisplayWaitVblankStart(void)
{
    int result = __real_sceDisplayWaitVblankStart();
    if (!atomic_load(&capture))
        return result;
    SceDisplayFrameBuf current = {.size = sizeof(current)};
    const int vcount = sceDisplayGetVcount();
    if (result < 0 || !queued_base || vcount < 0 ||
        sceDisplayGetFrameBuf(&current, SCE_DISPLAY_SETBUF_IMMEDIATE) < 0 ||
        current.base != queued_base || current.width != 960 || current.height != 544 ||
        frame_count == CAPACITY || (frame_count && (uint32_t)vcount == vcounts[frame_count - 1])) {
        ++display_errors;
        return result;
    }
    timestamps[frame_count] = sceKernelGetProcessTimeWide();
    vcounts[frame_count++] = (uint32_t)vcount;
    return result;
}

static bool read_memory(SceKernelFreeMemorySizeInfo *info)
{
    info->size = sizeof(*info);
    return sceKernelGetFreeMemorySize(info) >= 0 && info->size_user >= 0 && info->size_cdram >= 0;
}

void sweep_memory_baseline(void)
{
    baseline_valid = read_memory(&baseline);
    minimum = baseline;
}

static void sample_memory(void)
{
    SceKernelFreeMemorySizeInfo info;
    if (!read_memory(&info)) {
        memory_valid = false;
        return;
    }
    if (info.size_user < minimum.size_user)
        minimum.size_user = info.size_user;
    if (info.size_cdram < minimum.size_cdram)
        minimum.size_cdram = info.size_cdram;
}

static void clocks(int out[4])
{
    out[0] = scePowerGetArmClockFrequency();
    out[1] = scePowerGetBusClockFrequency();
    out[2] = scePowerGetGpuClockFrequency();
    out[3] = scePowerGetGpuXbarClockFrequency();
}

static void sample_density(const Combat *game)
{
    unsigned near = 0;
    if (game->live < workload.live_min)
        workload.live_min = game->live;
    if (game->live > workload.live_max)
        workload.live_max = game->live;
    for (unsigned i = 0; i < COMBAT_CAPACITY; ++i) {
        const CombatEnemy *enemy = &game->enemies[i];
        float x = enemy->position.x - game->player.x, z = enemy->position.z - game->player.z;
        if (enemy->hp && x * x + z * z <= 64)
            ++near;
    }
    if (near < workload.near_min)
        workload.near_min = near;
    workload.near_sum += near;
    ++workload.samples;
}

static void end_capture(void)
{
    sceGxmDisplayQueueFinish();
    atomic_store(&capture, false);
    measuring = false;
}

static void start_trial(Combat *game)
{
    if (gate_mode)
        benchmark_gate_trial(index, &trial);
    else
        benchmark_trial(index, &trial);
    combat_benchmark(game, trial.count, trial.scattered);
    workload = (BenchmarkWorkload){.target_live = trial.count, .live_min = UINT32_MAX, .near_min = UINT32_MAX};
    frame_count = display_errors = 0;
    memory_valid = baseline_valid;
    minimum = baseline;
    sample_memory();
    trial_start = sceKernelGetProcessTimeWide();
    snprintf(status, sizeof(status), "Trial %u/%u", index + 1, trial_count);
}

bool sweep_start(Combat *game, bool gate)
{
    mkdir(root, 0777);
    snprintf(directory, sizeof(directory), "%s/%s-%lld", root, gate ? "gate" : "pilot", (long long)time(NULL));
    if (mkdir(directory, 0777) < 0) {
        snprintf(status, sizeof(status), "Cannot create report folder");
        return false;
    }
    active = true;
    index = 0;
    gate_mode = gate;
    trial_count = gate ? BENCHMARK_GATE_TRIALS : BENCHMARK_TRIALS;
    start_trial(game);
    return true;
}

bool sweep_active(void)
{
    return active;
}

void sweep_cancel(void)
{
    if (measuring)
        end_capture();
    active = false;
    status[0] = '\0';
}

const char *sweep_status(void)
{
    return status;
}

static bool write_trial(void)
{
    char path[144], pending[148];
    snprintf(path, sizeof(path), "%s/%02u.csv", directory, index + 1);
    snprintf(pending, sizeof(pending), "%s.tmp", path);
    FILE *out = fopen(pending, "w");
    if (!out)
        return false;
    size_t count = 0;
    for (unsigned i = 1; i < frame_count; ++i) {
        const uint64_t interval = timestamps[i] - timestamps[i - 1];
        if (!interval || interval > UINT32_MAX)
            ++display_errors;
        else
            intervals[count++] = (uint32_t)interval;
    }
    BenchmarkSummary summary = {0};
    int summary_valid = !display_errors &&
        benchmark_summarize(intervals, count, scratch, CAPACITY, WINDOW_US, &summary);
    fprintf(out, "# mode=%s trial=%u repeat=%u enemies=%u layout=%s width=960 height=544\n",
            gate_mode ? "gate" : "pilot", index + 1, trial.repeat, trial.count, trial.scattered ? "scattered" : "gathered");
    fprintf(out, "# clock_start_mhz=%d/%d/%d/%d clock_end_mhz=%d/%d/%d/%d\n",
            first_clocks[0], first_clocks[1], first_clocks[2], first_clocks[3],
            last_clocks[0], last_clocks[1], last_clocks[2], last_clocks[3]);
    fprintf(out, "# live_min=%u live_max=%u near_radius=8 near_min=%u near_sum=%u density_samples=%u gate_density_met=%d\n",
            workload.live_min, workload.live_max, workload.samples ? workload.near_min : 0,
            workload.near_sum, workload.samples, benchmark_gate_density(workload));
    fprintf(out, "# memory_valid=%d main_initial_free=%d main_min_free=%d cdram_initial_free=%d cdram_min_free=%d\n",
            memory_valid, baseline.size_user, minimum.size_user, baseline.size_cdram, minimum.size_cdram);
    fprintf(out, "# timing=verified_display_latch_after_vblank summary_valid=%d display_errors=%u requested_us=%u intervals=%u duration_us=%" PRIu64
                 " p95_us=%u p99_us=%u max_us=%u over_33300_us=%u hitches_over_50000_us=%u\n",
            summary_valid, display_errors, WINDOW_US, (unsigned)count, summary.duration_us,
            summary.p95_us, summary.p99_us, summary.max_us,
            (unsigned)summary.over_budget, (unsigned)summary.hitches);
    fputs("vcount,observed_process_us\n", out);
    for (unsigned i = 0; i < frame_count; ++i)
        fprintf(out, "%u,%" PRIu64 "\n", vcounts[i], timestamps[i]);
    const bool ok = !ferror(out);
    return fclose(out) == 0 && ok && rename(pending, path) == 0;
}

void sweep_update(Combat *game)
{
    if (!active)
        return;
    uint64_t now = sceKernelGetProcessTimeWide();
    if (!measuring && now - trial_start >= WARMUP_US) {
        sceGxmDisplayQueueFinish();
        clocks(first_clocks);
        window_start = next_sample = sceKernelGetProcessTimeWide();
        measuring = true;
        atomic_store(&capture, true);
    }
    if (!measuring)
        return;
    if (now >= next_sample) {
        sample_density(game);
        sample_memory();
        next_sample += 250000;
    }
    if (now < window_start + WINDOW_US + 100000)
        return;
    end_capture();
    clocks(last_clocks);
    if (!write_trial()) {
        snprintf(status, sizeof(status), "Could not save trial %u", index + 1);
        active = false;
    } else if (++index == trial_count) {
        snprintf(status, sizeof(status), "%s saved", gate_mode ? "Gate check" : "Pilot sweep");
        active = false;
    } else {
        start_trial(game);
    }
}
