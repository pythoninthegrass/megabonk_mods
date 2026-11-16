// Package cli is the command-line entry point: it resolves Steam, the game and
// its prefix, then installs, checks, or uninstalls. Exit codes are stable.
package cli

import (
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"runtime"
	"strings"

	"github.com/pythoninthegrass/megabonk_mods/installer/internal/content"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/gamebuild"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/modinstall"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/plan"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ppath"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/proton"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/site"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/steam"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/thunderstore"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ui"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/window"
)

// Stable exit codes: a desktop shortcut or a script can act on them.
const (
	ExitOK               = 0
	ExitError            = 1
	ExitUsage            = 2
	ExitNotFound         = 3
	ExitUnsupportedBuild = 4
	ExitOutOfDate        = 10
)

// MountRoots are the places removable Steam libraries turn up.
var MountRoots = defaultMountRoots()

// defaultMountRoots reads MEGABONK_MOUNT_ROOTS so a test can keep a mounted
// library out of discovery.
func defaultMountRoots() []string {
	raw, found := os.LookupEnv("MEGABONK_MOUNT_ROOTS")
	if !found {
		raw = "/media,/run/media,/mnt,/Volumes"
	}
	roots := []string{}
	for _, root := range strings.Split(raw, ",") {
		if root != "" {
			roots = append(roots, root)
		}
	}
	return roots
}

// LogHint names the file to read when a launch goes wrong.
const LogHint = "MelonLoader/Latest.log"

// Prog is the name usage messages call this program.
const Prog = "megabonk-installer"

// modFlag is --mod or --no-mod: both set the same choice, and the pair is
// refused after parsing so neither flag's own order decides the outcome.
type modFlag struct {
	options *Options
	choice  plan.ModChoice
}

func (m modFlag) String() string {
	if m.options == nil || m.options.Mod != m.choice {
		return ""
	}
	return m.choice.String()
}

// IsBoolFlag says these flags take no value. Without it the flag package treats
// a Value as value-taking and swallows the level that follows --mod.
func (m modFlag) IsBoolFlag() bool { return true }

func (m modFlag) Set(string) error {
	if m.choice == plan.ModForced {
		m.options.saidMod = true
	} else {
		m.options.saidNoMod = true
	}
	m.options.Mod = m.choice
	return nil
}

func (c *Command) checkModFlags(options *Options) error {
	if options.saidMod && options.saidNoMod {
		return fmt.Errorf("--mod and --no-mod cannot both be given")
	}
	return nil
}

// stringList collects a repeatable flag.
type stringList []string

func (s *stringList) String() string { return strings.Join(*s, ",") }

func (s *stringList) Set(value string) error {
	*s = append(*s, value)
	return nil
}

// Options is the parsed command line.
type Options struct {
	Home           string
	GameDir        string
	Prefix         string
	Libraries      []string
	Inputs         []string
	WineOverride   string
	Proton         string
	NoGUI          bool
	NonInteractive bool
	Check          bool
	DryRun         bool
	Uninstall      bool
	AsJSON         bool
	// Mod is what the player said about the level editor mod: asked for, refused,
	// or nothing, which means "whatever the game folder needs".
	Mod plan.ModChoice

	saidMod   bool
	saidNoMod bool
}

// Command runs one installer invocation against injected streams so tests can
// read exactly what the player would see.
type Command struct {
	Stdout io.Writer
	Stderr io.Writer
	Env    map[string]string
	// Environ supplies the process environment when Env is nil.
	Environ func() map[string]string
	// PickProgress chooses the progress reporter; nil uses ui.PickProgress.
	PickProgress func(env map[string]string, forceText bool, writer func(string)) ui.Progress
	// StartWindow opens the MyGo native-UI progress window; nil uses window.Run.
	// It reports (code, started), started false meaning fall back to plain text.
	StartWindow func(title string, work func(ui.Progress) int) (int, bool)
	// GOOS names the operating system the install targets; empty uses runtime.GOOS.
	GOOS string
	// Executable returns the running binary's path; nil uses os.Executable.
	Executable func() (string, error)
	// Gallery talks to the level site; nil uses MEGABONK_API_URL. Tests point it
	// at a local server so no run reaches the network.
	Gallery *site.Client
	// Thunder talks to Thunderstore; nil uses its environment locations.
	Thunder *thunderstore.Client
	// Pins and ModPins are the digests the run will accept; nil uses the ones the
	// installer ships.
	Pins    map[string]string
	ModPins []modinstall.ModPin
	// WineRunner runs the wine command for a prefix edit; nil runs the real one.
	WineRunner proton.Runner
}

// defaultPackage is the folder holding the installer on Windows and macOS, where
// the unzipped binary is run with no arguments; empty elsewhere.
func (c *Command) defaultPackage() string {
	if !c.native() && !c.wine() {
		return ""
	}
	executable := c.Executable
	if executable == nil {
		executable = os.Executable
	}
	path, err := executable()
	if err != nil {
		return ""
	}
	return filepath.Dir(path)
}

// native reports a Windows install, which has no Proton prefix, Flatpak or
// launch option to deal with.
func (c *Command) native() bool {
	if c.GOOS != "" {
		return c.GOOS == "windows"
	}
	return runtime.GOOS == "windows"
}

