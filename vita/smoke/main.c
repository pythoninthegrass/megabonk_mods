#include <inttypes.h>
#include <stdio.h>
#include <sys/stat.h>

#include <psp2/ctrl.h>
#include <psp2/display.h>
#include <psp2/kernel/modulemgr.h>
#include <psp2/kernel/processmgr.h>
#include <psp2/kernel/sysmem.h>
#include <psp2/power.h>

#include "metrics.h"

enum {
    WIDTH = 960, HEIGHT = 544, PITCH = 960,
    FRAME_BYTES = PITCH * HEIGHT * sizeof(uint32_t),
    BUFFER_BYTES = (2 * FRAME_BYTES + 0x3ffff) & ~0x3ffff,
};

unsigned int _newlib_heap_size_user = 1024 * 1024;

static const char report_dir[] = "ux0:data/megabonk-vita-smoke";
static const char report_path[] = "ux0:data/megabonk-vita-smoke/result.txt";

static SceKernelFreeMemorySizeInfo free_memory(void)
{
    SceKernelFreeMemorySizeInfo info = {.size = sizeof(info)};
    if (sceKernelGetFreeMemorySize(&info) < 0)
        info.size_user = info.size_cdram = -1;
    return info;
}

static void report_memory(FILE *out, const char *pool, const MemoryPeak *peak)
{
    fprintf(out, "%s_initial_free_bytes=%u\n%s_min_free_bytes=%u\n%s_peak_delta_bytes=%u\n",
            pool, peak->initial_free, pool, peak->min_free, pool, memory_peak_used(peak));
}

static void report_stick(FILE *out, const char *name, const StickRange *range)
{
    fprintf(out, "%s_x=%u..%u %s_y=%u..%u %s_exercised=%d\n", name,
            (unsigned)range->min_x, (unsigned)range->max_x, name,
            (unsigned)range->min_y, (unsigned)range->max_y, name,
            stick_range_exercised(range));
}

static bool write_report(const FrameTimes *times, const StickRange *left,
                         const StickRange *right, const MemoryPeak *main_mem,
                         const MemoryPeak *cdram, bool memory_valid)
{
    SceKernelSystemSwVersion version = {.size = sizeof(version)};
    int fw_result = sceKernelGetSystemSwVersion(&version);
    FILE *out = fopen(report_path, "w");
    if (!out)
        return false;
    fprintf(out, "firmware=%.28s model_code=%d\n", fw_result < 0 ? "unknown" : version.versionString,
            sceKernelGetModel());
    fprintf(out, "arm_mhz=%d bus_mhz=%d gpu_mhz=%d xbar_mhz=%d\n",
            scePowerGetArmClockFrequency(), scePowerGetBusClockFrequency(),
            scePowerGetGpuClockFrequency(), scePowerGetGpuXbarClockFrequency());
    fprintf(out, "frames=%" PRIu64 " min_us=%" PRIu64 " mean_us=%" PRIu64 " max_us=%" PRIu64 "\n",
            times->count, times->min_us, times->total_us / times->count, times->max_us);
    report_stick(out, "left", left);
    report_stick(out, "right", right);
    fprintf(out, "main_newlib_reserved_bytes=%u cdram_framebuffer_bytes=%u\n",
            _newlib_heap_size_user, (unsigned)BUFFER_BYTES);
    if (memory_valid) {
        report_memory(out, "main", main_mem);
        report_memory(out, "cdram", cdram);
    } else {
        fputs("memory_query_failed\n", out);
    }
    bool written = !ferror(out);
    return fclose(out) == 0 && written;
}

static void rect(uint32_t *pixels, int x, int y, int w, int h, uint32_t color)
{
    for (int row = y; row < y + h; row++)
        for (int col = x; col < x + w; col++)
            pixels[row * PITCH + col] = color;
}

