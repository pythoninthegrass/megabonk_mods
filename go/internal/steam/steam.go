// Package steam finds Steam and the Megabonk install on a Linux machine: a
// native client, a Flatpak client whose data lives under ~/.var or anywhere a
// Flatpak grant points at, libraries on internal disks and removable media, and
// the Proton prefix Steam keeps per library.
package steam

import (
	"context"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ppath"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/vdf"
)

const (
	// AppID is Megabonk's Steam app id.
	AppID = "3405340"
	// GameName is the install directory Steam creates.
	GameName = "Megabonk"
	// GameExe is the Windows build's executable.
	GameExe = "Megabonk.exe"
	// NativeExe is the Linux native build's executable.
	NativeExe = "Megabonk.x86_64"
	// DataDir is the Unity data directory every build has.
	DataDir = "Megabonk_Data"
	// FlatpakID is the Flatpak Steam application id.
	FlatpakID = "com.valvesoftware.Steam"
	// ScanDepth is how deep the media scan walks.
	ScanDepth = 2

	gameAssembly = "GameAssembly.dll"
)

// Reasons a candidate was rejected; the CLI prints these verbatim.
const (
	ReasonMissing     = "does not exist"
	ReasonNoSteamapps = "no steamapps/ directory"
	ReasonDuplicate   = "already searched via an earlier candidate"
	ReasonNotMegabonk = "an Il2Cpp install (GameAssembly.dll) but no Megabonk.exe, Megabonk.x86_64 or Megabonk_Data/"
	ReasonNoPrefix    = "no steamapps/compatdata prefix in this library"
	ReasonNoDriveC    = "the prefix has no drive_c/: the game has never been launched under Proton in this library"
)

func reasonUnmounted(parent string) string {
	return "drive not attached (" + parent + " is missing)"
}

// FlatpakBinaries are the places the flatpak CLI may be.
var FlatpakBinaries = []string{"flatpak", "/usr/bin/flatpak", "/var/lib/flatpak/exports/bin/flatpak"}

var steamProcessMarkers = []string{
	"/Steam/ubuntu12_32/steam",
	"/steamapps/common/SteamLinuxRuntime",
	FlatpakID,
	"steamwebhelper",
}

var flatpakSpecialTokens = map[string]bool{
	"host": true, "host-os": true, "host-etc": true, "home": true, "os": true, "etc": true,
}

// CommandRunner runs a command and reports its exit code and stdout. Tests
// replace it so discovery can be driven without the tools installed.
var CommandRunner = runCommand

// Client is a Steam installation and the kind of install it is.
type Client struct {
	Kind string
	Root string
	// Prefix is the Wine prefix a wine or crossover client lives in; empty otherwise.
	Prefix string
}

// Library is a Steam library and how the installer came to consider it.
type Library struct {
	Path    string
	Source  string
	Client  *Client
	Granted *bool
}

// Candidate is one location considered, with the reason it was accepted or
// rejected.
type Candidate struct {
	Path     string
	Kind     string
	Accepted bool
	Reason   string
	Granted  *bool
	Client   *Client
}

// GameCandidate is a directory discovery thought might hold Megabonk, and what
// it decided.
type GameCandidate struct {
	Path     string
	Library  string
	How      string
	Accepted bool
	Reason   string
}

// PrefixCandidate is one library's compatdata prefix for this app, and whether
// Steam has created it.
type PrefixCandidate struct {
	Path     string
	Library  string
	Accepted bool
	Reason   string
}

// Probe is how the Flatpak grants were answered: the persisted file, the CLI, or
// neither.
type Probe struct {
	Paths    []string
	Source   string
	CLIFound bool
}

func yes() *bool { value := true; return &value }

func no() *bool { value := false; return &value }

