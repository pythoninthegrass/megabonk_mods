// Package gamebuild tells the Windows Megabonk build from the Linux native
// one and says what to do when it is the latter: MelonLoader 0.7.3 crashes
// the native build during Il2Cpp assembly generation, so only the Windows
// build under Steam Play / Proton is supported.
package gamebuild

import (
	"strings"

	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ppath"
)

const (
	Windows      = "windows"
	NativeLinux  = "native-linux"
	Mixed        = "mixed"
	Unknown      = "unknown"
	WindowsExe   = "Megabonk.exe"
	NativeExe    = "Megabonk.x86_64"
	DataDir      = "Megabonk_Data"
	GameAssembly = "GameAssembly.dll"
	UnityPlayer  = "UnityPlayer.dll"
)

// Build is the classification of one game directory.
type Build struct {
	GameDir       string
	Kind          string
	HasWindowsExe bool
	HasNativeExe  bool
	HasDataDir    bool
}

// Supported reports whether MelonLoader can hook this build on Linux today.
func (b Build) Supported() bool {
	return IsSupported(b.Kind)
}

// Classify inspects the directory the way the Python reference does.
func Classify(gameDir string) Build {
	build := Build{
		GameDir:       ppath.Normalize(gameDir),
		HasWindowsExe: ppath.IsFile(ppath.Join(gameDir, WindowsExe)),
		HasNativeExe:  ppath.IsFile(ppath.Join(gameDir, NativeExe)),
		HasDataDir:    ppath.IsDir(ppath.Join(gameDir, DataDir)),
	}
	switch {
	case build.HasWindowsExe && build.HasNativeExe:
		build.Kind = Mixed
	case build.HasWindowsExe || (build.HasDataDir && ppath.IsFile(ppath.Join(gameDir, GameAssembly))):
		build.Kind = Windows
	case build.HasNativeExe:
		build.Kind = NativeLinux
	default:
		build.Kind = Unknown
	}
	return build
}

// IsSupported reports whether the Windows layout is the one at hand.
func IsSupported(kind string) bool {
	return kind == Windows || kind == Mixed
}

// LaunchBinary names the executable the player starts for a build kind.
func LaunchBinary(kind string) string {
	if kind == NativeLinux {
		return NativeExe
	}
	return WindowsExe
}

// NativeBuildMessage refuses the native build and steers the player to Steam Play.
func NativeBuildMessage(melonloaderVersion string, gameDir string) string {
	where := ""
	if gameDir != "" {
		where = " in " + ppath.Normalize(gameDir)
	}
	return strings.Join([]string{
		"This is the Linux native build of Megabonk" + where + ": it runs " + NativeExe + ", not " + WindowsExe + ".",
		"MelonLoader " + melonloaderVersion + " crashes that build while it generates the Il2Cpp assemblies " +
			"(the upstream fix is not in a release yet), so the map editor cannot be installed on it.",
		"",
		"Install the Windows build instead and let Steam run it under Proton:",
		"  1. Steam > Library > Megabonk > right-click > Properties > Installed Files:",
		"     remove the checkmark from 'Only download on my OS for this game' (or untick the",
		"     Steam Play 'Use the Linux version when available' option), then let it redownload.",
		"  2. Properties > Compatibility > tick 'Force the use of a specific Steam Play",
		"     compatibility tool' and pick a Proton version.",
		"  3. Launch the game once so Steam creates its Proton prefix, then quit it.",
		"  4. Run this installer again.",
	}, "\n")
}

// UnknownBuildMessage says the directory does not look like a Megabonk install.
func UnknownBuildMessage(gameDir string) string {
	dir := ppath.Normalize(gameDir)
	return strings.Join([]string{
		dir + " does not look like a Megabonk install: there is no " + WindowsExe + " and no " + DataDir + "/ next to it.",
		"",
		"Point the installer at the folder Steam put the game in, the one holding",
		WindowsExe + ", " + GameAssembly + " and " + DataDir + "/, for example:",
		"  <steam library>/steamapps/common/Megabonk",
		"",
		"If Megabonk is not installed yet, install it in Steam first and start it once.",
	}, "\n")
}

// UnsupportedBuildMessage picks the refusal that matches the build kind.
func UnsupportedBuildMessage(gameDir, kind, melonloaderVersion string) string {
	if kind == NativeLinux {
		return NativeBuildMessage(melonloaderVersion, gameDir)
	}
	return UnknownBuildMessage(gameDir)
}
