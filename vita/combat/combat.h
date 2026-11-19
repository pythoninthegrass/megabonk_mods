#ifndef COMBAT_H
#define COMBAT_H

#include <stdbool.h>
#include <stdint.h>

enum { COMBAT_HZ = 60, COMBAT_CAPACITY = 240, COMBAT_XP_PER_LEVEL = 4, COMBAT_ARENA = 40, COMBAT_BOSS_HP = 60, COMBAT_STAGE_TICKS = 600 * COMBAT_HZ,
       COMBAT_BOSS_GRACE_TICKS = 10 * COMBAT_HZ };

typedef struct { float x, z; } CombatVec;
typedef struct { CombatVec move, aim; } CombatInput;
typedef enum { COMBAT_ENEMY_NORMAL, COMBAT_ENEMY_BOSS, COMBAT_ENEMY_GHOST, COMBAT_ENEMY_GREATER_GHOST,
    COMBAT_ENEMY_GHOST_PURPLE, COMBAT_ENEMY_GHOST_RED } CombatEnemyKind;
typedef struct { CombatVec position; unsigned hp; CombatEnemyKind kind; } CombatEnemy;
typedef struct { CombatVec position; bool active; } CombatDrop;
typedef enum { COMBAT_PLAY, COMBAT_UPGRADE, COMBAT_DEFEAT, COMBAT_EXITED } CombatPhase;
typedef enum { COMBAT_POWER, COMBAT_HASTE, COMBAT_UPGRADE_COUNT } CombatUpgrade;

typedef struct {
    CombatEnemy enemies[COMBAT_CAPACITY];
    CombatDrop drops[COMBAT_CAPACITY];
    CombatVec player, aim, shot_end, spawner;
    CombatPhase phase;
    unsigned swarm_ticks, ticks, live, damage, interval, cooldown, shot_ticks, hit_cooldown, health;
    int xp;
    unsigned level, kills, spawn_index;
    bool benchmark, scattered, boss_spawned, boss_defeated, portal_open, final_swarm;
} Combat;

float combat_axis(uint8_t raw);
void combat_start(Combat *game);
bool combat_benchmark(Combat *game, unsigned count, bool scattered);
void combat_tick(Combat *game, CombatInput input);
unsigned combat_timer_ticks(const Combat *game);
bool combat_can_interact(const Combat *game);
bool combat_interact(Combat *game);
bool combat_can_exit(const Combat *game);
bool combat_exit(Combat *game);
void combat_format_clock(unsigned ticks, char *out, unsigned size);
bool combat_choose(Combat *game, CombatUpgrade choice);

#endif
