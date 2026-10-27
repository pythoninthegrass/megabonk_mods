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

### Map and guide

- `tools/thps_warehouse_items_map.png` (with collectible markers) and `tools/thps_warehouse_itemless_map.png` (without), both 973x767, gitignored. Pixel positions below are in that image, x to the right and y down, read from the items map unless stated.
- `tools/thps_warehouse_strategywiki.md`, a saved copy of the StrategyWiki page `https://strategywiki.org/wiki/Tony_Hawk's_Pro_Skater/Warehouse`. It is the only source for the collectible descriptions and the gap names.
- The maps are an isometric (not top-down) render: floor and the two far walls are visible, the near sides are cut away, and everything raised appears shifted up the screen by its height.

## Scale

- The skater is the main ruler, taken as 1.8 m. Frame 188 and frame 71 show the skater beside doors, cones and barricades.
- Cross-checks: orange cone about 0.7 m, A-frame barricade about 1.1 m tall and 2 m wide, wooden crate about 1 m, steel pipe of the big rail about 0.1-0.15 m across.
- Perspective inflates anything nearer the camera than the skater, so every height and width below is a rough ratio, not a measurement. Numbers marked "low" were estimated from a single oblique view.

## Map orientation and scale

### Headings

The video cannot give compass headings, so the map defines its own. They are map headings, not real compass directions.

- **N** is up-right on screen, along the long far wall. **S** is down-left.
- **W** is up-left on screen, toward that long far wall. **E** is down-right.
- The long far wall (screen edge from about (25,375) to (460,110)) is the **west wall**. It carries a black-and-yellow "SKATEBOARDING" sign near its south end, at about (110,388), and brown wooden pilasters at about x 190-215 and x 385-410. A short **north wall** continues from (460,110) to (550,185).
- The south-west and south-east edges of the floor are cut away and show only the slab's thickness, so no south or east wall is shown.

### Scale

- Anchoring the half pipe's flat bottom at about 8 m against its width on the map (about 170 px between the two coping lines) gives roughly 20-25 px per metre along both floor axes. This is a single-anchor estimate, low confidence.
- The big rail is a thin line on the itemless map through the centre box pile, from about (428,572) to (603,490), about 195 px, so about 8-10 m. This agrees with the frame estimate of at least 8-12 m.
- The west wall is about 510 px, so about 20-25 m. The cut-away south-west edge from (25,375) to (250,660) is about 360 px, so about 14-17 m. The main room is therefore roughly 20-25 m by 14-17 m before the raised north-east block.
- A 14-17 m side matches the frame-derived door wall: two door sets of 7-8 m each plus a pillar. So the door wall is probably a cut-away side or the north-east side, not the west wall.

### Discrepancies with the frame analysis

- The map's sign reads "SKATEBOARDING". The frames' sign wall carries the "RENSSELAER HYDRANT CO." sign. They are different signs, so the map's west wall cannot be matched to the frames' sign wall with confidence, and may be the same wall with a second sign out of the frames' view.
- The frame analysis calls the half pipe's sides "left and back" only. The map shows two parallel coping lines about 170 px apart with a flat floor between them, so it has two opposing sides, which the frames did not show.
- Heights cannot be read from the map. Vertical screen offset mixes height with floor position, so heights stay as in the frame analysis and the guide text.

## Landmarks

Walls are named by what is on them.

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
- Positions on the map are in the Collectibles section.

## Floor plan

Feature codes (M1-M15) are used by the Collectibles and Gaps sections. Pixel boxes are x range, y range on the 973x767 map. Headings are the map headings defined above.

### Perimeter

- The west wall runs about 20-25 m from its south end at (25,375) to the north-west corner at (460,110). The wall is plain grey brick with pilasters, the sign, and a perforated gate at about (300,330) behind the half pipe.
- A short north wall steps out to the north-east at (460,110)-(550,185), then the outline jogs again and rises into the raised north-east block at (680-940,20-250).
- The east side is a stepped cut-away edge: from the south corner at about (250,660) the floor edge runs east, jogs out into a south tab (about (310-480,600-750)), then continues north-east along the south-east edge to (730,570), up the tall wall face at (685-730,440-600), and on to the east deck at about (890,400).
- Cut-away edges mean the room continues past the map on the south and east sides in the frames' view; the map shows no walls there.

