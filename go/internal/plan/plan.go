// Package plan works out what an install consists of before anything is
// written, and carries it out step by step. The plan compares the package
// against the game directory, so a second run does nothing, a repair replaces
// only what changed or went missing, and a dry run can show the whole thing
// without touching the disk.
package plan

import (
	"archive/zip"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/pythoninthegrass/megabonk_mods/installer/internal/content"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/gamebuild"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/manifest"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ppath"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/proton"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/steam"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ui"
)

// RuntimeModePrefix puts .NET inside the Proton prefix; RuntimeModeGameDir puts
// it beside the game and needs a Steam launch option; RuntimeModeNative is a
// Windows install, where MelonLoader finds the runtime under its own directory;
// RuntimeModeWine is that same placement inside a Wine prefix, which also needs
// the version.dll override.
const (
	RuntimeModePrefix  = "prefix"
	RuntimeModeGameDir = "gamedir"
	RuntimeModeNative  = "native"
	RuntimeModeWine    = "wine"

	versionMarkerFile = "MelonLoader/net6/MelonLoader.dll"
	shimName          = "version.dll"

	// loaderConfigName and pluginsDir are what MelonLoader creates on first launch.
	loaderConfigName = "Loader.cfg"
	pluginsDir       = "Plugins"
	fallbackVersion  = "0.7.3"
	loaderKind       = "melonloader"
	dotnetKind       = "dotnet"
)

// Error means the install cannot be planned: the package, the game, or the
// prefix is not in a usable state.
type Error struct{ message string }

func (e *Error) Error() string { return e.message }

func fail(format string, args ...any) error {
	return &Error{message: fmt.Sprintf(format, args...)}
}

// Action is one step of a plan.
type Action struct {
	Kind   string
	Path   string
	Detail string
	Source string
	// HasSource tells an empty Source apart from no source at all.
	HasSource bool
}

// Label is the step's description: its detail, or the file name.
func (a Action) Label() string {
	if a.Detail != "" {
		return a.Detail
	}
	return ppath.Name(a.Path)
}

// ActionDocument is an action in the shape --json prints.
type ActionDocument struct {
	Kind   string  `json:"kind"`
	Path   string  `json:"path"`
	Detail string  `json:"detail"`
	Source *string `json:"source,omitempty"`
}

// Document renders the action for --json.
func (a Action) Document() ActionDocument {
	entry := ActionDocument{Kind: a.Kind, Path: a.Path, Detail: a.Detail}
	if a.HasSource {
		source := a.Source
		entry.Source = &source
	}
	return entry
}

// Document is a plan in the shape --json prints.
type Document struct {
	Package            string           `json:"package"`
	PackageID          string           `json:"package_id"`
	ModVersion         string           `json:"mod_version"`
	MelonloaderVersion string           `json:"melonloader_version"`
	GameDir            string           `json:"game_dir"`
	Build              string           `json:"build"`
	Prefix             *string          `json:"prefix"`
	RuntimeMode        string           `json:"runtime_mode"`
	RuntimeTarget      string           `json:"runtime_target"`
	DllOverride        bool             `json:"dll_override"`
	LaunchOption       *string          `json:"launch_option"`
	Actions            []ActionDocument `json:"actions"`
	Warnings           []string         `json:"warnings"`
}

// Plan is the comparison between a package and a game directory.
type Plan struct {
	Package          string
	Manifest         *manifest.Package
	GameDir          string
	Build            string
	Prefix           string
	RuntimeMode      string
	RuntimeTarget    string
	DllOverride      bool
	Actions          []Action
	LaunchOption     *string
	Warnings         []string
	WineOverrideMode string
	WineBin          string
	ForcedTool       string
}

// IsNoop reports whether the game already matches the package.
func (p *Plan) IsNoop() bool { return len(p.Actions) == 0 }

// Document renders the plan for --json.
func (p *Plan) Document() Document {
	document := Document{
		Package:            p.Package,
		ModVersion:         p.Manifest.ModVersion,
		MelonloaderVersion: p.Manifest.MelonloaderVersion,
		GameDir:            p.GameDir,
		Build:              p.Build,
		RuntimeMode:        p.RuntimeMode,
		RuntimeTarget:      p.RuntimeTarget,
		DllOverride:        p.DllOverride,
		LaunchOption:       p.LaunchOption,
		Actions:            []ActionDocument{},
		Warnings:           p.Warnings,
	}
	if document.Warnings == nil {
		document.Warnings = []string{}
	}
	if p.Manifest != nil {
		document.PackageID = p.Manifest.PackageID
	}
	if p.Prefix != "" {
		prefix := p.Prefix
		document.Prefix = &prefix
	}
	for _, action := range p.Actions {
		document.Actions = append(document.Actions, action.Document())
	}
	return document
}

