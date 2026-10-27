# THPS Warehouse reference

What the Tony Hawk's Pro Skater Warehouse level physically contains, read from a 100% playthrough video. The only 3D view of the level is that video, so this doc records what it shows and what it cannot show, so the level does not have to be re-watched to rebuild it.

## Source

- 219 frames at 1 fps, `tools/thps_warehouse_frames/frame_0001.jpg` to `frame_0219.jpg`, 1920x1080, from video time 00:39 to 04:18 of `tools/thps1_100_playthrough.mkv`.
- Both the frames and the video are gitignored. Regenerate the frames with `ffmpeg -ss 00:39 -to 04:18 -i tools/thps1_100_playthrough.mkv -vf fps=1 -q:v 2 tools/thps_warehouse_frames/frame_%04d.jpg`.
- The footage is the Tony Hawk's Pro Skater 1 + 2 remake, not the 1999 original. The layout follows the original, but materials, lighting, graffiti and some props are remake art. Treat look notes as remake look.
- A facecam overlay covers roughly x 1520-1900, y 30-310 in every frame, and a HUD sits top left. Ignore both.

### Frame ranges

- 1-12: intro flyover over the whole room (12 is the best overview).
- 13-28: close flyover shots of the letters, the big rail, the channel and the secret room.
- 29-86, 92-113, 119-162: gameplay.
- 87-91, 114-118, 174-187, 218-219: pause menus and results screens, no geometry.
- 163-173: goal-camera flyover at the end of the first run.
- 188-217: gameplay of the second run.

## Scale

- The skater is the main ruler, taken as 1.8 m. Frame 188 and frame 71 show the skater beside doors, cones and barricades.
- Cross-checks: orange cone about 0.7 m, A-frame barricade about 1.1 m tall and 2 m wide, wooden crate about 1 m, steel pipe of the big rail about 0.1-0.15 m across.
- Perspective inflates anything nearer the camera than the skater, so every height and width below is a rough ratio, not a measurement. Numbers marked "low" were estimated from a single oblique view.

## Landmarks

Compass headings cannot be taken from the frames. Walls are named by what is on them.

- **Sign wall**: the long far wall with the painted "RENSSELAER HYDRANT CO. EST 1922" sign, a band of graffiti (KDR, JOSH, 518) at head height above the ramps, and a perforated X-braced gate beside the sign (frames 4, 119, 166, 167).
- **Window wall**: the long wall of tall steel-sash windows, three tiers high, with a red truck visible outside (frames 12, 101, 123, 169).
- **Door wall**: the end wall with two sets of white roll-up garage doors and a pillar between them (frames 1, 29, 163, 188).
- **Graffiti brick corner**: the teal and white brick corner with the CHRISTIAN and WERK murals (frames 16-18, 61-64).

## Structures

### Entrances (two roll-ins)

- Best frames: 1, 29, 30, 163, 188, 189 (door faces); 79, 92, 93, 98 (the way in from outside).
- Two sets of four-leaf white slatted roll-up doors on the door wall, separated by a pillar with a yellow warning sign (frame 1). Each leaf has two rows of glazed panes above a slatted lower half.
- Size (low): opening about 3 m tall; each set about 7-8 m wide, from the skater's size in frame 188.
- The skater smashes through the doors at the start, leaving splinters (frame 31). From outside, the way in is a ramp up between steel-lattice side walls, under a steel truss and lintel about 5 m above the floor and about 5-6 m wide (frames 79, 93). A diamond-plate steel threshold sits inside the door (frame 80).
- A third, darker door with a graffiti-covered lower half sits at the right edge of the door wall (frame 1).
- Beside the doors: a warning triangle and electrical box on the wall (188), a dark damaged opening with shelving to the left (163), and a puddle on the floor in front (188).

### Quarter pipes

The room has several distinct quarter pipes along its walls. The frames do not give a reliable one-to-one match with the wiki's wording, so they are grouped by look.

**Wide plywood quarter pipe with curved end (sign wall side)**

- Best frames: 156, 157, 158, 193, 196; 24 and 138 show it from the floor.
- A long, low plywood transition runs along the graffiti band of the sign wall. Its left end curves around a corner, which is where the "winding" shape comes from (156, 193).
- Size (low): about 2-3 m tall, wide enough to take the skater sideways across it for several seconds (frames 156-159).
- Plywood sheets with visible seams, dark steel coping, concrete wall above the lip. Window-bar light shadows fall across its floor (24, 138, 156).

**Wide slotted steel quarter pipe**

