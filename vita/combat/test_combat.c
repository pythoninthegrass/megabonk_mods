#include "character.h"
#include "combat.h"
#include "upgrades.h"

#include <assert.h>
#include <math.h>
#include <string.h>

static void movement_and_aim(void)
{
    Combat game;
    combat_start(&game);
    assert(game.live > 0);
    combat_tick(&game, (CombatInput){.move = {1, 1}, .aim = {-1, 0}});
    assert(game.player.x > 0 && game.player.z > 0);
    assert(fabsf(hypotf(game.player.x, game.player.z) - 0.13f) < 0.001f);
    assert(game.aim.x == -1 && game.aim.z == 0);
    combat_tick(&game, (CombatInput){0});
    assert(game.aim.x == -1 && game.aim.z == 0);
    assert(combat_axis(128) == 0 && combat_axis(140) == 0);
    assert(combat_axis(0) == -1 && combat_axis(255) == 1);
}

static void fight_and_upgrade(void)
{
    Combat game;
    combat_start(&game);
    for (int kill = 0; kill < COMBAT_XP_PER_LEVEL; ++kill) {
        game.enemies[0] = (CombatEnemy){.position = {0, -2}, .hp = 1};
        game.cooldown = 0;
        combat_tick(&game, (CombatInput){0});
        assert(game.enemies[0].hp == 0);
        assert(game.xp == kill && game.drops[0].active);
        game.player = game.drops[0].position;
        combat_tick(&game, (CombatInput){0});
        assert(!game.drops[0].active);
        game.player = (CombatVec){0, 0};
    }
    assert(game.phase == COMBAT_UPGRADE && game.offer_count == UPGRADE_OFFERS);
    unsigned ticks = game.ticks;
    combat_tick(&game, (CombatInput){.move = {1, 0}});
    assert(game.ticks == ticks && game.player.x == 0);
    assert(!combat_choose(&game, UPGRADE_OFFERS));
    game.offers[0] = (UpgradeOffer){.id = UPGRADE_TOME_COOLDOWN, .modifier_count = 1,
        .modifiers = {{STAT_ATTACK_SPEED, MODIFY_ADDITION, 0.075f}}};
    assert(combat_choose(&game, 0));
    assert(!combat_choose(&game, 0));
    assert(game.upgrades.level[UPGRADE_TOME_COOLDOWN] == 1 && game.interval == 17);
    assert(game.level == 2 && game.xp == 0 && game.phase == COMBAT_PLAY);
    combat_tick(&game, (CombatInput){.move = {1, 0}});
    assert(game.ticks == ticks + 1 && game.player.x > 0);
}

static void stat_effects(void)
{
    Combat game;
    combat_start(&game);
    assert(game.interval == 18 && fabsf(game.pickup_radius_squared - 1.44f) < 0.001f);
    game.phase = COMBAT_UPGRADE;
    game.offers[0] = (UpgradeOffer){.id = UPGRADE_TOME_AGILITY, .modifier_count = 1,
        .modifiers = {{STAT_MOVE_SPEED, MODIFY_ADDITION, 0.15f}}};
    game.offer_count = 1;
    assert(combat_choose(&game, 0));
    combat_tick(&game, (CombatInput){.move = {1, 0}});
    assert(fabsf(game.player.x - 0.145f) < 0.001f);
    game.phase = COMBAT_UPGRADE;
    game.offers[0] = (UpgradeOffer){.id = UPGRADE_TOME_COOLDOWN, .rarity = RARITY_LEGENDARY, .modifier_count = 1,
        .modifiers = {{STAT_ATTACK_SPEED, MODIFY_ADDITION, 10}}};
    assert(combat_choose(&game, 0));
    assert(game.interval == 6);
}

static void benchmark_layouts(void)
{
    Combat normal, gathered, scattered, reset;
    combat_start(&normal);
    assert(!normal.benchmark);
    assert(!combat_choose(&normal, 0));
    assert(!combat_benchmark(&gathered, 0, false));
    assert(!combat_benchmark(&gathered, COMBAT_CAPACITY + 1, false));
    assert(combat_benchmark(&gathered, COMBAT_CAPACITY, false));
    assert(combat_benchmark(&scattered, COMBAT_CAPACITY, true));
    assert(combat_benchmark(&reset, COMBAT_CAPACITY, false));
    assert(gathered.benchmark && scattered.benchmark);
    assert(gathered.live == COMBAT_CAPACITY && scattered.live == COMBAT_CAPACITY);
    for (unsigned i = 0; i < gathered.live; ++i) {
        CombatVec a = gathered.enemies[i].position;
        CombatVec b = scattered.enemies[i].position;
        assert(a.x == reset.enemies[i].position.x && a.z == reset.enemies[i].position.z);
        assert(a.x == b.x / 3 && a.z == b.z / 3);
        assert(gathered.enemies[i].hp == scattered.enemies[i].hp);
    }
    assert(gathered.enemies[0].position.x != gathered.enemies[1].position.x);
    CombatVec before = gathered.enemies[0].position;
    combat_tick(&gathered, (CombatInput){0});
    assert(gathered.enemies[0].position.x != before.x);
    assert(gathered.live == COMBAT_CAPACITY);
    assert(combat_benchmark(&reset, 24, true) && reset.live == 24);
    reset.enemies[0] = (CombatEnemy){.position = {0, -2}, .hp = 1};
    combat_tick(&reset, (CombatInput){0});
    assert(reset.live == 24 && reset.enemies[0].hp > 0 && !reset.drops[0].active);
}