// ClientCandidates is every client location considered, each with the reason it
// was accepted or rejected.
func ClientCandidates(home, xdgDataHome string, grantedPaths []string) []Candidate {
	home = ppath.ExpandUser(home)
	dataHomes := []string{}
	if xdgDataHome != "" {
		dataHomes = append(dataHomes, ppath.ExpandUser(xdgDataHome))
	}
	if configured := os.Getenv("XDG_DATA_HOME"); configured != "" {
		configuredPath := ppath.ExpandUser(configured)
		if !filepath.IsAbs(configuredPath) {
			configuredPath = ppath.Join(home, configuredPath)
		}
		dataHomes = append(dataHomes, configuredPath)
	}
	dataHomes = append(dataHomes, ppath.Join(home, ".local", "share"))

	candidates := []clientPlacement{}
	for _, dataHome := range dataHomes {
		candidates = append(candidates, clientPlacement{"native", ppath.Join(dataHome, "Steam")})
	}
	candidates = append(candidates,
		clientPlacement{"native", ppath.Join(home, ".steam", "root")},
		clientPlacement{"native", ppath.Join(home, ".steam", "steam")},
		clientPlacement{"flatpak", ppath.Join(home, ".var", "app", FlatpakID, ".local", "share", "Steam")},
		clientPlacement{"flatpak", ppath.Join(home, ".var", "app", FlatpakID, "data", "Steam")},
	)
	for _, granted := range grantedPaths {
		candidates = append(candidates, clientPlacement{"flatpak", ppath.ExpandUser(granted)})
	}

	return classifyClients(candidates)
}

// clientPlacement is a location that might hold a Steam client of a kind.
type clientPlacement struct {
	kind string
	path string
}

// classifyClients accepts the placements that are a Steam root and names why
// each other one was rejected.
func classifyClients(placements []clientPlacement) []Candidate {
	out := []Candidate{}
	seen := map[string]bool{}
	for _, item := range placements {
		if !ppath.IsDir(item.path) {
			out = append(out, Candidate{Path: item.path, Kind: item.kind, Reason: ReasonMissing})
			continue
		}
		if !ppath.Exists(ppath.Join(item.path, "steamapps")) {
			out = append(out, Candidate{Path: item.path, Kind: item.kind, Reason: ReasonNoSteamapps})
			continue
		}
		key := identity(item.path)
		if seen[key] {
			out = append(out, Candidate{Path: item.path, Kind: item.kind, Reason: ReasonDuplicate})
			continue
		}
		seen[key] = true
		out = append(out, Candidate{Path: item.path, Kind: item.kind, Accepted: true})
	}
	return out
}

// ClientRoots are Steam clients for a user: native first, then Flatpak, whose
// root may sit in a granted path rather than under ~/.var.
func ClientRoots(home, xdgDataHome string, grantedPaths []string) []Client {
	clients := []Client{}
	for _, candidate := range ClientCandidates(home, xdgDataHome, grantedPaths) {
		if candidate.Accepted {
			clients = append(clients, Client{Kind: candidate.Kind, Root: candidate.Path})
		}
	}
	return clients
}

// FlatpakOverridePaths is the absolute paths a Flatpak Steam may read, taken from
// `flatpak override --show` output.
func FlatpakOverridePaths(text, home string) []string {
	if home == "" {
		home = ppath.ExpandUser("~")
	}
	inContext := false
	paths := []string{}
	seen := map[string]bool{}
	for _, raw := range splitLines(text) {
		line := strings.TrimSpace(raw)
		if strings.HasPrefix(line, "[") && strings.HasSuffix(line, "]") {
			inContext = line == "[Context]"
			continue
		}
		if !inContext || !strings.HasPrefix(line, "filesystems=") {
			continue
		}
		for _, entry := range strings.Split(strings.SplitN(line, "=", 2)[1], ";") {
			entry = strings.TrimSpace(entry)
			if entry == "" || strings.HasPrefix(entry, "!") {
				continue
			}
			path, ok := expandFlatpakPath(entry, home)
			if !ok || seen[path] {
				continue
			}
			seen[path] = true
			paths = append(paths, path)
		}
	}
	return paths
}

func expandFlatpakPath(entry, home string) (string, bool) {
	if flatpakSpecialTokens[entry] ||
		strings.HasPrefix(entry, "host-") || strings.HasPrefix(entry, "xdg-") || strings.HasPrefix(entry, "home/") {
		return "", false
	}
	switch {
	case entry == "~":
		return ppath.Normalize(home), true
	case strings.HasPrefix(entry, "~/"):
		return ppath.Join(home, entry[2:]), true
	}
	if filepath.IsAbs(entry) {
		return ppath.Normalize(entry), true
	}
	return ppath.Join(home, entry), true
}

