# megabonk_mods

[Megabonk](https://store.steampowered.com/app/3405340/Megabonk/) mods source code.

Playing levels: see the [player guide](docs/player-guide.md). Building and changing the mod: see [docs/modding-setup.md](docs/modding-setup.md).

The **Megabonk Level Editor** Thunderstore package lives in [`pkg/`](pkg/README.md);
see [packaging and releases](docs/thunderstore.md) for build and verification commands.

The single-page showcase for **megabonkmod.party** lives in [`site/`](site/README.md).

Press backquote/tilde to open the in-game console. Type `help` to browse commands, use Tab to complete them, or Ctrl-R to search history. The console pauses a running game and restores its previous pause state when closed. Music controls such as `music.pause`, `music.play` and `music.next` are available to everyone; cheat/debug commands require `MEGABONK_DEV=true`. See the [console guide](docs/development.md#console-command-language) for commands and key bindings.