static void draw_stick(uint32_t *pixels, int x, uint8_t sx, uint8_t sy, bool exercised)
{
    rect(pixels, x, 144, 256, 256, exercised ? 0xff346328 : 0xff504740);
    rect(pixels, x + 127, 144, 2, 256, 0xff908880);
    rect(pixels, x, 271, 256, 2, 0xff908880);
    rect(pixels, x + sx - 6, 144 + sy - 6, 13, 13, 0xfff8f0e8);
}

int main(void)
{
    mkdir(report_dir, 0777);
    SceKernelFreeMemorySizeInfo info = free_memory();
    bool memory_valid = info.size_user >= 0 && info.size_cdram >= 0;
    MemoryPeak main_mem = memory_peak_start(memory_valid ? (unsigned)info.size_user : 0);
    MemoryPeak cdram = memory_peak_start(memory_valid ? (unsigned)info.size_cdram : 0);
    SceUID block = sceKernelAllocMemBlock("smoke-display", SCE_KERNEL_MEMBLOCK_TYPE_USER_CDRAM_RW,
                                          BUFFER_BYTES, NULL);
    void *buffers;
    if (block < 0 || sceKernelGetMemBlockBase(block, &buffers) < 0 ||
        sceCtrlSetSamplingMode(SCE_CTRL_MODE_ANALOG_WIDE) < 0)
        return 1;

    FrameTimes times = {0};
    StickRange left = {0}, right = {0};
    unsigned back = 0;
    uint32_t previous_buttons = 0;
    uint64_t previous_frame = 0;
    bool saved = false, save_failed = false;
    SceCtrlData pad = {.lx = 128, .ly = 128, .rx = 128, .ry = 128};
    for (;;) {
        SceCtrlData sample;
        int samples = sceCtrlPeekBufferPositive(0, &sample, 1);
        if (samples < 0)
            return 1;
        if (samples > 0) {
            pad = sample;
            stick_range_add(&left, pad.lx, pad.ly);
            stick_range_add(&right, pad.rx, pad.ry);
        }
        if (pad.buttons & SCE_CTRL_START)
            break;
        if (memory_valid) {
            info = free_memory();
            memory_valid = info.size_user >= 0 && info.size_cdram >= 0;
            if (memory_valid) {
                memory_peak_sample(&main_mem, (unsigned)info.size_user);
                memory_peak_sample(&cdram, (unsigned)info.size_cdram);
            }
        }
        uint32_t *pixels = (uint32_t *)((char *)buffers + back * FRAME_BYTES);
        rect(pixels, 0, 0, WIDTH, HEIGHT, 0xff201810);
        draw_stick(pixels, 112, pad.lx, pad.ly, stick_range_exercised(&left));
        draw_stick(pixels, 592, pad.rx, pad.ry, stick_range_exercised(&right));
        if (saved || save_failed)
            rect(pixels, 368, 448, 224, 12, saved ? 0xff64e05a : 0xff4040e0);
        SceDisplayFrameBuf frame = {
            .size = sizeof(frame), .base = pixels, .pitch = PITCH,
            .pixelformat = SCE_DISPLAY_PIXELFORMAT_A8B8G8R8, .width = WIDTH, .height = HEIGHT,
        };
        if (sceDisplaySetFrameBuf(&frame, SCE_DISPLAY_SETBUF_NEXTFRAME) < 0 ||
            sceDisplayWaitVblankStart() < 0)
            return 1;
        back ^= 1;
        uint64_t now = sceKernelGetProcessTimeWide();
        if (previous_frame)
            frame_times_add(&times, now - previous_frame);
        previous_frame = now;
        if (times.count && (pad.buttons & ~previous_buttons & SCE_CTRL_CROSS)) {
            saved = write_report(&times, &left, &right, &main_mem, &cdram, memory_valid);
            save_failed = !saved;
            previous_frame = 0;
        }
        previous_buttons = pad.buttons;
    }
    return 0;
}