static void boss_opens_portal(void)
{
    Combat game;
    combat_start(&game);
    game.spawner = (CombatVec){0, -6};
    assert(!combat_interact(&game) && !game.boss_spawned);
    game.player = (CombatVec){0, -5};
    assert(combat_interact(&game) && game.boss_spawned);
    assert(!combat_interact(&game));
    unsigned boss = COMBAT_CAPACITY;
    for (unsigned i = 0; i < COMBAT_CAPACITY; ++i)
        if (game.enemies[i].hp && game.enemies[i].kind == COMBAT_ENEMY_BOSS)
            boss = i;
    assert(boss < COMBAT_CAPACITY && game.enemies[boss].hp > 1);
    game.enemies[boss] = (CombatEnemy){.position = {0, -8}, .hp = 1, .kind = COMBAT_ENEMY_BOSS};
    game.player = (CombatVec){0, -5};
    game.aim = (CombatVec){0, -1};
    game.cooldown = 0;
    game.drops[5] = (CombatDrop){{3, 3}, true};
    combat_tick(&game, (CombatInput){0});
    assert(!game.drops[5].active && game.xp == 1);
    assert(game.enemies[boss].hp == 0 && game.boss_defeated && game.portal_open);
    assert(game.phase == COMBAT_PLAY && !game.final_swarm);
    assert(game.ticks == COMBAT_STAGE_TICKS - COMBAT_BOSS_GRACE_TICKS);
    unsigned ticks = game.ticks;
    combat_tick(&game, (CombatInput){.move = {1, 0}});
    assert(game.ticks == ticks + 1);
    game.health = 100000;
    for (unsigned i = 0; i < COMBAT_CAPACITY; ++i)
        game.enemies[i] = (CombatEnemy){0};
    game.live = 0;
    for (unsigned i = 0; i < COMBAT_BOSS_GRACE_TICKS - 61; ++i)
        combat_tick(&game, (CombatInput){0});
    assert(game.live == 0 && !game.final_swarm);
    for (unsigned i = 0; i < 60; ++i)
        combat_tick(&game, (CombatInput){0});
    assert(game.final_swarm && game.swarm_ticks == 0 && game.live > 0);
    combat_start(&game);
    assert(game.phase == COMBAT_PLAY && !game.boss_spawned);
}

static void final_swarm_restarts_clock(void)
{
    Combat game;
    combat_start(&game);
    game.health = 100000;
    game.ticks = COMBAT_STAGE_TICKS - 2;
    assert(combat_timer_ticks(&game) == COMBAT_STAGE_TICKS - 2);
    combat_tick(&game, (CombatInput){0});
    assert(!game.final_swarm && combat_timer_ticks(&game) == COMBAT_STAGE_TICKS - 1);
    combat_tick(&game, (CombatInput){0});
    assert(game.final_swarm && game.swarm_ticks == 0 && combat_timer_ticks(&game) == 0);
    for (unsigned i = 0; i < COMBAT_HZ; ++i)
        combat_tick(&game, (CombatInput){0});
    assert(combat_timer_ticks(&game) == COMBAT_HZ);
    assert(game.live >= 40);
    for (unsigned i = 0; i < COMBAT_CAPACITY; ++i)
        if (game.enemies[i].hp && i >= 20)
            assert(game.enemies[i].kind == COMBAT_ENEMY_GHOST);
    unsigned fresh = game.live;
    for (unsigned i = 0; i < 40 * COMBAT_HZ; ++i)
        combat_tick(&game, (CombatInput){0});
    assert(game.live > fresh || game.live >= 200);
    combat_start(&game);
    assert(!game.final_swarm && game.swarm_ticks == 0);
}

