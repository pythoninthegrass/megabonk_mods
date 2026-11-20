// Package proton writes the Wine DllOverrides entry a prefix needs, the state
// the installer cannot leave to a first launch because it is prefix state rather
// than game-folder state.
package proton

import (
	"context"
	"io"
	"os"
	"os/exec"
	"regexp"
	"sort"
	"strings"
	"time"

	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ppath"
)

const (
	// DllOverridesSection is the registry section DllOverrides lives in.
	DllOverridesSection = `Software\Wine\DllOverrides`
)

// Runner runs a command with an environment and reports its exit code; tests
// inject their own.
type Runner func(argv []string, env map[string]string) int

// UserRegPath is the prefix's registry file.
func UserRegPath(prefix string) string { return ppath.Join(prefix, "user.reg") }

var (
	entryLine   = regexp.MustCompile(`^"([^"]+)"\s*=\s*(?:\([^)]*\)\s*)?"(.*)"\s*$`)
	sectionLine = regexp.MustCompile(`^\[(.+)\](?:\s+\d+)?\s*$`)
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