### Interior features

- **M1 West bank**: brown plywood quarter pipe against the south end of the west wall, about (60-170,400-490), with a curved end that wraps around the south-west corner at about (75,475). The SKATEBOARDING sign is directly above it. Painted text on its face reads "FIRM".
- **M2 West platform**: an L-shaped raised concrete platform north-east of M1, about (165-250,380-430), with a lipped front edge facing south-east. A box pile sits on it. A flat floor with cardboard sheets lies in front, at about (140-270,415-480).
- **M3 Taxi**: a yellow cab shell on the floor, about (265,505), surrounded by flattened cardboard. It is the only yellow object on the itemless map, so the funbox in the frames is the taxi.
- **M4 Half pipe**: a long channel running along the E axis from the west wall to the middle of the room. Two parallel yellow-and-black coping lines, one along (385,320)-(540,445) (north-east side) and one along (245,350)-(415,520) (south-west side), bound a flat floor with the T icon over it. The ramp face on the north-east side is a smooth brown surface; the south-west side is a grey sloped face with seams.
- **M5 Hanging corridor**: a dark box on a black steel frame with two diagonal black beams rising toward the west wall, about (285-375,265-350), directly above the north end of M4. The tape icon sits at its south-east end at (355,322).
- **M6 North bank**: a plywood quarter pipe under the north wall, about (440-540,225-320), with yellow-and-black coping along its top edge and a red graffiti mark on the wall above it at about (440,190).
- **M7 Middle quarter pipe and pillar**: a small quarter pipe at about (570-640,340-400) with a tall grey pillar behind it at about (600-650,230-370) carrying yellow graffiti.
- **M8 East channel quarter pipe**: a quarter pipe at about (665-760,415-500) running down to the east, with a dark vertical wall face at (685-730,440-540) on its south side.
- **M9 East deck and back pipe**: a flat deck at about (740-880,400-460) holding a box pile, with a second, taller plywood quarter pipe behind it at about (780-890,320-420) against the east end.
- **M10 South notch quarter pipe**: a small curved quarter pipe at about (350-390,600-650) at the end of the south tab, with a box pile on the ledge in front at (330,615).
- **M11 South-east ledge**: a low ledge in the notch at the foot of M8's wall, about (680-720,570-610), holding a box pile at (695,598).
- **M12 Plywood kickers**: two flat plywood sheets on low frames, one at about (540-585,605-630) and one at about (480-520,640-675). The S icon floats between them at (525,625).
- **M13 Dark pit**: a dark, textured, shadowed area at about (470-580,650-720) at the south-east end of the kickers. It reads as a hollow or dark ramp and is not identified.
- **M14 Raised north-east block**: a large brown curved mass at about (680-940,20-250) with wall pilasters on its north-east face and a dark gap under it at about (660-800,140-260). The start arrow sits on its floor at (855,210).
- **M15 Big rail and box pile**: a thin dark rail line through a heap of cardboard, from (428,572) to (603,490), runs roughly along the N axis at about the middle of the room. The same heap exists on the itemless map.
- **Two sloped channels**: a wide grey slope rises from about (600,360) toward the dark gap under M14. It is divided into two lanes by the middle quarter pipe M7. M6, M7 and M8 flank the two lanes, which matches the guide's channel: three quarter pipes sandwiching both entrances.

### ASCII sketch

The sketch is schematic (map headings, not to scale). N is up, E is right.

```text
              N
   +----------------------------+
   | W wall: sign, pilasters    |  M14 raised block (NE)
   |  M1 bank   M2 platform     |    start arrow
   |   M3 taxi   M5 corridor    |  M6 bank   lanes
   |             M4 half pipe   |  M7 pillar+QP
   |   K        M15 rail+pile   |  M8 QP, M9 deck+back QP (E)
   |          S kickers  M13    |  M11 ledge
   |  M10 notch                 |
   +----------------------------+
              S
```