// wine reports a Mac install, which runs the Windows build in a Wine prefix.
func (c *Command) wine() bool {
	if c.GOOS != "" {
		return c.GOOS == "darwin"
	}
	return runtime.GOOS == "darwin"
}

// NewCommand returns a Command wired to the given streams.
func NewCommand(stdout, stderr io.Writer) *Command {
	return &Command{Stdout: stdout, Stderr: stderr}
}

func (c *Command) environment() map[string]string {
	if c.Env != nil {
		return c.Env
	}
	if c.Environ != nil {
		return c.Environ()
	}
	return ui.Environ()
}

func (c *Command) pickProgress(env map[string]string, forceText bool, writer func(string)) ui.Progress {
	if c.PickProgress != nil {
		return c.PickProgress(env, forceText, writer)
	}
	return ui.PickProgress(env, forceText, writer)
}

// Reporter writes what the player sees. In JSON mode human lines are silenced
// so stdout stays machine-readable; warnings still go to stderr.
type Reporter struct {
	AsJSON bool
	Stdout io.Writer
	Stderr io.Writer
	// Tee receives every non-empty human line as well; the window's details log.
	Tee func(line string)
}

func (r *Reporter) tee(line string) {
	if r.Tee != nil && line != "" {
		r.Tee(line)
	}
}

// Say prints a human-readable line on stdout.
func (r *Reporter) Say(message string) {
	if r.AsJSON {
		return
	}
	fmt.Fprintln(r.Stdout, message)
	r.tee(message)
}

// Warn prints a warning on stderr.
func (r *Reporter) Warn(message string) {
	fmt.Fprintf(r.Stderr, "warning: %s\n", message)
	r.tee("warning: " + message)
}

// Problem lists one validation failure on stderr.
func (r *Reporter) Problem(message string) {
	fmt.Fprintf(r.Stderr, "  - %s\n", message)
}

// Fail prints a fatal message on stderr and reports its exit code.
func (r *Reporter) Fail(message string, code int) int {
	fmt.Fprintln(r.Stderr, message)
	return code
}

func (r *Reporter) json(value any) {
	body, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return
	}
	fmt.Fprintln(r.Stdout, string(body))
}

// newFlagSet wires the command line. The help text is Go's own; the flag names,
// their meanings, and the exit codes are the contract.
func newFlagSet(options *Options) (*flag.FlagSet, *stringList) {
	fs := flag.NewFlagSet(Prog, flag.ContinueOnError)
	fs.SetOutput(io.Discard)
	var libraries stringList
	fs.StringVar(&options.Home, "home", "", "home directory to search for Steam (default: $HOME)")
	fs.StringVar(&options.GameDir, "game-dir", "", "install straight into this Megabonk folder, skipping Steam discovery")
	fs.StringVar(&options.Prefix, "prefix", "", "Proton or Wine prefix (the folder holding drive_c) to set the winhttp DLL override in")
	fs.Var(&libraries, "library", "extra Steam library folder to search (repeatable)")
	fs.Var(modFlag{options, plan.ModForced}, "mod", "also install the level editor mod and the loader it needs")
	fs.Var(modFlag{options, plan.ModRefused}, "no-mod", "install levels and packs only, leaving the mod alone")
	fs.StringVar(&options.WineOverride, "wine-override", "auto", "how to set winhttp = native,builtin")
	fs.StringVar(&options.Proton, "proton", "", "force a named Proton compatibility tool when looking for wine")
	fs.BoolVar(&options.NoGUI, "no-gui", false, "never open a progress dialog")
	fs.BoolVar(&options.NonInteractive, "non-interactive", false, "force plain text without terminal input")
	fs.BoolVar(&options.Check, "check", false, "report what is missing instead of changing anything")
	fs.BoolVar(&options.DryRun, "dry-run", false, "print what would be done and change nothing")
	fs.BoolVar(&options.Uninstall, "uninstall", false, "remove what this installer placed")
	fs.BoolVar(&options.AsJSON, "json", false, "machine-readable output on stdout")
	// --mod and --no-mod are one choice spelled two ways, each recorded as it is
	// seen so the pair can be refused once the whole line is read.
	return fs, &libraries
}

// ParseFlags reads the command line and rejects a choice outside the set the
// reference allows.
func ParseFlags(argv []string) (*Options, error) {
	options := &Options{WineOverride: "auto"}
	fs, libraries := newFlagSet(options)
	if err := fs.Parse(argv); err != nil {
		return nil, err
	}
	// Leftovers are the levels the player asked for. A word shaped like a flag was
	// meant to be one: Go stops at the first non-flag word, so it lands here.
	for _, arg := range fs.Args() {
		if strings.HasPrefix(arg, "-") {
			return nil, fmt.Errorf("%s: error: unrecognized arguments: %s", Prog, arg)
		}
	}
	options.Inputs = append(options.Inputs, fs.Args()...)
	switch options.WineOverride {
	case "auto", "registry", "wine", "off":
	default:
		return nil, fmt.Errorf("%s: error: argument --wine-override: invalid choice: '%s' (choose from 'auto', 'off', 'registry', 'wine')",
			Prog, options.WineOverride)
	}
	options.Libraries = *libraries
	return options, nil
}