- Best frames: 119, 86, 120, 121, 4 (from above).
- Diamond-plate steel panels about 1.2-1.5 m wide, each with pairs of vertical slot cutouts, forming a long bank (119). A yellow painted stripe runs along the floor at its base.
- Size (low): about 2.5-3 m tall. At its top it joins a deck, and the mezzanine glass corridor hangs overhead near its right end (119).
- Dark metal, much cooler than the plywood ramps. This is the "slotted steel panel ramp" visible in several flyover frames (3, 4, 71, 72).

**Winding quarter pipe**

- Best frames: 7, 60, 122, 123, 124, 161, 162, 204.
- A curved plywood quarter pipe with a U-shaped pocket on top; three crates sit in the pocket (frame 7).
- Concave 90-degree corner with "Cheer The..." graffiti (161), steel coping, dark pipe rail at the lip (124).
- Size (low): about 2.5-3 m tall, pocket deck about 3 m above the floor.

**Tall channel quarter pipes**

- Best frames: 25, 26, 27, 110, 129, 149, 151, 152, 212; 10 and 11 from the flyover.
- Tall plywood panels with seams about every 1.2 m, graffiti (WERK, VERT, RAZ, TUKID), dark steel coping, mesh grille above (129).
- They flank both entrances and are stepped in tiers along one corner wall: three steps rising roughly 1.5, 2.2 and 3 m (frame 110, low).
- The tallest is about 3 m or more. Shoulder walls beside the ramps are about 1.5-2 m (frame 151).
- A concrete pillar with WERK graffiti stands between the two large ramps that sandwich the entrances (10, 25, 171).

**Small quarter pipe and second quarter pipe behind a deck**

- Best frames: 16, 17, 18, 213, 214.
- A small graffiti quarter pipe sits by the teal brick wall (16-18). A deck with another quarter pipe behind it carries a "RAZ" graffiti wall (213, 214).

### Half pipe

- Best frames: 138, 139, 145, 146, 135, 136.
- A wooden bay with plywood transitions on the left and back, concrete wall above the lip with "518", "WEAK" and other graffiti, and window-bar shadows on a stained concrete floor (138).
- Size (low): flat bottom about 8 m wide at skater scale, transitions about 2.5-3 m tall (138, 145).
- It sits below the same graffiti wall as the wide plywood quarter pipe above (156 and 138 share the 518 and KDR graffiti). It is probably the same plywood bay; see Unresolved.

### Kickers

- Best frames: 9, 10, 11 (corner pair), 58, 103, 127.
- At the corner near the sign wall, two kickers sit side by side with the S letter floating between them (9, 11). One is a plywood-panel ramp about 2.5-3 m wide and about 1 m tall at the lip (103, 127). The other is a lower open-frame wooden ramp about 0.6 m high.
- Near the big rail, a flat plywood kicker sits at each end of the rail, with barricades and cones beside it (101, 126).
- Plywood sheets with seams on a wooden frame; the plank panel pattern is visible on the 2x2 panel ramp in frame 9.

### Taxi funbox (probable)

- Best frames: 156, 193, 194, 217, 71; 4 and 12 from above.
- A dark, low, car-sized object on the floor, near the sign wall end. Frame 156 shows a wrecked car shell, with an arched roof frame and planks laid over it. Frame 71 shows the same object as a faceted plywood-clad mound with debris on top.
- Size (low): about 4-5 m long and 1-1.5 m high at the highest point, from frame 71 (barricade and skater scale).
- The taxi's paint and body shape are never visible, so the identification is probable, not confirmed. See Unresolved.

### Big rail

- Best frames: 24, 23, 22, 126, 170, 210, 33, 34.
- A long rust-red steel pipe about 0.1-0.15 m across on black posts, about 0.9-1 m above its base, with a bend and an elbow down at the near end (24).
- It runs diagonally across the middle of the room. The base is a diamond-plate steel platform with a grated drain trench beside it and a graffitied steel beam under the pipe (23, 24).
- Size (low): at least 8-12 m long.
- Orange-and-white A-frame barricades and traffic cones sit around both ends, and one barricade is fixed to the rail.

### Decks, platforms and ledges

**Decks**

- Best frames: 19-21, 26, 27, 133, 171, 213, 217.
- A deck sits on top of the channel quarter pipes and carries a crate pile and mesh cage walls (19-21, 171). Lip about 1.5-3 m above the floor.
- A concrete deck with a yellow painted border and graffiti face sits at floor level beside the half pipe (133).
- A diamond-plate deck with a red rail edge and grates borders the rail (209).

**Ledges**

- Best frames: 40, 56, 57, 108, 127, 128, 211.
- A long low concrete ledge runs along one wall, with a yellow edge stripe and a dark blue lower wall (108, 128).
- Height about 0.8-1 m (frame 108), or about 1.5 m in frame 211 ("VERT" graffiti, low). Cardboard boxes sit on top.
- A low curb about 0.2 m high appears in 205 and 216.

