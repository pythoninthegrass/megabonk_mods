#include "combat.h"

#include <math.h>
#include <stdio.h>

static CombatVec subtract(CombatVec a, CombatVec b)
{
    return (CombatVec){a.x - b.x, a.z - b.z};
}

static float length_squared(CombatVec v)
{
    return v.x * v.x + v.z * v.z;
}

static CombatVec scale(CombatVec v, float factor)
{
    return (CombatVec){v.x * factor, v.z * factor};
}

static void advance(CombatVec *p, CombatVec direction, float amount)
{
    p->x += direction.x * amount;
    p->z += direction.z * amount;
}

static const float PLAYER_SPEED = 0.1f;

float combat_axis(uint8_t raw)
{
    const int offset = (int)raw - 128;
    if (offset < -16)
        return (offset + 16) / 112.0f;
    if (offset > 16)
        return (offset - 16) / 111.0f;
    return 0;
}

static const float BASE_INTERVAL = 18;
static const float PICKUP_UNITS_PER_STAT = 0.15f;
static const unsigned MIN_INTERVAL = 6;

static void refresh_stats(Combat *game)
{
    const float attack_speed = upgrades_stat(&game->upgrades, game->character, STAT_ATTACK_SPEED);
    const unsigned interval = (unsigned)lroundf(BASE_INTERVAL / attack_speed);
    game->interval = interval < MIN_INTERVAL ? MIN_INTERVAL : interval;
    const float radius = upgrades_stat(&game->upgrades, game->character, STAT_PICKUP_RANGE) * PICKUP_UNITS_PER_STAT;
    game->pickup_radius_squared = radius * radius;
}

static void initialize(Combat *game)
{
    const uint32_t seed = game->rng.state;
    *game = (Combat){.character = &COMBAT_TONY_MCZOOM, .aim = {0, -1}, .spawner = {0, -14}, .damage = 1, .health = 6, .level = 1,
                     .rng = {seed}};
    upgrades_init(&game->upgrades);
    refresh_stats(game);
}

void combat_seed(Combat *game, uint32_t seed)
{
    game->rng.state = seed;
}

static void open_upgrade_menu(Combat *game)
{
    game->phase = COMBAT_UPGRADE;
    const float luck = upgrades_stat(&game->upgrades, game->character, STAT_LUCK);
    game->offer_count = upgrades_roll(&game->upgrades, &game->rng, luck, game->offers);
}

static CombatVec benchmark_position(unsigned i, bool scattered)
{
    CombatVec position = {(float)((int)(i % 16) - 7), (float)((int)(i / 16) - 15)};
    return scale(position, scattered ? 2.25f : 0.75f);
}

static bool spawn_enemy(Combat *game, unsigned hp, CombatEnemyKind kind)
{
    for (unsigned i = 0; i < COMBAT_CAPACITY; ++i) {
        if (game->enemies[i].hp)
            continue;
        const unsigned index = game->spawn_index++;
        const float angle = index * 2.399963f;
        game->enemies[i] = (CombatEnemy){{sinf(angle) * 9, -cosf(angle) * 9}, hp, kind};
        ++game->live;
        return true;
    }
    return false;
}

static void spawn(Combat *game)
{
    spawn_enemy(game, game->spawn_index % 4 == 3 ? 2 : 1, COMBAT_ENEMY_NORMAL);
}

static CombatEnemyKind ghost_kind(unsigned seconds)
{
    if (seconds > 720)
        return COMBAT_ENEMY_GHOST_RED;
    if (seconds > 360)
        return COMBAT_ENEMY_GHOST_PURPLE;
    return seconds > 60 ? COMBAT_ENEMY_GREATER_GHOST : COMBAT_ENEMY_GHOST;
}

static unsigned ghost_hp(unsigned seconds)
{
    const float hp = ceilf(1.3f * exp2f(fminf(seconds / 30.0f, 20.0f)));
    return (unsigned)hp;
}