## Collectibles

Positions are pixels on the 973x767 items map. Every icon floats above its true floor position by an unknown height, so the floor position is only known to within about the icon's height in screen terms. Heights are from the guide text and the frame analysis.

### Box piles

The red circles. The guide's order cannot be matched to the circles with confidence; the match given is the best reading.

| Circle | Pixel | On | Guide entry | Height | Confidence |
| --- | --- | --- | --- | --- | --- |
| R1 | (200,400) | M2 west platform | 2 (platform with rail by the taxi), or 3 (U-shape on the winding quarter pipe) | on the platform, about 1-1.5 m, at the lip of M1 | the guide's #2 and #3 both fit here |
| R2 | (330,615) | M10 ledge in the south notch | 4 (ledge in a corner near the two kickers) | on a ledge about 1 m above the floor | probable |
| R3 | (695,598) | M11 south-east ledge | 4 (corner ledge near the kickers) or 1 (turn right from start) | low ledge at the foot of the wall | the guide's #4 fits R2 and R3 |
| R4 | (790,457) | M9 east deck, in front of the back pipe | 5 (deck with a second quarter pipe behind) | deck level, about 1.5-2 m | probable, shares its spot with E |
| R5 | (695,155) | the dark gap under M14, beside M6 | 1 or 3 | unknown, in shadow | uncertain |

### Letters

| Letter | Pixel | Over | Height relative to nearby structures | Guide wording |
| --- | --- | --- | --- | --- |
| S | (525,625) | floor between the two kickers M12 | in the air, above the kicker lips, reached by an ollie | between two makeshift ramps |
| K | (165,562) | floor in the south-west corner, south of M3 | high above the wide quarter pipe, reached by launching from it | end of the room, above the wide quarter pipe, behind the taxi |
| A | (267,505) | directly above the taxi M3 | an ollie above the taxi roof | above the taxi funbox |
| T | (405,382) | over the M4 half pipe floor | above the half pipe, reached from the ramp at speed | above the half pipe, next to the glass corridor |
| E | (757,433) | M8 and M9, over the end of the quarter pipe | just past the quarter pipe's lip | corner quarter pipe, with a deck and another quarter pipe behind |

### Tape and 100-point pickups

| Item | Pixel | Over | Height | Guide wording |
| --- | --- | --- | --- | --- |
| Secret tape | (355,322) | south-east end of M5, above the north end of M4 | inside the corridor, about 3 m above the floor | floating inside the room above the half pipe |
| 100 (north) | (570,303) | lane between M6 and M7 | in the air in the channel between two quarter pipes | in front of the left roll-in, between two quarter pipes |
| 100 (east) | (668,382) | lane between M7 and M8 | same, in the other lane | the same, near the right roll-in |
| 100 (south) | (398,686) | above M10 at the end of the south tab | above the wide quarter pipe, reached by launching from it | above the wide quarter pipe at the two-kicker corner |

## Gaps and rails

The guide's gaps with the structures they connect. Map codes are the best reading and marked "probable" where the guide wording does not pin a single structure.