// usage is the help text argparse would print: usage lines, the description, and
// each flag with its help.
func usage() string {
	options := &Options{}
	fs, _ := newFlagSet(options)
	var body strings.Builder
	fs.SetOutput(&body)
	fs.PrintDefaults()
	lines := []string{
		"usage: " + Prog + " [-h] [--home HOME] [--game-dir GAME_DIR] [--prefix PREFIX]",
		"                    [--library LIBRARY]",
		"                    [--wine-override {auto,off,registry,wine}] [--proton PROTON]",
		"                    [--mod | --no-mod] [--no-gui] [--non-interactive] [--check]",
		"                    [--dry-run] [--uninstall] [--json]",
		"                    LEVEL [LEVEL ...]",
		"",
		"Install Megabonk levels from " + site.SiteHost + " into a Megabonk folder, on Linux",
		"(Steam Play / Proton), Windows, or macOS under Wine. Each LEVEL is a share code",
		"such as 7N1-MVB-WKF, a " + site.SiteHost + " level link, or the path to a",
		".mblevel.json file.",
		"",
		"options:",
		"  -h, --help            show this help message and exit",
	}
	for _, line := range strings.Split(strings.TrimRight(body.String(), "\n"), "\n") {
		lines = append(lines, "  "+strings.TrimSpace(line))
	}
	return strings.Join(lines, "\n") + "\n"
}

// FindInstall locates Megabonk through Steam, reporting the libraries it
// searched. A prefix chosen with --prefix needs no reporting.
func (c *Command) FindInstall(home string, extraLibraries []string, reporter *Reporter, prefixChosen bool) (gameDir string, prefix string, searched []string) {
	if c.native() {
		return c.findWindowsInstall(extraLibraries, reporter)
	}
	if c.wine() {
		return c.findWineInstall(home, extraLibraries, "", reporter)
	}
	probe := steam.ProbeFlatpak(home)
	granted := append([]string{}, probe.Paths...)
	clients := steam.ClientRoots(home, "", granted)
	if len(granted) > 0 {
		reporter.Say("Flatpak Steam may only read: " + strings.Join(granted, ", "))
	}
	if probe.Source == "none" && !probe.CLIFound && anyFlatpak(clients) {
		reporter.Warn("flatpak CLI not found: Flatpak Steam grants were not read; install flatpak, " +
			"or pass --library <path> for a library the sandbox cannot read")
	}
	roots := steam.LibraryRoots(clients, granted, expandAll(extraLibraries), existingMountRoots(), false)
	warnUngrantedFlatpakRoots(reporter, clients, roots)
	if len(roots) == 0 {
		reporter.Say("no Steam library found; pass --game-dir if Megabonk is somewhere unusual")
	}
	found := steam.FindGameDir(roots, "")
	if found == "" {
		return "", "", rootPaths(roots)
	}
	prefix, prefixes := steam.FindPrefix(found, rootPaths(roots), "")
	reportPrefix(reporter, found, prefix, prefixes, prefixChosen)
	return found, prefix, rootPaths(roots)
}

// findWindowsInstall searches the libraries Steam records for a Windows client.
func (c *Command) findWindowsInstall(extraLibraries []string, reporter *Reporter) (gameDir string, prefix string, searched []string) {
	clients := steam.WindowsClientRoots(steam.ProgramFilesDirs(func(key string) string { return c.environment()[key] }))
	roots := steam.LibraryRoots(clients, nil, expandAll(extraLibraries), nil, false)
	if len(roots) == 0 {
		reporter.Say("no Steam library found; pass --game-dir if Megabonk is somewhere unusual")
	}
	return steam.FindGameDir(roots, ""), "", rootPaths(roots)
}

// findWineInstall searches the Steam clients inside Wine prefixes, plain Wine
// before CrossOver, or only the one prefix the player named.
func (c *Command) findWineInstall(home string, extraLibraries []string, prefix string, reporter *Reporter) (gameDir string, winePrefix string, searched []string) {
	clients := steam.WineClientRoots(home)
	if prefix != "" {
		clients = nil
		if client, found := steam.WineClientIn(ppath.ExpandUser(prefix), "wine"); found {
			clients = append(clients, client)
		}
	}
	roots := steam.LibraryRoots(clients, nil, expandAll(extraLibraries), nil, false)
	if len(roots) == 0 {
		reporter.Say("no Steam library found; pass --game-dir if Megabonk is somewhere unusual")
	}
	found := steam.FindGameDir(roots, "")
	if found == "" {
		return "", "", rootPaths(roots)
	}
	return found, steam.PrefixOfGameDir(found), rootPaths(roots)
}