func flatpakOverrideFile(home string) string {
	path := ppath.Join(home, ".var", "app", FlatpakID, "configuration", "flatpak", "local-overrides", FlatpakID)
	if ppath.IsFile(path) {
		return path
	}
	return ""
}

// ProbeFlatpak reports how the Flatpak grants were answered.
func ProbeFlatpak(home string) Probe {
	home = ppath.ExpandUser(home)
	if stored := flatpakOverrideFile(home); stored != "" {
		if text, err := ppath.ReadTextReplace(stored); err == nil {
			return Probe{Paths: FlatpakOverridePaths(text, home), Source: "file", CLIFound: true}
		}
	}
	cliFound := false
	for _, binary := range FlatpakBinaries {
		code, stdout, err := CommandRunner([]string{binary, "override", "--show", FlatpakID}, 15*time.Second)
		if err != nil {
			continue
		}
		cliFound = true
		if code == 0 && stdout != "" {
			return Probe{Paths: FlatpakOverridePaths(stdout, home), Source: "cli", CLIFound: true}
		}
	}
	return Probe{Paths: nil, Source: "none", CLIFound: cliFound}
}

// FlatpakGrantedPaths are the paths Flatpak Steam may read, from the persisted
// override file or the flatpak CLI.
func FlatpakGrantedPaths(home string) []string {
	return ProbeFlatpak(home).Paths
}

// LibraryFolders is the library list in a client's libraryfolders.vdf.
func LibraryFolders(client Client) []string {
	path := ppath.Join(client.Root, "steamapps", "libraryfolders.vdf")
	if !ppath.IsFile(path) {
		return nil
	}
	data, err := vdf.Load(path)
	if err != nil {
		return nil
	}
	paths := vdf.LibraryFolderPaths(data)
	for index, path := range paths {
		paths[index] = slashDrivePath(path)
		if client.Prefix != "" {
			paths[index] = winePath(client.Prefix, paths[index])
		}
	}
	return paths
}

type libraryOptions struct {
	Overrides      []string
	ExtraPaths     []string
	MountRoots     []string
	IncludeMissing bool
}

// LibraryCandidates is every library considered, each with the reason it was
// accepted or rejected.
func LibraryCandidates(clients []Client, overrides, extraPaths, mountRoots []string, includeMissing bool) []Candidate {
	options := libraryOptions{Overrides: overrides, ExtraPaths: extraPaths, MountRoots: mountRoots, IncludeMissing: includeMissing}
	found := []Candidate{}
	seen := map[string]bool{}
	grantedPaths := append([]string{}, options.Overrides...)
	granted := map[string]bool{}
	for _, path := range grantedPaths {
		granted[ppath.Normalize(path)] = true
	}

	add := func(path, source string, client *Client, isGranted *bool) {
		path = ppath.Normalize(path)
		if !options.IncludeMissing && !plausible(path) {
			found = append(found, Candidate{Path: path, Kind: source, Reason: reasonUnmounted(ppath.Parent(path)), Granted: isGranted, Client: client})
			return
		}
		key := identity(path)
		if seen[key] {
			found = append(found, Candidate{Path: path, Kind: source, Accepted: false, Reason: ReasonDuplicate, Granted: isGranted, Client: client})
			return
		}
		seen[key] = true
		found = append(found, Candidate{Path: path, Kind: source, Accepted: true, Granted: isGranted, Client: client})
	}

	for _, client := range clients {
		current := client
		for _, path := range LibraryFolders(client) {
			var isGranted *bool
			if granted[ppath.Normalize(path)] {
				isGranted = yes()
			} else if client.Kind == "flatpak" {
				isGranted = no()
			}
			add(path, "client", &current, isGranted)
		}
	}
	for _, path := range grantedPaths {
		add(path, "flatpak-override", nil, yes())
	}
	for _, path := range options.ExtraPaths {
		add(path, "explicit", nil, nil)
	}
	for _, mount := range options.MountRoots {
		for _, path := range ScanForLibraries(mount, ScanDepth) {
			add(path, "scan", nil, nil)
		}
	}
	return found
}