// Options carries the caller's choices; the zero value is a prefix install with
// everything checked.
type Options struct {
	Manifest     *manifest.Package
	Game         string
	Build        string
	Prefix       string
	RuntimeMode  string
	DllOverride  string
	WineOverride string
	ForcedTool   string
	// WineBin is the wine binary that edits a Wine-mode prefix's registry; empty
	// falls back to editing user.reg.
	WineBin string
	Level   string
	Pack    string
	Verify  bool
}

// BuildPlan compares the package against the game and returns the steps still
// needed.
func BuildPlan(packageDir string, options Options) (*Plan, error) {
	packageDir = ppath.Normalize(packageDir)
	pkg := options.Manifest
	if pkg == nil {
		loaded, err := manifest.LoadManifest(ppath.Join(packageDir, "manifest.json"))
		if err != nil {
			return nil, err
		}
		pkg = loaded
	}
	if options.Game == "" {
		return nil, fail("no game directory: pass --game-dir, or install Megabonk in Steam first")
	}
	game := ppath.Normalize(options.Game)
	if options.Verify {
		if err := checkPackage(packageDir); err != nil {
			return nil, err
		}
	}
	build, err := effectiveBuild(game, options.Build)
	if err != nil {
		return nil, err
	}
	mode := options.RuntimeMode
	if mode == "" {
		mode = RuntimeModePrefix
	}
	if mode != RuntimeModePrefix && mode != RuntimeModeGameDir && mode != RuntimeModeNative && mode != RuntimeModeWine {
		return nil, fail("unknown runtime mode %s (expected %s, %s, %s, %s)", strconv.Quote(mode), RuntimeModePrefix, RuntimeModeGameDir, RuntimeModeNative, RuntimeModeWine)
	}
	if mode == RuntimeModeWine && options.Prefix == "" {
		return nil, fail("no Wine prefix found: pass --prefix <path to the directory that holds drive_c>")
	}

	prefix := options.Prefix
	wantOverride := overrideWanted(options.DllOverride)
	if mode == RuntimeModeNative {
		prefix = ""
		wantOverride = false
	}

	warnings := []string{}
	if mode == RuntimeModePrefix && !(prefix != "" && proton.UsablePrefix(prefix)) {
		mode = RuntimeModeGameDir
		where := ""
		if prefix != "" {
			where = " at " + prefix
		}
		warnings = append(warnings,
			"no usable Proton prefix"+where+", so the .NET runtime goes beside the game; "+
				"Steam needs the launch option printed at the end")
		warnings = append(warnings,
			"pass --prefix <path to the pfx directory> to install into an existing Proton prefix, "+
				"or launch Megabonk once in Steam under Proton so Steam creates it")
	}

	dotnet, err := pkg.Vendor(dotnetKind)
	if err != nil {
		return nil, err
	}
	runtimeTarget := content.RuntimePath(game)
	switch mode {
	case RuntimeModePrefix:
		runtimeTarget = proton.RuntimeTarget(prefix)
	case RuntimeModeNative, RuntimeModeWine:
		runtimeTarget = content.NativeRuntimePath(game)
	}
	runtimeMissing := !proton.RuntimeInstalled(runtimeTarget, dotnet.Version)
	var launchOption *string
	if mode == RuntimeModeGameDir {
		text := proton.LaunchOption(runtimeTarget)
		launchOption = &text
	}

	actions := []Action{}
	actions = append(actions, loaderActions(packageDir, pkg, game)...)
	fileSteps, err := fileActions(packageDir, pkg, game)
	if err != nil {
		return nil, err
	}
	actions = append(actions, fileSteps...)

	if runtimeMissing {
		detail := ".NET " + dotnet.Version + " into " + runtimeTarget
		if launchOption != nil {
			detail += " (Steam launch option: " + *launchOption + ")"
		}
		actions = append(actions, Action{
			Kind:      "install-runtime",
			Path:      runtimeTarget,
			Detail:    detail,
			Source:    dotnet.Path(packageDir),
			HasSource: true,
		})
	}

	if wantOverride && prefix != "" && usesPrefix(mode) {
		current, found := proton.ReadDllOverride(prefix, proton.DLLName, "")
		if !found || current != proton.DLLValue || runtimeMissing {
			actions = append(actions, Action{
				Kind:   "enable-dll-override",
				Path:   prefix,
				Detail: proton.DLLName + ".dll = " + proton.DLLValue + " in " + prefix,
			})
		}
	}

	if !ppath.IsDir(content.LevelsPath(game)) {
		levels := content.LevelsPath(game)
		actions = append(actions, Action{Kind: "create-levels-dir", Path: levels, Detail: "create " + levels})
	}

	if options.Level != "" {
		levelSteps, err := levelActions(game, ppath.Normalize(options.Level))
		if err != nil {
			return nil, err
		}
		actions = append(actions, levelSteps...)
	}
	if options.Pack != "" {
		packSteps, err := packActions(game, ppath.Normalize(options.Pack))
		if err != nil {
			return nil, err
		}
		actions = append(actions, packSteps...)
	}

	return &Plan{
		Package:          packageDir,
		Manifest:         pkg,
		GameDir:          game,
		Build:            build,
		Prefix:           prefix,
		RuntimeMode:      mode,
		RuntimeTarget:    runtimeTarget,
		DllOverride:      wantOverride && usesPrefix(mode),
		Actions:          actions,
		LaunchOption:     launchOption,
		Warnings:         warnings,
		WineOverrideMode: options.WineOverride,
		WineBin:          options.WineBin,
		ForcedTool:       options.ForcedTool,
	}, nil
}