// reportPrefix tells the player when the prefix written to is not the one beside
// the game, and which two prefixes were competing when none could be picked.
func reportPrefix(reporter *Reporter, gameDir, prefix string, prefixes []steam.PrefixCandidate, prefixChosen bool) {
	if prefixChosen {
		return
	}
	own := steam.PrefixForGameDir(gameDir, "")
	if prefix != "" {
		if prefix != own {
			reporter.Say("Proton prefix: " + prefix + " (Steam keeps it in that library, not beside the game)")
		}
		return
	}
	usable := []steam.PrefixCandidate{}
	for _, candidate := range prefixes {
		if candidate.Accepted {
			usable = append(usable, candidate)
		}
	}
	if len(usable) > 1 {
		reporter.Warn("more than one usable Proton prefix exists — pass --prefix <path to the pfx directory> to pick one")
		for _, candidate := range usable {
			reporter.Warn("  - " + candidate.Path + " (library " + candidate.Library + ")")
		}
	}
}

func anyFlatpak(clients []steam.Client) bool {
	for _, client := range clients {
		if client.Kind == "flatpak" {
			return true
		}
	}
	return false
}

func rootPaths(roots []steam.Library) []string {
	paths := make([]string, 0, len(roots))
	for _, root := range roots {
		paths = append(paths, root.Path)
	}
	return paths
}

func expandAll(paths []string) []string {
	out := make([]string, 0, len(paths))
	for _, path := range paths {
		out = append(out, ppath.ExpandUser(path))
	}
	return out
}

func existingMountRoots() []string {
	roots := []string{}
	for _, root := range MountRoots {
		if ppath.IsDir(root) {
			roots = append(roots, root)
		}
	}
	return roots
}

func warnUngrantedFlatpakRoots(reporter *Reporter, clients []steam.Client, roots []steam.Library) {
	flatpakClients := map[string]bool{}
	for _, client := range clients {
		if client.Kind == "flatpak" {
			flatpakClients[client.Root] = true
		}
	}
	for _, root := range roots {
		if root.Source != "client" || root.Client == nil || !flatpakClients[root.Client.Root] {
			continue
		}
		if root.Granted != nil && *root.Granted {
			continue
		}
		reporter.Warn(fmt.Sprintf("library %s is not granted to the Flatpak sandbox: Steam cannot read files installed there; "+
			"grant it with: flatpak override --user --filesystem=%s %s", root.Path, root.Path, steam.FlatpakID))
	}
}

// ValidateInputs checks the --level and --pack arguments before anything else.
func launchOptionNote(launchOption string) string {
	return "Steam > Library > Megabonk > Properties, then paste this into Launch Options:\n\n" +
		"    " + launchOption + "\n\n" +
		"Steam rewrites its own config while it runs, so the installer cannot set this for you."
}

// progress chooses the reporter: plain text on the command's stdout, silenced
// entirely in JSON mode so stdout stays machine-readable.
func (c *Command) progress(options *Options, reporter *Reporter) ui.Progress {
	writer := func(line string) { fmt.Fprintln(c.Stdout, line) }
	if reporter.AsJSON {
		writer = func(string) {}
	}
	return c.pickProgress(c.environment(), options.NoGUI || options.NonInteractive || reporter.AsJSON, writer)
}

func (c *Command) startWindow(title string, work func(ui.Progress) int) (int, bool) {
	if c.StartWindow != nil {
		return c.StartWindow(title, work)
	}
	return window.Run(title, work)
}

// runProgress reports a long run: the MyGo native-UI window first when this
// session can show one, and the plain-text reporter otherwise.
func (c *Command) runProgress(options *Options, reporter *Reporter, run windowRun, work func(ui.Progress) (int, error)) (int, error) {
	env := c.environment()
	forced := options.NoGUI || options.NonInteractive || reporter.AsJSON
	if ui.ShouldAttemptGUI(env, forced) {
		var (
			code    int
			workErr error
		)
		declined := false
		_, started := c.startWindow(run.Title, func(progress ui.Progress) int {
			if planner, ok := progress.(ui.Planner); ok {
				planner.Plan(run.Steps)
			}
			if confirmer, ok := progress.(ui.Confirmer); ok && !confirmer.Confirm(run.Prompt) {
				declined = true
				return ExitError
			}
			if logger, ok := progress.(ui.Logger); ok {
				reporter.Tee = logger.Log
				defer func() { reporter.Tee = nil }()
			}
			code, workErr = work(progress)
			if workErr != nil {
				progress.Finish(run.failure(workErr), false)
			}
			return code
		})
		if started && declined {
			reporter.Say("cancelled — nothing was changed")
			return ExitError, nil
		}
		if started {
			return code, workErr
		}
		if note := ui.WindowSkipNote(env); note != "" {
			reporter.Warn(note)
		}
	}
	return work(c.progress(options, reporter))
}

// windowRun describes a long run to the progress window.
type windowRun struct {
	Title  string
	Prompt string
	// Steps are the labels the run will report, in order; nil lists them as they finish.
	Steps []string
	// Cancelled is what the window says when the person aborts mid-run.
	Cancelled string
}

func (r windowRun) failure(err error) string {
	if errors.Is(err, plan.ErrCancelled) {
		return r.Cancelled
	}
	return err.Error()
}