// LibraryRoots are the libraries to search, in priority order: the client's own
// list, Flatpak grants, explicit paths, then a media scan.
func LibraryRoots(clients []Client, overrides, extraPaths, mountRoots []string, includeMissing bool) []Library {
	roots := []Library{}
	for _, candidate := range LibraryCandidates(clients, overrides, extraPaths, mountRoots, includeMissing) {
		if candidate.Accepted {
			roots = append(roots, Library{Path: candidate.Path, Source: candidate.Kind, Client: candidate.Client, Granted: candidate.Granted})
		}
	}
	return roots
}

// ScanForLibraries finds directories under a mount point that look like a Steam
// library: they hold steamapps/common.
func ScanForLibraries(mountRoot string, depth int) []string {
	if depth <= 0 {
		depth = ScanDepth
	}
	if !ppath.IsDir(mountRoot) {
		return nil
	}
	found := []string{}
	frontier := []string{ppath.Normalize(mountRoot)}
	for level := 0; level < depth; level++ {
		next := []string{}
		for _, directory := range frontier {
			entries, err := os.ReadDir(directory)
			if err != nil {
				continue
			}
			children := []string{}
			for _, entry := range entries {
				child := ppath.Join(directory, entry.Name())
				if ppath.IsDir(child) {
					children = append(children, child)
				}
			}
			sort.Strings(children)
			for _, child := range children {
				if strings.HasPrefix(ppath.Name(child), ".") {
					continue
				}
				if ppath.IsDir(ppath.Join(child, "steamapps", "common")) {
					found = append(found, child)
				} else {
					next = append(next, child)
				}
			}
		}
		frontier = next
	}
	return found
}

// isMegabonk recognises an install only by the names Megabonk itself writes.
func isMegabonk(directory string) bool {
	if !ppath.IsDir(directory) {
		return false
	}
	for _, marker := range []string{GameExe, NativeExe} {
		if ppath.IsFile(ppath.Join(directory, marker)) {
			return true
		}
	}
	return ppath.IsDir(ppath.Join(directory, DataDir))
}

// isIl2Cpp says a folder is a Unity/Il2Cpp game: proof of a game, not of which.
func isIl2Cpp(directory string) bool {
	return ppath.IsDir(directory) && ppath.IsFile(ppath.Join(directory, gameAssembly))
}

func commonChildren(library string) []string {
	common := ppath.Join(library, "steamapps", "common")
	entries, err := os.ReadDir(common)
	if err != nil {
		return nil
	}
	out := make([]string, 0, len(entries))
	for _, entry := range entries {
		child := ppath.Join(common, entry.Name())
		if ppath.IsDir(child) {
			out = append(out, child)
		}
	}
	sort.Strings(out)
	return out
}

// GameCandidates lists every directory discovery offered as Megabonk, in the
// order it should be trusted: Steam's own appmanifest, the folder name Steam
// creates, then any other Il2Cpp install in the library.
func GameCandidates(roots []Library, gameName string) []GameCandidate {
	if gameName == "" {
		gameName = GameName
	}
	out := make([]GameCandidate, 0, len(roots))
	seen := map[string]bool{}
	take := func(directory, library, how string) {
		key := resolve(directory)
		if seen[key] {
			return
		}
		seen[key] = true
		switch {
		case !ppath.Exists(directory):
			out = append(out, GameCandidate{directory, library, how, false, ReasonMissing})
		case isMegabonk(directory):
			out = append(out, GameCandidate{directory, library, how, true, ""})
		default:
			out = append(out, GameCandidate{directory, library, how, false, ReasonNotMegabonk})
		}
	}
	for _, root := range roots {
		if installDir := installDirFromManifests(root.Path); installDir != "" {
			take(installDir, root.Path, "manifest")
		}
	}
	for _, root := range roots {
		named := ppath.Join(root.Path, "steamapps", "common", gameName)
		if ppath.IsDir(named) {
			take(named, root.Path, "name")
		}
	}
	for _, root := range roots {
		for _, child := range commonChildren(root.Path) {
			if isMegabonk(child) || isIl2Cpp(child) {
				take(child, root.Path, "scan")
			}
		}
	}
	return out
}

