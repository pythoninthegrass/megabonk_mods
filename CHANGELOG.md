# Changelog

## [0.3.0](https://github.com/pythoninthegrass/megabonk_mods/compare/v0.2.0...v0.3.0) (2026-11-20)


### Features

* bridge native and lifted arm64 calls with typed adapters ([489e95a](https://github.com/pythoninthegrass/megabonk_mods/commit/489e95acd94cd50a14ee52e4530b4aa5ae930781))
* **characters:** add the Squeaker model, rig, cookie and icon ([a1fcb58](https://github.com/pythoninthegrass/megabonk_mods/commit/a1fcb58535fbf39a36a92634865f13d6617f4cf3))
* **characters:** build the squeaker asset bundle from the Squeaker FBX exports ([00f71fe](https://github.com/pythoninthegrass/megabonk_mods/commit/00f71fe12929cf6f255b47e02bf7a554c1cdbd63))
* **characters:** keep mod character runs off the Steam leaderboards ([57515da](https://github.com/pythoninthegrass/megabonk_mods/commit/57515da61f87744b86c889dfbe8ef286edf6023e))
* **characters:** register Squeaker with the Tiny Target passive and a stale cookie weapon ([a7ecf46](https://github.com/pythoninthegrass/megabonk_mods/commit/a7ecf46e3b11dbc1c033f44ecead4616bbfcf7ff))
* **characters:** wire the Squeaker controller to the player renderer's Animator parameters ([d0643ef](https://github.com/pythoninthegrass/megabonk_mods/commit/d0643ef2860e43a1228b241ba3bf60f22b4a6f15))
* **deploy:** deploy the PocketBase API with the site ([b2d0c11](https://github.com/pythoninthegrass/megabonk_mods/commit/b2d0c11db94fbee7d0f68b614a96a86366b4d4ad))
* **il2cpp_dump:** dump the pinned Linux pair and score its names ([f57d6a3](https://github.com/pythoninthegrass/megabonk_mods/commit/f57d6a340de77a12e0673a579086eeb812ebeca4))
* **installer:** add a megabonkmod.party API client ([#14](https://github.com/pythoninthegrass/megabonk_mods/issues/14)) ([fb43ed9](https://github.com/pythoninthegrass/megabonk_mods/commit/fb43ed9d3350e29d706f7fa4140d45866a8ab8bf))
* **installer:** install BepInEx and the level editor mod ([#17](https://github.com/pythoninthegrass/megabonk_mods/issues/17)) ([a856e43](https://github.com/pythoninthegrass/megabonk_mods/commit/a856e430ce7774c2beaec8619c4bce6178c6f8b5))
* **installer:** install levels, images and pack zips into UserData ([#16](https://github.com/pythoninthegrass/megabonk_mods/issues/16)) ([5198fc1](https://github.com/pythoninthegrass/megabonk_mods/commit/5198fc162a4a771f295ddaf878c058904cb6aa75))
* **installer:** plan and apply level installs from share codes, links and files ([#19](https://github.com/pythoninthegrass/megabonk_mods/issues/19)) ([7534af9](https://github.com/pythoninthegrass/megabonk_mods/commit/7534af9723806976ddbf1b57c8181da928803729))
* **installer:** resolve the mod and BepInEx pack from Thunderstore ([#15](https://github.com/pythoninthegrass/megabonk_mods/issues/15)) ([76514f1](https://github.com/pythoninthegrass/megabonk_mods/commit/76514f1eb94e743b735d79d956e0515b11e85dfb))
* **lift:** account for every exception-bearing body and document the unwind contract ([87ee833](https://github.com/pythoninthegrass/megabonk_mods/commit/87ee8331b80a647458272db93ea79b5822f8b7e0))
* **lift:** account for every executable byte of the image before a full lift ([4077c2f](https://github.com/pythoninthegrass/megabonk_mods/commit/4077c2f14333e20b69b0aab973bd3470eccfae95))
* **lift:** add raw register-file imports, a pending-exception guard and the guest unwinder runtime ([9ddafe0](https://github.com/pythoninthegrass/megabonk_mods/commit/9ddafe037a9a723679915ab597209bb3d14aba51))
* **lift:** audit frame bounds in targeted jump recovery ([32d933f](https://github.com/pythoninthegrass/megabonk_mods/commit/32d933f38a2f31905f3e59da83401d4bfa32649d))
* **lift:** bind cpuid and rdrand to host helpers in the generated shim ([d0fc767](https://github.com/pythoninthegrass/megabonk_mods/commit/d0fc7675bac5659df753dfd3cf1ebf368cb8ea84))
* **lift:** bound targeted jump-table recovery ([322e019](https://github.com/pythoninthegrass/megabonk_mods/commit/322e01990a0e7116cf16d3ce9b90ed232c0b96dc))
* **lift:** build unwind tables from frame descriptions and reject unrepresentable sets ([a204630](https://github.com/pythoninthegrass/megabonk_mods/commit/a204630975436efef0cd297800eec38bd31c6f9a))
* **lift:** check landing pads of every LSDA body against dumped pcode ([3f89de4](https://github.com/pythoninthegrass/megabonk_mods/commit/3f89de41d498fef0d8445573d6d4ed0d4234f766))
* **lift:** decide switch cases from the image's table bytes ([0ebce80](https://github.com/pythoninthegrass/megabonk_mods/commit/0ebce802e8af9033e665cbb6dc45a13631ff2b96))
* **lift:** emit pending-unwind checks and landing-pad dispatch behind an unwind mode ([a7092cf](https://github.com/pythoninthegrass/megabonk_mods/commit/a7092cf92a80e7a25c8bb8f1689574b01a7a111b))
* **lift:** execute a lifted shipped method natively on arm64 ([763d2f1](https://github.com/pythoninthegrass/megabonk_mods/commit/763d2f1ca08855e515a5b2c559ce4864db8dfe56))
* **lift:** give each export call a private guest TLS block ([7458432](https://github.com/pythoninthegrass/megabonk_mods/commit/745843225389d9f70c1e2cce4b6660ef88bc4b8a))
* **lift:** implement pshuflw immediate word shuffle ([2cf00be](https://github.com/pythoninthegrass/megabonk_mods/commit/2cf00be809451e65085a567df3600bc1f2c064c5))
* **lift:** lift a handed-over indirect jump as a sibling call ([a1131ee](https://github.com/pythoninthegrass/megabonk_mods/commit/a1131eea145a93f4ab2da3db3845aa645641bfe9))
* **lift:** lower a proven-balanced BRANCHIND as an indirect tail call ([2e08d77](https://github.com/pythoninthegrass/megabonk_mods/commit/2e08d77467e29d226be1700a5c63bc7e68f328b1))
* **lift:** lower a switch from the image's own jump-table bytes ([04145b7](https://github.com/pythoninthegrass/megabonk_mods/commit/04145b7a4c654548fe6df9884d2da6a486813ac0))
* **lift:** lower Ghidra lock regions as arm64 atomics ([43e31fa](https://github.com/pythoninthegrass/megabonk_mods/commit/43e31fa0120b69dff6ce8fac166b7cc074d79371))
* **lift:** lower maxpd, packssdw, movmskpd and pshufhw ([b2570f5](https://github.com/pythoninthegrass/megabonk_mods/commit/b2570f5adf44dd979ae634a81b633ad97f1e3fc7))
* **lift:** lower packed float sign-bit masks ([03ec21b](https://github.com/pythoninthegrass/megabonk_mods/commit/03ec21be706d08370f99306f09d5f6fa863fb7d1))
* **lift:** lower the 80-bit x87 float ops the image contains ([efbf4bc](https://github.com/pythoninthegrass/megabonk_mods/commit/efbf4bc41de34062e46d50d9fd1b596e4d70c8cd))
* **lift:** lower the CALLOTHER tail of the pinned image ([578a9a2](https://github.com/pythoninthegrass/megabonk_mods/commit/578a9a2d912cbb1d4a731b44d663c5cbe6ffa6a9))
* **lift:** match typed catch through relocated typeinfo words ([eff8e35](https://github.com/pythoninthegrass/megabonk_mods/commit/eff8e359f65ce2ae0a78d3e4ae6417d66a96cd45))
* **lift:** name scored bodies from the Linux metadata dump ([2b3f60f](https://github.com/pythoninthegrass/megabonk_mods/commit/2b3f60fda365ef02115ceb69ac5735bb3e4d3c1b))
* **lift:** parse call-frame rows and landing pads from exception metadata ([8773b5c](https://github.com/pythoninthegrass/megabonk_mods/commit/8773b5c16b39329cc11b50ad0cc45c70a05ccbc7))
* **lift:** reject typed catch and exception specifications in unwind tables ([0e0716c](https://github.com/pythoninthegrass/megabonk_mods/commit/0e0716ccc2846b01749e18d9a614d6a649148c7b))
* **lift:** report evidence switches in the blocker rescore summary ([90cb28f](https://github.com/pythoninthegrass/megabonk_mods/commit/90cb28f96a6e8272543e26d5eabb13b703bf960e))
* **lift:** resume rescoring baseline blockers ([ebd9ca8](https://github.com/pythoninthegrass/megabonk_mods/commit/ebd9ca89b0091d37f91748afc4642dc20fa68cdb))
* **lift:** run the shipped libsupc++ lifted under the guest unwinder ([15b3911](https://github.com/pythoninthegrass/megabonk_mods/commit/15b39115af8e0d450946cb7e94cab52769d57ca1))
* **lift:** score the pinned executable image in resumable shards ([cf2ed81](https://github.com/pythoninthegrass/megabonk_mods/commit/cf2ed81ade962e4e6547b134c06a1ba0a8c16932))
* **lift:** unwind lifted C++ exceptions through a guest-stack unwinder ([7f86a3d](https://github.com/pythoninthegrass/megabonk_mods/commit/7f86a3d150828969c2e4c8fbe187fe5189ead7b2))
* **mcp:** add the blender MCP server ([86c65b0](https://github.com/pythoninthegrass/megabonk_mods/commit/86c65b0e34ea11516f31e0b8a02613acc9a386fe))
* **mod:** say which steam_api64 backs a readiness verdict ([25eebe8](https://github.com/pythoninthegrass/megabonk_mods/commit/25eebe853c2f70632940678c3b97e1f515581bdf))
* **pocketbase:** add security headers to API responses ([b132af5](https://github.com/pythoninthegrass/megabonk_mods/commit/b132af581f3b5a522e793ea73bd9a342b1316257))
* **pocketbase:** add site owners and per-user level visibility ([89d4bd5](https://github.com/pythoninthegrass/megabonk_mods/commit/89d4bd53de2a4e2a85021da5af39a37c5033a7e1))
* **pocketbase:** add the level gallery API service ([dec68fb](https://github.com/pythoninthegrass/megabonk_mods/commit/dec68fbb4c92f52aee5a16022458746338877e08))
* **pocketbase:** host asset packs and categorize reports ([5c145eb](https://github.com/pythoninthegrass/megabonk_mods/commit/5c145eb119bb16d9dde0f3cbf9cfb5c41fb8507d))
* **pocketbase:** rate limit requests from the environment ([08a5e44](https://github.com/pythoninthegrass/megabonk_mods/commit/08a5e44bbd114f62d6b693c537194ef74dceaf62))
* **pocketbase:** schedule backups from environment ([f9b6655](https://github.com/pythoninthegrass/megabonk_mods/commit/f9b66553d24c7368650d9b1e5fd7c27e6f05ac8e))
* **re:** add arm64 liftability probe for the shipped il2cpp code ([d7628ee](https://github.com/pythoninthegrass/megabonk_mods/commit/d7628eeded6373df8543ffdaa11025bcb3428f94))
* **re:** audit the indirect tail-call rule against the decompiler ([6407cd2](https://github.com/pythoninthegrass/megabonk_mods/commit/6407cd2ad33b7949f20b95af465d8058c10b018d))
* **re:** census base-relative relocations by what they point at ([a4efd98](https://github.com/pythoninthegrass/megabonk_mods/commit/a4efd98ee67d5d41952735a4bd6e5ce88a11178d))
* **re:** census exception handling across the il2cpp section ([5426506](https://github.com/pythoninthegrass/megabonk_mods/commit/5426506c044e11e24e810f2930da25fed03853cf))
* **re:** census hole kinds on larger samples and account for dropped bodies ([c31c918](https://github.com/pythoninthegrass/megabonk_mods/commit/c31c918c00e28e72ce9fd3af7169a353b27b06d9))
* **re:** classify the unresolved computed jumps left in the lift sample ([c226525](https://github.com/pythoninthegrass/megabonk_mods/commit/c226525569a322473313e1d097ba20418aa16831))
* **re:** compare LLVM optimisation pipelines on lifted code ([276074d](https://github.com/pythoninthegrass/megabonk_mods/commit/276074d7cac642f82c74acc7a11762fe1b8c53ac))
* **re:** lift packed float and double division in the pcode emitter ([e2ce897](https://github.com/pythoninthegrass/megabonk_mods/commit/e2ce897cf15f274a14131257de6c4f7d202880e0))
* **re:** lift packed float minps and maxps with the x86 lane rule ([47ca036](https://github.com/pythoninthegrass/megabonk_mods/commit/47ca0366f4fdcc6fbbb03b35b8a1cbf5fb1e911c))
* **re:** match x86 float-to-int conversion in the pcode emitter ([1425908](https://github.com/pythoninthegrass/megabonk_mods/commit/1425908ab68cc26f4df6b018c471326504de1c9d))
* **re:** score the shipped GLSL to Metal translation pass ([1d33a01](https://github.com/pythoninthegrass/megabonk_mods/commit/1d33a011f4c6371f3a34d85604213fa25cb65b08))
* **research:** bind the Il2Cpp runtime by symbol without a mod loader ([a827655](https://github.com/pythoninthegrass/megabonk_mods/commit/a82765561e519b743c04807282b74b095db4486c))
* **research:** record the exception a shipped method throws as an oracle ([d5f4624](https://github.com/pythoninthegrass/megabonk_mods/commit/d5f4624e049baec788790c06c5cc40ce932d4463))
* **research:** score the ELF-load-and-shim step behind Route B ([829ca64](https://github.com/pythoninthegrass/megabonk_mods/commit/829ca640a21c18979299411cefed078cb2716a57))
* **site:** add a branded not-found page ([8e98ba6](https://github.com/pythoninthegrass/megabonk_mods/commit/8e98ba66e90b9c34e88759b9c4bc65b7e449803c))
* **site:** add a dev panel to switch users and delete levels in site:dev ([298e60e](https://github.com/pythoninthegrass/megabonk_mods/commit/298e60e4bc9841146e9b74a81871389c5860ea1e))
* **site:** add creator pages listing a maker's levels ([696d9a5](https://github.com/pythoninthegrass/megabonk_mods/commit/696d9a500444d0d32e5d650b994808bd11dd727b))
* **site:** add level gallery browse, level and upload pages ([13082f7](https://github.com/pythoninthegrass/megabonk_mods/commit/13082f7294ec4d744d75e69e28c474b6df74f313))
* **site:** add level share-code helpers and the /l/&lt;code&gt; route ([7c62b4a](https://github.com/pythoninthegrass/megabonk_mods/commit/7c62b4a3848a5067885c986e6404bff872ef75bf))
* **site:** add owner moderation controls to level cards and pages ([171aff2](https://github.com/pythoninthegrass/megabonk_mods/commit/171aff260c88dab892b05744201462f1e029374e))
* **site:** add pack pages, pack upload and copyright reports ([c5b78a0](https://github.com/pythoninthegrass/megabonk_mods/commit/c5b78a03ff87f2a0cf1ebcb1c2a0d1981df17317))
* **site:** keep the gallery stable while navigating from the showcase ([f32fc73](https://github.com/pythoninthegrass/megabonk_mods/commit/f32fc73e92645f8d670bccc101c191170c9118ff))
* **site:** like and download from the level cards ([fa17292](https://github.com/pythoninthegrass/megabonk_mods/commit/fa1729210db8e9d2025a4144ea5c295b7e8bace7))
* **site:** like and download from the level page counts ([76612d7](https://github.com/pythoninthegrass/megabonk_mods/commit/76612d740dd1c1b3e7d30d65ce48a79a4ead2a8d))
* **site:** link level owners to the edit form ([3f72b1e](https://github.com/pythoninthegrass/megabonk_mods/commit/3f72b1efb281882566b69d83977f62a43e7a4898))
* **site:** match giscus discussion titles strictly ([ca52588](https://github.com/pythoninthegrass/megabonk_mods/commit/ca525881a3eef9183625ea2cb9f0a5efb79b6901))
* **site:** offer only the sign-in providers the API has configured ([8736acc](https://github.com/pythoninthegrass/megabonk_mods/commit/8736accb2fe2869b638920edd795b4b3908bfcb9))
* **site:** open a level for editing from a link ([7ca643a](https://github.com/pythoninthegrass/megabonk_mods/commit/7ca643a607518592486d1816c34860f9ab232744))
* **site:** publish security.txt ([f089fe3](https://github.com/pythoninthegrass/megabonk_mods/commit/f089fe360c5a17866929513e4e7e877913addc18))
* **site:** revalidate html pages and send ETags ([6b6b093](https://github.com/pythoninthegrass/megabonk_mods/commit/6b6b093089b5f4835f9541681ce75af9321cbc08))
* **site:** run Mailpit and enable SMTP in the dev API ([f85e1bf](https://github.com/pythoninthegrass/megabonk_mods/commit/f85e1bf1b4dada6e650fe78461fcc2236025de8a))
* **site:** send security headers and a content security policy ([c601268](https://github.com/pythoninthegrass/megabonk_mods/commit/c601268a56959996aadd96a9af0ac3bcbd1f4ab8))
* **site:** serve wiki guides at the docs hostname root ([41d5454](https://github.com/pythoninthegrass/megabonk_mods/commit/41d5454692f189b6561c815206f718e3474d302b))
* **site:** show heart and download icons beside the counts ([e708907](https://github.com/pythoninthegrass/megabonk_mods/commit/e708907119fa5d50ee04cd83f183a3cbaac4b1ed))
* **site:** sign in as a seeded maker through a dev-only route ([33c6c68](https://github.com/pythoninthegrass/megabonk_mods/commit/33c6c684523aaa21633e93977b0b727a3f671464))
* **site:** start a seeded local API and share-link rewrites in site:dev ([d38fbe0](https://github.com/pythoninthegrass/megabonk_mods/commit/d38fbe08e6e14e692be979d463e97476e5f3e7bd))
* **vita:** add boss, final swarm and portal exit to the combat slice ([b8190bf](https://github.com/pythoninthegrass/megabonk_mods/commit/b8190bf0eee1e4ca3e1b74f363204cdd786d3527))
* **vita:** add Forest combat feasibility prototype ([aa3d6db](https://github.com/pythoninthegrass/megabonk_mods/commit/aa3d6db33c9d03b0c1d7fd5f9c7825e05cf179c3))
* **vita:** add native hardware smoke test ([7fa66a9](https://github.com/pythoninthegrass/megabonk_mods/commit/7fa66a923027cf626815b6380e359a0893b117c9))
* **vita:** add paired benchmark sweep and gate check to combat spike ([a01f355](https://github.com/pythoninthegrass/megabonk_mods/commit/a01f355ceacaa59e92918058aa027487fcb4b635))
* **vita:** add Tony McZoom character data and apply his move speed ([f448e1f](https://github.com/pythoninthegrass/megabonk_mods/commit/f448e1fcce71ea88ed4ee412d015c22a6a75d9b8))
* **vita:** replace the spike upgrades with OpenBonk-style level-up offers ([2315261](https://github.com/pythoninthegrass/megabonk_mods/commit/2315261617f42d2291c84f867f326114fdb57183))


### Bug Fixes

* **characters:** enable the Unity animation module so the squeaker bundle keeps its Animator ([fe31b0e](https://github.com/pythoninthegrass/megabonk_mods/commit/fe31b0e31f160898b2a28dd865af9abaad0dad5d))
* **characters:** keep Squeaker out of stats and tier completion saves ([d095697](https://github.com/pythoninthegrass/megabonk_mods/commit/d095697ea2bbe6b2eb2ce6f0a1ba6b42d41dc12d))
* **launch:** forward the stub's failed-init switch through the GUI handoff ([e4aa904](https://github.com/pythoninthegrass/megabonk_mods/commit/e4aa904d6e4d9f615d51f26193054ed5315b89f2))
* **lift:** key scored shards on the lifter and tool timeout ([ac31d4d](https://github.com/pythoninthegrass/megabonk_mods/commit/ac31d4d3e5e38c5f6bdec818bad8464cbb87aac8))
* **lift:** license a proven-balanced BRANCHIND only for a memory-read target ([4c7fd88](https://github.com/pythoninthegrass/megabonk_mods/commit/4c7fd884c51f9840b66415c92a5e570b8f7046c3))
* **lift:** name the gate that refused a BRANCHIND ([b5ee002](https://github.com/pythoninthegrass/megabonk_mods/commit/b5ee00260562facd36a883d44d60749d85c90630))
* **lift:** preserve complete dump rows after tool timeouts ([7a7b6fc](https://github.com/pythoninthegrass/megabonk_mods/commit/7a7b6fcd43d6a12010b33e63122f2b3533c812bf))
* **lift:** require a guarded straight-line span for an evidence switch ([3959f81](https://github.com/pythoninthegrass/megabonk_mods/commit/3959f81de3f0a706f9cd3614d8b08b01f22bc454))
* **pocketbase:** accept a multipart update without a level file ([a545f43](https://github.com/pythoninthegrass/megabonk_mods/commit/a545f4342c336a90646d3b3cddfb161b2ab6d385))
* **pocketbase:** reject queries that probe the visibility lists ([ccd6c99](https://github.com/pythoninthegrass/megabonk_mods/commit/ccd6c99c7e7cf46e42d68f33a4214317d8e118b6))
* **repair:** normalize doorstop paths that point outside the game folder ([69eaaf3](https://github.com/pythoninthegrass/megabonk_mods/commit/69eaaf3b0519049509086cd6393fbe42a52cc262))
* **site:** allow giscus stylesheet in the content security policy ([3baf4b5](https://github.com/pythoninthegrass/megabonk_mods/commit/3baf4b5bf7c45a0ec69e58c70f22373f3ad43a8f))
* **site:** clarify edit mode and tighten the mobile gallery layout ([f5b7f0f](https://github.com/pythoninthegrass/megabonk_mods/commit/f5b7f0f7e7f474d0cc815f5681e027cbbc75c136))
* **site:** disable new-login alerts on the dev API ([659ab83](https://github.com/pythoninthegrass/megabonk_mods/commit/659ab83dbd3f24eefb16b116e78b73f9f49118b5))
* **site:** harden gallery loading and accessibility ([279995d](https://github.com/pythoninthegrass/megabonk_mods/commit/279995d8155b9d19f6075d7ad82b42b722d572a1))
* **site:** rank level page actions and keep keyboard focus on delete ([15bd27f](https://github.com/pythoninthegrass/megabonk_mods/commit/15bd27f864f3daa7b2c978c0ab17687c802cd07a))
* **site:** return to the level page when canceling an edit opened from it ([400a511](https://github.com/pythoninthegrass/megabonk_mods/commit/400a5115b9bc8e3f6205aafc03c3cffc3422d019))
* **site:** shorten the dev sign-in snippet to the session fields the pages read ([1fe8f11](https://github.com/pythoninthegrass/megabonk_mods/commit/1fe8f11f242e38818da0f1a9be8944ad081fafd2))
* **site:** space and center the level page byline counts ([808bf46](https://github.com/pythoninthegrass/megabonk_mods/commit/808bf4662e5c8bd18af9308e6bace6c969ac455f))
* **site:** stop the dev API writing PocketBase migrations into the repository ([7604a2f](https://github.com/pythoninthegrass/megabonk_mods/commit/7604a2f1a6845962011842edac2886e8f9402ea0))
* **site:** stretch the share code button and pin the footer ([03a41ac](https://github.com/pythoninthegrass/megabonk_mods/commit/03a41aceee6145390d8dd587c876e085a374d7cb))
* **site:** use outline sign-in buttons on the upload page ([096d5b4](https://github.com/pythoninthegrass/megabonk_mods/commit/096d5b41e55aea0a19057c8bf646976e3e560ce6))
* **steam:** load levels with an uninitialized Steamworks client ([e5d6bc2](https://github.com/pythoninthegrass/megabonk_mods/commit/e5d6bc261ecdb5acb99899cdd0cbbf559be42628))
* **steamstub:** answer as no client when init is made to fail ([738d7ac](https://github.com/pythoninthegrass/megabonk_mods/commit/738d7ac94ab9ee5ccb23e8f4ee4db38602e8de05))
* **steamstub:** gate verbs by what they need, not by the built stub ([47b1dbc](https://github.com/pythoninthegrass/megabonk_mods/commit/47b1dbcfcb7a697a25b252030266c1cc53756650))
* **steamstub:** name the artifact an install copies ([2da66c2](https://github.com/pythoninthegrass/megabonk_mods/commit/2da66c29aca1c7839256c253792e12d3228cb9a6))
* **steamstub:** re-deploy the stub when the artifact was rebuilt ([c480276](https://github.com/pythoninthegrass/megabonk_mods/commit/c480276aee360258a6a56c537480a1f2eafd675d))
* **thps:** install level thumbnail and biome sidecars ([24fb152](https://github.com/pythoninthegrass/megabonk_mods/commit/24fb1524368cad7df8def8bdbf179e919dfb596f))

## [0.2.0](https://github.com/pythoninthegrass/megabonk_mods/compare/v0.1.0...v0.2.0) (2026-11-09)


### Features

* **ci:** add path-filtered Thunderstore build and approved publish workflow ([63bc8a0](https://github.com/pythoninthegrass/megabonk_mods/commit/63bc8a0de98f2ad3f11eee4c07c45979ddd64072))
* **mcp:** package the harness as an installable megabonk-mcp command ([7191421](https://github.com/pythoninthegrass/megabonk_mods/commit/71914210b781b914e527f35d632c37c9c6c8ca75))
* **mcp:** register the server through uvx ([266bfab](https://github.com/pythoninthegrass/megabonk_mods/commit/266bfab2278df80b73b0aa0f13a0c8b7eae247fb))
* **site:** add searchable player wiki ([b3a5c5f](https://github.com/pythoninthegrass/megabonk_mods/commit/b3a5c5f85527138e76af5ac757a09f5de43550ab))
* **site:** link docs from showcase navigation ([cd0413f](https://github.com/pythoninthegrass/megabonk_mods/commit/cd0413fb3cbd7bbfe64a668007fc16dd1711e257))
* **thps:** add grind rails to the east deck ledge ([33ff224](https://github.com/pythoninthegrass/megabonk_mods/commit/33ff224a88a0eeaa4f18242982e328df0ca730db))
* **wine:** automate BepInEx runtime repair after r2modmac apply ([22ede08](https://github.com/pythoninthegrass/megabonk_mods/commit/22ede080775ef8fe42663260ff0c6d06bb99d07d))


### Bug Fixes

* **ci:** run Thunderstore gate tooling from the workflow commit ([12a3773](https://github.com/pythoninthegrass/megabonk_mods/commit/12a37734ef634beaa6a49e34db321a2b81b85233))
* **site:** link setup to wiki guide and public release ([2538f19](https://github.com/pythoninthegrass/megabonk_mods/commit/2538f1925681f17d68bcb1c2239f81574838720e))
* **site:** use home slug for wiki landing page ([f513448](https://github.com/pythoninthegrass/megabonk_mods/commit/f513448354b6dabb161f7358aeb9ec8257b239f6))
* **wine:** distinguish unchanged installs from completed repairs ([1f0fdad](https://github.com/pythoninthegrass/megabonk_mods/commit/1f0fdad4fdd235bd0b05959dc8c681bc05af82fe))
* **wine:** log repair details and keep success output quiet ([682c8c6](https://github.com/pythoninthegrass/megabonk_mods/commit/682c8c6014f91f49aaecdea0ff037df25c1855cb))

## 0.1.0

Initial development baseline for Megabonk Level Editor.

### Create and play

- In-game editor with terrain and object tools, asset palette, undo/redo, save/load
  and from-scratch level creation.
- Versioned JSON level format (schema v4), authored spawns, randomized
  interactables, custom music and Map Selection thumbnail/biome sidecars.
- Bramblecrown Hill starter level and optional local Warehouse authoring workflow.

### Console and development tools

- Tilde console with completion, persistent history, fuzzy search and music controls.
- CLI and MCP harness for editor input, screenshots, player/run controls and
  performance diagnostics; debug/cheat commands require development mode.
- Runtime MP3 playback and optional local asset-pack support.

### Runtime and packaging

- Current plugin targets BepInEx 6 IL2CPP and the Windows game build, including
  Proton/Linux and Wine/macOS. Native Linux mod support remains unverified.
- Runtime-only Thunderstore-format package with NLayer and its license; levels,
  game references, packs and music are not included.
- Go standalone installer and Linux, Windows and macOS packaging tools are retained
  for the legacy MelonLoader runtime, not the current BepInEx plugin.
- Developer/player guides and the megabonkmod.party showcase.

Optional proprietary-derived assets stay local; this baseline does not authorize
their redistribution or announce a public package release.
