// Package proton is the Proton side of the install: where .NET 6 goes in a
// prefix, the Wine DllOverrides entry MelonLoader needs, and which Proton tool
// to run. MelonLoader hooks an Il2Cpp game through a version.dll next to the
// executable, which Wine only loads when the registry says it is native, and
// the Il2Cpp interop needs a .NET 6 runtime the prefix can find. Both are
// prefix state, so the installer writes them itself rather than relying on a
// first launch to do it.
package proton

import (
	"archive/zip"
	"context"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ppath"
)

const (
	// RuntimeMarkerName records which .NET version sits in the runtime folder.
	RuntimeMarkerName = "MegabonkLevels.dotnet_version"
	// DLLName is the DLL Wine must load natively for MelonLoader to hook in.
	DLLName = "version"
	// DLLValue is the DllOverrides value that makes Wine load it.
	DLLValue = "native,builtin"
	// DllOverridesSection is the registry section DllOverrides lives in.
	DllOverridesSection = `Software\Wine\DllOverrides`
	// RuntimeHost is the file that proves a runtime version is really there.
	RuntimeHost = "hostfxr.dll"

	dotnetFolder = "drive_c/Program Files/dotnet"
	hostfxrDir   = "host/fxr"
	commandShell = "%command%"
)

// Error is a Proton or Wine step that could not be completed.
type Error struct{ message string }

func (e *Error) Error() string { return e.message }

func fail(format string, args ...any) error {
	return &Error{message: fmt.Sprintf(format, args...)}
}

// Runner runs a command with an environment and reports its exit code; tests
// inject their own.
type Runner func(argv []string, env map[string]string) int

// WindowsPath is a Unix path as Wine sees it through the Z: drive.
func WindowsPath(path string) string {
	text := path
	if drivePath.MatchString(text) {
		return strings.ToUpper(text[:1]) + ":" + strings.ReplaceAll(text[2:], "/", `\`)
	}
	return "Z:" + strings.ReplaceAll(text, "/", `\`)
}

// RuntimeTarget is the standard .NET folder inside a prefix.
func RuntimeTarget(prefix string) string { return ppath.Join(prefix, dotnetFolder) }

// RuntimeInstalled reports whether a .NET runtime of exactly this version sits
// at target: the marker has to say so and hostfxr.dll has to be there.
func RuntimeInstalled(target, version string) bool {
	marker := ppath.Join(target, RuntimeMarkerName)
	if !ppath.IsFile(marker) {
		return false
	}
	text, err := ppath.ReadTextReplace(marker)
	if err != nil || strings.TrimSpace(text) != version {
		return false
	}
	return ppath.IsFile(ppath.Join(target, hostfxrDir, version, RuntimeHost))
}

// ExtractRuntime unpacks a Windows .NET runtime archive and marks it installed.
func ExtractRuntime(archive, target, version string) error {
	if err := extractAll(archive, target); err != nil {
		return err
	}
	if err := os.MkdirAll(target, 0o755); err != nil {
		return err
	}
	if err := os.WriteFile(ppath.Join(target, RuntimeMarkerName), []byte(version), 0o644); err != nil {
		return err
	}
	return nil
}

// RemoveRuntime deletes an extracted runtime; true when something was removed.
func RemoveRuntime(target string) bool {
	if !ppath.Exists(target) {
		return false
	}
	_ = os.RemoveAll(target)
	return !ppath.Exists(target)
}

// UserRegPath is the prefix's registry file.
func UserRegPath(prefix string) string { return ppath.Join(prefix, "user.reg") }

var (
	drivePath   = regexp.MustCompile(`^[A-Za-z]:[\\/]`)
	driveLetter = regexp.MustCompile(`^[A-Za-z]:`)
	entryLine   = regexp.MustCompile(`^"([^"]+)"\s*=\s*(?:\([^)]*\)\s*)?"(.*)"\s*$`)
	sectionLine = regexp.MustCompile(`^\[(.+)\](?:\s+\d+)?\s*$`)
	numbers     = regexp.MustCompile(`\d+`)
)

