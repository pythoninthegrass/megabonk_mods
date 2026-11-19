#include "upgrades.h"

#include <assert.h>
#include <math.h>
#include <string.h>

static bool near(float a, float b)
{
    return fabsf(a - b) < 0.0001f;
}

static void rarity_weights_and_roll(void)
{
    float weights[5];
    upgrades_rarity_weights(0, weights);
    float total = 0;
    for (unsigned i = 0; i < 5; ++i)
        total += weights[i];
    assert(near(total, 1) && near(weights[0], 1.5f / 1.9985f) && near(weights[4], 0.0085f / 1.9985f));
    upgrades_rarity_weights(2, weights);
    assert(weights[4] > 0.0085f / 1.9985f && weights[0] < 1.5f / 1.9985f);
    assert(upgrades_pick_rarity(0, 0.0f) == RARITY_COMMON);
    assert(upgrades_pick_rarity(0, 0.75f) == RARITY_COMMON);
    assert(upgrades_pick_rarity(0, 0.76f) == RARITY_UNCOMMON);
    assert(upgrades_pick_rarity(0, 0.90f) == RARITY_UNCOMMON);
    assert(upgrades_pick_rarity(0, 0.91f) == RARITY_RARE);
    assert(upgrades_pick_rarity(0, 0.98f) == RARITY_EPIC);
    assert(upgrades_pick_rarity(0, 0.999f) == RARITY_LEGENDARY);
}

static void scaled_modifiers(void)
{
    assert(near(upgrades_scale(0.15f, RARITY_NEW), 0.15f) && near(upgrades_scale(0.15f, RARITY_COMMON), 0.15f));
    assert(near(upgrades_scale(0.15f, RARITY_UNCOMMON), 0.18f) && near(upgrades_scale(0.15f, RARITY_RARE), 0.21f));
    assert(near(upgrades_scale(0.15f, RARITY_EPIC), 0.24f) && near(upgrades_scale(0.15f, RARITY_LEGENDARY), 0.3f));
    assert(near(upgrades_scale(25, RARITY_RARE), 35));
}

static void fresh_state_offers(void)
{
    UpgradeState state;
    upgrades_init(&state);
    assert(state.level[UPGRADE_WIRELESS_DAGGER] == 1);
    assert(!upgrade_is_tome(UPGRADE_WIRELESS_DAGGER) && upgrade_is_tome(UPGRADE_TOME_DAMAGE));
    assert(!strcmp(upgrade_name(UPGRADE_TOME_DAMAGE), "Damage Tome"));
    for (uint32_t seed = 1; seed < 200; ++seed) {
        UpgradeRng rng = {seed};
        UpgradeOffer offers[UPGRADE_OFFERS];
        assert(upgrades_roll(&state, &rng, 0, offers) == UPGRADE_OFFERS);
        for (unsigned i = 0; i < UPGRADE_OFFERS; ++i) {
            for (unsigned j = i + 1; j < UPGRADE_OFFERS; ++j)
                assert(offers[i].id != offers[j].id);
            if (offers[i].id == UPGRADE_WIRELESS_DAGGER) {
                assert(offers[i].rarity >= RARITY_COMMON);
                assert(offers[i].modifier_count == 1 || offers[i].modifier_count == 2);
            } else {
                assert(offers[i].rarity == RARITY_NEW && offers[i].modifier_count == 1);
            }
        }
    }
}

static void applying_offers(void)
{
    UpgradeState state;
    upgrades_init(&state);
    const CombatCharacter *tony = &COMBAT_TONY_MCZOOM;
    assert(near(upgrades_stat(&state, tony, STAT_MOVE_SPEED), 1.3f));
    assert(near(upgrades_stat(&state, tony, STAT_PICKUP_RANGE), 8));
    assert(near(upgrades_stat(&state, tony, STAT_MAX_HEALTH), 70));
    assert(near(upgrades_stat(&state, tony, STAT_DAMAGE), 1));
    UpgradeOffer agility = {.id = UPGRADE_TOME_AGILITY, .rarity = RARITY_NEW, .modifier_count = 1,
        .modifiers = {{STAT_MOVE_SPEED, MODIFY_ADDITION, 0.15f}}};
    upgrades_apply(&state, &agility);
    upgrades_apply(&state, &agility);
    assert(state.level[UPGRADE_TOME_AGILITY] == 2);
    assert(near(upgrades_stat(&state, tony, STAT_MOVE_SPEED), 1.6f));
    UpgradeOffer damage = {.id = UPGRADE_TOME_DAMAGE, .rarity = RARITY_NEW, .modifier_count = 1,
        .modifiers = {{STAT_DAMAGE, MODIFY_MULTIPLICATION, 0.08f}}};
    upgrades_apply(&state, &damage);
    assert(near(upgrades_stat(&state, tony, STAT_DAMAGE), 1.08f));
    upgrades_apply(&state, &damage);
    assert(near(upgrades_stat(&state, tony, STAT_DAMAGE), 1.16f));
    UpgradeOffer dagger = {.id = UPGRADE_WIRELESS_DAGGER, .rarity = RARITY_RARE, .modifier_count = 2,
        .modifiers = {{STAT_DAMAGE, MODIFY_FLAT, 2.8f}, {STAT_PROJECTILES, MODIFY_FLAT, 1.4f}}};
    upgrades_apply(&state, &dagger);
    assert(state.level[UPGRADE_WIRELESS_DAGGER] == 2);
    assert(near(state.weapon_flat[STAT_DAMAGE], 2.8f) && near(state.weapon_flat[STAT_PROJECTILES], 1.4f));
}

