// Command megabonk-installer installs MelonLoader and the MegabonkLevels map
// editor into a Steam Play (Proton) Megabonk install. It is a single static
// binary with no runtime dependencies; see docs/player-installer.md.
package main

import (
	"os"

	"github.com/pythoninthegrass/megabonk_mods/installer/internal/cli"
)

func main() {
	os.Exit(cli.Run(os.Args[1:], os.Stdout, os.Stderr))
}