func (c *Command) planOptions(options *Options, gameDir string, located *Located) plan.Options {
	inputs := make([]plan.Input, 0, len(options.Inputs))
	for _, raw := range options.Inputs {
		inputs = append(inputs, plan.Input{Raw: raw})
	}
	mode := ""
	if c.native() {
		mode = plan.PlatformNative
	}
	wineBin := ""
	if c.wine() {
		mode = plan.PlatformWine
		wineBin = c.wineBinary()
	}
	return plan.Options{
		Game:       gameDir,
		Prefix:     c.prefix(options, gameDir, located),
		Platform:   mode,
		WineBin:    wineBin,
		WineRunner: c.WineRunner,
		Inputs:     inputs,
		Mod:        options.Mod,
		APIClient:  c.Gallery,
		Thunder:    c.Thunder,
		Pins:       c.Pins,
		ModPins:    c.ModPins,
		Cache:      c.downloadCache(),
	}
}

// downloadCache is where archives are kept between runs, so a repair can reuse
// what was already fetched and verified.
func (c *Command) downloadCache() string {
	home, found := lookupHome(c.environment())
	if !found {
		return ""
	}
	return filepath.Join(home, ".cache", "megabonk-levels")
}

func lastOf(values []string) string {
	if len(values) == 0 {
		return ""
	}
	return ppath.ExpandUser(values[len(values)-1])
}

// wineBinary is the wine that edits a prefix's registry: MEGABONK_WINE, then
// the search path, then a Wine.app under the user's or the system's Applications.
func (c *Command) wineBinary() string {
	env := c.environment()
	home, _ := lookupHome(env)
	return proton.FindWineBinary(env["MEGABONK_WINE"], filepath.SplitList(env["PATH"]),
		[]string{ppath.Join(home, "Applications"), "/Applications"})
}

func (c *Command) prefix(options *Options, gameDir string, located *Located) string {
	if c.native() {
		return ""
	}
	if c.wine() {
		if options.Prefix != "" {
			return ppath.ExpandUser(options.Prefix)
		}
		if located != nil && located.Prefix != "" {
			return located.Prefix
		}
		return steam.PrefixOfGameDir(gameDir)
	}
	if options.Prefix != "" {
		return ppath.ExpandUser(options.Prefix)
	}
	if located != nil && located.PrefixDiscovered {
		return located.Prefix
	}
	return steam.PrefixForGameDir(gameDir, "")
}

// Located is what discovery settled on: the game, the prefix to write into, and
// the libraries it looked in.
type Located struct {
	GameDir          string
	Prefix           string
	Searched         []string
	PrefixDiscovered bool
}

// doCheck reports what the named levels still need and whether the mod is in
// place. It changes nothing.
func (c *Command) doCheck(options *Options, reporter *Reporter, gameDir string, located *Located) (int, error) {
	built, err := plan.BuildPlan(c.planOptions(options, gameDir, located))
	if err != nil {
		return 0, err
	}
	for _, warning := range built.Warnings {
		reporter.Warn(warning)
	}
	if len(built.Actions) == 0 {
		reporter.Say(checkCleanMessage(built))
		// A clean content check still answers the mod question, which is the only
		// thing --check can be asked once nothing is left to place.
		reporter.Say(modStatusLine(built))
		if reporter.AsJSON {
			reporter.json(withPlan(map[string]any{"ok": true, "missing": []any{}, "mod": modDocument(built)}, built))
		}
		return ExitOK, nil
	}
	reporter.Say(fmt.Sprintf("%d thing(s) are missing from %s:", len(built.Actions), gameDir))
	missing := []any{}
	for _, action := range built.Actions {
		reporter.Say(fmt.Sprintf("  - %s: %s", action.Kind, action.Label()))
		missing = append(missing, action.Document())
	}
	reporter.Say(modStatusLine(built))
	if reporter.AsJSON {
		reporter.json(withPlan(map[string]any{"ok": false, "missing": missing, "mod": modDocument(built)}, built))
	}
	return ExitOutOfDate, nil
}

// checkCleanMessage tells the player the game already holds every level asked
// for, naming what is there.
func checkCleanMessage(built *plan.Plan) string {
	if len(built.Levels) == 0 {
		return "nothing to do — the game already holds what was asked for"
	}
	return "nothing to do — " + strings.Join(built.Levels, ", ") + " " +
		grammaticalIs(len(built.Levels)) + " already installed"
}

func grammaticalIs(count int) string {
	if count == 1 {
		return "is"
	}
	return "are"
}

// modStatusLine says whether the level editor mod is installed, and at what
// version.
func modStatusLine(built *plan.Plan) string {
	if built.ModStatus == nil || !built.ModStatus.Installed {
		return "the " + thunderstore.ModName + " mod is not installed"
	}
	release := built.ModStatus.Release
	if release == "" {
		release = built.ModStatus.ModVersion
	}
	if release == "" {
		return "the " + thunderstore.ModName + " mod is installed"
	}
	return "the " + thunderstore.ModName + " mod is installed (version " + release + ")"
}

// modDocument is the mod half of a --json payload.
func modDocument(built *plan.Plan) map[string]any {
	installed := built.ModStatus != nil && built.ModStatus.Installed
	document := map[string]any{"installed": installed, "wanted": built.Mod}
	if built.ModStatus != nil {
		document["version"] = built.ModStatus.Release
		document["bepinex_version"] = built.ModStatus.BepInExVersion
	}
	return document
}

