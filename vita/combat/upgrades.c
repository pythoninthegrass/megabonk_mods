#include "upgrades.h"

#include <math.h>
#include <stdio.h>

typedef struct { const char *name; UpgradeModifier tome; } TomeEntry;

static const float BASE_STATS[] = {
    100, 10, 0, 0, 0, 0.01f, 0, 0, 1, 1, 1, 1, 1, 0, 0,
    1, 0, 0, 0.01f, 1, 1, 1, 1, 1, 1, 1, 7, 0, 0, 5,
    0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0,
    0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1,
};

static const TomeEntry TOMES[UPGRADE_COUNT] = {
    [UPGRADE_TOME_AGILITY] = {"Agility Tome", {STAT_MOVE_SPEED, MODIFY_ADDITION, 0.15f}},
    [UPGRADE_TOME_COOLDOWN] = {"Cooldown Tome", {STAT_ATTACK_SPEED, MODIFY_ADDITION, 0.075f}},
    [UPGRADE_TOME_DAMAGE] = {"Damage Tome", {STAT_DAMAGE, MODIFY_MULTIPLICATION, 0.08f}},
    [UPGRADE_TOME_EVASION] = {"Evasion Tome", {STAT_EVASION, MODIFY_FLAT, 0.1f}},
    [UPGRADE_TOME_GOLDEN] = {"Golden Tome", {STAT_GOLD, MODIFY_ADDITION, 0.12f}},
    [UPGRADE_TOME_HEALTH] = {"Health Tome", {STAT_MAX_HEALTH, MODIFY_FLAT, 25}},
    [UPGRADE_TOME_KNOCKBACK] = {"Knockback Tome", {STAT_KNOCKBACK, MODIFY_ADDITION, 0.2f}},
    [UPGRADE_TOME_PRECISION] = {"Precision Tome", {STAT_CRIT_CHANCE, MODIFY_FLAT, 0.07f}},
    [UPGRADE_TOME_PROJECTILE_SPEED] = {"Projectile Speed Tome", {STAT_PROJECTILE_SPEED, MODIFY_ADDITION, 0.15f}},
    [UPGRADE_TOME_REGEN] = {"Regen Tome", {STAT_HEALTH_REGEN, MODIFY_FLAT, 40}},
    [UPGRADE_TOME_SHIELD] = {"Shield Tome", {STAT_SHIELD, MODIFY_FLAT, 25}},
    [UPGRADE_TOME_SILVER] = {"Silver Tome", {STAT_SILVER, MODIFY_ADDITION, 0.12f}},
    [UPGRADE_TOME_SIZE] = {"Size Tome", {STAT_SIZE, MODIFY_ADDITION, 0.1f}},
};

static const UpgradeModifier DAGGER_UPGRADES[UPGRADE_WEAPON_MODIFIERS] = {
    {STAT_DAMAGE, MODIFY_FLAT, 2},
    {STAT_PROJECTILES, MODIFY_FLAT, 1},
    {STAT_PROJECTILE_BOUNCES, MODIFY_FLAT, 1},
    {STAT_PROJECTILE_SPEED, MODIFY_ADDITION, 0.15f},
};

static const float RARITY_MULTIPLIER[RARITY_COUNT] = {1, 1, 1.2f, 1.4f, 1.6f, 2};

const char *upgrade_name(UpgradeId id)
{
    return id == UPGRADE_WIRELESS_DAGGER ? "Wireless Dagger" : TOMES[id].name;
}

bool upgrade_is_tome(UpgradeId id)
{
    return id != UPGRADE_WIRELESS_DAGGER;
}

void upgrades_init(UpgradeState *state)
{
    *state = (UpgradeState){0};
    state->level[UPGRADE_WIRELESS_DAGGER] = 1;
}

float upgrades_rng_unit(UpgradeRng *rng)
{
    uint32_t x = rng->state ? rng->state : 1;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    rng->state = x;
    return (x >> 8) / 16777216.0f;
}

unsigned upgrades_rng_below(UpgradeRng *rng, unsigned limit)
{
    return (unsigned)(upgrades_rng_unit(rng) * limit);
}

