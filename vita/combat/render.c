#include "render.h"

#include <math.h>
#include <stddef.h>
#include <vita2d.h>

typedef struct { float x, y, z; } Point;
typedef struct {
    vita2d_color_vertex *vertices;
    unsigned count;
    float zoom;
    CombatVec center;
} Scene;

enum { WIDTH = 960, HEIGHT = 544, MAX_VERTICES = (2 * COMBAT_CAPACITY + 72) * 36 };

static vita2d_pgf *font;
static const unsigned ink = 0xff24201a, paper = 0xffececde, accent = 0xff9bde81;

bool render_init(void)
{
    if (vita2d_init_advanced_with_msaa(2 * 1024 * 1024, SCE_GXM_MULTISAMPLE_NONE) < 0)
        return false;
    font = vita2d_load_default_pgf();
    if (!font) {
        vita2d_fini();
        return false;
    }
    vita2d_set_vblank_wait(1);
    vita2d_set_clear_color(0xff343529);
    return true;
}

static void vertex(Scene *scene, Point p, unsigned color)
{
    const float x = p.x - scene->center.x, z = p.z - scene->center.z;
    scene->vertices[scene->count++] = (vita2d_color_vertex){
        WIDTH / 2 + x * scene->zoom,
        HEIGHT / 2 + (0.68f * z - 0.73f * p.y) * scene->zoom,
        0.25f + (0.73f * z + 0.68f * p.y) / 384,
        color,
    };
}

static void quad(Scene *scene, Point a, Point b, Point c, Point d, unsigned color)
{
    vertex(scene, a, color);
    vertex(scene, b, color);
    vertex(scene, c, color);
    vertex(scene, a, color);
    vertex(scene, c, color);
    vertex(scene, d, color);
}

static unsigned shade(unsigned color, unsigned factor)
{
    unsigned r = (color & 255) * factor / 255;
    unsigned g = ((color >> 8) & 255) * factor / 255;
    unsigned b = ((color >> 16) & 255) * factor / 255;
    return 0xff000000 | b << 16 | g << 8 | r;
}

static void box(Scene *scene, CombatVec p, float y, float w, float h, float d, unsigned color)
{
    Point a = {p.x - w, y, p.z - d}, b = {p.x + w, y, p.z - d};
    Point c = {p.x + w, y, p.z + d}, e = {p.x - w, y, p.z + d};
    Point at = {a.x, y + h, a.z}, bt = {b.x, y + h, b.z};
    Point ct = {c.x, y + h, c.z}, et = {e.x, y + h, e.z};
    quad(scene, at, bt, ct, et, color);
    quad(scene, a, at, et, e, shade(color, 170));
    quad(scene, b, bt, ct, c, shade(color, 210));
    quad(scene, a, b, bt, at, shade(color, 155));
    quad(scene, e, c, ct, et, shade(color, 195));
}

static void ground(Scene *scene)
{
    for (int z = -5; z < 5; ++z) {
        for (int x = -5; x < 5; ++x) {
            float a = x * 8, b = z * 8;
            quad(scene, (Point){a, 0, b}, (Point){a + 8, 0, b},
                 (Point){a + 8, 0, b + 8}, (Point){a, 0, b + 8},
                 (x + z) % 2 ? 0xff4c6240 : 0xff506844);
        }
    }
    for (int i = 0; i < 28; ++i) {
        float angle = i * 2.399963f, radius = 14 + (i * 7 % 23);
        CombatVec p = {cosf(angle) * radius, sinf(angle) * radius};
        box(scene, p, 0, 0.22f, 2.5f, 0.22f, 0xff42749a);
        box(scene, p, 2, 0.9f, 1.4f, 0.9f, i % 2 ? 0xff416933 : 0xff507b42);
        box(scene, p, 3.4f, 0.52f, 0.7f, 0.52f, 0xff59824a);
    }
}

static void draw_world(const Combat *game)
{
    Scene scene = {
        .vertices = vita2d_pool_memalign(MAX_VERTICES * sizeof(vita2d_color_vertex), 16),
        .zoom = game->benchmark ? 10.5f : 23,
        .center = game->player,
    };
    if (!scene.vertices)
        return;
    ground(&scene);
    for (unsigned i = 0; i < COMBAT_CAPACITY; ++i) {
        if (game->drops[i].active)
            box(&scene, game->drops[i].position, 0.12f, 0.17f, 0.25f, 0.17f, 0xfff0e243);
        if (game->enemies[i].hp)
            box(&scene, game->enemies[i].position, 0, 0.31f, 0.95f, 0.31f,
                game->enemies[i].hp > 1 ? 0xff6137d8 : 0xff4642f5);
    }
    box(&scene, game->player, 0, 0.38f, 1.35f, 0.38f, accent);
    CombatVec end = game->shot_ticks ? game->shot_end :
        (CombatVec){game->player.x + 1.55f * game->aim.x, game->player.z + 1.55f * game->aim.z};
    float y = 0.72f, w = game->shot_ticks ? 0.047f : 0.025f;
    float dx = game->aim.z * w, dz = -game->aim.x * w;
    quad(&scene, (Point){game->player.x - dx, y, game->player.z - dz},
         (Point){game->player.x + dx, y, game->player.z + dz},
         (Point){end.x + dx, y, end.z + dz}, (Point){end.x - dx, y, end.z - dz},
         game->shot_ticks ? 0xff8eeaff : paper);
    vita2d_draw_array(SCE_GXM_PRIMITIVE_TRIANGLES, scene.vertices, scene.count);
}

