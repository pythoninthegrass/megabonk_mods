package steam

import (
	"regexp"
	"strings"
	"time"

	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ppath"
)

const registryTimeout = 5 * time.Second

var driveLetterPath = regexp.MustCompile(`^[A-Za-z]:[\\/]`)

var regValue = regexp.MustCompile(`(?m)^\s+\S+\s+REG_\w+\s+(.*?)\s*$`)

// RegistryString reads one string value through reg.exe, so the lookup needs no
// Windows-only code and tests can drive it through CommandRunner.
func RegistryString(key, name string) (string, bool) {
	code, out, err := CommandRunner([]string{"reg", "query", key, "/v", name}, registryTimeout)
	if err != nil || code != 0 {
		return "", false
	}
	match := regValue.FindStringSubmatch(out)
	if match == nil || match[1] == "" {
		return "", false
	}
	return match[1], true
}

// ProgramFilesDirs are the Program Files directories named by the environment,
// 32-bit first because Steam installs there by default.
func ProgramFilesDirs(getenv func(string) string) []string {
	dirs := []string{}
	for _, name := range []string{"ProgramFiles(x86)", "ProgramFiles"} {
		if value := getenv(name); value != "" {
			dirs = append(dirs, ppath.Normalize(strings.ReplaceAll(value, `\`, "/")))
		}
	}
	return dirs
}

// WindowsClientRoots are Steam clients on a Windows machine: the install path
// Steam records in the registry, then Steam under each Program Files directory.
func WindowsClientRoots(programFiles []string) []Client {
	placements := []clientPlacement{}
	if path, found := RegistryString(`HKCU\Software\Valve\Steam`, "SteamPath"); found {
		placements = append(placements, clientPlacement{"native", ppath.Normalize(strings.ReplaceAll(path, `\`, "/"))})
	}
	if path, found := RegistryString(`HKLM\SOFTWARE\WOW6432Node\Valve\Steam`, "InstallPath"); found {
		placements = append(placements, clientPlacement{"native", ppath.Normalize(strings.ReplaceAll(path, `\`, "/"))})
	}
	for _, dir := range programFiles {
		placements = append(placements, clientPlacement{"native", ppath.Join(dir, "Steam")})
	}
	clients := []Client{}
	for _, candidate := range classifyClients(placements) {
		if candidate.Accepted {
			clients = append(clients, Client{Kind: candidate.Kind, Root: candidate.Path})
		}
	}
	return clients
}

// slashDrivePath renders a Windows drive path in the slash form the installer
// uses everywhere; Steam writes backslashes, each one doubled in the file.
func slashDrivePath(path string) string {
	if !driveLetterPath.MatchString(path) {
		return path
	}
	return ppath.Normalize(strings.ReplaceAll(path, `\`, "/"))
}