// usesPrefix reports the modes that write the version.dll override into a prefix.
func usesPrefix(mode string) bool {
	return mode == RuntimeModePrefix || mode == RuntimeModeWine
}

// overrideWanted mirrors Python's `dll_override not in (False, 0, "off",
// "none", "no")`: the CLI passes the --wine-override mode through.
func overrideWanted(value string) bool {
	switch value {
	case "off", "none", "no", "false":
		return false
	}
	return true
}

func checkPackage(packageDir string) error {
	problems, err := manifest.VerifyPackage(packageDir)
	if err != nil {
		return err
	}
	if len(problems) == 0 {
		return nil
	}
	kept := problems
	more := ""
	if len(problems) > 4 {
		kept = problems[:4]
		more = fmt.Sprintf(" (+%d more)", len(problems)-4)
	}
	return fail("the install package does not match its manifest: %s%s", strings.Join(kept, "; "), more)
}

func effectiveBuild(game, requested string) (string, error) {
	derived := gamebuild.Classify(game).Kind
	if derived == gamebuild.NativeLinux || derived == gamebuild.Unknown ||
		requested == gamebuild.NativeLinux || requested == gamebuild.Unknown {
		return "", fail("%s", gamebuild.UnsupportedBuildMessage(game, derived, loaderVersion(game)))
	}
	return derived, nil
}

func loaderVersion(game string) string {
	if installed := content.InstalledLoaderVersion(game); installed != "" {
		return installed
	}
	return fallbackVersion
}

func loaderActions(packageDir string, pkg *manifest.Package, game string) []Action {
	markerOK := content.InstalledLoaderVersion(game) == pkg.MelonloaderVersion
	loaded := ppath.IsFile(ppath.Join(game, content.LoaderDir, "net6", "MelonLoader.dll"))
	shim := ppath.IsFile(ppath.Join(game, shimName))
	if markerOK && loaded && shim {
		return nil
	}
	loader, err := pkg.Vendor(loaderKind)
	if err != nil {
		return nil
	}
	return []Action{{
		Kind:      "install-loader",
		Path:      ppath.Join(game, content.LoaderDir),
		Detail:    "MelonLoader " + loader.Version + " into " + game,
		Source:    loader.Path(packageDir),
		HasSource: true,
	}}
}

func fileActions(packageDir string, pkg *manifest.Package, game string) ([]Action, error) {
	actions := []Action{}
	for _, entry := range pkg.Files {
		source := entry.Source(packageDir)
		if !ppath.IsFile(source) {
			return nil, fail("%s is missing from the package (%s)", ppath.Name(ppath.Normalize(entry.Path)), entry.Path)
		}
		target := entry.Target(game)
		needed, err := needsCopy(source, target, entry.SHA256)
		if err != nil {
			return nil, err
		}
		if needed {
			actions = append(actions, Action{
				Kind:      "install-file",
				Path:      target,
				Detail:    entry.Path + " -> " + target,
				Source:    source,
				HasSource: true,
			})
		}
	}
	return actions, nil
}

