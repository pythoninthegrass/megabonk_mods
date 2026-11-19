#ifndef CHARACTER_H
#define CHARACTER_H

#include <stdbool.h>

typedef struct {
    const char *name;
    float damage, knockback, crit_chance, attack_duration, max_duration, projectile_speed;
    float end_cooldown, burst_time, min_burst_interval, spawn_range;
    unsigned projectiles, bounces;
    bool can_bounce, only_when_enemies_close;
} CombatWeapon;

typedef struct {
    const char *name;
    int max_health_flat;
    float shield, move_speed_addition, pickup_range;
    CombatWeapon weapon;
} CombatCharacter;

extern const CombatCharacter COMBAT_TONY_MCZOOM;

unsigned combat_character_health(const CombatCharacter *character);
float combat_character_speed_scale(const CombatCharacter *character);

#endif
