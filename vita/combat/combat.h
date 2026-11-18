#ifndef COMBAT_H
#define COMBAT_H

#include <stdbool.h>
#include <stdint.h>

enum { COMBAT_HZ = 60, COMBAT_CAPACITY = 240, COMBAT_XP_PER_LEVEL = 4, COMBAT_ARENA = 40 };

typedef struct { float x, z; } CombatVec;
typedef struct { CombatVec move, aim; } CombatInput;
typedef struct { CombatVec position; unsigned hp; } CombatEnemy;
typedef struct { CombatVec position; bool active; } CombatDrop;
typedef enum { COMBAT_PLAY, COMBAT_UPGRADE, COMBAT_DEFEAT } CombatPhase;
typedef enum { COMBAT_POWER, COMBAT_HASTE, COMBAT_UPGRADE_COUNT } CombatUpgrade;

typedef struct {
    CombatEnemy enemies[COMBAT_CAPACITY];
    CombatDrop drops[COMBAT_CAPACITY];
    CombatVec player, aim, shot_end;
    CombatPhase phase;
    unsigned ticks, live, damage, interval, cooldown, shot_ticks, hit_cooldown, health;
    int xp;
    unsigned level, kills, spawn_index;
    bool benchmark, scattered;
} Combat;

float combat_axis(uint8_t raw);
void combat_start(Combat *game);
bool combat_benchmark(Combat *game, unsigned count, bool scattered);
void combat_tick(Combat *game, CombatInput input);
bool combat_choose(Combat *game, CombatUpgrade choice);

#endif