// FindGameDir is the first library holding a Megabonk install, by its own files
// rather than its shape. "" means none of them does.
func FindGameDir(roots []Library, gameName string) string {
	for _, candidate := range GameCandidates(roots, gameName) {
		if candidate.Accepted {
			return candidate.Path
		}
	}
	return ""
}

func installDirFromManifests(library string) string {
	steamapps := ppath.Join(library, "steamapps")
	if !ppath.IsDir(steamapps) {
		return ""
	}
	matches, err := filepath.Glob(filepath.Join(steamapps, "appmanifest_"+AppID+".acf"))
	if err != nil || len(matches) == 0 {
		return ""
	}
	names := make([]string, 0, len(matches))
	for _, match := range matches {
		names = append(names, filepath.ToSlash(match))
	}
	sort.Strings(names)
	for _, manifest := range names {
		data, err := vdf.Load(manifest)
		if err != nil {
			continue
		}
		appIDs := make([]string, 0, 1)
		for _, value := range vdf.FindAll(data, []string{"*", "appid"}) {
			if text := stringValue(value); text != "" {
				appIDs = append(appIDs, text)
			}
		}
		if len(appIDs) > 0 && !containsString(appIDs, AppID) {
			continue
		}
		install := ""
		for _, value := range vdf.FindAll(data, []string{"*", "installdir"}) {
			if text := strings.TrimSpace(stringValue(value)); text != "" {
				install = text
				break
			}
		}
		if install != "" {
			return ppath.Join(steamapps, "common", install)
		}
	}
	return ""
}

func stringValue(value any) string {
	if text, ok := value.(string); ok {
		return text
	}
	return ""
}

func containsString(values []string, want string) bool {
	for _, value := range values {
		if value == want {
			return true
		}
	}
	return false
}

// PrefixCandidates lists each library's compatdata prefix for this app, and
// whether Steam has filled it in.
func PrefixCandidates(libraries []string, appID string) []PrefixCandidate {
	if appID == "" {
		appID = AppID
	}
	out := make([]PrefixCandidate, 0, len(libraries))
	seen := map[string]bool{}
	for _, library := range libraries {
		key := resolve(library)
		if seen[key] {
			continue
		}
		seen[key] = true
		prefix := PrefixRoot(library, appID)
		switch {
		case !ppath.IsDir(prefix):
			out = append(out, PrefixCandidate{prefix, library, false, ReasonNoPrefix})
		case !ppath.IsDir(ppath.Join(prefix, "drive_c")):
			out = append(out, PrefixCandidate{prefix, library, false, ReasonNoDriveC})
		default:
			out = append(out, PrefixCandidate{prefix, library, true, ""})
		}
	}
	return out
}

// FindPrefix is the prefix to install into, plus every prefix considered.
//
// Steam keeps the prefix in the library the game was installed to, which is not
// always the one holding the game files today. When the game's own library has
// no usable prefix, the only other usable one is taken; two of them is a guess,
// so nothing is chosen.
func FindPrefix(gameDir string, libraries []string, appID string) (string, []PrefixCandidate) {
	if appID == "" {
		appID = AppID
	}
	own := PrefixForGameDir(gameDir, appID)
	ownLibrary := libraryOfGameDir(gameDir)
	ordered := make([]string, 0, len(libraries))
	if ownLibrary != "" {
		ordered = append(ordered, ownLibrary)
	}
	for _, library := range libraries {
		if ownLibrary != "" && resolve(library) == resolve(ownLibrary) {
			continue
		}
		ordered = append(ordered, library)
	}
	considered := PrefixCandidates(ordered, appID)
	if own != "" && ppath.IsDir(ppath.Join(own, "drive_c")) {
		return own, considered
	}
	var others []PrefixCandidate
	for _, candidate := range considered {
		if candidate.Accepted && candidate.Path != own {
			others = append(others, candidate)
		}
	}
	if len(others) == 1 {
		return others[0].Path, considered
	}
	if len(others) > 1 {
		return "", considered
	}
	return own, considered
}

func libraryOfGameDir(gameDir string) string {
	for _, parent := range ppath.Parents(ppath.Normalize(gameDir)) {
		if ppath.Name(parent) == "common" {
			return ppath.Parent(ppath.Parent(parent))
		}
	}
	return ""
}