static unsigned swarm_target(unsigned seconds)
{
    const float limit = seconds < 120 ? 400.0f : 300.0f;
    const unsigned target = (unsigned)(50.0f + fminf(seconds * 2.5f, limit));
    return target < COMBAT_CAPACITY ? target : COMBAT_CAPACITY;
}

static void swarm_spawn(Combat *game)
{
    const unsigned seconds = game->swarm_ticks / COMBAT_HZ;
    const unsigned target = swarm_target(seconds);
    while (game->live < target && spawn_enemy(game, ghost_hp(seconds), ghost_kind(seconds)))
        ;
}

static void advance_stage_clock(Combat *game)
{
    if (game->final_swarm)
        ++game->swarm_ticks;
    else if (game->ticks >= COMBAT_STAGE_TICKS)
        game->final_swarm = true;
}

unsigned combat_timer_ticks(const Combat *game)
{
    return game->final_swarm ? game->swarm_ticks : game->ticks;
}

void combat_start(Combat *game)
{
    initialize(game);
    for (unsigned i = 0; i < 20; ++i)
        spawn(game);
}

bool combat_benchmark(Combat *game, unsigned count, bool scattered)
{
    if (!count || count > COMBAT_CAPACITY)
        return false;
    initialize(game);
    game->benchmark = true;
    game->scattered = scattered;
    game->live = count;
    for (unsigned i = 0; i < count; ++i)
        game->enemies[i] = (CombatEnemy){benchmark_position(i, scattered), 1, COMBAT_ENEMY_NORMAL};
    return true;
}

static void drop_xp(Combat *game, CombatVec position)
{
    for (unsigned i = 0; i < COMBAT_CAPACITY; ++i) {
        if (!game->drops[i].active) {
            game->drops[i] = (CombatDrop){position, true};
            return;
        }
    }
}

static void collect_xp(Combat *game)
{
    for (unsigned i = 0; i < COMBAT_CAPACITY; ++i) {
        CombatDrop *drop = &game->drops[i];
        if (drop->active && length_squared(subtract(drop->position, game->player)) < game->pickup_radius_squared) {
            drop->active = false;
            if (++game->xp >= COMBAT_XP_PER_LEVEL) {
                open_upgrade_menu(game);
                return;
            }
        }
    }
}

static void collect_all_xp(Combat *game)
{
    for (unsigned i = 0; i < COMBAT_CAPACITY; ++i) {
        if (game->drops[i].active) {
            game->drops[i].active = false;
            ++game->xp;
        }
    }
    if (game->xp >= COMBAT_XP_PER_LEVEL)
        open_upgrade_menu(game);
}

static void fire(Combat *game)
{
    unsigned target = COMBAT_CAPACITY;
    float distance = 13;
    game->cooldown = game->interval;
    game->shot_ticks = 4;
    game->shot_end = game->player;
    for (unsigned i = 0; i < COMBAT_CAPACITY; ++i) {
        if (!game->enemies[i].hp)
            continue;
        CombatVec delta = subtract(game->enemies[i].position, game->player);
        float forward = delta.x * game->aim.x + delta.z * game->aim.z;
        float side = fabsf(delta.x * game->aim.z - delta.z * game->aim.x);
        if (forward >= 0 && forward < distance && side < 0.55f + forward * 0.12f) {
            target = i;
            distance = forward;
        }
    }
    advance(&game->shot_end, game->aim, distance);
    if (target == COMBAT_CAPACITY)
        return;
    CombatEnemy *enemy = &game->enemies[target];
    game->shot_end = enemy->position;
    if (enemy->hp > game->damage) {
        enemy->hp -= game->damage;
        return;
    }
    ++game->kills;
    if (enemy->kind == COMBAT_ENEMY_BOSS) {
        enemy->hp = 0;
        --game->live;
        game->boss_defeated = game->portal_open = true;
        collect_all_xp(game);
        if (game->ticks < COMBAT_STAGE_TICKS - COMBAT_BOSS_GRACE_TICKS)
            game->ticks = COMBAT_STAGE_TICKS - COMBAT_BOSS_GRACE_TICKS;
    } else if (game->benchmark) {
        *enemy = (CombatEnemy){benchmark_position(target, game->scattered), 1, COMBAT_ENEMY_NORMAL};
    } else {
        drop_xp(game, enemy->position);
        enemy->hp = 0;
        --game->live;
    }
}