func needsCopy(source, target, digest string) (bool, error) {
	if !ppath.IsFile(target) {
		return true, nil
	}
	if digest != "" {
		actual, err := manifest.Sha256File(target)
		if err != nil {
			return false, err
		}
		return actual != digest, nil
	}
	sourceDigest, err := manifest.Sha256File(source)
	if err != nil {
		return false, err
	}
	targetDigest, err := manifest.Sha256File(target)
	if err != nil {
		return false, err
	}
	return sourceDigest != targetDigest, nil
}

func levelActions(game, level string) ([]Action, error) {
	if problems := content.ValidateLevelFile(level); len(problems) > 0 {
		return nil, fail("%s", strings.Join(problems, "; "))
	}
	target := ppath.Join(content.LevelsPath(game), ppath.Name(level))
	if ppath.IsFile(target) {
		targetDigest, err := manifest.Sha256File(target)
		if err != nil {
			return nil, err
		}
		sourceDigest, err := manifest.Sha256File(level)
		if err != nil {
			return nil, err
		}
		if targetDigest == sourceDigest {
			return nil, nil
		}
	}
	return []Action{{
		Kind:      "install-file",
		Path:      target,
		Detail:    ppath.Name(level) + " -> " + target,
		Source:    level,
		HasSource: true,
	}}, nil
}

func packActions(game, pack string) ([]Action, error) {
	if problems := content.ValidatePackSource(pack); len(problems) > 0 {
		return nil, fail("%s", strings.Join(problems, "; "))
	}
	dest := content.PackDest(game, ppath.Name(pack))
	actions := []Action{}
	for _, source := range content.PackFiles(pack) {
		target := ppath.Join(dest, ppath.Name(source))
		needed, err := needsCopy(source, target, "")
		if err != nil {
			return nil, err
		}
		if needed {
			actions = append(actions, Action{
				Kind:      "install-file",
				Path:      target,
				Detail:    ppath.Name(pack) + "/" + ppath.Name(source) + " -> " + target,
				Source:    source,
				HasSource: true,
			})
		}
	}
	return actions, nil
}

// Apply builds the plan, carries it out, and records what was installed.
func Apply(packageDir string, options Options, progress ui.Progress) ([]Action, error) {
	built, err := BuildPlan(packageDir, options)
	if err != nil {
		return nil, err
	}
	return ApplyPlan(built, progress)
}

// ErrCancelled reports a between-steps cancel. A cancelled install is rolled
// back through the recorded uninstall before this error surfaces.
var ErrCancelled = errors.New("cancelled")

// cancelledProgress reports whether the reporter was asked to abort; only the
// window reporter is ever cancellable.
func cancelledProgress(progress ui.Progress) bool {
	cancellable, ok := progress.(ui.Cancellable)
	return ok && cancellable.Cancelled()
}

// ApplyPlan carries out a plan the caller has already inspected, then records
// what was installed. A cancellable progress can abort between actions; the
// completed actions are then rolled back through the recorded uninstall.
func ApplyPlan(built *Plan, progress ui.Progress) ([]Action, error) {
	if progress != nil {
		total := len(built.Actions)
		if total < 1 {
			total = 1
		}
		progress.Start(total, "install "+built.Manifest.Label())
	}
	var overrideVia *string
	done := []Action{}
	for _, action := range built.Actions {
		if cancelledProgress(progress) {
			return nil, rollback(built, done, overrideVia)
		}
		result, err := execute(action, built)
		if err != nil {
			return nil, err
		}
		if action.Kind == "enable-dll-override" {
			overrideVia = result
		}
		done = append(done, action)
		if progress != nil {
			progress.Step(action.Label())
		}
	}
	if len(built.Actions) > 0 || content.LoadRecord(built.GameDir) == nil {
		if err := writeRecord(built, overrideVia); err != nil {
			return nil, err
		}
	}
	if progress != nil {
		message := "already installed"
		if len(built.Actions) > 0 {
			message = "installed"
		}
		progress.Finish(message, true)
	}
	return built.Actions, nil
}