// withPlan merges a plan document into a JSON payload.
func withPlan(payload map[string]any, built *plan.Plan) map[string]any {
	body, err := json.Marshal(built.Document())
	if err != nil {
		return payload
	}
	var document map[string]any
	if err := json.Unmarshal(body, &document); err != nil {
		return payload
	}
	for key, value := range document {
		payload[key] = value
	}
	return payload
}

// doInstall shows the plan, asks for it to be confirmed through the progress
// window, and applies it. Nothing in the game folder changes before that.
func (c *Command) doInstall(options *Options, reporter *Reporter, gameDir string, located *Located) (int, error) {
	opts := c.planOptions(options, gameDir, located)
	built, err := plan.BuildPlan(opts)
	if err != nil {
		return 0, err
	}
	for _, warning := range built.Warnings {
		reporter.Warn(warning)
	}

	if reporter.AsJSON && (options.DryRun || built.IsNoop()) {
		reporter.json(withPlan(map[string]any{"ok": true, "dry_run": options.DryRun}, built))
		return ExitOK, nil
	}

	if options.DryRun {
		if len(built.Actions) == 0 {
			reporter.Say(checkCleanMessage(built))
		} else {
			reporter.Say(fmt.Sprintf("would do %d thing(s) to %s:", len(built.Actions), gameDir))
			for _, action := range built.Actions {
				reporter.Say(fmt.Sprintf("  - %s: %s", action.Kind, action.Label()))
			}
			reporter.Say(modStatusLine(built))
		}
		return ExitOK, nil
	}

	steps := make([]string, 0, len(built.Actions))
	for _, action := range built.Actions {
		steps = append(steps, action.Label())
	}
	installRun := windowRun{
		Title:     "Megabonk Levels installer",
		Prompt:    "Install Megabonk Levels",
		Steps:     steps,
		Cancelled: "Cancelled; files already placed were rolled back.",
	}
	code, err := c.runProgress(options, reporter, installRun, func(progress ui.Progress) (int, error) {
		taken, err := plan.ApplyPlan(built, progress)
		if err != nil {
			return 0, err
		}
		if reporter.AsJSON {
			steps := []any{}
			for _, action := range taken {
				steps = append(steps, action.Document())
			}
			reporter.json(withPlan(map[string]any{"ok": true, "dry_run": false, "taken": steps}, built))
			return ExitOK, nil
		}
		c.reportInstall(reporter, built, taken)
		reportGameBuild(reporter, steam.InstalledBuildID(built.GameDir))
		if shower, ok := progress.(ui.LaunchOptionShower); ok && built.LaunchOption != nil {
			shower.ShowLaunchOption(*built.LaunchOption)
		}
		return ExitOK, nil
	})
	if errors.Is(err, plan.ErrCancelled) {
		reporter.Say("install cancelled — files already placed were rolled back")
		return ExitError, nil
	}
	if err != nil {
		return 0, err
	}
	return code, nil
}

// reportInstall tells the player what landed, in the order the plan promised it:
// levels, packs, the mod if one was placed, and the record --uninstall reads.
func (c *Command) reportInstall(reporter *Reporter, built *plan.Plan, taken []plan.Action) {
	if len(taken) == 0 {
		reporter.Say(checkCleanMessage(built))
	} else {
		reporter.Say(fmt.Sprintf("installed %d thing(s) into %s", len(taken), built.GameDir))
	}
	for _, action := range taken {
		reporter.Say(fmt.Sprintf("  %s: %s", action.Kind, action.Path))
	}
	if len(taken) > 0 {
		reporter.Say("  " + modStatusLine(built))
	}
	if built.LaunchOption != nil {
		reporter.Say("")
		reporter.Say(launchOptionNote(*built.LaunchOption))
	} else if built.OverrideNote != "" {
		// A Wine run edited the prefix itself; say so instead of pointing at Steam.
		reporter.Say("")
		reporter.Say("Set " + built.OverrideNote + ".")
	}
	record := content.LoadRecord(built.GameDir)
	if record != nil {
		reporter.Say("")
		for _, line := range content.DescribeRecord(record) {
			reporter.Say("  " + line)
		}
	}
	reporter.Say("")
	reporter.Say("Start Megabonk from Steam; the map editor loads with the game. Anything that goes wrong is in " + LogHint + ".")
}

func (c *Command) doUninstall(options *Options, reporter *Reporter, gameDir string) (int, error) {
	record := content.LoadRecord(gameDir)
	if record == nil {
		reporter.Say("nothing to uninstall: no installer record in " + gameDir)
		return ExitOK, nil
	}
	uninstallRun := windowRun{
		Title:     "Megabonk Levels uninstaller",
		Prompt:    "Uninstall Megabonk Levels",
		Cancelled: "Stopped; run the uninstaller again to finish.",
	}
	code, err := c.runProgress(options, reporter, uninstallRun, func(progress ui.Progress) (int, error) {
		removed, err := plan.Uninstall(gameDir, progress)
		if err != nil {
			return 0, err
		}
		reporter.Say(fmt.Sprintf("removed %d item(s) from %s", len(removed), gameDir))
		for _, path := range removed {
			reporter.Say("  " + path)
		}
		if reporter.AsJSON {
			items := make([]any, 0, len(removed))
			for _, path := range removed {
				items = append(items, path)
			}
			reporter.json(map[string]any{"ok": true, "removed": items})
		}
		return ExitOK, nil
	})
	if errors.Is(err, plan.ErrCancelled) {
		reporter.Say("uninstall stopped — run --uninstall again to finish")
		return ExitError, nil
	}
	if err != nil {
		return 0, err
	}
	return code, nil
}