| Gap | From | To | Map reading |
| --- | --- | --- | --- |
| Big Rail | one end of the big rail | the far end | M15, grind the whole rail |
| Channel Gap | quarter pipe on one side of an entrance | quarter pipe on the other side | M6/M7 or M7/M8, either lane |
| Deck 2 Rail | the deck holding another quarter pipe | the big rail | M9 deck to M15 |
| Face Plant | the same quarter pipe | the wall beyond both pipes | M9 back pipe to the east wall, needs high speed |
| High Rail | the winding quarter pipe | the high rail under the "skateboarding" sign | M1 to a high rail on the west wall above the sign |
| Holy Shi... | a rail by the half pipe | the whole wide quarter pipe | M4 ramp to a rail on the wide pipe, then grind the pipe edge (the guide does not say which pipe in map terms; probable M6) |
| Kicker 2 Ledge | the kicker facing away from the wall | the grey ledge at the corner | M12 to M11 |
| Kicker Gap | one kicker | the other kicker | M12, short plank to plank |
| Monster Grind | the high rail | the quarter pipe edge, then the ledge rail at its end | M1 high rail, down M1, then the M2 platform rail |
| Over the Pipe | the large ramp on one side of the half pipe | the large ramp on the other side | the two sides of M4 |
| Secret Room | one ramp | the other ramp, through the corridor | M4 sides, through M5 |
| Taxi 2 Ledge | the taxi funbox | the ledge with the short rail on top | M3 to the M2 platform edge |
| Taxi 2 Rail | the taxi funbox | the big rail | M3 to M15 |
| Taxi Gap | the taxi funbox | the middle of the half pipe | M3 to the M4 floor |
| Transfer | one side of the U-bend in the wide quarter pipe | the other side | the U-shape on the wide quarter pipe (probable M1 or M6) |
| Transition Grind | the quarter pipe between a roll-in and a wall | the wall, then the half pipe edge | a lane-side pipe (probable M6) along the wall, wallride, then the M4 coping |

Rails named in the guide: the big rail (M15); the short rail on the ledge by the taxi (M2); the high rail under the "skateboarding" sign (west wall, not visible as geometry on the map because it is above the wall line); the rail at the other side of the half pipe (not identified on the map).

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

- **Walls and headings**: the map defines its own headings. The door wall, window wall and graffiti brick corner are not placed on it, since the south and east sides are cut away. The map's "SKATEBOARDING" wall is not confirmed to be the frames' sign wall.
- **Room dimensions**: the 20-25 m by 14-17 m extent comes from one anchor (the half pipe flat at about 8 m) and is low confidence. The height of the raised north-east block and of every wall is not shown.
- **Box pile numbering**: the guide's five piles cannot be matched one to one to the five circles. R1 fits guide piles 2 and 3, R2 and R3 both fit pile 4, and R5 sits in shadow under the north-east block.
- **Floating icon heights**: all icons are drawn above their floor position by an unknown height, so ground positions and heights come from the guide text only.
- **Start position and roll-ins**: the blue start arrow is on the raised north-east block, and the guide's "left" and "right" roll-ins are not matched to the two lanes with confidence. The function of the block (roof, ramp or platform) is not shown.
- **Dark pit M13**: unidentified; it may be a hollow, a dark ramp or a drain.
- **Floor line near K**: a thin dark line with three ticks at about (120,490)-(180,540) in the south-west bay is either a floor marking or a low rail; unresolved.
- **Quarter pipe naming**: the guide's "wide", "winding" and "U-shaped" quarter pipes are not mapped to M1, M6 and M8 with confidence. M1 is the best fit for the winding pipe (curved end). The U-shape on the guide's wide pipe is not visible on the map.
- **Half pipe sides**: the map shows two coping lines, but not whether both sides are full-height transitions of the same size.
- **Relationship between the wide plywood and wide slotted quarter pipes**: the frames and the map do not settle which map structure is which.
- **The "large ramp slope with lattice shadows"** at the right of frames 154, 155 and 191: possibly the sloped lanes under the north-east block, not confirmed.
- **Glass corridor versus secret room**: the map shows one hanging box (M5), so they are probably one space. The tape room's exact access point and the interior length are not shown.
- **Exact heights and widths**: every size is a skater-scale ratio from an oblique view and is low confidence. The tallest ramps never show their coping in frame.
- **Frames 215 and 216**: extreme top-down camera angles that do not map to a known structure.
- **Remake versus original differences**: the map render is also a remake render. Which props and textures are remake-only is not known. Layout is assumed to match the original.
- **Hidden surfaces**: backs of the ramps, the underside of the decks and the space behind the mezzanine and the north-east block are never on camera.