// rollback records what the completed actions placed and removes it through
// the same uninstall path an explicit --uninstall takes, so a between-steps
// cancel never leaves a half-installed game directory behind.
func rollback(built *Plan, done []Action, overrideVia *string) error {
	if len(done) == 0 && content.LoadRecord(built.GameDir) == nil {
		return ErrCancelled
	}
	if len(done) > 0 {
		if err := writePartialRecord(built, done, overrideVia); err != nil {
			return err
		}
	}
	if _, err := Uninstall(built.GameDir, nil); err != nil {
		return err
	}
	return ErrCancelled
}

func execute(action Action, built *Plan) (*string, error) {
	switch action.Kind {
	case "install-loader":
		if err := extractLoader(built.Package, built.Manifest, built.GameDir); err != nil {
			return nil, err
		}
	case "install-file":
		if !action.HasSource {
			return nil, fail("no source for %s", action.Path)
		}
		if err := copyFile(action.Source, action.Path); err != nil {
			return nil, err
		}
	case "install-runtime":
		if !action.HasSource {
			return nil, fail("no .NET runtime archive for %s", action.Path)
		}
		dotnet, err := built.Manifest.Vendor(dotnetKind)
		if err != nil {
			return nil, err
		}
		if err := proton.ExtractRuntime(action.Source, action.Path, dotnet.Version); err != nil {
			return nil, err
		}
	case "enable-dll-override":
		wine, err := built.wineBinary(action.Path)
		if err != nil {
			return nil, err
		}
		via := proton.SetDllOverride(action.Path, proton.DLLName, proton.DLLValue, "", wine, nil)
		return &via, nil
	case "create-levels-dir":
		if err := os.MkdirAll(action.Path, 0o755); err != nil {
			return nil, err
		}
	default:
		return nil, fail("unknown action kind %s", strconv.Quote(action.Kind))
	}
	return nil, nil
}

func copyFile(source, target string) error {
	if err := os.MkdirAll(ppath.Parent(target), 0o755); err != nil {
		return err
	}
	handle, err := os.Open(source)
	if err != nil {
		return err
	}
	defer handle.Close()
	out, err := os.OpenFile(target, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, 0o644)
	if err != nil {
		return err
	}
	if _, err := io.Copy(out, handle); err != nil {
		out.Close()
		return err
	}
	return out.Close()
}

func extractLoader(packageDir string, pkg *manifest.Package, game string) error {
	loader, err := pkg.Vendor(loaderKind)
	if err != nil {
		return err
	}
	if err := manifest.VerifyVendor(pkg, loader, packageDir); err != nil {
		return err
	}
	if err := os.MkdirAll(game, 0o755); err != nil {
		return err
	}
	root := resolve(game)
	bundle, err := zip.OpenReader(loader.Path(packageDir))
	if err != nil {
		return err
	}
	defer bundle.Close()
	for _, member := range bundle.File {
		resolved := resolve(ppath.Join(game, filepath.ToSlash(member.Name)))
		if resolved != root && !isUnder(root, resolved) {
			return fail("%s: entry %s would escape the game directory", loader.Name, strconv.Quote(member.Name))
		}
	}
	for _, member := range bundle.File {
		if err := extractMember(member, game); err != nil {
			return err
		}
	}
	marker := content.VersionMarkerPath(game)
	if err := os.MkdirAll(ppath.Parent(marker), 0o755); err != nil {
		return err
	}
	if err := os.WriteFile(marker, []byte(pkg.MelonloaderVersion), 0o644); err != nil {
		return err
	}
	return nil
}

func isUnder(root, path string) bool {
	return strings.HasPrefix(path, root+"/")
}

func resolve(path string) string {
	return resolveWith(path, filepath.Abs, filepath.ToSlash, filepath.EvalSymlinks)
}

// resolveWith answers in slashes on every OS; the seams let tests replay
// Windows separators (backslash Abs, a slash-ing ToSlash) on any host.
func resolveWith(path string, abs func(string) (string, error), toSlash func(string) string, eval func(string) (string, error)) string {
	absolute, err := abs(path)
	if err != nil {
		return ppath.Normalize(path)
	}
	target, err := eval(toSlash(absolute))
	if err != nil {
		return resolveMissing(ppath.Normalize(toSlash(absolute)), abs, toSlash, eval)
	}
	return toSlash(target)
}

