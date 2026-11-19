#ifndef COMBAT_SWEEP_H
#define COMBAT_SWEEP_H

#include "combat.h"

void sweep_memory_baseline(void);
bool sweep_start(Combat *game, bool gate);
bool sweep_active(void);
void sweep_cancel(void);
void sweep_update(Combat *game);
const char *sweep_status(void);

#endif
