#ifndef UPGRADES_H
#define UPGRADES_H

#include <stdbool.h>
#include <stdint.h>

#include "character.h"

typedef enum {
    STAT_MAX_HEALTH = 0, STAT_HEALTH_REGEN = 1, STAT_SHIELD = 2, STAT_EVASION = 5, STAT_SIZE = 9,
    STAT_PROJECTILE_SPEED = 11, STAT_DAMAGE = 12, STAT_ATTACK_SPEED = 15, STAT_PROJECTILES = 16,
    STAT_CRIT_CHANCE = 18, STAT_KNOCKBACK = 24, STAT_MOVE_SPEED = 25, STAT_PICKUP_RANGE = 29,
    STAT_LUCK = 30, STAT_GOLD = 31, STAT_PROJECTILE_BOUNCES = 45, STAT_SILVER = 49, STAT_COUNT = 50
} UpgradeStat;
typedef enum { MODIFY_ADDITION, MODIFY_MULTIPLICATION, MODIFY_FLAT } UpgradeModify;
typedef enum { RARITY_NEW, RARITY_COMMON, RARITY_UNCOMMON, RARITY_RARE, RARITY_EPIC, RARITY_LEGENDARY,
    RARITY_COUNT } UpgradeRarity;
typedef struct { UpgradeStat stat; UpgradeModify type; float value; } UpgradeModifier;

typedef enum {
    UPGRADE_WIRELESS_DAGGER, UPGRADE_TOME_AGILITY, UPGRADE_TOME_COOLDOWN, UPGRADE_TOME_DAMAGE,
    UPGRADE_TOME_EVASION, UPGRADE_TOME_GOLDEN, UPGRADE_TOME_HEALTH, UPGRADE_TOME_KNOCKBACK,
    UPGRADE_TOME_PRECISION, UPGRADE_TOME_PROJECTILE_SPEED, UPGRADE_TOME_REGEN, UPGRADE_TOME_SHIELD,
    UPGRADE_TOME_SILVER, UPGRADE_TOME_SIZE, UPGRADE_COUNT
} UpgradeId;

enum { UPGRADE_OFFERS = 3, UPGRADE_WEAPON_MODIFIERS = 4, UPGRADE_WEAPON_MAX_LEVEL = 40,
       UPGRADE_TOME_MAX_LEVEL = 99, UPGRADE_TOME_SLOTS = 2 };

typedef struct {
    UpgradeId id;
    UpgradeRarity rarity;
    UpgradeModifier modifiers[UPGRADE_WEAPON_MODIFIERS];
    unsigned modifier_count;
} UpgradeOffer;

typedef struct {
    unsigned level[UPGRADE_COUNT];
    float tome_total[UPGRADE_COUNT];
    float weapon_flat[STAT_COUNT], weapon_addition[STAT_COUNT];
} UpgradeState;

typedef struct { uint32_t state; } UpgradeRng;

const char *upgrade_name(UpgradeId id);
bool upgrade_is_tome(UpgradeId id);
void upgrades_init(UpgradeState *state);
float upgrades_rng_unit(UpgradeRng *rng);
unsigned upgrades_rng_below(UpgradeRng *rng, unsigned limit);
void upgrades_rarity_weights(float luck, float weights[RARITY_COUNT - 1]);
UpgradeRarity upgrades_pick_rarity(float luck, float roll);
float upgrades_scale(float value, UpgradeRarity rarity);
unsigned upgrades_roll(const UpgradeState *state, UpgradeRng *rng, float luck, UpgradeOffer offers[UPGRADE_OFFERS]);
void upgrades_describe(const UpgradeOffer *offer, char *out, unsigned size);
void upgrades_apply(UpgradeState *state, const UpgradeOffer *offer);
float upgrades_stat(const UpgradeState *state, const CombatCharacter *character, UpgradeStat stat);

#endif
