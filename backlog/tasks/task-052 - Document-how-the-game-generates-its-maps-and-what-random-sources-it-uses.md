---
id: TASK-052
title: Document how the game generates its maps and what random sources it uses
status: Done
assignee: []
created_date: '2026-11-07T23:07:00Z'
updated_date: '2026-11-08T00:54:00Z'
labels:
  - research
  - generation
dependencies: []
documentation:
  - docs/map-generation-determinism.md
  - docs/runtime-map-structure.md
priority: medium
type: spike
ordinal: 189000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The mod's generation log line records only counts and hashes, and the existing notes in docs/map-generation-determinism.md leave the core questions open: which function sequences generation, how the two tile-height algorithms consume randomness, what seeds the Desert and Hell terrain, how props are placed, and which random source the boss and miniboss draws use. Without those answers a level author cannot tell which parts of a generated level are fixed and which vary per run, and the custom-level work keeps hitting the same unknowns. Playing full Tier 2 runs to find out is slow and yields only the hash line, so the answers should come from the game's code.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 docs/map-generation-determinism.md answers each open unknown it lists, or states why it could not be answered: what sequences generation, how the Forest and Graveyard tile heights are drawn, what seed and parameters the Desert and Hell terrain generator receives, how props and interactables are placed, and which random source the enemy, miniboss and boss draws use.
- [x] #2 Every claim names its provenance (decompiled function with its address, dump signature, or measured in the running game), and the unknowns list is updated to match what remains unconfirmed.
- [x] #3 The write-up says which parts of a from-scratch custom level are deterministic and which still vary per run, with the evidence for each.
- [x] #4 Any new test or tool added to support the findings is covered by tests, and markdown lint passes.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Plan

Deliverable is docs only: docs/map-generation-determinism.md. docs/runtime-map-structure.md is owned by the sibling task and will not be touched. No game launches, no megabonk MCP calls - the sibling owns the running game, so anything needing a live measurement is marked as such instead of measured.

Method: static analysis only.
1. Signatures, fields, enums, RVAs from .tools/il2cpp_dump/dump.cs (rg -u scoped to that file).
2. Native decompiles from headless Ghidra 12.1.4 (Ghidra 12.1.4, MAXMEM 10G) against .tools/GameAssembly/GameAssembly.dll, which is byte-identical to the installed GameAssembly.dll (sha256 4350a7ae...), so dump.cs RVAs map to VA = 0x180000000 + RVA. The REA MCP is not wired into this session, so the same headless Ghidra it would drive is invoked directly through a local gitignored helper (.tools/ghidra_work/MBResearch.java, commands file) with the project cached under .tools/ghidra_work/proj.
3. Follow callee RVAs discovered in pass 1 decompiles in further headless batches (analysis is cached, so later batches are fast).

First decompile batch (RVAs from the task plus dump lookups): MapGenerationController.<GenerateMap>d__39.MoveNext 0x4A26F0, MapGenerator.GenerateMap 0x509EA0, Noise.GenerateNoiseMap 0x51CED0, GenerateHeightHein 0x422E10, GenerateHeightMe 0x4235E0, GenerateTileObjects.MapSpecificTiles 0x4962E0, RandomObjectSpawner 0x49C2A0, RandomMapObject.GetAmount 0x4810F0, RsgController.Generate 0x50F6E0, MapGenerationController.CryptGeneration 0x49A170, SummonerController.EventMiniboss 0x487240, SummonerController.SpawnStageBoss 0x487C20, EnemyManager.SpawnBoss 0x41A200, plus re-reads of ProceduralTileGeneration.Generate 0x5208A0 and the GenerateHeight dispatcher 0x423F10 for context.

Questions to close, in the order of the doc's Unknowns list: (1) who passes the Desert/Hell seed to MapGenerator.GenerateMap and with what noise parameters; (2) how GenerateHeightHein and GenerateHeightMe consume randomness; (3) which random source the enemy/miniboss/boss draws use; (4) RandomObjectSpawner raycast/rotation/alignWithNormal; (5) RsgController.Generate and the HasCustomSeed rules; (6) where mapSeed is written and read; (7) the residual Proton objectsHash drift (likely stays open - it needs a live measurement).

Then: rewrite the "How the original game uses random numbers, per map" section and "What stays random in an authored from-scratch level" with per-claim provenance (decompiled + function + address / dump signature / measured), refresh the Unknowns list, keep paragraphs one-line, and run markdownlint -c .markdownlint.jsonc docs plus mise exec -- task check.

