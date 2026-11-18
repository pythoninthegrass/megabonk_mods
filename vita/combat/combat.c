#include "combat.h"

#include <math.h>

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

float combat_axis(uint8_t raw)
{
    const int offset = (int)raw - 128;
    if (offset < -16)
        return (offset + 16) / 112.0f;
    if (offset > 16)
        return (offset - 16) / 111.0f;
    return 0;
}

static void initialize(Combat *game)
{
    *game = (Combat){.aim = {0, -1}, .damage = 1, .interval = 18, .health = 6, .level = 1};
}

static CombatVec benchmark_position(unsigned i, bool scattered)
{
    CombatVec position = {(float)((int)(i % 16) - 7), (float)((int)(i / 16) - 15)};
    return scale(position, scattered ? 2.25f : 0.75f);
}

static void spawn(Combat *game)
{
    for (unsigned i = 0; i < COMBAT_CAPACITY; ++i) {
        if (game->enemies[i].hp)
            continue;
        const unsigned index = game->spawn_index++;
        const float angle = index * 2.399963f;
        game->enemies[i] = (CombatEnemy){{sinf(angle) * 9, -cosf(angle) * 9}, index % 4 == 3 ? 2 : 1};
        ++game->live;
        return;
    }
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
        game->enemies[i] = (CombatEnemy){benchmark_position(i, scattered), 1};
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
        if (drop->active && length_squared(subtract(drop->position, game->player)) < 1.44f) {
            drop->active = false;
            if (++game->xp == COMBAT_XP_PER_LEVEL) {
                game->phase = COMBAT_UPGRADE;
                return;
            }
        }
    }
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
    if (game->benchmark) {
        *enemy = (CombatEnemy){benchmark_position(target, game->scattered), 1};
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
    advance(&game->player, input.move, speed > 1 ? 0.1f / sqrtf(speed) : 0.1f);
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
        if (game->ticks % COMBAT_HZ == 0 && game->live < 60)
            spawn(game);
    }
    chase(game);
    if (game->phase == COMBAT_PLAY && (!game->cooldown || !--game->cooldown))
        fire(game);
}

bool combat_choose(Combat *game, CombatUpgrade choice)
{
    if (game->phase != COMBAT_UPGRADE || (choice != COMBAT_POWER && choice != COMBAT_HASTE))
        return false;
    if (choice == COMBAT_POWER)
        ++game->damage;
    else if (game->interval > 6)
        game->interval -= 3;
    ++game->level;
    game->xp = 0;
    game->phase = COMBAT_PLAY;
    return true;
}
