#ifndef COMBAT_RENDER_H
#define COMBAT_RENDER_H

#include "combat.h"

typedef enum { SCREEN_TITLE, SCREEN_BENCHMARK, SCREEN_RUN } CombatScreen;

typedef struct {
    CombatScreen screen;
    unsigned count, choice;
    bool scattered;
} CombatView;

bool render_init(void);
void render_frame(const Combat *game, const CombatView *view);
void render_end(void);

#endif
