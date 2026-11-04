package steam

import (
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"

	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ppath"
)

// wineSteamSubpath is where Steam's own installer puts the client in a prefix.
const wineSteamSubpath = "drive_c/Program Files (x86)/Steam"

var slashDrive = regexp.MustCompile(`^([A-Za-z]):/(.*)$`)

// WineClientRoots are Steam clients inside Wine prefixes on a Mac: plain Wine
// prefixes first, then CrossOver bottles, since CrossOver is commercial and
// not assumed to be installed.
func WineClientRoots(home string) []Client {
	home = ppath.Normalize(home)
	placements := []clientPlacement{
		{"wine", ppath.Join(home, ".local", "share", "megabonk", "wine")},
		{"wine", ppath.Join(home, ".wine")},
	}
	bottles := ppath.Join(home, "Library", "Application Support", "CrossOver", "Bottles")
	entries, _ := os.ReadDir(bottles)
	names := []string{}
	for _, entry := range entries {
		if entry.IsDir() {
			names = append(names, entry.Name())
		}
	}
	sort.Strings(names)
	for _, name := range names {
		placements = append(placements, clientPlacement{"crossover", ppath.Join(bottles, name)})
	}
	clients := []Client{}
	for _, placement := range placements {
		if client, found := WineClientIn(placement.path, placement.kind); found {
			clients = append(clients, client)
		}
	}
	return clients
}

// WineClientIn is the Steam client inside one prefix, when it has one.
func WineClientIn(prefix, kind string) (Client, bool) {
	prefix = ppath.Normalize(prefix)
	root := ppath.Join(prefix, wineSteamSubpath)
	if !ppath.IsDir(ppath.Join(root, "steamapps")) {
		return Client{}, false
	}
	return Client{Kind: kind, Root: root, Prefix: prefix}, true
}

// winePath turns a slash-form Windows path into the Unix path it names in a
// prefix: C: is drive_c, Z: is the filesystem root, any other letter is
// whatever the prefix's dosdevices link points at.
func winePath(prefix, path string) string {
	match := slashDrive.FindStringSubmatch(path)
	if match == nil {
		return path
	}
	letter, rest := strings.ToLower(match[1]), match[2]
	switch letter {
	case "c":
		return ppath.Join(prefix, "drive_c", rest)
	case "z":
		return ppath.Normalize("/" + rest)
	}
	target, err := filepath.EvalSymlinks(filepath.Join(filepath.FromSlash(prefix), "dosdevices", letter+":"))
	if err != nil {
		return path
	}
	return ppath.Join(filepath.ToSlash(target), rest)
}

// PrefixOfGameDir is the Wine prefix that holds a game directory, taken from the
// drive_c component of its path; empty when the game is not under one.
func PrefixOfGameDir(gameDir string) string {
	normal := ppath.Normalize(gameDir)
	if index := strings.Index(normal, "/drive_c/"); index > 0 {
		return normal[:index]
	}
	return ""
}
