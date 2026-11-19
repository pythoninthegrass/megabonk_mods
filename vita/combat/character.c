#include "character.h"

enum { BASE_MAX_HEALTH = 100 };

const CombatCharacter COMBAT_TONY_MCZOOM = {
    .name = "Tony McZoom",
    .max_health_flat = -30,
    .shield = 10,
    .move_speed_addition = 0.3f,
    .pickup_range = 3,
    .weapon = {
        .name = "Wireless Dagger",
        .damage = 9,
        .knockback = 0.4f,
        .attack_duration = 2.5f,
        .max_duration = 8,
        .projectile_speed = 0.75f,
        .end_cooldown = 0.5f,
        .burst_time = 1.1f,
        .min_burst_interval = 0.02f,
        .spawn_range = 40,
        .projectiles = 1,
        .bounces = 1,
        .can_bounce = true,
        .only_when_enemies_close = true,
    },
};

unsigned combat_character_health(const CombatCharacter *character)
{
    return (unsigned)(BASE_MAX_HEALTH + character->max_health_flat);
}

float combat_character_speed_scale(const CombatCharacter *character)
{
    return 1 + character->move_speed_addition;
}