// Main runs one installer invocation and reports its exit code.
func (c *Command) Main(argv []string) int {
	options, err := ParseFlags(argv)
	if err != nil {
		if err == flag.ErrHelp {
			fmt.Fprint(c.Stdout, usage())
			return ExitOK
		}
		fmt.Fprintln(c.Stderr, usageError(err.Error()))
		return ExitUsage
	}
	if err := c.checkModFlags(options); err != nil {
		fmt.Fprintln(c.Stderr, usageError(err.Error()))
		return ExitUsage
	}
	reporter := &Reporter{AsJSON: options.AsJSON, Stdout: c.Stdout, Stderr: c.Stderr}

	if options.Uninstall {
		located := c.locate(options, reporter)
		if located == nil || located.GameDir == "" {
			return ExitNotFound
		}
		code, err := c.doUninstall(options, reporter, located.GameDir)
		if err != nil {
			return reporter.Fail(err.Error(), ExitError)
		}
		return code
	}

	if len(options.Inputs) == 0 {
		return reporter.Fail("nothing to install: name at least one level — a share code such as "+
			site.ExampleCode+", a "+site.SiteHost+" level link, or a "+plan.LevelFileSuffix+
			" file on disk", ExitUsage)
	}

	located := c.locate(options, reporter)
	if located == nil || located.GameDir == "" {
		return ExitNotFound
	}
	gameDir := located.GameDir
	if steam.SteamRunning() {
		reporter.Warn("Steam is running — quit it first if a step looks like it did not stick")
	}

	if options.Check {
		code, err := c.doCheck(options, reporter, gameDir, located)
		if err != nil {
			return reporter.Fail(err.Error(), ExitError)
		}
		return code
	}
	code, err := c.doInstall(options, reporter, gameDir, located)
	if err != nil {
		switch {
		case plan.IsUnsupportedBuild(err):
			return reporter.Fail(err.Error(), ExitUnsupportedBuild)
		// The player left out an argument the platform needs, which is a usage
		// error rather than something that went wrong along the way.
		case plan.IsMissingPrefix(err):
			return reporter.Fail(err.Error(), ExitUsage)
		default:
			return reporter.Fail(err.Error(), ExitError)
		}
	}
	return code
}

// reportGameBuild names the Steam build the game is on, for a player reporting a
// problem. It is an observation, not a verdict: nothing is pinned to one build.
func reportGameBuild(reporter *Reporter, installed string) {
	if installed == "" {
		reporter.Say("installed game build is unknown (no Steam appmanifest found)")
		return
	}
	reporter.Say("game build " + installed)
}

// locate resolves the game directory from --game-dir or Steam discovery.
func (c *Command) locate(options *Options, reporter *Reporter) *Located {
	if options.GameDir != "" {
		gameDir := ppath.ExpandUser(options.GameDir)
		if !ppath.IsDir(gameDir) {
			reporter.Fail(gamebuild.UnknownBuildMessage(gameDir), ExitNotFound)
			return nil
		}
		return &Located{GameDir: gameDir}
	}
	home := ""
	if options.Home != "" {
		home = ppath.ExpandUser(options.Home)
	} else if value, found := lookupHome(c.environment()); found {
		home = value
	} else if value, err := os.UserHomeDir(); err == nil {
		home = value
	}
	var gameDir, prefix string
	var searched []string
	if c.wine() {
		gameDir, prefix, searched = c.findWineInstall(home, options.Libraries, options.Prefix, reporter)
	} else {
		gameDir, prefix, searched = c.FindInstall(home, options.Libraries, reporter, options.Prefix != "")
	}
	if gameDir == "" {
		reporter.Fail(strings.Join(c.notFoundLines(home, options.Libraries), "\n"), ExitNotFound)
		return &Located{Searched: searched}
	}
	return &Located{GameDir: gameDir, Prefix: prefix, Searched: searched, PrefixDiscovered: true}
}

func lookupHome(env map[string]string) (string, bool) {
	value, found := env["HOME"]
	return value, found && value != ""
}