Commit: atomic conventional commits, no attribution. Tooling stays in gitignored .tools/ so no new tracked tool needs tests; if a tracked test or tool becomes necessary, the failing test is written first.

Risks: headless analysis of GameAssembly.dll takes ~12 minutes once (cached afterwards); some tiny stub methods may not decompile (documented Ghidra limitation) - those claims stay at dump-level provenance. Il2Cpp static field writes show as DAT_ offsets, so mapSeed's writer may need offset matching against dump.cs field offsets.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Static analysis complete for every unknown closable without the running game. REA MCP is not wired into this session, so the headless Ghidra it would drive is invoked directly (Ghidra 12.1.4, analyzeHeadless -noanalysis -postScript on a cached project, MAXMEM=8G; at 12G the decompiler subprocess died with "Decompiler executable may not be compatible"). Helper and outputs live outside the repo (/Users/lance/megabonk-ghidra: work/MBResearch.java, work/commands*.txt, work/out/, proj/), so no tracked tooling and no new tests. The GameAssembly.dll analysed is sha256 4350a7ae..., identical to the installed copy, so dump.cs RVAs map to VA 0x180000000 + RVA.

Findings, with the address each claim rests on:

1. Sequencer, MapGenerationController.<GenerateMap>d__39.MoveNext 0x4A26F0: A_PreGeneration, isGenerating=true, mapSeed = UnityEngine.Random.Range(0, int.MaxValue) into statics+0xb8+0x2c; branch on MapData.mapType(0x70): Tiles(0) -> ProceduralTileGeneration.Generate(...,useDebugSeed=false), tileSpawnPosition/tileSpawnDir from the maze exit, GenerateTileObjects.Generate 0x495870, CryptGeneration when MapData.eMap(0x58)==8, four RandomObjectPlacer.RandomObjectSpawner passes 0x49C2A0, then SpawnInteractables.SetArea/SpawnRails 0x49D840/SpawnChests 0x49CF60/SpawnShrines 0x49E180/SpawnOther 0x49D4F0; ProceduralMesh(1) -> MapGenerator.GenerateMap 0x509EA0.
2. mapSeed (unknown 6): that MoveNext is the only writer in the binary - staticusers sweep over every function referencing the MapGenerationController statics block (DAT_182f59000) for the needle "+ 0xb8) + 0x2c" gives one HIT. Only other reader is InteractableCrypt.Teleport 0x4C90E0, which feeds RsgController.Generate on crypt entry. Never derived from debugSeed.
3. Tiles (unknown 2): ProceduralTileGeneration.Generate 0x5208A0 draws seed = useDebugSeed ? debugSeed(0x20) : Random.Range(0,int.MaxValue), Maze.Generate(size,size,seed) 0x423F60, write-back debugSeed = seed, then the height dispatcher 0x423F10 on MapParameters.heightGenerationStrategy(0x40): 0 -> GenerateHeightHein 0x422E10, 1 -> GenerateHeightMe 0x4235E0. Each builds a private new System.Random(seed) (0x14F8D30) and draws through vtable slot 0x198 Next(int,int) / 0x1b8 NextDouble() against volatility(0x18) and biasStrategy(0x3c); no Unity Random. Then FillHoles 0x520260 and one edge pass by currentStage(0x88)->StageData.mapEdgeFillType(0x28): 0 FillEdgesIsland 0x51E4D0, 1 FillEdgesWalls 0x51EAE0, 2 FillEdgesTrees 0x51E8D0, 3 none.
4. ProceduralMesh (unknown 1): 0x509EA0 copies StageData.proceduralTerrainData(0xF8)/proceduralNoiseData(0x100)/proceduralMapScale(0x108) then GenerateMap(int) 0x509B90 -> GeneratePerlinNoiseMap(seed) 0x509F80 -> Noise.GenerateNoiseMap 0x51CED0, which builds new ConsistentRandom(seed) (0x4F88F0) and takes Next(-100000,100000) per octave before Mathf.PerlinNoise, then min/max normalises; FalloffGenerator and MeshGenerator.GenerateTerrainMesh 0x51C920 draw nothing. Terrain is a pure function of mapSeed.
5. Crypt (unknown 5): RsgController.Generate 0x50F6E0 uses customSeed (statics+0x18) when customSeed != 0 and CanUseCustomSeed() (0x50EC70 -> !ChallengesTracker.HasChallengeModifier 0x3FEC30), else Random.Range(0,int.MaxValue); sets isCurrentMapRandomSeed (statics+0x28), seed (statics+0x8) and random = new ConsistentRandom(newSeed). .cctor 0x50FDC0 defaults seed 0x10f2c (69420), customSeed 0; HasCustomSeed 0x50FEC0 is customSeed != 0; debug console SetSeedCrypt 0x3D8F00 and GetSeed 0x3D8A20. CryptGeneration 0x49A170 draws nothing.
6. Props (unknown 4): RandomObjectSpawner 0x49C2A0 count = RoundToInt(GetAmount() * amountMultiplier) plus ItemBeacon.GetExtraShrines extras; per instance one Random.value for the box position, SpawnPositions.GetObjectSpawnPosition 0x483470 (50 attempts, ground layer, maxSlopeAngle 0x24), upOffset(0x28)*Random.value along the hit normal, Random.Range(0,prefabs.Length), alignWithNormal(0x44) false -> Quaternion.Euler over scaleMin(0x1C)/scaleMax(0x20) plus three more Random.value, else Quaternion.LookRotation(normal); localScale *= Random.value. RandomMapObject.GetAmount 0x4810F0 returns amount(0x10) when maxAmount(0x14)==0 else MyRandom.random.Next(amount, maxAmount+1). MapSpecificTiles 0x4962E0 makes no draws.
7. Enemies (unknown 3): StageSummoner.AddEnemyToPoolAndPickNewCard 0x485DB0 picks the pool entry with Unity Random.Range; BaseSummoner.GetRandomCard 0x46CDD0 and SummonerController.EventMiniboss 0x487240 draw on MyRandom.random; SummonerController.SpawnStageBoss 0x487C20 uses Random.insideUnitSphere; EnemyManager.SpawnBoss 0x41A200 spawns nothing itself.
8. MyRandom is only a holder: public static System.Random random; .cctor 0x3C4B30 does new System.Random() -> 0x14F8CD0 -> ..ctor(GenerateSeed()) 0x14F8630, so the old doc claim that it is seeded from QueryPerformanceCounter is wrong (no perf-counter read on that path). ConsistentRandom : System.Random with the ordinary subtractive int-seeded constructor, so it is seed-reproducible.
9. Corrections to the previous doc: MapEdgeFillType is Island 0, Walls 1, Trees 2, None 3 (the doc had 1 and 2 swapped); the previously cited GenerateTileGrid and the earlier FillEdges*/FillHoles addresses were bogus (Ghidra merged those entries into neighbouring functions) - the real ones are in item 3.
10. Desert reconciliation: runtime-map-structure.md measures mapType=1 with proceduralTiles null and Generate never called, so the recorded Desert hash cannot be describing terrain, and objectsHash covers only scene-root (Clone) props - terrain height is not in it. The cross-run identity of that hash is explained by seed_force_patch.cs ReseedPhase, which calls Random.InitState(phaseSeed) and MyRandom.random = new ConsistentRandom(phaseSeed) per spawn phase while a force is active.