### Glass corridor and secret room

- Best frames: 4, 12, 166 (exterior); 28, 43, 172, 173 (interior).
- A windowed box hangs on a black steel frame above the floor, near the right end of the sign wall (4, 119, 166). Pale wood-clad exterior with multi-pane steel windows.
- The interior has a plank floor, wood wainscot about 1 m high, black-framed multi-pane windows on both long sides and an open truss ceiling beyond (172, 173).
- Size (low): about 4 m wide and 3 m high, from window height and sill scale (28). The length cannot be measured.
- The glass is breakable (43). The tape icon floats inside (4).
- The skater reaches it by launching off the quarter pipe in front, not by a door (frames 39, 42, 43).

### Box piles

- Best frames: 82, 81, 98, 94 (by the door wall); 19-21 (on the deck); 25-27 and 171 (crates and cardboard boxes); 7 (on top of the winding quarter pipe); 40, 57 (on the ledge).
- Two stacked wooden crates about 1.4 m tall together sit beside the door wall (82), and a pallet and plank pile sits nearby (94).
- Crates are marked "FRAGILE" and "123-09". Cardboard boxes (about 0.4-0.5 m) sit in small piles at the start (163, 164) and five on the deck at the sign wall corner (171).

### SKATE letters and other collectibles

- Letters are floating neon icons, visible in the flyover only: S between the corner kickers (9, 11, 12), K above the wide ramp (4 and 33 area), A near the taxi (4, 12), T above the half pipe (12, 73), E over the second deck (25-27).
- Hydrant markers (neon blue icons) float above several ramps (108-111). The tape icon floats inside the corridor (4).
- The positions of the letters relative to each other are in the sibling wiki analysis, not in the frames.

## Look

- **Floor**: pale stained concrete, cracked, with tile seams, wet patches and puddles (188, 10). Diamond-plate steel at the entrance threshold and rail platform.
- **Walls**: stained grey concrete, white brick and corrugated rust-coloured metal. A teal and dark-blue painted band runs along the lower wall (10, 16, 128). The sign wall carries the large painted hydrant company sign.
- **Graffiti**: heavy on every ramp and wall. Names seen: KDR, JOSH, WERK, 518, RAZ, VERT, WEAK, CIRCUIT, TOKU, DOM, TUKID, CHRISTIAN.
- **Windows**: steel-sash grid windows, three tiers high, along the window wall, with clerestory windows overhead. Window-bar shadows cast bright grids on the floor and ramps (24, 138, 156).
- **Ceiling**: exposed steel trusses and beams with hanging fluorescent fixtures (163, 172). The ceiling is about 5 m or higher near the entrance.
- **Ramp materials**: tall quarter pipes and the half pipe are plywood sheets with seams and steel coping. The wide bank along the sign wall is slotted diamond-plate steel.
- **Props**: orange cones, orange-and-white A-frame barricades, wire or mesh cage panels, orange safety fence (55), pipes, a High Voltage sign above one ramp (122).
- **Lighting**: bright shafts of sun from the window wall on a dim, dusty interior. Frame 188 and frame 24 show the contrast.

## Unresolved

- **Room dimensions and layout**: no frame gives an overall plan. The relative position of the door wall, sign wall and window wall is unresolved, and so are all headings. The maps in `tools/` (see the sibling analysis) are needed.
- **Half pipe**: frames 134-146 show transitions on the left and back only. Whether a matching opposing wall exists, and whether this bay is the same structure as the wide plywood quarter pipe, is not shown.
- **Taxi funbox**: the car shell in 156 and the mound in 71 are likely the same object, but no yellow paint or taxi roof sign is ever visible.
- **Relationship between the wide plywood and wide slotted quarter pipes**: both sit below the same graffiti band, but their order and extent along the wall are not shown.
- **The "large ramp slope with lattice shadows"** at the right of frames 154, 155 and 191: what it is, and where it sits relative to the rail, is unresolved.
- **Glass corridor versus secret room**: whether they are one space or two, and the tape room's exact access point, are not shown. The interior length is unmeasured.
- **Exact heights and widths**: every size is a skater-scale ratio from an oblique view and is low confidence. The tallest ramps never show their coping in frame.
- **Frames 215 and 216**: extreme top-down camera angles that do not map to a known structure.
- **Remake versus original differences**: which props and textures are remake-only is not known. Layout is assumed to match the original, which the frames cannot confirm.
- **Hidden surfaces**: backs of the ramps, the underside of the decks and the space behind the mezzanine are never on camera.