// notFoundLines lists every candidate discovery considered, why each was
// rejected, and the flag to retry with.
func (c *Command) notFoundLines(home string, extraLibraries []string) []string {
	lines := []string{
		"Megabonk was not found in any Steam library.",
		"Install it in Steam and start it once, or point the installer straight at it:",
		"  " + Prog + " --game-dir <path to the folder holding " + gamebuild.WindowsExe + "> LEVEL...",
	}
	if c.native() {
		return c.windowsNotFoundLines(extraLibraries, lines)
	}
	if c.wine() {
		return c.wineNotFoundLines(home, extraLibraries, lines)
	}
	lines = append(lines, "", "Steam clients considered:")
	candidates := steam.ClientCandidates(home, "", nil)
	accepted := []steam.Client{}
	for _, candidate := range candidates {
		status := candidate.Reason
		if candidate.Accepted {
			status = "found"
			accepted = append(accepted, steam.Client{Kind: candidate.Kind, Root: candidate.Path})
		}
		lines = append(lines, fmt.Sprintf("  - %s (%s): %s", candidate.Path, candidate.Kind, status))
	}
	if len(accepted) == 0 {
		lines = append(lines, "  none accepted — pass --home <path> if Steam is not under "+home)
	}
	granted := append([]string{}, steam.ProbeFlatpak(home).Paths...)
	considered := steam.LibraryCandidates(accepted, granted, expandAll(extraLibraries), existingMountRoots(), false)
	var searched, skipped []steam.Candidate
	for _, candidate := range considered {
		switch {
		case candidate.Accepted:
			searched = append(searched, candidate)
		case candidate.Reason != steam.ReasonDuplicate:
			skipped = append(skipped, candidate)
		}
	}
	if len(searched) > 0 {
		lines = append(lines, "Libraries searched:")
		for _, candidate := range searched {
			lines = append(lines, fmt.Sprintf("  - %s (%s)", candidate.Path, candidate.Kind))
		}
	} else {
		lines = append(lines, "Libraries searched: none — pass --library <path> to add one")
	}
	if len(skipped) > 0 {
		lines = append(lines, "Libraries skipped:")
		for _, candidate := range skipped {
			lines = append(lines, fmt.Sprintf("  - %s (%s): %s — retry with --library %s",
				candidate.Path, candidate.Kind, candidate.Reason, candidate.Path))
		}
	}
	roots := make([]steam.Library, 0, len(searched))
	for _, candidate := range searched {
		roots = append(roots, steam.Library{Path: candidate.Path, Source: candidate.Kind, Client: candidate.Client, Granted: candidate.Granted})
	}
	rejected := []steam.GameCandidate{}
	for _, candidate := range steam.GameCandidates(roots, "") {
		if !candidate.Accepted {
			rejected = append(rejected, candidate)
		}
	}
	if len(rejected) > 0 {
		lines = append(lines, "Il2Cpp installs that were not Megabonk:")
		for _, candidate := range rejected {
			lines = append(lines, fmt.Sprintf("  - %s: %s", candidate.Path, candidate.Reason))
		}
	}
	return lines
}

// wineNotFoundLines says where a Mac run looked: Steam inside a Wine prefix,
// plain Wine before CrossOver, and the libraries those name.
func (c *Command) wineNotFoundLines(home string, extraLibraries, header []string) []string {
	lines := append([]string{}, header...)
	lines = append(lines, "", "Megabonk runs as the Windows build under Wine. Steam is looked for inside a Wine prefix, under ~/.local/share/megabonk/wine, ~/.wine and any CrossOver bottle.")
	clients := steam.WineClientRoots(home)
	if len(clients) == 0 {
		return append(lines, "No Steam client was found in a Wine prefix — pass --prefix <the Wine prefix folder that holds drive_c>, or --game-dir.")
	}
	for _, client := range clients {
		lines = append(lines, "  - Steam client: "+client.Root)
	}
	roots := steam.LibraryRoots(clients, nil, expandAll(extraLibraries), nil, false)
	if len(roots) == 0 {
		return append(lines, "Libraries searched: none — pass --library <path> to add one")
	}
	lines = append(lines, "Libraries searched:")
	for _, root := range roots {
		lines = append(lines, "  - "+root.Path)
	}
	return lines
}

// windowsNotFoundLines says where a Windows run looked: the registry path Steam
// records, Steam under Program Files, and the libraries those name.
func (c *Command) windowsNotFoundLines(extraLibraries, header []string) []string {
	lines := append([]string{}, header...)
	lines = append(lines, "", "Steam is found through HKCU\\Software\\Valve\\Steam (SteamPath) and Steam under Program Files, then its libraryfolders.vdf.")
	clients := steam.WindowsClientRoots(steam.ProgramFilesDirs(func(key string) string { return c.environment()[key] }))
	if len(clients) == 0 {
		return append(lines, "No Steam client was found there — pass --game-dir, or --library <path> for a Steam library folder.")
	}
	for _, client := range clients {
		lines = append(lines, "  - Steam client: "+client.Root)
	}
	roots := steam.LibraryRoots(clients, nil, expandAll(extraLibraries), nil, false)
	if len(roots) == 0 {
		return append(lines, "Libraries searched: none — pass --library <path> to add one")
	}
	lines = append(lines, "Libraries searched:")
	for _, root := range roots {
		lines = append(lines, "  - "+root.Path)
	}
	return lines
}

// usageError keeps a flag-package parse failure in argparse's shape: the program
// name, then the reason.
func usageError(message string) string {
	if strings.HasPrefix(message, Prog+": ") {
		return message
	}
	return Prog + ": error: " + message
}

// Run is the entry point the command binary calls.
func Run(argv []string, stdout, stderr io.Writer) int {
	return NewCommand(stdout, stderr).Main(argv)
}