static void tome_slots_and_levels(void)
{
    UpgradeState state;
    upgrades_init(&state);
    state.level[UPGRADE_TOME_AGILITY] = 1;
    state.level[UPGRADE_TOME_DAMAGE] = 1;
    for (uint32_t seed = 1; seed < 200; ++seed) {
        UpgradeRng rng = {seed};
        UpgradeOffer offers[UPGRADE_OFFERS];
        unsigned count = upgrades_roll(&state, &rng, 0, offers);
        assert(count == UPGRADE_OFFERS);
        for (unsigned i = 0; i < count; ++i) {
            assert(offers[i].id == UPGRADE_WIRELESS_DAGGER || offers[i].id == UPGRADE_TOME_AGILITY ||
                   offers[i].id == UPGRADE_TOME_DAMAGE);
            if (offers[i].id != UPGRADE_WIRELESS_DAGGER) {
                assert(offers[i].rarity >= RARITY_COMMON && offers[i].modifier_count == 1);
            }
        }
    }
    state.level[UPGRADE_TOME_AGILITY] = UPGRADE_TOME_MAX_LEVEL;
    state.level[UPGRADE_WIRELESS_DAGGER] = UPGRADE_WEAPON_MAX_LEVEL;
    UpgradeRng rng = {7};
    UpgradeOffer offers[UPGRADE_OFFERS];
    assert(upgrades_roll(&state, &rng, 0, offers) == 1 && offers[0].id == UPGRADE_TOME_DAMAGE);
}

static void rng_is_deterministic(void)
{
    UpgradeRng a = {42}, b = {42};
    for (unsigned i = 0; i < 20; ++i) {
        float x = upgrades_rng_unit(&a);
        assert(x == upgrades_rng_unit(&b) && x >= 0 && x < 1);
        assert(upgrades_rng_below(&a, 5) == upgrades_rng_below(&b, 5));
    }
    UpgradeRng zero = {0};
    assert(upgrades_rng_unit(&zero) >= 0);
}

static void descriptions(void)
{
    char text[96];
    UpgradeOffer agility = {.id = UPGRADE_TOME_AGILITY, .modifier_count = 1,
        .modifiers = {{STAT_MOVE_SPEED, MODIFY_ADDITION, 0.15f}}};
    upgrades_describe(&agility, text, sizeof text);
    assert(!strcmp(text, "+15% Move Speed"));
    UpgradeOffer health = {.id = UPGRADE_TOME_HEALTH, .modifier_count = 1,
        .modifiers = {{STAT_MAX_HEALTH, MODIFY_FLAT, 25}}};
    upgrades_describe(&health, text, sizeof text);
    assert(!strcmp(text, "+25 Max Health"));
    UpgradeOffer dagger = {.id = UPGRADE_WIRELESS_DAGGER, .modifier_count = 2,
        .modifiers = {{STAT_DAMAGE, MODIFY_FLAT, 2.8f}, {STAT_PROJECTILES, MODIFY_FLAT, 1}}};
    upgrades_describe(&dagger, text, sizeof text);
    assert(!strcmp(text, "+2.8 Damage, +1 Projectiles"));
    UpgradeOffer damage = {.id = UPGRADE_TOME_DAMAGE, .modifier_count = 1,
        .modifiers = {{STAT_DAMAGE, MODIFY_MULTIPLICATION, 0.08f}}};
    upgrades_describe(&damage, text, sizeof text);
    assert(!strcmp(text, "+8% Damage"));
}

int main(void)
{
    descriptions();
    rarity_weights_and_roll();
    scaled_modifiers();
    fresh_state_offers();
    applying_offers();
    tome_slots_and_levels();
    rng_is_deterministic();
}