// resolveMissing resolves symlinks in the part of a path that exists, then
// appends the rest, so a file not yet written compares equal to its directory.
func resolveMissing(path string, abs func(string) (string, error), toSlash func(string) string, eval func(string) (string, error)) string {
	parent := ppath.Parent(path)
	if parent == path || parent == "" || parent == "." {
		return path
	}
	return ppath.Join(resolveWith(parent, abs, toSlash, eval), ppath.Name(path))
}

func extractMember(member *zip.File, game string) error {
	target := ppath.Join(game, filepath.ToSlash(member.Name))
	native := filepath.FromSlash(filepath.ToSlash(target))
	if member.FileInfo().IsDir() {
		return os.MkdirAll(native, 0o755)
	}
	if err := os.MkdirAll(filepath.Dir(native), 0o755); err != nil {
		return err
	}
	source, err := member.Open()
	if err != nil {
		return err
	}
	defer source.Close()
	handle, err := os.OpenFile(native, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, member.Mode().Perm())
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
	return os.Chmod(native, member.Mode().Perm())
}

// wineBinary is the wine binary that edits the prefix's registry: the one the
// caller named in Wine mode, otherwise the one found inside a Proton tool.
func (p *Plan) wineBinary(prefix string) (string, error) {
	if p.RuntimeMode != RuntimeModeWine {
		return wineFor(prefix, p.WineOverrideMode, p.ForcedTool)
	}
	if p.WineOverrideMode == "off" {
		return "", nil
	}
	if p.WineBin == "" && p.WineOverrideMode == "wine" {
		return "", fail("no wine binary found; install Wine or set MEGABONK_WINE to its path")
	}
	return p.WineBin, nil
}

// wineFor finds the wine binary that can edit a prefix's registry. An empty
// result means fall back to editing user.reg directly; mode "wine" rules that
// out, so a missing binary is an error there.
func wineFor(prefix, mode, forcedTool string) (string, error) {
	if mode == "off" {
		return "", nil
	}
	library := libraryForPrefix(prefix)
	if library == "" {
		return "", nil
	}
	tool := proton.PickProton(library, forcedTool)
	if tool == "" {
		tool = proton.PickProton(library, "")
	}
	wine := ""
	if tool != "" {
		wine = proton.ProtonWineBin(tool)
	}
	if wine == "" && mode == "wine" {
		return "", fail("no wine binary found in the Proton tools under %s; pass --proton <name> to point at the tool that has one", library)
	}
	return wine, nil
}

func libraryForPrefix(prefix string) string {
	for _, parent := range ppath.Parents(prefix) {
		if ppath.Name(parent) == "compatdata" {
			return ppath.Parent(ppath.Parent(parent))
		}
	}
	return ""
}

func relative(game, path string) string {
	clean := ppath.Normalize(path)
	prefix := ppath.Normalize(game) + "/"
	if strings.HasPrefix(clean, prefix) {
		return clean[len(prefix):]
	}
	return clean
}

func installedBuildID(game string) *string {
	if build := steam.InstalledBuildID(game); build != "" {
		return &build
	}
	return nil
}