func normaliseSection(section string) string {
	body := strings.TrimSpace(section)
	body = strings.Trim(body, "[]")
	body = strings.ReplaceAll(body, `\\`, `\`)
	return strings.ToLower(body)
}

func quotedEntry(name, value string) string {
	return `"` + name + `"="` + value + `"`
}

func sectionName(line string) (string, bool) {
	match := sectionLine.FindStringSubmatch(strings.TrimSpace(line))
	if match == nil {
		return "", false
	}
	return normaliseSection(match[1]), true
}

var lineBreaks = strings.NewReplacer("\r\n", "\n", "\r", "\n")

func readLines(prefix string) ([]string, bool) {
	path := UserRegPath(prefix)
	if !ppath.IsFile(path) {
		return nil, false
	}
	text, err := ppath.ReadTextReplace(path)
	if err != nil {
		return nil, false
	}
	// str.splitlines() does not end the list with an empty element.
	lines := strings.Split(lineBreaks.Replace(text), "\n")
	if len(lines) > 0 && lines[len(lines)-1] == "" {
		lines = lines[:len(lines)-1]
	}
	return lines, true
}

// ReadDllOverride is the DllOverrides value Wine has for a DLL name, or "" when
// it has none.
func ReadDllOverride(prefix, name, section string) (string, bool) {
	if section == "" {
		section = DllOverridesSection
	}
	lines, found := readLines(prefix)
	if !found {
		return "", false
	}
	wanted := normaliseSection(section)
	inside := false
	for _, line := range lines {
		stripped := strings.TrimSpace(line)
		if seen, ok := sectionName(stripped); ok {
			inside = seen == wanted
			continue
		}
		if !inside {
			continue
		}
		match := entryLine.FindStringSubmatch(stripped)
		if match != nil && strings.EqualFold(match[1], name) {
			return match[2], true
		}
	}
	return "", false
}

// SetDllOverride points Wine at the game directory's DLL and says how it was
// done: "wine" or "registry".
func SetDllOverride(prefix, name, value, section, wineBin string, runner Runner) string {
	if section == "" {
		section = DllOverridesSection
	}
	if wineBin != "" {
		if runOverride(runner, regAddArgv(wineBin, name, value, section), prefix) == 0 {
			return "wine"
		}
	}
	setInRegistry(prefix, name, value, section)
	return "registry"
}

// ClearDllOverride removes a DllOverrides entry the installer added.
func ClearDllOverride(prefix, name, section, wineBin string, runner Runner) string {
	if section == "" {
		section = DllOverridesSection
	}
	if wineBin != "" {
		if runOverride(runner, regDeleteArgv(wineBin, name, section), prefix) == 0 {
			return "wine"
		}
	}
	clearInRegistry(prefix, name, section)
	return "registry"
}

func regKey(section string) string {
	return `HKCU\` + strings.Trim(strings.TrimSpace(section), "[]")
}

func regAddArgv(wineBin, name, value, section string) []string {
	return []string{wineBin, "reg", "add", regKey(section), "/v", name, "/d", value, "/f"}
}

func regDeleteArgv(wineBin, name, section string) []string {
	return []string{wineBin, "reg", "delete", regKey(section), "/v", name, "/f"}
}

func runOverride(runner Runner, argv []string, prefix string) int {
	env := environment(prefix)
	if runner != nil {
		return runner(argv, env)
	}
	return run(argv, env)
}

func environment(prefix string) map[string]string {
	env := map[string]string{}
	for _, pair := range os.Environ() {
		if key, value, ok := strings.Cut(pair, "="); ok {
			env[key] = value
		}
	}
	env["WINEPREFIX"] = ppath.Normalize(prefix)
	env["WINEDEBUG"] = "-all"
	return env
}

func run(argv []string, env map[string]string) int {
	if len(argv) == 0 || argv[0] == "" {
		return 1
	}
	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()
	command := exec.CommandContext(ctx, argv[0], argv[1:]...)
	command.Env = flattenEnv(env)
	command.Stdout = io.Discard
	command.Stderr = io.Discard
	if err := command.Run(); err != nil {
		if ctx.Err() != nil {
			return 1
		}
		if exit, ok := err.(*exec.ExitError); ok {
			return exit.ExitCode()
		}
		return 1
	}
	return 0
}

func flattenEnv(env map[string]string) []string {
	keys := make([]string, 0, len(env))
	for key := range env {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	pairs := make([]string, 0, len(keys))
	for _, key := range keys {
		pairs = append(pairs, key+"="+env[key])
	}
	return pairs
}

func setInRegistry(prefix, name, value, section string) {
	path := UserRegPath(prefix)
	entry := quotedEntry(name, value)
	wanted := normaliseSection(section)
	lines, found := readLines(prefix)
	if !found {
		body := "REGEDIT4\n\n[" + strings.Trim(strings.TrimSpace(section), "[]") + "]\n" + entry + "\n"
		_ = os.MkdirAll(ppath.Parent(path), 0o755)
		_ = os.WriteFile(path, []byte(body), 0o644)
		return
	}
	inside := false
	out := make([]string, 0, len(lines)+2)
	replaced := false
	for _, line := range lines {
		stripped := strings.TrimSpace(line)
		if seen, ok := sectionName(stripped); ok {
			if inside && !replaced {
				out = append(out, entry)
				replaced = true
			}
			inside = seen == wanted
			out = append(out, line)
			continue
		}
		if inside && !replaced {
			match := entryLine.FindStringSubmatch(stripped)
			if match != nil && strings.EqualFold(match[1], name) {
				out = append(out, entry)
				replaced = true
				continue
			}
		}
		out = append(out, line)
	}
	if inside && !replaced {
		out = append(out, entry)
		replaced = true
	}
	if !replaced {
		if len(out) > 0 && strings.TrimSpace(out[len(out)-1]) != "" {
			out = append(out, "")
		}
		out = append(out, headerFor(lines, section), entry)
	}
	_ = os.WriteFile(path, []byte(strings.Join(out, "\n")+"\n"), 0o644)
}

// headerFor is a new section header in the file's own style: Wine's user.reg
// escapes backslashes in key names, a hand-written REGEDIT4 file does not.
func headerFor(lines []string, section string) string {
	body := strings.Trim(strings.TrimSpace(section), "[]")
	if len(lines) > 0 && strings.HasPrefix(strings.ToUpper(strings.TrimSpace(lines[0])), "WINE REGISTRY") {
		body = strings.ReplaceAll(body, `\`, `\\`)
	}
	return "[" + body + "]"
}

func clearInRegistry(prefix, name, section string) {
	lines, found := readLines(prefix)
	if !found {
		return
	}
	inside := false
	wanted := normaliseSection(section)
	out := make([]string, 0, len(lines))
	for _, line := range lines {
		stripped := strings.TrimSpace(line)
		if seen, ok := sectionName(stripped); ok {
			inside = seen == wanted
			out = append(out, line)
			continue
		}
		if inside {
			match := entryLine.FindStringSubmatch(stripped)
			if match != nil && strings.EqualFold(match[1], name) {
				continue
			}
		}
		out = append(out, line)
	}
	_ = os.WriteFile(UserRegPath(prefix), []byte(strings.Join(out, "\n")+"\n"), 0o644)
}

// ProtonRoots are Steam's own Proton builds plus any compatibility tool the
// user dropped in.
func ProtonRoots(library string) []string {
	tools := []string{}
	for _, directory := range []string{ppath.Join(library, "steamapps", "common"), ppath.Join(library, "compatibilitytools.d")} {
		if !ppath.IsDir(directory) {
			continue
		}
		entries, err := os.ReadDir(directory)
		if err != nil {
			continue
		}
		names := make([]string, 0, len(entries))
		for _, entry := range entries {
			names = append(names, entry.Name())
		}
		sort.Strings(names)
		for _, name := range names {
			child := ppath.Join(directory, name)
			if ppath.IsDir(child) && strings.HasPrefix(strings.ToLower(name), "proton") {
				tools = append(tools, child)
			}
		}
	}
	return tools
}

func versionKey(tool string) []int {
	var numbersFound []int
	for _, match := range numbers.FindAllString(ppath.Name(tool), -1) {
		number, err := strconv.Atoi(match)
		if err != nil {
			continue
		}
		numbersFound = append(numbersFound, number)
	}
	return numbersFound
}

// compareVersionKeys is Python's tuple comparison: element-wise, and a shorter
// key is smaller when it is a prefix of the longer one.
func compareVersionKeys(left, right []int) int {
	for index := 0; index < len(left) && index < len(right); index++ {
		if left[index] != right[index] {
			if left[index] < right[index] {
				return -1
			}
			return 1
		}
	}
	switch {
	case len(left) < len(right):
		return -1
	case len(left) > len(right):
		return 1
	}
	return 0
}

func normaliseToken(text string) string {
	return strings.Trim(regexp.MustCompile(`[^a-z0-9]+`).ReplaceAllString(strings.ToLower(text), "_"), "_")
}

func matchesForced(tool, forced string) bool {
	needle := normaliseToken(forced)
	haystack := normaliseToken(ppath.Name(tool))
	if needle == "" {
		return false
	}
	for _, token := range strings.Split(needle, "_") {
		if !containsToken(strings.Split(haystack, "_"), token) && !strings.Contains(haystack, token) {
			return false
		}
	}
	return true
}

func containsToken(tokens []string, wanted string) bool {
	for _, token := range tokens {
		if token == wanted {
			return true
		}
	}
	return false
}

// PickProton is the compatibility tool to use: the forced one when named, else
// the newest numbered Proton. "" means there is none.
func PickProton(library, forced string) string {
	tools := ProtonRoots(library)
	if len(tools) == 0 {
		return ""
	}
	if forced != "" {
		var matches []string
		for _, tool := range tools {
			if matchesForced(tool, forced) {
				matches = append(matches, tool)
			}
		}
		if len(matches) == 0 {
			return ""
		}
		needle := normaliseToken(forced)
		best := matches[0]
		for _, tool := range matches[1:] {
			if forcedKeyBetter(tool, best, needle) {
				best = tool
			}
		}
		return best
	}
	best := tools[0]
	for _, tool := range tools[1:] {
		if keyBetter(tool, best) {
			best = tool
		}
	}
	return best
}

func keyBetter(tool, best string) bool {
	return compareToolKeys(ppath.Name(tool), ppath.Name(best), nil) > 0
}

func forcedKeyBetter(tool, best, needle string) bool {
	return compareToolKeys(ppath.Name(tool), ppath.Name(best), &needle) > 0
}

// compareToolKeys is Python's max key: an optional "the name starts with the
// forced prefix" bool, then the numeric version, then the name.
func compareToolKeys(left, right string, needle *string) int {
	if needle != nil {
		l := startsWithNeedle(left, *needle)
		r := startsWithNeedle(right, *needle)
		if l != r {
			if l {
				return 1
			}
			return -1
		}
	}
	if order := compareVersionKeys(versionKey(left), versionKey(right)); order != 0 {
		return order
	}
	return strings.Compare(left, right)
}

func startsWithNeedle(name, needle string) bool {
	return strings.HasPrefix(strings.ReplaceAll(strings.ToLower(name), "-", "_"), needle)
}

// ProtonWineBin is the wine binary inside a Proton tool, for registry edits.
func ProtonWineBin(tool string) string {
	binDir := ppath.Join(tool, "files", "bin")
	for _, name := range []string{"wine64", "wine"} {
		if candidate := ppath.Join(binDir, name); ppath.IsFile(candidate) {
			return candidate
		}
	}
	return ""
}

// LaunchOption is the Steam launch option that points .NET at a runtime outside
// the prefix.
func LaunchOption(runtimeDir string, extra ...string) string {
	assignments := append([]string{"DOTNET_ROOT=" + WindowsPath(runtimeDir)}, extra...)
	return strings.Join(append(assignments, commandShell), " ")
}

// UsablePrefix reports whether Steam has created this prefix yet; it does so on
// the first Proton launch.
func UsablePrefix(prefix string) bool {
	return ppath.IsDir(ppath.Join(prefix, "drive_c"))
}

func extractAll(archive, target string) error {
	if err := os.MkdirAll(target, 0o755); err != nil {
		return err
	}
	root, err := filepath.EvalSymlinks(target)
	if err != nil {
		root = target
	}
	reader, err := zip.OpenReader(archive)
	if err != nil {
		return fail("%s: %s", ppath.Name(archive), err.Error())
	}
	defer reader.Close()
	name := ppath.Name(archive)
	for _, member := range reader.File {
		if err := checkInside(member.Name, root, name); err != nil {
			return err
		}
	}
	for _, member := range reader.File {
		if err := extractMember(member, root); err != nil {
			return fail("%s: %s", name, err.Error())
		}
	}
	return nil
}

func checkInside(entry, root, archive string) error {
	slash := filepath.ToSlash(entry)
	if strings.HasPrefix(slash, "/") || driveLetter.MatchString(slash) {
		return escapeError(archive, entry)
	}
	clean := filepath.Clean(root)
	resolved := filepath.Clean(filepath.Join(clean, filepath.FromSlash(slash)))
	if resolved != clean && !strings.HasPrefix(resolved, clean+string(filepath.Separator)) {
		return escapeError(archive, entry)
	}
	return nil
}

func escapeError(archive, entry string) error {
	return &Error{message: archive + ": entry " + strconv.Quote(entry) + " would escape its target directory"}
}

func extractMember(member *zip.File, root string) error {
	destination := filepath.Join(root, filepath.FromSlash(filepath.ToSlash(member.Name)))
	if member.FileInfo().IsDir() {
		return os.MkdirAll(destination, 0o755)
	}
	if err := os.MkdirAll(filepath.Dir(destination), 0o755); err != nil {
		return err
	}
	source, err := member.Open()
	if err != nil {
		return err
	}
	defer source.Close()
	handle, err := os.OpenFile(destination, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, member.Mode().Perm())
	if err != nil {
		return err
	}
	if _, err := io.Copy(handle, source); err != nil {
		handle.Close()
		return err
	}
	if err := handle.Close(); err != nil {
		return err
	}
	return os.Chmod(destination, member.Mode().Perm())
}
