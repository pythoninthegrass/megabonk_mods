# Warehouse construction piece inventory

This is the additive construction kit's source partition, and the pieces it
names are live assets: the pack builder ships each row below as a placeable
`bundle:thps/<id>` prefab in the editor's Packs palette. The shipped
`bundle:thps/Warehouse`, its assets and `levels/thps.mblevel.json` remain
unchanged. See [asset-bundles.md](asset-bundles.md) for the piece prefabs,
their pivots and the `pieces.json` sidecar, and the
[reference](thps-warehouse.md), [shipped layout](thps-warehouse-layout.md) and
[preservation check](development.md#preserving-the-shipped-warehouse).

## Source and addressing

Source: `.tools/thps1/warehouse/warehouse.obj`, from the PS1 extraction.
Source SHA-256: `917aa268b447df4e7131cac0b55cbf0894e848789c86289daf845d25a562b25a`

There are **252 object declarations, 200 nonempty objects and 1,345 polygon
faces**, assigned to **214 named source pieces** below. A face number is the one-based ordinal of an `f` line across the
whole file, before triangulation, coplanar separation or importer filtering.
Ranges are inclusive; comma-separated ranges form one piece. Groups are the
literal `o` hashes, not material hashes. Every source face has exactly one
owner, including double-sided faces and suppressed post remnants. There is no
catch-all remainder. Each table row is one independently editable instance;
module types describe reuse, not a second assignment of its faces.

Empty objects: `947969A2`, `0D703818`, `7A77088E`, `E4139D2D`, `9314ADBB`, `0A1DFC01`, `7D1ACC97`, `0108955F`, `9801C4E5`, `EF06F473`, `B31D819B`, `D0B9495C`, `2A14D021`, `49B018E6`, `BE5B0A8C`, `27525B36`, `50556BA0`, `CE31FE03`, `DFB35C91`, `46BA0D2B`, `6F12583B`, `954EED36`, `F61B0981`, `811C3917`, `1F78ACB4`, `687F9C22`, `1E575FE1`, `875E0E5B`, `370A0C19`, `AE035DA3`, `271B3BAD`, `D9046D35`, `BA664D03`, `CABEDA1B`, `4760F896`, `9F9D74DB`, `86B0FA50`, `0C47BC8C`, `EF5B1379`, `817474C9`, `27CBD007`, `187D2573`, `F673445F`, `6FD0D543`, `0DE57681`, `F28254C7`, `A114B35C`, `94EC273B`, `7B408C1A`, `E52419B9`, `F0593ECD`, `6E3DAB6E`

Those 52 declarations have no geometry and need no palette placeholder. They
are accounted for separately, not assigned invented faces.

Run `uv run scripts/check_thps_piece_inventory.py` to verify the fingerprint,
empty declarations, selectors, unique names/IDs and exact face coverage. The
same check runs in pytest and fails rather than skips without the extraction.
The Markdown tables are the machine-readable inventory; edit them rather than
maintaining a competing manifest.

### Coordinates and preservation rules

Measurements here are **Megabonk world units**, not the reference video's
estimated metres or its map headings. Transform raw OBJ `(x,y,z)` to
`((x-1.519043)*79.2+100, -y*79.2+0.5, (z-1.9661865)*79.2)`.
World north is +Z. Keep unrounded source coordinates/UVs in meshes; numbers
below are rounded for reading, never snapping targets.

Use one canonical pivot at the midpoint of a module's lower riding edge,
with local +Y up and +Z pointing from toe toward lip; deck/flat pivots are
their walking-surface centres. Corner pivots are at the intersection of the
extended lip lines at deck height. Props use bottom-centre; wall/window pivots
use bottom-centre of the panel; roof tiles use centre of the lower face.
Store the inverse pivot transform so reassembly restores the original world
vertices exactly. These are kit conventions to implement, not changes to the
legacy mesh's centre pivot.

The start area contains paired state/double-sided geometry that the importer
currently draws together. Rows naming two groups retain both, including
nonidentical material variants; do not deduplicate them on the assumption
that only one should be visible. Preserve global `CoplanarLayering` offsets
before partitioning so posters and planks do not gain different offsets when
their neighbours move. Triangulation, winding, UVs and transparency stay as in
`ThpsPack.cs`.

## Source face inventory

### Hanging glass box

The room occupies x 149.36–178.95, z 20.93–31.47. Its window objects are
individual **window sections**, not every small pane painted in a texture.
Each two-face window is the two sides of one section and moves as one piece.
The east wall is part of the arena wall panel below, not an eighth glass window.

| ID | Element | Groups | Faces | Module |
| --- | --- | --- | --- | --- |
| piece-room-wall-south | Glass box south wall frame | B22D8FBF | 71-82 | wall |
| piece-room-wall-north | Glass box north wall frame | 5C23EE93 | 83-94 | wall |
| piece-room-roof | Glass box roof slab | 4E3C5402 | 177-180 | roof |
| piece-room-floor | Glass box floor slab and edge fascia | 4E3C5402 | 181-201 | deck |
| piece-room-window-se | Glass box south east intact window | BB7DC2A2 | 202-203 | window |
| piece-room-window-sw | Glass box south west broken window | BC1006BB | 204-205 | window |
| piece-room-window-ne | Glass box north east broken window | 521E6797 | 206-207 | window |
| piece-room-window-nw | Glass box north west intact window | CC7AF234 | 208-209 | window |
| piece-room-underside-box | Glass box underside support box | 105A150D | 210-228 | support |
| piece-room-wall-west | Glass box west wall frame | 2B24DE05 | 312-323 | wall |
| piece-room-window-west | Glass box west broken window | 25195701 | 553-554 | window |
| piece-room-chain-north | Glass box north suspension chain | 10500CBD | 121-124 | support |
| piece-room-chain-south | Glass box south suspension chain | 89595D07 | 125-128 | support |
| piece-room-brace-north-outer | Glass box north outer diagonal brace | 6BA45667 | 115-117 | support |
| piece-room-brace-south-outer | Glass box south outer diagonal brace | 1CA366F1 | 118-120 | support |

Floor top is 15.640, bottom 15.311; roof underside is 25.424, top 25.753.
Keep each slab's top, bottom and edge faces together. Intact room windows
(`F2184063`) are collision-open only in the authored room bounds; broken
windows (`FA88F30D`) are always collision-open. Their frames remain solid.
Window pieces must carry that result locally, not keep testing the old world
bounds after movement. No new breakable-window gameplay is implied.

### Main half pipe and hip ends

| ID | Element | Groups | Faces | Module |
| --- | --- | --- | --- | --- |
| piece-main-hip-north | Main half pipe north west hip end | ED3C7CD2 | 229-231 | hip |
| piece-main-hip-south | Main half pipe south west hip end | 9A3B4C44 | 232-234 | hip |
| piece-main-hip-apron | Main half pipe tapered west sloping apron | 1D44E8A6 | 264-270 | hip-apron |
| piece-main-bank-north-01 | Main half pipe north outer bank west strip | 1F4E66D8 | 330 | outer-bank |
| piece-main-bank-north-02 | Main half pipe north outer bank middle strip | 1F4E66D8 | 331 | outer-bank |
| piece-main-bank-north-03 | Main half pipe north outer bank east strip | 1F4E66D8 | 332 | outer-bank |
| piece-main-bank-north-end | Main half pipe north outer bank hip end | 1F4E66D8 | 333 | bank-end |
| piece-main-bank-south-01 | Main half pipe south outer bank west strip | 86473762 | 334 | outer-bank |
| piece-main-bank-south-02 | Main half pipe south outer bank middle strip | 86473762 | 335 | outer-bank |
| piece-main-bank-south-03 | Main half pipe south outer bank ledge join | 86473762 | 336-338 | outer-bank |
| piece-main-bank-south-end | Main half pipe south outer bank hip end | 86473762 | 339 | bank-end |
| piece-main-south-03 | Main half pipe south transition east section | 03321DFE | 1127-1131 | main-transition |
| piece-main-north-01 | Main half pipe north transition west section | 0A8451D5 | 1132-1136 | main-transition |
| piece-main-south-01 | Main half pipe south transition west section | 7358E971 | 1137-1141 | main-transition |
| piece-main-south-02 | Main half pipe south transition middle section | EA51B8CB | 1142-1146 | main-transition |
| piece-main-north-02 | Main half pipe north transition middle section | 9D56885D | 1147-1151 | main-transition |
| piece-main-flat | Main half pipe rectangular flat bottom | 7D836143 | 1152-1154 | flat |
| piece-main-north-03 | Main half pipe north transition east section | 74352D68 | 1155-1159 | main-transition |

### Wall quarter pipes, corners and decks

Deck faces are split from riding transitions even when the original object
mixed them. Lip/coping strips stay with their transition; grind paths follow
their owning transition, not the adjacent deck. Names use measured world
location rather than uncertain remake wall names.

| ID | Element | Groups | Faces | Module |
| --- | --- | --- | --- | --- |
| piece-south-transition-end | South wall quarter pipe west end section | C02D64C7 | 272-276 | wall-transition |
| piece-south-deck-end | South wall quarter pipe west end deck | C02D64C7 | 277 | deck |
| piece-pocket-return | South pocket return corner transition | B72A5451 | 278-280,285-296 | corner |
| piece-pocket-return-deck | South pocket return corner deck | B72A5451 | 281-284,297 | deck |
| piece-pocket-tip-west | South pocket rounded tip west transition | 3055F0B3 | 1031-1040 | convex-tip |
| piece-pocket-tip-west-deck | South pocket rounded tip west deck | 3055F0B3 | 1041-1042 | deck |
| piece-pocket-side-west | South pocket west side transition | 4752C025 | 1043-1057 | wall-transition |
| piece-pocket-side-west-deck | South pocket west side deck | 4752C025 | 1058-1062 | deck |
| piece-pocket-tip-east | South pocket rounded tip east transition | A95CA109 | 1063-1072 | convex-tip |
| piece-pocket-tip-east-deck | South pocket rounded tip east deck | A95CA109 | 1073-1074 | deck |
| piece-pocket-side-east | South pocket east side transition | 373834AA | 1075-1079 | wall-transition |
| piece-pocket-side-east-deck | South pocket east side deck | 373834AA | 1080-1081 | deck |
| piece-south-transition-middle | South wall quarter pipe middle run | D9365586 | 1082-1086 | wall-transition |
| piece-south-deck-middle | South wall quarter pipe middle deck | D9365586 | 1087 | deck |
| piece-southeast-corner-deck | South east quarter pipe corner deck | AE316510 | 1088-1092 | deck |
| piece-southeast-corner | South east quarter pipe corner transition | AE316510 | 1093-1107 | corner |
| piece-north-transition-east | North wall quarter pipe east run | 5E49F164 | 1160-1169 | wall-transition |
| piece-north-deck-east | North wall quarter pipe east deck | 5E49F164 | 1170-1171 | deck |
| piece-north-transition-middle | North wall quarter pipe middle run | C740A0DE | 1172-1176 | wall-transition |
| piece-north-deck-middle | North wall quarter pipe middle deck | C740A0DE | 1177 | deck |
| piece-north-upper-transition | North wall upper tier transition | 2E2305EB | 1178-1187 | wall-transition |
| piece-north-upper-deck | North wall upper tier deck | 2E2305EB | 1188-1189 | deck |
| piece-north-transition-west-01 | North wall lower tier west transition | B0479048 | 1190-1194 | wall-transition |
| piece-north-transition-west-02 | North wall lower tier east transition | B0479048 | 1195-1199 | wall-transition |
| piece-north-tier-platform | North wall tier connecting platform | BAD88457 | 1200-1204 | deck |
| piece-south-transition-east | South wall quarter pipe east straight run | 279549C0 | 1205-1209 | wall-transition |
| piece-south-deck-east | South wall quarter pipe east straight deck | 279549C0 | 1210 | deck |
| piece-east-transition | East wall quarter pipe straight run | 50927956 | 1212-1218 | wall-transition |
| piece-east-deck | East wall quarter pipe straight deck | 50927956 | 1211 | deck |
| piece-south-transition-west | South wall quarter pipe west straight run | DE5B919F | 1246-1250 | wall-transition |
| piece-south-deck-west | South wall quarter pipe west straight deck | DE5B919F | 1251 | deck |
| piece-south-transition-return | South wall quarter pipe pocket to middle run | 403F043C | 1252-1256 | wall-transition |
| piece-south-deck-return | South wall quarter pipe pocket to middle deck | 403F043C | 1257 | deck |

### Start platform, roll-ins and upper enclosure

The two roll-ins are separate left/right modules. Start flat-bottom geometry
belongs to the platform, not the long roll-in. The high rear quarter pipe has
the same 8.06 rise as a wall pipe but starts at y 27.78.

| ID | Element | Groups | Faces | Module |
| --- | --- | --- | --- | --- |
| piece-start-fence-west | Start roll-in west lattice side panel | 9D14F7B5, 041DA60F | 1-23,48-70 | wall |
| piece-start-gable | Start rear wall and overhead lintel assembly | EA147B7B, ADCB734A | 389-426,723-760 | wall |
| piece-start-window-frame-west | Start window west frame | 602D8163, FE56F714 | 427-432,707-712 | wall |
| piece-start-window-frame-east | Start window east frame | F924D0D9, 78C285BA | 433-442,713-722 | wall |
| piece-start-transition-west | Start rear half pipe west transition | 5924357D, B2C3B10F | 443-447,681-685 | wall-transition |
| piece-start-transition-east | Start rear half pipe east transition | 5924357D, B2C3B10F | 448-452,686-690 | wall-transition |
| piece-start-rear-deck | Start rear half pipe high deck | 5924357D, B2C3B10F | 453-454,691-692 | deck |
| piece-rollin-east | East entrance curved roll-in | 4AA01023, 25DF6D67 | 455-462,650-657 | roll-in |
| piece-start-flat-east | Start half pipe east flat platform | 4AA01023, 25DF6D67 | 463-464,658-659 | flat |
| piece-start-enclosure-east | Start east side wall panels | 9A7E8FF4, FD06E2F9 | 465-489,624-648 | wall |
| piece-start-enclosure-west | Start west side wall panels | ED79BF62, 365A315C | 607-618,660-671 | wall |
| piece-start-lamp | Start rear overhead lamp | 895344B7, 12633D46 | 619-623,676-680 | support |
| piece-start-flat-west | Start half pipe west flat platform | EE83BEC2, 3DA720B5 | 694-697,773-776 | flat |
| piece-rollin-west | West entrance curved roll-in | EE83BEC2, 3DA720B5 | 698-705,765-772 | roll-in |
| piece-start-window-west | Start west individual window | 4F87E3FF | 761-762 | window |
| piece-start-window-east | Start east individual window | D68EB245 | 763-764 | window |
| piece-start-roof-east | Start east upper roof panel | 1ACB7E91 | 777-784 | roof |
| piece-start-roof-west | Start west upper roof panel | 83C22F2B | 840-847 | roof |
| piece-start-ceiling-middle | Start central flat ceiling panel | F4C51FBD | 848-854 | roof |
| piece-start-ceiling-east | Start east flat ceiling panel | 6AA18A1E | 855-860 | roof |
| piece-start-side-wall | Start roll-in lower west solid wall | AF25296F | 989-997 | wall |

The two start windows are intact `F2184063` sections but collision-open at
their starting location. The two frames still block. The source has neither
remake door splinters nor a separate animated roll-up-door asset to expose.

### Arena floor, ledges, walls and structural supports

These are named spatial panels, not one uneditable shell. Wall panels include
their textured brick/window bands; those painted bands are not separate glass
objects. Deep skirts and subterranean details remain individually accounted
for even though the kill floor makes them unreachable.

| ID | Element | Groups | Faces | Module |
| --- | --- | --- | --- | --- |
| piece-west-ledge-skirt | West ledge lower skirt | A8556103 | 235-236 | ledge |
| piece-west-foundation-north | West wall north foundation skirt | DA61E06B | 237-238 | wall |
| piece-south-under-ramp | South quarter pipe below-floor transition strip | 1C7398A9 | 239-250 | wall-transition |
| piece-west-foundation-end | West wall foundation end panel | 41C4AC04 | 251 | wall |
| piece-west-pillar-lower | West pillar below-floor section | 57B36E8A | 252-263 | support |
| piece-wall-northwest-bay | North west arena wall bay | 7470EED8 | 298-311 | wall |
| piece-wall-southeast-bay | South east arena wall bay | 731D2AC1 | 324-329 | wall |
| piece-wall-west-north | West arena wall north panel | 0377DE4E | 340-349 | wall |
| piece-floor-west-middle | West floor panel with surface decals | AD183D24 | 350-360 | floor |
| piece-floor-taxi-south | Taxi south floor panel | D4C48580 | 522-529 | floor |
| piece-floor-kickers | Kicker bay floor panel | 4DCDD43A | 530-533 | floor |
| piece-floor-northwest | North west floor panel | 3ACAE4AC | 534-535 | floor |
| piece-floor-rollin-toe | Entrance roll-in toe floor panel | D3A94199 | 536-538 | floor |
| piece-wall-pocket-back | South pocket rear wall panel | 041A1A57 | 539-547 | wall |
| piece-wall-east-entrance | East wall entrance end panel | 93C8C3DF | 861-869 | wall |
| piece-wall-east-north | East wall north of main half pipe | E4CFF349 | 870-875 | wall |
| piece-wall-east-pipe | East wall behind main half pipe and box | 84087AAC | 876-900 | wall |
| piece-wall-east-deck | East wall behind ledge and rail | F30F4A3A | 901-913 | wall |
| piece-floor-pipe-south | Floor south of main half pipe | CDDFB4C1 | 914-918 | floor |
| piece-wall-south-east | South wall east panel | 6A061B80 | 919-924 | wall |
| piece-wall-south-middle | South wall middle panel | 1D012B16 | 925-930 | wall |
| piece-wall-south-west | South wall west straight panel | 8365BEB5 | 931-936 | wall |
| piece-wall-south-end | South west corner wall panel | F4628E23 | 937-949 | wall |
| piece-wall-west-south | West wall south panel | 6D6BDF99 | 950-963 | wall |
| piece-wall-north-tier-side | North tier west side wall | 1A6CEF0F | 964-974 | wall |
| piece-wall-north-tier-end | North tier west rear wall | 8AD3F29E | 975-982 | wall |
| piece-wall-north-tier-back | North tier upper back wall | FDD4C208 | 983-988 | wall |
| piece-floor-rail-drain | Big rail platform and drain floor | 23D1D5ED | 998-1005 | floor |
| piece-floor-rail-south | Big rail south floor panel | BDB5404E | 1006-1018 | floor |
| piece-floor-rail-north | Big rail north floor panel | CAB270D8 | 1019-1023 | floor |
| piece-floor-west-north | West ledge north floor panel | 53BB2162 | 1024-1028 | floor |
| piece-floor-east-north | East entrance floor panel | 24BC11F4 | 1029-1030 | floor |
| piece-south-foundation | South wall deep foundation skirt | A89BBCBC | 1108-1110 | wall |
| piece-west-foundation-south | West wall south foundation skirt | 3192ED06 | 1111-1122 | wall |
| piece-floor-taxi-north | Taxi north floor panel | DA1F0DB2 | 1219-1224 | floor |
| piece-floor-east-drain | East ledge drain floor panel | A4AE710F | 1225-1232 | floor |
| piece-floor-east-south | East south floor panel | 54D6E57B | 1233-1235,1240-1245 | floor |
| piece-east-ramp-end | East quarter pipe ledge-height end cap | 54D6E57B | 1236-1239 | end-cap |
| piece-ledge-west | Shorty's west ledge top and front | 3999C81C | 1262-1269 | ledge |
| piece-ledge-east | East deck low ledge top and front | A09099A6 | 1270-1284 | ledge |
| piece-crane-hook | Suspended crane hook and chain | E2F52869 | 101-108 | support |
| piece-truss-east-north-01 | East north ceiling diagonal brace | E56DBEAE | 109-111 | support |
| piece-truss-east-north-02 | East north inner ceiling brace | 85AA374B | 112-114 | support |
| piece-west-pillar-upper | West pillar above-floor section | 4B768210 | 143-158 | support |
| piece-truss-south-01 | South ceiling brace west | EBB6369C | 159-161 | support |
| piece-truss-south-02 | South ceiling brace east | 72BF6726 | 162-164 | support |
| piece-truss-west-01 | West ceiling brace north | 82C7F352 | 165-167 | support |
| piece-truss-west-02 | West ceiling brace middle north | F5C0C3C4 | 168-170 | support |
| piece-truss-west-03 | West ceiling brace south | 6CC9927E | 171-173 | support |
| piece-truss-west-04 | West ceiling brace middle south | 1BCEA2E8 | 174-176 | support |

### Rails, taxi, kickers and loose boards

The big rail's straight and bent bars are separate pieces, including both
visible sides. Suppressed post plates get an explicit owner/disposition:
they are archival post-remnant pieces, **excluded from the default assembly's
render and collision**, matching `RemoveRailLeftovers`. Do not accidentally
restore them, or omit their accounting because they are hidden in the legacy
mesh. They can be exposed as optional repair/debris pieces, not structural posts.

| ID | Element | Groups | Faces | Module |
| --- | --- | --- | --- | --- |
| piece-rail-sign | High sign rail rod and wall brackets | 63097BD6 | 25-47 | rail |
| piece-kicker-south-frame | South kicker wooden frame | 51F9A12C | 129-132 | kicker |
| piece-kicker-north-frame | North kicker wooden frame | C8F0F096 | 133-136 | kicker |
| piece-rail-big-bend | Big rail bent bar and end cap | 8D071AFA | 363-365,373-375 | rail |
| piece-rail-big-straight | Big rail straight bar and end cap | 8D071AFA | 366-372,376-382 | rail |
| piece-post-remnant-01 | Big rail suppressed post plate 1 | E67C9BCD | 383 | suppressed-post |
| piece-post-remnant-02 | Big rail suppressed post plate 2 | 0F1F3EF8 | 384 | suppressed-post |
| piece-post-remnant-03 | Big rail suppressed post plate 3 | 96166F42 | 385 | suppressed-post |
| piece-post-remnant-04 | Big rail suppressed post plate 4 | E1115FD4 | 386 | suppressed-post |
| piece-post-remnant-05 | Big rail suppressed post plate 5 | 7F75CA77 | 387 | suppressed-post |
| piece-post-remnant-06 | Big rail suppressed bend post plate | 0872FAE1 | 388 | suppressed-post |
| piece-post-remnant-07 | Big rail suppressed post plate 7 | 917BAB5B | 490 | suppressed-post |
| piece-rail-deck | East deck rail bar | 140E4B40 | 496-512 | rail |
| piece-post-remnant-08 | Deck rail suppressed north post plate | 76C3865C | 513 | suppressed-post |
| piece-post-remnant-09 | Deck rail suppressed south post plate | 01C4B6CA | 514 | suppressed-post |
| piece-kicker-south-board | South kicker riding board | 81140CCD | 517-521 | kicker |
| piece-board-taxi-01 | Taxi north loose board 1 | B79E1F26 | 548-552 | prop |
| piece-board-taxi-02 | Taxi south loose board 2 | 59907E0A | 555-559 | prop |
| piece-board-taxi-03 | Taxi west loose board 3 | B0F3DB3F | 560-564 | prop |
| piece-board-taxi-04 | Taxi north west loose board 4 | 5EFDBA13 | 565-569 | prop |
| piece-board-taxi-05 | Taxi south east loose board 5 | B9459714 | 570-574 | prop |
| piece-board-floor-01 | East floor loose board 1 | D08B6AF6 | 575-578 | prop |
| piece-board-floor-02 | East floor loose board 2 | 39E8CFC3 | 579-582 | prop |
| piece-board-floor-03 | Big rail north loose board 3 | A0E19E79 | 583-586 | prop |
| piece-board-floor-04 | Big rail east loose board 4 | 4759B37E | 587-590 | prop |
| piece-board-floor-05 | Big rail west loose board 5 | 279E3A9B | 591-594 | prop |
| piece-board-floor-06 | Big rail middle loose board 6 | C9905BB7 | 595-598 | prop |
| piece-board-floor-07 | Big rail diagonal loose board 7 | BE976B21 | 599-602 | prop |
| piece-board-floor-08 | Big rail west middle loose board 8 | CEFD9FAE | 603-606 | prop |
| piece-taxi | Taxi funbox | B5300BF6 | 785-839 | prop |
| piece-kicker-north-board | North kicker riding board | 181D5D77 | 1285-1289 | kicker |
| piece-board-taxi-06 | Taxi east loose board 6 | C7F4EBA9 | 1290-1294 | prop |
| piece-board-taxi-07 | Taxi north east loose board 7 | 29FA8A85 | 1295-1299 | prop |
| piece-board-taxi-08 | Taxi south west loose board 8 | CE42A782 | 1300-1304 | prop |
| piece-board-floor-09 | East south loose board 9 | 49823B4C | 1305-1308 | prop |
| piece-board-floor-10 | East middle loose board 10 | A78C5A60 | 1309-1312 | prop |
| piece-board-floor-11 | East north middle loose board 11 | 4EEFFF55 | 1313-1316 | prop |
| piece-board-floor-12 | East diagonal loose board 12 | D7E6AEEF | 1317-1320 | prop |
| piece-board-floor-13 | Big rail south loose board 13 | 305E83E8 | 1321-1324 | prop |
| piece-board-floor-14 | Big rail centre loose board 14 | 50990A0D | 1325-1328 | prop |
| piece-board-floor-15 | Big rail north east loose board 15 | 20F3FE82 | 1329-1332 | prop |
| piece-board-floor-16 | Big rail north west loose board 16 | 57F4CE14 | 1333-1336 | prop |

Taxi bounds are x 121.64–137.36, y 0.83–5.24, z 76.17–81.57.
Its eight surrounding sloping boards are separate pieces, not welded into
the car. Kicker frames and boards may be grouped for placement but remain
independently editable; north board/frame meet near z 44.44–47.60, south
near z 61.13–64.28, board tops y 3.30.

### Signs, posters and graffiti overlays

These are textured overlay faces, not new mesh lettering or remake props.
Each row can move independently of its supporting wall. Paired start-area
copies stay with the same sign. Materials identify appearance, while the
source selector determines ownership.

| ID | Element | Groups | Faces | Module |
| --- | --- | --- | --- | --- |
| piece-sign-entrance-middle | Middle entrance overhead sign | 912CB677 | 24 | sign |
| piece-poster-northwest-01 | North west upper poster | 7C1384F6 | 95 | sign |
| piece-poster-northwest-02 | North west tall poster | ECAC9967 | 96 | sign |
| piece-graffiti-northwest | North west wall graffiti strip | 9BABA9F1 | 97 | sign |
| piece-poster-northwest-03 | North west lower poster | FB6C2014 | 98 | sign |
| piece-poster-rollin-east | East roll-in wall poster | 82B098B0 | 99 | sign |
| piece-graffiti-east-entrance | East entrance graffiti strip | D04173D7 | 100 | sign |
| piece-sign-south-high | South wall high sign | 7B7E40EF | 137 | sign |
| piece-sign-west | West wall banner | 921DE5DA | 138 | sign |
| piece-sign-northwest | North west wall banner | 0B14B460 | 139 | sign |
| piece-graffiti-east-south | East south wall graffiti | 8C6B1082 | 140 | sign |
| piece-poster-east-deck | East deck wall poster | 626571AE | 141 | sign |
| piece-sign-east | East wall banner | 120F8521 | 142 | sign |
| piece-sign-start-side | Start east side sign | 4948226D, 14E269BE | 271,649 | sign |
| piece-sign-south-underfloor | South foundation banner | 6C8D5CED | 361 | sign |
| piece-sign-start-middle | Start middle window sign | FCDA3430, C6365CE4 | 362,706 | sign |
| piece-sign-start-rear | Start rear wall banner | A7464341, 592AC8B5 | 491-493,672-674 | sign |
| piece-poster-start-rear | Start rear high poster | 3E4F12FB, DFBEBA1B | 494,675 | sign |
| piece-graffiti-start | Start window graffiti | D72CB7CE, 09E75906 | 495,693 | sign |
| piece-sign-skateboarding | SKATEBOARDING hanging sign | A02B8758 | 515-516 | sign |
| piece-poster-foundation-south | West foundation south poster | 4695DD90 | 1123 | sign |
| piece-poster-foundation-north | West foundation north poster | D8F14833 | 1124 | sign |
| piece-poster-box-east | Main pipe east wall poster | 15624138 | 1125 | sign |
| piece-poster-middle-pillar | Middle entrance pillar poster | F5B7A826 | 1126 | sign |
| piece-poster-west-north | West ledge north poster | 3922D6E2 | 1258 | sign |
| piece-poster-west-middle | West ledge middle poster | 4E25E674 | 1259 | sign |
| piece-sign-east-entrance | East entrance wide sign | 92DC24F5 | 1260-1261 | sign |
| piece-graffiti-south-west | South west wall graffiti | E51AD54C | 1337 | sign |
| piece-graffiti-east-north | East north wall graffiti | 6508B5B7 | 1338-1339 | sign |
| piece-graffiti-north-side | North side lower graffiti | 957021C3 | 1340 | sign |
| piece-graffiti-pocket-back | South pocket back graffiti | 8B06D49B | 1341 | sign |
| piece-banner-south-east | South east wall banner | FC01E40D | 1342 | sign |
| piece-banner-south-west | South west wall banner | 0C797079 | 1343 | sign |
| piece-banner-west | West ledge wall banner | DE9AFBE5 | 1344 | sign |
| piece-banner-entrance-middle | Middle entrance wall banner | A99DCB73 | 1345 | sign |

## Ramp module profiles and mating contract

Profiles are the original **piecewise-linear** riding surfaces, not circular
quarter pipes fitted to a radius. Keep every profile vertex and texture seam.
For the table below, `(run,rise)` starts at the toe; run points toward the lip.
Width can vary independently only when both mating edges retain the same
profile; uniform scaling is the safe initial palette transform. A reflected
module needs reversed winding/normals, not merely a negative collider scale.

| Module | Measured profile and height | Width and mating edges |
| --- | --- | --- |
| main-transition | South profile `(0,0), (4.931,1.334), (8.334,3.364), (10.538,6.671), (11.312,10.054), (11.370,10.692)`; toe y -4.933, lip 5.759 | Six 19.722-wide strips across x 119.781–178.949. Like-side profiles butt together; north is a near mirror with small source differences, not an exact reflection. Toe joins flat at z 19.945 or 32.436; lip joins the outer bank at z 8.595 or 43.806 (no horizontal main-pipe deck). |
| flat | Main bottom y -4.933, depth 12.491 (z 19.945–32.436) | Rectangular bottom joins both main toes. Start flats are separate at y 27.783, not interchangeable at the same elevation. |
| hip-apron | Seven triangular sloping faces from x 100.058 at y 0.5 to the main west profile x 119.781 at y -4.933–0.5 | Joins rectangular flat and the lower parts of both hip transitions. It is not a flat-bottom module despite occupying the bottom of the tapered end. |
| outer-bank / bank-end | Straight bank rises 5.259 over run 7.889, from floor 0.5 to lip 5.759 | Three strips on each side share the main transition lip; opposite toe meets arena floor. Two triangular west end pieces mate the hip end. South east strip is not rectangular: it meets the 3.787-high ledge. |
| hip | West end tapers from lip y 5.759 at x 119.781 to floor y 0.5 at x 100.058; three original faces per side | East edge mates to full main profile; west edge closes onto floor. Diagonal lip ends at z 3.51/48.87, not the straight lip's z. Keep both asymmetric end types. |
| wall-transition | Typical `(0,0), (1.547,0.522), (4.466,1.972), (6.574,4.447), (7.425,7.077), (8.082,8.063)`; floor 0.5 to lip 8.563 | Straight widths usually 19.722, with longer/shorter source runs retained. Side mates use the full profile, toes meet floor, lips meet deck. Upper north tier has same rise from 8.563 to 16.626; start rear from 27.783 to 35.846. Slight source variations (including steel faces and a 0.019 vertex offset) must not be rounded away. |
| corner | Same wall rise 8.063 swept through the three faceted sectors of a 90-degree concave turn | `piece-pocket-return` and `piece-southeast-corner` mate at both straight profile ends; their split decks fill the inside lip polygon. Rotate to reuse; do not replace with a smooth torus. |
| convex-tip | Same wall rise, each tip half turns 90 degrees in two faceted sectors; full tip turns back 180 degrees | West/east tip halves meet at x 80.335, lip z 85.030; side lips continue at x 77.048/83.622, z 88.317. Mate side transitions at z 88.317. Coping uses two chords across four mesh edges, not four short grind rails. |
| deck | Flat walking surface at the parent lip elevation; room slab thickness 0.329; wall decks generally 3.287 deep | Mate lip boundary without overlap; straight outer edge can mate another deck. Corner decks are polygonal, not bounding-box rectangles. Keep source fascia with its deck. |
| roll-in | Toe `(z,y)` is `(-19.017,0.5)`, then `(-20.564,1.022), (-23.483,2.472), (-32.262,8.447), (-40.499,16.007), (-48.756,22.562), (-58.017,26.952), (-65.752,27.783), (-73.312,27.783)` | Two tapered entrance lanes, separated by the centre pillar/channel. Upper edge meets start flat y 27.783; lower edge meets floor y 0.5. Width changes toward the top: preserve the boundary polyline, not a rectangular substitute. |
| kicker | Board rises from about 0.38 to 3.30 over about 10.06; frame from 0.5 to 3.19 | North/south boards face opposite directions and meet their frame at the original lip. Toe meets floor; side and rear edges are terminal, not quarter-pipe mates. |
| ledge | West/east top y 3.787, floor 0.5; vertical front with shaped plan outline | Top may mate a deck at y 3.787. This is an end/curb module, not a rideable transition. Separate skirt retains its own below-floor faces. |
| end-cap | East quarter pipe terminal face at z 79.770, y 3.710–8.563 | Vertical terminal face joins the 3.787-high east ledge and upper transition/deck boundary. It is not a riding face or a substitute for a full-height wall. |

The below-floor strip at faces 239–250 is an archival transition/end strip
(y -7.54–0), not an alternative floor-height wall pipe. Preserve it in the
assembly; never use its bounds as the regular wall pipe's profile.

For joins, compare the **ordered boundary vertices** after placement, not just
bounding boxes or nominal heights. Endpoints must coincide at source precision
and adjacent riding normals follow the original faceting. The wall ends and
hip ends above are the terminal modules; do not invent caps across open riding
edges. Splitting additional width strips is permitted later only along existing
face boundaries (or an explicitly recorded new cut with interpolated UVs).

## Importer and generator additions

No source-face selector is possible for these: their source is the named
code/config value below. Every enumerated instance needs an editable transform
or setting, not a hidden consequence of the monolithic Warehouse placement.
These are implementation requirements for the additive kit, not APIs that
already exist. Behaviour ownership can be grouped for convenience, but must
not prevent selecting an individual support or marker.

| Inventory ID / instances | Authoritative source | Editable form and ownership |
| --- | --- | --- |
| added-roof-quad-`ordinal` | `ThpsPack.AddRoof`, `WarehouseRoof.Quads`, spill-level ceiling and edge wall profiles | Bake each emitted quad as an addressed roof panel in emission order, recording its top/step/skirt/underside kind, cell/edge and original vertices. Preserve all generated quads and their lowered underside/inset; do not substitute a flat lid. Roof pieces have their own collision and may be selected/deleted individually. The room/source roof rows above are separate. |
| added-floor-patch-0 | `FloorPatches[0]`, `AddFloorPatches` | One floor patch, OBJ x 0.52–0.76, z 2.58–3.04, y -0.003 after Y flip; world x 20.876–39.884, z 48.614–85.046, y 0.2624. Keep fitted floor UVs and depth under decals. |
| added-post-0 through added-post-6 | `RailPosts[0:7]`, `AddRailPosts` | Seven independent 0.5-wide box posts below big rail: (x,z) (75,4), (75,16), (75,28), (75,40), (75,52), (78.3,56.8), (81.4,60.5). Bottom y 0.5, top 3.17, five faces each. Associate with straight/bend bars without baking into them. |
| added-post-7 through added-post-9 | `RailPosts[7:10]` | Three deck rail posts at (175.66,49.1), (175.66,61.3), (175.66,73.45), bottom 0.5, top 8.31. Same independent selection and collision as big rail posts. |
| added-grind-mesh-0 through added-grind-mesh-3 | `MESH_RAILS`, `hidden_rail_edit` | Four hidden game rail paths: big straight, big bend, sign rod, deck rail. Attach local path/collider metadata to the matching visible rail; expose path editing/selection even when render-hidden. Transform and delete with the bar; no second visible game rail. |
| added-grind-coping-0 through added-grind-coping-27 | Every ordered `COPING_LIPS` entry via `COPING_RAILS`/`rail_along` | 28 paths: indices 0–3 are main north/south and their west hips, 4–22 are the 19 wall/pocket lips, 23–26 the four west ledge lips, 27 the start lip. Keep exact source endpoints and two-chord pocket tip. A path spanning adjacent strips needs explicit ownership/subpaths without duplicate catch regions; splitting must preserve handoffs and avoid paths shorter than 3.5. Decks must not own a second copy. |
| added-boss-portal | `spawn_moves`, `gen:object:BossSpawner:0000` | Editable boss portal at (170,15.6,27), scale 0.4, yaw 90; retain hidden `BottomPiece` and `Collider`. Select/move the portal independently of the room. |
| added-boss-spawn | `bossSpawnPosition`, `boss_spawn_position()` | Separate editable destination marker, initially (170,-4.933,20) outside the box. Keep the explicit redirect when the portal moves; moving room/portal must not silently put the boss inside a closed room. Save the destination as a level setting. |
| added-radio | `radio_edits`, `RADIO_POSITION` | Ordinary `interactable/boombox` at (90,35.9,-123.5), separately movable/deletable. Playback track belongs to level music setting, not its geometry. |
| added-pile-R1 through added-pile-R5 | Baddy nodes 43,107,109,111,113; `collectibles()` | Five separate `interactable/chest` placements. These are replacements for goal piles, not five extra source crate meshes. Keep final anchored/overridden transforms. |
| added-letter-S, K, A, T, E | Letter nodes 28,29,17,13,12; `LETTER_SHRINES` | Five independently editable `forest/shrines/0..4` objects. T is the merchant prefab. Preserve upright rotation and deliberate overrides, not just node coordinates. |
| added-tape | Node 16 | Separate `interactable/chestFree` inside the room. |
| added-bonus-15, added-bonus-30, added-bonus-31 | `LANE_BONUS_NODES` | Three separately editable free chests. Nodes 148–150 (100/200/500 cluster) are intentionally not placed: no invented kit instances. |
| added-player-start | `PLAYER_START`, level `playerStart` | Editable start marker at (109,38,-116), where y is player centre, not feet. Marker saves the level setting independently of the portal. |
| retained-spawn-portal | `PlayerSpawnPortal`, `KEPT_OBJECT_CATEGORIES` | Existing generated portal remains separately selectable; the generator does not move it. Do not conflate its transform with `playerStart`. |
| retained-forest-particles | `ForestParticles`, `KEPT_OBJECT_CATEGORIES` | Retained generated effect roots, not OBJ geometry; retain normal object editability and visibility controls in the separate level. |
| added-terrain-bootstrap | `tile_edits`, `GENERATED_SPAWN_CELL` | Editable kept tile (10,7), height -1, slope none, with other 224 grid cells removed. Expose normal tile edits; preserve it during initial spawn before edits finish. |
| added-clutter-removals | `clutter_removals`, seed object/tile/scenery counts | Retain explicit removal edits for generated clutter; these are editable edit-stack operations, not a baked mesh remainder or new props. |
| settings-gameplay | `killFloorY=-35`, `maxSlopeAngle=88`, `grindRequiresSlide=true`, `noGrass=true` | Authored level controls, editable and saved once per level. Do not bake them into individual ramp assets. |
| settings-music | `music=bundle:thps/04_Superman` | Editable track reference, independent of boombox transform; soundtrack bytes stay baselined. |
| settings-presentation | `title`, `description`, `mapDescription`, `allowedCharacters` | Editable level metadata; initial values come from `build_level()` (Calcium/Tony McZoom restriction). |
| settings-generation | `map=1`, `stageIndex=0`, `tier=0`, `seed=20261007`, `packs` | Editable generation/pack dependencies; changing seed/map invalidates generated target IDs and needs regeneration, not silent reuse of removal IDs. |
| settings-format | `schemaVersion`, `gameBuildId` | Serialization/compatibility metadata, preserved by save/load rather than represented as scene objects. |

Roof generation must run against the same pre-partition geometry and post
repairs as the legacy importer. Re-running a spill calculation separately on
each movable piece would change its output and is not equivalent. Store the
baked roof panel transforms; do not rebuild it implicitly when a ramp moves.

## Landmark cross-check

This checks the inventory against the structures and M1–M15 map labels in
[the reference](thps-warehouse.md#structures). The reference mixes remake
imagery with a PS1 extraction: an unmatched remake detail is not evidence for
adding geometry to the preserved PS1 assembly.

| Reference landmark / structure | Inventory coverage and limits |
| --- | --- |
| M1 winding bank, M10 south notch | South wall transitions, pocket side/tip/return modules and split decks. Their world-space positions, not uncertain map headings, define placement. |
| M2 west platform / ledges | West Shorty's ledge, its skirt, adjacent floor, deck rail/sign rail where measured; five chest replacements remain separate. The remake/map's rail names do not prove a different source ownership. |
| M3 taxi | `piece-taxi` plus eight surrounding loose boards; distinct from the wall ramps. |
| M4 half pipe | Six transition strips, rectangular flat bottom, sloping tapered apron, six outer bank strips and their two end pieces, and two hip ends; four authored main/diagonal coping paths. |
| M5 glass corridor / secret room | Three wall frames, arena east wall, five individual window sections, floor and roof slabs, underside support and suspension pieces; tape, boss portal and destination separate. |
| M6 north bank, M7 middle quarter pipe/pillar, M8 east channel | Three lower north runs, upper tier, two independent roll-ins, centre/rear lintel assembly, side panels and window frames. The reference's exact map-to-world headings remain uncertain. |
| M9 east deck / back pipe | Tier platform, south/east deck/transition rows and the east ledge-height end cap cover the extracted decks and back pipes; do not substitute remake measurements for the source placement. |
| M11 south-east ledge | East low ledge with top/front faces, drain floor and adjacent arena wall. |
| M12 kickers | Two frames and two opposite riding boards, not one combined kicker pair. |
| M13 dark pit | Reference identification is unresolved. Extracted underfloor skirts, below-floor transition and drain panels are all assigned; no fabricated pit prop is needed to close coverage. |
| M14 raised start block / two entrances | High rear transition and deck, start flats, left/right roll-ins, windows, lattice/solid walls and upper roof/ceiling panels. |
| M15 big rail | Straight bar, bent bar, seven added posts, suppressed old plates, floor/drain, loose boards and two hidden grind paths. |
| High rail / SKATEBOARDING sign | Sign rod with original brackets, hanging sign faces and one hidden grind path; no added posts under the wall rod. |
| Deck rail | East bar, three added posts, two suppressed old plates and one hidden grind path. |
| Box piles / letters / tape / bonus icons | Fourteen actual game placements from final generator transforms; extracted goal-pile nodes are not wooden crate geometry. |
| Window wall / brick and graffiti walls | Spatial wall panels, textured window bands and independently assigned sign/poster/graffiti overlays. Source transparency is retained. |
| Ceiling / trusses / lamp / crane | Source upper roof/ceiling panels, ten ceiling/room diagonal braces, chains, crane hook, lamp, pillar sections and added spill roof panels. |
| Remake cones, barricades, truck, door splinters, sunlight shafts | No separate source objects or generator placements identified. Do not invent instances from video-only details; the source partition still covers every face. |

This is a source/measurement audit. The kit's palette listing, search,
thumbnails, placement at world scale, selection, rotation, drag-move, removal
and undo/redo were checked in the running editor through the dev harness for a
prop, a window and an added piece. Joint collision behaviour, the hidden grind
paths, save/reload round-trips and visual equivalence in an assembled level
remain open; the original preservation check stays the guard against changes to
the shipped Warehouse throughout that work.