static void swarm_spawn_at(Combat *game, unsigned seconds)
{
    combat_start(game);
    game->health = 100000;
    for (unsigned i = 0; i < COMBAT_CAPACITY; ++i)
        game->enemies[i] = (CombatEnemy){0};
    game->live = 0;
    game->final_swarm = true;
    game->ticks = COMBAT_STAGE_TICKS;
    game->swarm_ticks = seconds * COMBAT_HZ - 1;
    combat_tick(game, (CombatInput){0});
}

static unsigned swarm_hp_at(unsigned seconds)
{
    Combat game;
    swarm_spawn_at(&game, seconds);
    assert(game.live > 0);
    return game.enemies[0].hp;
}

static void swarm_ghost_tiers_and_growth(void)
{
    const struct { unsigned seconds; CombatEnemyKind kind; } tiers[] = {
        {1, COMBAT_ENEMY_GHOST}, {61, COMBAT_ENEMY_GREATER_GHOST},
        {361, COMBAT_ENEMY_GHOST_PURPLE}, {721, COMBAT_ENEMY_GHOST_RED},
    };
    for (unsigned t = 0; t < 4; ++t) {
        Combat game;
        swarm_spawn_at(&game, tiers[t].seconds);
        assert(game.live > 0);
        for (unsigned i = 0; i < COMBAT_CAPACITY; ++i)
            if (game.enemies[i].hp)
                assert(game.enemies[i].kind == tiers[t].kind);
    }
    assert(swarm_hp_at(30) == 3);
    assert(swarm_hp_at(60) == 6);
}

static void defeat_then_restart(void)
{
    Combat game;
    combat_start(&game);
    game.health = 1;
    game.enemies[0] = (CombatEnemy){.position = {0, 0}, .hp = 1};
    combat_tick(&game, (CombatInput){0});
    assert(game.phase == COMBAT_DEFEAT);
    combat_start(&game);
    assert(game.phase == COMBAT_PLAY && game.health == 6 && game.kills == 0);
}

static void clock_and_prompt(void)
{
    char text[16];
    combat_format_clock(0, text, sizeof text);
    assert(!strcmp(text, "0:00"));
    combat_format_clock(61 * COMBAT_HZ + 59, text, sizeof text);
    assert(!strcmp(text, "1:01"));
    combat_format_clock(600 * COMBAT_HZ, text, sizeof text);
    assert(!strcmp(text, "10:00"));
    Combat game;
    combat_start(&game);
    assert(!combat_can_interact(&game));
    game.player = game.spawner;
    assert(combat_can_interact(&game));
    assert(combat_interact(&game) && !combat_can_interact(&game));
}

static void portal_exit(void)
{
    Combat game;
    combat_start(&game);
    game.player = game.spawner;
    assert(!combat_can_exit(&game) && !combat_exit(&game));
    game.portal_open = true;
    game.player = (CombatVec){0, 0};
    assert(!combat_can_exit(&game) && !combat_exit(&game));
    game.player = game.spawner;
    assert(combat_can_exit(&game) && combat_exit(&game));
    assert(game.phase == COMBAT_EXITED && !combat_can_exit(&game) && !combat_exit(&game));
    unsigned ticks = game.ticks;
    combat_tick(&game, (CombatInput){.move = {1, 0}});
    assert(game.ticks == ticks);
    combat_start(&game);
    assert(game.phase == COMBAT_PLAY && !game.portal_open);
}

static void tony_mczoom_data(void)
{
    const CombatCharacter *tony = &COMBAT_TONY_MCZOOM;
    assert(!strcmp(tony->name, "Tony McZoom"));
    assert(combat_character_health(tony) == 70);
    assert(fabsf(combat_character_speed_scale(tony) - 1.3f) < 0.0001f);
    assert(tony->shield == 10 && tony->pickup_range == 3);
    const CombatWeapon *weapon = &tony->weapon;
    assert(!strcmp(weapon->name, "Wireless Dagger"));
    assert(weapon->damage == 9 && weapon->knockback == 0.4f && weapon->crit_chance == 0);
    assert(weapon->projectiles == 1 && weapon->bounces == 1 && weapon->can_bounce);
    assert(weapon->attack_duration == 2.5f && weapon->max_duration == 8);
    assert(weapon->projectile_speed == 0.75f && weapon->end_cooldown == 0.5f);
    assert(weapon->burst_time == 1.1f && weapon->min_burst_interval == 0.02f);
    assert(weapon->spawn_range == 40 && weapon->only_when_enemies_close);
    Combat game;
    combat_start(&game);
    assert(game.character == tony);
}

int main(void)
{
    stat_effects();
    tony_mczoom_data();
    portal_exit();
    clock_and_prompt();
    boss_opens_portal();
    final_swarm_restarts_clock();
    swarm_ghost_tiers_and_growth();
    defeat_then_restart();
    movement_and_aim();
    fight_and_upgrade();
    benchmark_layouts();
}
