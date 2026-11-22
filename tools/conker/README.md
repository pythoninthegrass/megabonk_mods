# Conker's Bad Fur Day (N64) multiplayer — keyframe reference

Source video: `Conker's Bad Fur Day (N64) ＂Colors＂ Multiplayer Mode (With Bots) [AoobfXkfN2U].mkv` (<https://youtu.be/AoobfXkfN2U>), 640x480 30 fps, h264 + opus, 10:59, 61 MB. 480p is the ceiling on YouTube: format 135 + 251 is the best available, so there is nothing higher to re-pull.

The US retail ROM sits at `rom/baserom.us.z64`, local-only like the captures. Everything under `videos/` is gitignored (`tools/**` in the root `.gitignore` tracks only `.gitkeep` and `.md` files). Regenerate the images from the mkv rather than asking for them back.

## Layout

- `videos/<source>.mkv` — the recording, named as yt-dlp saved it.
- `videos/frames/frame_0001.jpg` … `frame_0649.jpg` — full survey, 1 fps from video 00:10, quality `-q:v 2`.
- `videos/keyframes/kf_NN_<mmss>_<slug>.jpg` — 31 curated stills covering the distinct environments, characters, weapons, effects and match beats. `<mmss>` is approximate video time (±5 s).
- `videos/keyframes_sheet.jpg` — the curated set as one contact sheet.
- `videos/sheets/sheet_00.jpg` … `sheet_13.jpg` — the survey as 48-frame contact sheets, 8x6, labeled with the frame file name. Sheet N starts at frame `48N + 1`.
- `rom/baserom.us.z64` — the US retail ROM image.

## Regenerate

```sh
cd ~/git/megabonk_mods/tools/conker/videos
ffmpeg -hide_banner -loglevel error -y -ss 10 -i \
  "Conker's Bad Fur Day (N64) ＂Colors＂ Multiplayer Mode (With Bots) [AoobfXkfN2U].mkv" \
  -vf fps=1 -q:v 2 frames/frame_%04d.jpg

montage frames/frame_*.jpg -tile 8x6 -geometry 240x180+2+2 -background '#111' -fill '#ff0' \
  -pointsize 16 -label '%f' sheets/sheet_%02d.jpg
```

Frame N sits at video time about `N + 9` seconds (`-ss 10` plus 1 fps sampling). Quote the URL when re-downloading: an unquoted `?si=…&t=…` backgrounds the command at the `&`, and yt-dlp ignores `t` anyway.

## Match structure

The recording is one continuous take of the "Colors" capture-the-flag mode against bots, single map, with a HUD (score left and right, a 10:00 countdown in the middle, a circular radar top right). Video time = match-clock time plus about 30 seconds.

- 0:00-0:29 — title card plus the briefing cutscene: Conker barks orders in speech bubbles ("LISTEN UP!", "SHOOT THE EVIL SQUIRREL ON SIGHT.", "FALL OUT!"), the squad lines up.
- 0:29 (clock 10:00) — match starts in the brown/wood team base with the red floor.
- 0:30-1:40 — the base interior and the first sniper-rifle segment. Roughly 50 seconds of scoped aiming at the towers: the densest filler in the video, only two frames kept.
- 1:45-3:00 — outdoors: grass ledges and ridges between stone walls, wooden bridges and ramps, waterfall on a rock face, dirt trenches. Melee with bats, knives, chainsaws and a mallet.
- 3:00-4:20 — the long green-floored trench canyon that runs between the two bases. About 48 near identical frames; one is kept (`kf_14`).
- 4:20-6:30 — mixed combat: green-armored enemy squirrels, laser tracers, explosions, blood spray, a white/pale Conker (respawn or powered state) in the red-lit corridors.
- 6:30-8:30 — the enemy base: green-lit interiors, `S$` graffiti on the walls, red blast doors, glowing green flag pads.
- 8:30-9:30 — the flag grab and carry: striped blue/green flag, running it back through the red hall.
- 10:20-10:59 — post-match: black frames, then the victory scene with the green tank, the red `T` flags and the stats screen.

## Look notes

- Characters are stitched cloth toys: visible seams, button-like eyes, stubby limbs. Conker is brown with a lighter belly; enemy squirrels are tan, or brown with a green hood and backpack.
- Two team palettes: brown wood plus red floor with white lightning-bolt markings, and green-lit stone with `S$` graffiti. Flags are green with a white `S`, or red with a black `T` and a bolt.
- Environment is low-res N64 texture work: mottled green grass, gray rock, wooden crates and ramps, no anti-aliasing, heavy dithering, flat fog in the distance.
- Combat effects: chunky red blood particle bursts, green laser tracers, muzzle flashes, yellow sparks on pickup collection, ragdoll flips on death.