static void panel(const char *title)
{
    vita2d_draw_rectangle(196, 145, 568, 249, ink);
    vita2d_draw_rectangle(196, 145, 568, 4, accent);
    vita2d_pgf_draw_text(font, 228, 200, paper, 1.43f, title);
}

static void draw_ui(const Combat *game, const CombatView *view)
{
    if (view->screen == SCREEN_TITLE) {
        panel("FOREST COMBAT");
        vita2d_pgf_draw_text(font, 228, 249, accent, 1, "Cross: Play     Triangle: Benchmark");
        vita2d_pgf_draw_text(font, 228, 292, paper, 0.86f, "Left stick: Move     Right stick: Aim");
        vita2d_pgf_draw_text(font, 228, 328, paper, 0.86f, "Weapon fires automatically. Collect XP to upgrade.");
    } else if (view->screen == SCREEN_BENCHMARK) {
        panel("BENCHMARK SETUP");
        vita2d_pgf_draw_textf(font, 228, 249, accent, 1, "%u enemies   /   %s", view->count,
                             view->scattered ? "Scattered" : "Gathered");
        vita2d_pgf_draw_text(font, 228, 290, paper, 0.90f, "Left / Right: Count     Up / Down: Layout");
        vita2d_pgf_draw_text(font, 228, 330, paper, 0.90f, "Cross: Run     Circle: Back");
    } else if (game->phase == COMBAT_UPGRADE) {
        panel("CHOOSE AN UPGRADE");
        vita2d_pgf_draw_text(font, 228, 251, view->choice == COMBAT_POWER ? accent : paper, 1,
                            "Power   /   +1 weapon damage");
        vita2d_pgf_draw_text(font, 228, 289, view->choice == COMBAT_HASTE ? accent : paper, 1,
                            "Haste   /   Fire more often");
        vita2d_pgf_draw_text(font, 228, 343, paper, 0.90f, "Up / Down: Choose     Cross: Confirm");
    } else if (game->phase == COMBAT_DEFEAT) {
        panel("RUN OVER");
        vita2d_pgf_draw_textf(font, 228, 250, accent, 1, "Level %u   /   %u defeated", game->level, game->kills);
        vita2d_pgf_draw_text(font, 228, 302, paper, 0.90f, "Cross: Retry     Start: Title");
    }
    if (view->screen != SCREEN_RUN)
        return;
    vita2d_draw_rectangle(18, 16, 560, 44, ink);
    if (game->benchmark) {
        vita2d_pgf_draw_textf(font, 30, 45, paper, 0.90f, "BENCHMARK  %s   /   %u live   /   Square: Reset",
                             game->scattered ? "Scattered" : "Gathered", game->live);
    } else {
        vita2d_pgf_draw_textf(font, 30, 45, paper, 0.90f, "HP %u   XP %d/%d   LV %u   DMG %u   SHOT %u TICKS",
                             game->health, game->xp, COMBAT_XP_PER_LEVEL, game->level, game->damage, game->interval);
    }
}

void render_frame(const Combat *game, const CombatView *view)
{
    SceGxmContext *ctx = vita2d_get_context();
    vita2d_start_drawing();
    sceGxmSetFrontDepthFunc(ctx, SCE_GXM_DEPTH_FUNC_ALWAYS);
    sceGxmSetFrontDepthWriteEnable(ctx, SCE_GXM_DEPTH_WRITE_ENABLED);
    vita2d_clear_screen();
    sceGxmSetFrontDepthFunc(ctx, SCE_GXM_DEPTH_FUNC_LESS_EQUAL);
    draw_world(game);
    sceGxmSetFrontDepthFunc(ctx, SCE_GXM_DEPTH_FUNC_ALWAYS);
    sceGxmSetFrontDepthWriteEnable(ctx, SCE_GXM_DEPTH_WRITE_DISABLED);
    draw_ui(game, view);
    vita2d_end_drawing();
    vita2d_swap_buffers();
}

void render_end(void)
{
    vita2d_wait_rendering_done();
    vita2d_free_pgf(font);
    vita2d_fini();
}