static void chase(Combat *game)
{
    for (unsigned i = 0; i < COMBAT_CAPACITY; ++i) {
        CombatEnemy *enemy = &game->enemies[i];
        if (!enemy->hp)
            continue;
        CombatVec delta = subtract(game->player, enemy->position);
        float length = length_squared(delta);
        if (length > 0.36f) {
            advance(&enemy->position, delta, 0.042f / sqrtf(length));
        } else if (!game->hit_cooldown && !game->benchmark) {
            game->hit_cooldown = COMBAT_HZ;
            if (!--game->health)
                game->phase = COMBAT_DEFEAT;
        }
    }
}

void combat_tick(Combat *game, CombatInput input)
{
    if (game->phase != COMBAT_PLAY)
        return;
    ++game->ticks;
    float speed = length_squared(input.move);
    const float step = PLAYER_SPEED * upgrades_stat(&game->upgrades, game->character, STAT_MOVE_SPEED);
    advance(&game->player, input.move, speed > 1 ? step / sqrtf(speed) : step);
    game->player.x = fmaxf(-COMBAT_ARENA, fminf(COMBAT_ARENA, game->player.x));
    game->player.z = fmaxf(-COMBAT_ARENA, fminf(COMBAT_ARENA, game->player.z));
    float aim = length_squared(input.aim);
    if (aim > 0)
        game->aim = scale(input.aim, 1 / sqrtf(aim));
    if (game->shot_ticks)
        --game->shot_ticks;
    if (game->hit_cooldown)
        --game->hit_cooldown;
    if (!game->benchmark) {
        collect_xp(game);
        if (game->phase != COMBAT_PLAY)
            return;
        advance_stage_clock(game);
        if (game->final_swarm) {
            if (game->swarm_ticks % (COMBAT_HZ / 2) == 0)
                swarm_spawn(game);
        } else if (!game->boss_defeated && game->ticks % COMBAT_HZ == 0 && game->live < 60) {
            spawn(game);
        }
    }
    chase(game);
    if (game->phase == COMBAT_PLAY && (!game->cooldown || !--game->cooldown))
        fire(game);
}

bool combat_can_interact(const Combat *game)
{
    return game->phase == COMBAT_PLAY && !game->boss_spawned && length_squared(subtract(game->spawner, game->player)) <= 25;
}

void combat_format_clock(unsigned ticks, char *out, unsigned size)
{
    const unsigned seconds = ticks / COMBAT_HZ;
    snprintf(out, size, "%u:%02u", seconds / 60, seconds % 60);
}

bool combat_interact(Combat *game)
{
    if (!combat_can_interact(game))
        return false;
    for (unsigned i = 0; i < COMBAT_CAPACITY; ++i) {
        if (game->enemies[i].hp)
            continue;
        game->enemies[i] = (CombatEnemy){game->spawner, COMBAT_BOSS_HP, COMBAT_ENEMY_BOSS};
        game->boss_spawned = true;
        ++game->live;
        return true;
    }
    return false;
}

bool combat_can_exit(const Combat *game)
{
    return game->phase == COMBAT_PLAY && game->portal_open && length_squared(subtract(game->spawner, game->player)) <= 25;
}

bool combat_exit(Combat *game)
{
    if (!combat_can_exit(game))
        return false;
    game->phase = COMBAT_EXITED;
    return true;
}

bool combat_choose(Combat *game, unsigned choice)
{
    if (game->phase != COMBAT_UPGRADE || choice >= game->offer_count)
        return false;
    upgrades_apply(&game->upgrades, &game->offers[choice]);
    refresh_stats(game);
    ++game->level;
    game->xp = 0;
    game->phase = COMBAT_PLAY;
    return true;
}