Still open, all listed in the doc's Unknowns: the Proton objectsHash drift needs a live measurement (the sibling owns the game); the exact mix inside System.Random.GenerateSeed; the challenge-modifier name CanUseCustomSeed tests; whether Unity Random persists across an authored map's generation chain; SpawnInteractables.SetArea and RandomObjectPlacer.GenerateInteractables have no direct call sites; Hell and Dungeon branches are inferred from mapType only.

Docs: docs/map-generation-determinism.md rewritten - MyRandom seeding fixed, Desert results restated as hash stability rather than terrain determinism, new "The generation sequence" subsection, generator table rebuilt with addresses, Tiles/ProceduralMesh/Props sections updated, new Crypt and Enemies subsections, What stays random and Unknowns rewritten. markdownlint clean; mise exec -- task check passes (1105 tests, ruff clean). docs/runtime-map-structure.md untouched.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Static analysis (headless Ghidra + Il2Cpp dump) answered all six open questions in docs/map-generation-determinism.md: the sequencer is MapGenerationController.<GenerateMap>d__39.MoveNext (0x4A26F0), which is also the only writer of mapSeed; Tiles run on a per-call seed shared by Maze.Generate and a private System.Random in each height variant; ProceduralMesh terrain is a pure function of mapSeed through Noise.GenerateNoiseMap's ConsistentRandom; the crypt reuses mapSeed unless RsgController.customSeed is set; props split between MyRandom.random for counts and the Unity stream for transforms; enemy pool, card, miniboss and boss draws were each attributed. Two stale claims were fixed (MapEdgeFillType numbering, the QueryPerformanceCounter seeding story). Live-only items are listed as Unknowns.
<!-- SECTION:FINAL_SUMMARY:END -->