void upgrades_rarity_weights(float luck, float weights[RARITY_COUNT - 1])
{
    const float base[RARITY_COUNT - 1] = {1.5f, 0.3f, 0.15f, 0.04f, 0.0085f};
    const float scaled_luck = logf(luck + 1) * -1.5f;
    float total = 0;
    for (unsigned i = 0; i < RARITY_COUNT - 1; ++i) {
        weights[i] = base[i] * powf(1.5f, (RARITY_COUNT - 2 - i) * scaled_luck);
        total += weights[i];
    }
    for (unsigned i = 0; i < RARITY_COUNT - 1; ++i)
        weights[i] /= total;
}

UpgradeRarity upgrades_pick_rarity(float luck, float roll)
{
    float weights[RARITY_COUNT - 1], cumulative = 0;
    upgrades_rarity_weights(luck, weights);
    for (unsigned i = 0; i < RARITY_COUNT - 1; ++i) {
        cumulative += weights[i];
        if (cumulative >= roll)
            return (UpgradeRarity)(RARITY_COMMON + i);
    }
    return RARITY_COMMON;
}

float upgrades_scale(float value, UpgradeRarity rarity)
{
    return roundf(value * RARITY_MULTIPLIER[rarity] * 100) / 100;
}

static unsigned max_level(UpgradeId id)
{
    return upgrade_is_tome(id) ? UPGRADE_TOME_MAX_LEVEL : UPGRADE_WEAPON_MAX_LEVEL;
}

static unsigned owned_tomes(const UpgradeState *state)
{
    unsigned count = 0;
    for (unsigned id = 0; id < UPGRADE_COUNT; ++id)
        if (upgrade_is_tome((UpgradeId)id) && state->level[id])
            ++count;
    return count;
}

static void take(UpgradeId *pool, unsigned *count, unsigned index, UpgradeId *out)
{
    *out = pool[index];
    pool[index] = pool[--*count];
}

static void build_offer(const UpgradeState *state, UpgradeRng *rng, float luck, UpgradeId id, UpgradeOffer *offer)
{
    *offer = (UpgradeOffer){.id = id};
    if (!state->level[id]) {
        offer->modifiers[0] = TOMES[id].tome;
        offer->modifier_count = 1;
        return;
    }
    offer->rarity = upgrades_pick_rarity(luck, upgrades_rng_unit(rng));
    if (upgrade_is_tome(id)) {
        offer->modifiers[0] = TOMES[id].tome;
        offer->modifiers[0].value = upgrades_scale(offer->modifiers[0].value, offer->rarity);
        offer->modifier_count = 1;
        return;
    }
    UpgradeModifier remaining[UPGRADE_WEAPON_MODIFIERS];
    unsigned left = UPGRADE_WEAPON_MODIFIERS;
    for (unsigned i = 0; i < left; ++i)
        remaining[i] = DAGGER_UPGRADES[i];
    const unsigned wanted = offer->rarity == RARITY_COMMON && upgrades_rng_below(rng, 2) != 1 ? 1 : 2;
    for (unsigned i = 0; i < wanted; ++i) {
        const unsigned index = upgrades_rng_below(rng, left);
        UpgradeModifier picked = remaining[index];
        remaining[index] = remaining[--left];
        picked.value = upgrades_scale(picked.value, offer->rarity);
        offer->modifiers[offer->modifier_count++] = picked;
    }
}

unsigned upgrades_roll(const UpgradeState *state, UpgradeRng *rng, float luck, UpgradeOffer offers[UPGRADE_OFFERS])
{
    UpgradeId owned[UPGRADE_COUNT], available[UPGRADE_COUNT];
    unsigned owned_count = 0, available_count = 0;
    const bool tome_slot_free = owned_tomes(state) < UPGRADE_TOME_SLOTS;
    for (unsigned id = 0; id < UPGRADE_COUNT; ++id) {
        const unsigned level = state->level[id];
        if (level >= max_level((UpgradeId)id))
            continue;
        if (level)
            owned[owned_count++] = (UpgradeId)id;
        else if (upgrade_is_tome((UpgradeId)id) && tome_slot_free)
            available[available_count++] = (UpgradeId)id;
    }
    const unsigned total = owned_count + available_count;
    const unsigned count = total < UPGRADE_OFFERS ? total : UPGRADE_OFFERS;
    UpgradeId chosen[UPGRADE_OFFERS];
    for (unsigned i = 0; i < count; ++i) {
        const bool fresh = available_count && (!owned_count || upgrades_rng_unit(rng) >= 1.0f / count);
        if (fresh)
            take(available, &available_count, upgrades_rng_below(rng, available_count), &chosen[i]);
        else
            take(owned, &owned_count, upgrades_rng_below(rng, owned_count), &chosen[i]);
    }
    for (unsigned i = 0; i < count; ++i)
        build_offer(state, rng, luck, chosen[i], &offers[i]);
    return count;
}

