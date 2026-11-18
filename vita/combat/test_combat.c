#include "combat.h"

#include <assert.h>
#include <math.h>

static void movement_and_aim(void)
{
    Combat game;
    combat_start(&game);
    assert(game.live > 0);
    combat_tick(&game, (CombatInput){.move = {1, 1}, .aim = {-1, 0}});
    assert(game.player.x > 0 && game.player.z > 0);
    assert(fabsf(hypotf(game.player.x, game.player.z) - 0.10f) < 0.001f);
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
    assert(game.phase == COMBAT_UPGRADE);
    unsigned ticks = game.ticks;
    combat_tick(&game, (CombatInput){.move = {1, 0}});
    assert(game.ticks == ticks && game.player.x == 0);
    assert(!combat_choose(&game, COMBAT_UPGRADE_COUNT));
    assert(combat_choose(&game, COMBAT_POWER));
    assert(!combat_choose(&game, COMBAT_POWER));
    assert(game.damage == 2 && game.level == 2 && game.phase == COMBAT_PLAY);
    combat_tick(&game, (CombatInput){.move = {1, 0}});
    assert(game.ticks == ticks + 1 && game.player.x > 0);
}

static void benchmark_layouts(void)
{
    Combat normal, gathered, scattered, reset;
    combat_start(&normal);
    assert(!normal.benchmark);
    assert(!combat_choose(&normal, COMBAT_POWER));
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

int main(void)
{
    movement_and_aim();
    fight_and_upgrade();
    benchmark_layouts();
}
