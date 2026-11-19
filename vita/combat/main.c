#include "render.h"
#include "sweep.h"

#include <psp2/ctrl.h>
#include <psp2/kernel/processmgr.h>

enum { TICK_UNITS = 1000000, COUNT_STEP = 24 };

unsigned int _newlib_heap_size_user = 8 * 1024 * 1024;

static Combat game;

static void choose_benchmark(CombatView *view, uint32_t pressed)
{
    if ((pressed & SCE_CTRL_LEFT) && view->count > COUNT_STEP)
        view->count -= COUNT_STEP;
    if ((pressed & SCE_CTRL_RIGHT) && view->count < COMBAT_CAPACITY)
        view->count += COUNT_STEP;
    if (pressed & SCE_CTRL_UP)
        view->scattered = false;
    if (pressed & SCE_CTRL_DOWN)
        view->scattered = true;
    if (pressed & SCE_CTRL_CIRCLE) {
        view->screen = SCREEN_TITLE;
    } else if (pressed & (SCE_CTRL_TRIANGLE | SCE_CTRL_SQUARE)) {
        if (sweep_start(&game, (pressed & SCE_CTRL_SQUARE) != 0))
            view->screen = SCREEN_RUN;
    } else if ((pressed & SCE_CTRL_CROSS) && combat_benchmark(&game, view->count, view->scattered)) {
        sweep_cancel();
        view->screen = SCREEN_RUN;
    }
}

static bool handle_buttons(CombatView *view, uint32_t pressed)
{
    if (pressed & SCE_CTRL_START) {
        if (view->screen == SCREEN_TITLE)
            return false;
        sweep_cancel();
        view->screen = SCREEN_TITLE;
        combat_start(&game);
        return true;
    }
    switch (view->screen) {
    case SCREEN_TITLE:
        if (pressed & SCE_CTRL_TRIANGLE) {
            view->screen = SCREEN_BENCHMARK;
        } else if (pressed & SCE_CTRL_CROSS) {
            combat_start(&game);
            view->screen = SCREEN_RUN;
        }
        break;
    case SCREEN_BENCHMARK:
        choose_benchmark(view, pressed);
        break;
    case SCREEN_RUN:
        if (sweep_active())
            break;
        if (game.benchmark && (pressed & SCE_CTRL_SQUARE)) {
            sweep_cancel();
            combat_benchmark(&game, view->count, view->scattered);
        }
        if (!game.benchmark && (pressed & SCE_CTRL_SQUARE))
            if (!combat_interact(&game))
                combat_exit(&game);
        if ((game.phase == COMBAT_DEFEAT || game.phase == COMBAT_EXITED) && (pressed & SCE_CTRL_CROSS))
            combat_start(&game);
        if (game.phase == COMBAT_UPGRADE) {
            if (pressed & SCE_CTRL_UP)
                view->choice = COMBAT_POWER;
            if (pressed & SCE_CTRL_DOWN)
                view->choice = COMBAT_HASTE;
            if (pressed & SCE_CTRL_CROSS)
                combat_choose(&game, view->choice);
        }
        break;
    }
    return true;
}

int main(void)
{
    sweep_memory_baseline();
    if (sceCtrlSetSamplingMode(SCE_CTRL_MODE_ANALOG_WIDE) < 0 || !render_init())
        return 1;
    CombatView view = {.screen = SCREEN_TITLE, .count = 48};
    combat_start(&game);
    SceCtrlData pad = {.lx = 128, .ly = 128, .rx = 128, .ry = 128};
    uint32_t previous_buttons = 0;
    uint64_t last = sceKernelGetProcessTimeWide();
    unsigned accumulator = 0;
    for (;;) {
        SceCtrlData sample;
        if (sceCtrlPeekBufferPositive(0, &sample, 1) > 0)
            pad = sample;
        uint32_t pressed = pad.buttons & ~previous_buttons;
        previous_buttons = pad.buttons;
        const bool was_running = view.screen == SCREEN_RUN && game.phase == COMBAT_PLAY;
        const unsigned previous_tick = game.ticks;
        if (!handle_buttons(&view, pressed))
            break;
        uint64_t now = sceKernelGetProcessTimeWide(), elapsed = now - last;
        last = now;
        if (was_running && view.screen == SCREEN_RUN && game.ticks == previous_tick) {
            const CombatInput input = sweep_active() ? (CombatInput){0} : (CombatInput){
                .move = {combat_axis(pad.lx), combat_axis(pad.ly)},
                .aim = {combat_axis(pad.rx), combat_axis(pad.ry)},
            };
            accumulator += (elapsed > 100000 ? 100000 : (unsigned)elapsed) * COMBAT_HZ;
            while (accumulator >= TICK_UNITS && game.phase == COMBAT_PLAY) {
                accumulator -= TICK_UNITS;
                combat_tick(&game, input);
                if (game.phase == COMBAT_UPGRADE)
                    view.choice = COMBAT_POWER;
            }
        } else {
            accumulator = 0;
        }
        sweep_update(&game);
        if (game.ticks < previous_tick)
            accumulator = 0;
        render_frame(&game, &view);
    }
    render_end();
    return 0;
}