static const char *stat_label(UpgradeStat stat)
{
    switch (stat) {
    case STAT_MAX_HEALTH: return "Max Health";
    case STAT_HEALTH_REGEN: return "Health Regen";
    case STAT_SHIELD: return "Shield";
    case STAT_EVASION: return "Evasion";
    case STAT_SIZE: return "Size";
    case STAT_PROJECTILE_SPEED: return "Projectile Speed";
    case STAT_DAMAGE: return "Damage";
    case STAT_ATTACK_SPEED: return "Attack Speed";
    case STAT_PROJECTILES: return "Projectiles";
    case STAT_CRIT_CHANCE: return "Crit Chance";
    case STAT_KNOCKBACK: return "Knockback";
    case STAT_MOVE_SPEED: return "Move Speed";
    case STAT_PICKUP_RANGE: return "Pickup Range";
    case STAT_LUCK: return "Luck";
    case STAT_GOLD: return "Gold Gain";
    case STAT_PROJECTILE_BOUNCES: return "Projectile Bounces";
    case STAT_SILVER: return "Silver Gain";
    default: return "Stat";
    }
}

void upgrades_describe(const UpgradeOffer *offer, char *out, unsigned size)
{
    unsigned used = 0;
    if (size)
        out[0] = 0;
    for (unsigned i = 0; i < offer->modifier_count && used + 1 < size; ++i) {
        const UpgradeModifier *modifier = &offer->modifiers[i];
        const bool percent = modifier->type != MODIFY_FLAT;
        const int written = snprintf(out + used, size - used, "%s+%g%s %s", i ? ", " : "",
                                     percent ? modifier->value * 100 : modifier->value, percent ? "%" : "",
                                     stat_label(modifier->stat));
        if (written < 0)
            return;
        used += (unsigned)written;
    }
}

void upgrades_apply(UpgradeState *state, const UpgradeOffer *offer)
{
    const UpgradeId id = offer->id;
    if (upgrade_is_tome(id) && !state->level[id])
        state->tome_total[id] = TOMES[id].tome.type == MODIFY_MULTIPLICATION ? 1 : 0;
    ++state->level[id];
    for (unsigned i = 0; i < offer->modifier_count; ++i) {
        const UpgradeModifier *modifier = &offer->modifiers[i];
        if (upgrade_is_tome(id))
            state->tome_total[id] += modifier->value;
        else if (modifier->type == MODIFY_FLAT)
            state->weapon_flat[modifier->stat] += modifier->value;
        else if (modifier->type == MODIFY_ADDITION)
            state->weapon_addition[modifier->stat] += modifier->value;
    }
}

static void accumulate(UpgradeModify type, float value, float *flat, float *addition, float *multiplication)
{
    if (type == MODIFY_FLAT)
        *flat += value;
    else if (type == MODIFY_ADDITION)
        *addition += value;
    else
        *multiplication *= value;
}

float upgrades_stat(const UpgradeState *state, const CombatCharacter *character, UpgradeStat stat)
{
    float flat = 0, addition = 0, multiplication = 1;
    if (stat == STAT_MAX_HEALTH)
        flat += character->max_health_flat;
    else if (stat == STAT_SHIELD)
        flat += character->shield;
    else if (stat == STAT_MOVE_SPEED)
        addition += character->move_speed_addition;
    else if (stat == STAT_PICKUP_RANGE)
        flat += character->pickup_range;
    for (unsigned id = 0; id < UPGRADE_COUNT; ++id)
        if (upgrade_is_tome((UpgradeId)id) && state->level[id] && TOMES[id].tome.stat == stat)
            accumulate(TOMES[id].tome.type, state->tome_total[id], &flat, &addition, &multiplication);
    const float base = (unsigned)stat < sizeof BASE_STATS / sizeof *BASE_STATS ? BASE_STATS[stat] : 0;
    return (base + flat) * (1 + addition) * multiplication;
}