// PrefixRoot is the compatdata prefix Steam keeps for an app in a library.
func PrefixRoot(library, appID string) string {
	if appID == "" {
		appID = AppID
	}
	return ppath.Join(library, "steamapps", "compatdata", appID, "pfx")
}

// PrefixForGameDir is the compatdata prefix that belongs to an install, when the
// library layout is Steam's. "" means there is none.
func PrefixForGameDir(gameDir, appID string) string {
	if appID == "" {
		appID = AppID
	}
	for _, parent := range ppath.Parents(ppath.Normalize(gameDir)) {
		if ppath.Name(parent) != "common" {
			continue
		}
		library := ppath.Parent(ppath.Parent(parent))
		if candidate := PrefixRoot(library, appID); ppath.IsDir(candidate) {
			return candidate
		}
		return ""
	}
	return ""
}

// CompatdataRoot is the compatdata directory holding a game's prefixes.
func CompatdataRoot(gameDir, appID string) string {
	prefix := PrefixForGameDir(gameDir, appID)
	if prefix == "" {
		return ""
	}
	return ppath.Parent(prefix)
}

// Localconfig is a client's localconfig.vdf, or nil when it cannot be read.
func Localconfig(client Client) *vdf.Dict {
	path := ppath.Join(client.Root, "config", "localconfig.vdf")
	if !ppath.IsFile(path) {
		return nil
	}
	data, err := vdf.Load(path)
	if err != nil {
		return nil
	}
	return data
}

// SteamRunning reports whether a Steam client is running, which is when it
// rewrites localconfig.vdf.
func SteamRunning() bool {
	_, stdout, err := CommandRunner([]string{"ps", "-eo", "args"}, 10*time.Second)
	if err != nil {
		return false
	}
	for _, line := range splitLines(stdout) {
		for _, marker := range steamProcessMarkers {
			if strings.Contains(line, marker) {
				return true
			}
		}
	}
	return false
}

var lineBreaks = strings.NewReplacer("\r\n", "\n", "\r", "\n")

// splitLines is str.splitlines(): no empty element for a trailing newline.
func splitLines(text string) []string {
	lines := strings.Split(lineBreaks.Replace(text), "\n")
	if len(lines) > 0 && lines[len(lines)-1] == "" {
		lines = lines[:len(lines)-1]
	}
	return lines
}

// plausible says a library is worth searching when it exists, or its parent
// does: a parent that is gone too means the drive is not attached.
func plausible(path string) bool {
	return ppath.IsDir(path) || ppath.IsDir(ppath.Parent(path))
}

// resolve is Path.resolve(non_strict=True): absolute, symlinks followed as far
// as the filesystem allows.
func resolve(path string) string {
	return resolveWith(path, filepath.Abs, filepath.ToSlash, filepath.EvalSymlinks)
}

// resolveWith answers in slashes on every OS; the seams let tests replay
// Windows separators (backslash Abs, a slash-ing ToSlash) on any host.
func resolveWith(path string, abs func(string) (string, error), toSlash func(string) string, eval func(string) (string, error)) string {
	normalised := ppath.Normalize(path)
	absolute, err := abs(normalised)
	if err != nil {
		return normalised
	}
	target, err := eval(toSlash(absolute))
	if err != nil {
		return ppath.Normalize(toSlash(absolute))
	}
	return toSlash(target)
}

func runCommand(argv []string, timeout time.Duration) (int, string, error) {
	if len(argv) == 0 || argv[0] == "" {
		return 1, "", errNoCommand
	}
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()
	command := exec.CommandContext(ctx, argv[0], argv[1:]...)
	var stdout strings.Builder
	command.Stdout = &stdout
	command.Stderr = nil
	err := command.Run()
	if ctx.Err() != nil {
		return 1, stdout.String(), ctx.Err()
	}
	if err != nil {
		if exit, ok := err.(*exec.ExitError); ok {
			return exit.ExitCode(), stdout.String(), nil
		}
		return 1, stdout.String(), err
	}
	return 0, stdout.String(), nil
}

var errNoCommand = &commandError{"no command to run"}

type commandError struct{ message string }

func (e *commandError) Error() string { return e.message }