func writeRecord(built *Plan, overrideVia *string) error {
	game := built.GameDir
	record := content.LoadRecord(game)
	if record == nil {
		record = &content.Record{}
	}
	record.Schema = content.RecordSchema
	record.PackageID = built.Manifest.PackageID
	record.ModVersion = built.Manifest.ModVersion
	record.MelonloaderVersion = built.Manifest.MelonloaderVersion
	record.GameBuildID = built.Manifest.GameBuildID
	record.InstalledGameBuildID = installedBuildID(game)
	record.InstalledAt = time.Now().UTC().Format("2006-01-02T15:04:05Z")
	record.GameDir = game

	files := append([]string{}, record.Files...)
	for _, entry := range built.Manifest.Files {
		dest := ppath.Normalize(entry.Dest)
		if !contains(files, dest) {
			files = append(files, dest)
		}
	}
	record.Files = files

	levels := append([]string{}, record.Levels...)
	for _, action := range built.Actions {
		if action.Kind != "install-file" || ppath.Parent(action.Path) != content.LevelsPath(game) {
			continue
		}
		name := relative(game, action.Path)
		if !contains(levels, name) {
			levels = append(levels, name)
		}
	}
	record.Levels = levels

	packs := map[string]content.PackEntry{}
	for name, entry := range record.Packs {
		packs[name] = entry
	}
	packRoot := content.LevelPacksPath(game)
	for _, action := range built.Actions {
		if action.Kind != "install-file" || ppath.Parent(ppath.Parent(action.Path)) != packRoot {
			continue
		}
		packID := ppath.Name(ppath.Parent(action.Path))
		entry := packs[packID]
		placed := append([]string{}, entry.Files...)
		name := relative(game, action.Path)
		if !contains(placed, name) {
			placed = append(placed, name)
		}
		entry.Files = placed
		entry.Dir = relative(game, ppath.Parent(action.Path))
		packs[packID] = entry
	}
	record.Packs = packs

	dotnet, err := built.Manifest.Vendor(dotnetKind)
	if err != nil {
		return err
	}
	record.Runtime = &content.Runtime{
		Mode:         built.RuntimeMode,
		Path:         built.RuntimeTarget,
		Version:      dotnet.Version,
		LaunchOption: built.LaunchOption,
	}

	prefix := ""
	if usesPrefix(built.RuntimeMode) {
		prefix = built.Prefix
	}
	applied := false
	if prefix != "" {
		value, found := proton.ReadDllOverride(prefix, proton.DLLName, "")
		applied = found && value == proton.DLLValue
	}
	record.DllOverride = &content.DllOverride{Applied: applied, Name: proton.DLLName, Value: proton.DLLValue}
	if prefix != "" {
		value := prefix
		record.DllOverride.Prefix = &value
	}
	via := overrideVia
	if via == nil && applied {
		already := "already set"
		via = &already
	}
	record.DllOverride.Via = via
	_, err = content.SaveRecord(game, record)
	return err
}

// writePartialRecord is writeRecord for a cancelled run: the lists are derived
// from the actions that actually completed (merged with any earlier record),
// so the rollback removes exactly what was placed and nothing that was not.
func writePartialRecord(built *Plan, done []Action, overrideVia *string) error {
	game := built.GameDir
	record := content.LoadRecord(game)
	if record == nil {
		record = &content.Record{}
	}
	record.Schema = content.RecordSchema
	record.PackageID = built.Manifest.PackageID
	record.ModVersion = built.Manifest.ModVersion
	record.MelonloaderVersion = built.Manifest.MelonloaderVersion
	record.GameBuildID = built.Manifest.GameBuildID
	record.InstalledGameBuildID = installedBuildID(game)
	record.InstalledAt = time.Now().UTC().Format("2006-01-02T15:04:05Z")
	record.GameDir = game

	files := append([]string{}, record.Files...)
	levels := append([]string{}, record.Levels...)
	packs := map[string]content.PackEntry{}
	for name, entry := range record.Packs {
		packs[name] = entry
	}
	dotnet := false
	packRoot := content.LevelPacksPath(game)
	for _, action := range done {
		if action.Kind == "install-runtime" {
			dotnet = true
		}
		if action.Kind != "install-file" {
			continue
		}
		name := relative(game, action.Path)
		switch {
		case ppath.Parent(action.Path) == content.LevelsPath(game):
			if !contains(levels, name) {
				levels = append(levels, name)
			}
		case ppath.Parent(ppath.Parent(action.Path)) == packRoot:
			packID := ppath.Name(ppath.Parent(action.Path))
			entry := packs[packID]
			placed := append([]string{}, entry.Files...)
			if !contains(placed, name) {
				placed = append(placed, name)
			}
			entry.Files = placed
			entry.Dir = relative(game, ppath.Parent(action.Path))
			packs[packID] = entry
		default:
			if !contains(files, name) {
				files = append(files, name)
			}
		}
	}
	record.Files = files
	record.Levels = levels
	record.Packs = packs

	if dotnet {
		runtime, err := built.Manifest.Vendor(dotnetKind)
		if err != nil {
			return err
		}
		record.Runtime = &content.Runtime{
			Mode:         built.RuntimeMode,
			Path:         built.RuntimeTarget,
			Version:      runtime.Version,
			LaunchOption: built.LaunchOption,
		}
	}

	prefix := ""
	if usesPrefix(built.RuntimeMode) {
		prefix = built.Prefix
	}
	applied := false
	if prefix != "" {
		value, found := proton.ReadDllOverride(prefix, proton.DLLName, "")
		applied = found && value == proton.DLLValue
	}
	record.DllOverride = &content.DllOverride{Applied: applied, Name: proton.DLLName, Value: proton.DLLValue}
	if prefix != "" {
		value := prefix
		record.DllOverride.Prefix = &value
	}
	via := overrideVia
	if via == nil && applied {
		already := "already set"
		via = &already
	}
	record.DllOverride.Via = via
	_, err := content.SaveRecord(game, record)
	return err
}

func contains(items []string, wanted string) bool {
	for _, item := range items {
		if item == wanted {
			return true
		}
	}
	return false
}

// Uninstall removes exactly what the installer recorded placing; a directory
// with no record is left alone. A cancellable progress can stop it between
// groups, and the record survives so a rerun finishes the job.
func Uninstall(game string, progress ui.Progress) ([]string, error) {
	game = ppath.Normalize(game)
	record := content.LoadRecord(game)
	if record == nil {
		return nil, nil
	}
	removed := []string{}

	remove := func(path string, tree bool) {
		if tree {
			if ppath.IsDir(path) {
				_ = os.RemoveAll(path)
				if !ppath.Exists(path) {
					removed = append(removed, path)
				}
			}
			return
		}
		if ppath.IsFile(path) {
			if err := os.Remove(path); err == nil {
				removed = append(removed, path)
			}
		}
	}

	if progress != nil {
		steps := 5 + len(record.Files)
		for _, entry := range record.Packs {
			steps += len(entry.Files)
		}
		if steps < 1 {
			steps = 1
		}
		label := "MegabonkLevels"
		if record.PackageID != "" {
			label = record.PackageID
		}
		progress.Start(steps, "uninstall "+label)
	}

	remove(ppath.Join(game, content.LoaderDir), true)
	remove(ppath.Join(game, shimName), false)
	remove(ppath.Join(game, content.UserData, loaderConfigName), false)
	if progress != nil {
		progress.Step("MelonLoader")
	}
	if cancelledProgress(progress) {
		return removed, ErrCancelled
	}

	for _, name := range record.Files {
		remove(ppath.Join(game, name), false)
	}
	removeIfEmpty := func(directory string) {
		candidate := ppath.Join(game, directory)
		if ppath.IsDir(candidate) {
			if err := os.Remove(native(candidate)); err == nil {
				removed = append(removed, candidate)
			}
		}
	}
	for _, directory := range []string{content.ModsDir, content.UserLibsDir, pluginsDir} {
		removeIfEmpty(directory)
	}
	if progress != nil {
		progress.Step("mod files")
	}
	if cancelledProgress(progress) {
		return removed, ErrCancelled
	}

	for _, name := range record.Levels {
		remove(ppath.Join(game, name), false)
	}
	for packID, entry := range record.Packs {
		target := content.PackDest(game, packID)
		if entry.Dir != "" {
			target = ppath.Join(game, entry.Dir)
		}
		remove(target, true)
	}
	for _, directory := range []string{ppath.Join(content.UserData, content.LevelPacksDir), ppath.Join(content.UserData, content.LevelsDir), content.UserData} {
		removeIfEmpty(directory)
	}
	if progress != nil {
		progress.Step("levels and packs")
	}
	if cancelledProgress(progress) {
		return removed, ErrCancelled
	}

	if record.Runtime != nil && record.Runtime.Path != "" {
		target := record.Runtime.Path
		if ppath.IsFile(ppath.Join(target, proton.RuntimeMarkerName)) {
			remove(target, true)
		}
	}
	if progress != nil {
		progress.Step(".NET runtime")
	}
	if cancelledProgress(progress) {
		return removed, ErrCancelled
	}

	if record.DllOverride != nil && record.DllOverride.Prefix != nil && *record.DllOverride.Prefix != "" {
		prefix := *record.DllOverride.Prefix
		if ppath.IsDir(prefix) {
			library := libraryForPrefix(prefix)
			wine := ""
			if library != "" {
				if tool := proton.PickProton(library, ""); tool != "" {
					wine = proton.ProtonWineBin(tool)
				}
			}
			proton.ClearDllOverride(prefix, proton.DLLName, "", wine, nil)
		}
	}
	if progress != nil {
		progress.Step("version.dll override")
	}
	if cancelledProgress(progress) {
		return removed, ErrCancelled
	}

	remove(content.RecordFilePath(game), false)
	if progress != nil {
		progress.Finish("uninstalled", true)
	}
	return removed, nil
}

func native(path string) string { return filepath.FromSlash(path) }
