// Package modinstall installs BepInEx and the Megabonk Levels mod from
// Thunderstore. The offline package path lives in package plan.
package modinstall

import (
	"archive/zip"
	"errors"
	"fmt"
	"os"
	"path"
	"path/filepath"
	"runtime"
	"sort"
	"strconv"
	"strings"

	"github.com/pythoninthegrass/megabonk_mods/installer/internal/content"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/gamebuild"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ppath"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/proton"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/steam"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/thunderstore"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ui"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/zipx"
)

// Platforms the installer sets up; detection picks one when the caller does not.
const (
	PlatformProton = "proton"
	PlatformWine   = "wine"
	PlatformNative = "native"
)

// backupDir is the folder the transaction keeps pre-write backups in.
const backupDir = ".megabonk-levels-backup"

// ErrCancelled stops a run the user aborted; everything it placed is rolled back
// before the error reaches the caller.
var ErrCancelled = errors.New("cancelled")

// Error is a refusal that names what to do about it.
type Error struct{ message string }

func (e *Error) Error() string { return e.message }

func fail(format string, args ...any) error {
	return &Error{message: fmt.Sprintf(format, args...)}
}

// Options is one run's input.
type Options struct {
	// Game is the directory holding Megabonk.exe.
	Game string
	// Prefix is the Proton or Wine prefix, where the platform needs one.
	Prefix string
	// Platform is one of the Platform constants, or "" to detect it.
	Platform string
	// Cache holds the downloaded archives. Empty means a temporary folder.
	Cache string
	// Pins are known-good loader pack digests by version; a version with no pin
	// anywhere is refused.
	Pins map[string]string
	// ModPins are known-good digests for the mod's own releases, which
	// Thunderstore does not publish.
	ModPins []ModPin
	// WineBin names the wine binary for prefix edits; "" uses the built-in
	// registry writer.
	WineBin string
	// Runner runs the wine command, which tests supply.
	Runner proton.Runner
	// OverrideOnly places no loader or plugin files: the caller installed them,
	// and this run only applies the platform's winhttp override and records it.
	OverrideOnly bool
	// DryRun plans the run and changes nothing.
	DryRun bool
	// SkipRecord leaves the install record to the caller, which is what a plan
	// that also places levels and packs wants: one record, written once.
	SkipRecord bool
}

// Result is what a run did.
type Result struct {
	ModVersion     string `json:"mod_version"`
	BepInExVersion string `json:"bepinex_version"`
	Platform       string `json:"platform"`
	Game           string `json:"game"`
	Prefix         string `json:"prefix,omitempty"`

	Placed    []string `json:"placed,omitempty"`
	Planned   []string `json:"planned,omitempty"`
	PackFiles []string `json:"pack_files,omitempty"`
	ModFiles  []string `json:"mod_files,omitempty"`

	Noop   bool `json:"noop"`
	DryRun bool `json:"dry_run,omitempty"`

	// LaunchOption is what the player pastes into Steam's Launch Options, empty
	// where no launch option is needed.
	LaunchOption string `json:"launch_option,omitempty"`
	// OverrideApplied says the winhttp override was written into the prefix.
	OverrideApplied bool   `json:"override_applied,omitempty"`
	OverrideVia     string `json:"override_via,omitempty"`
	// ProxyParked says a MelonLoader version.dll was moved aside.
	ProxyParked bool `json:"proxy_parked,omitempty"`
	// ModSHA256 is the digest the mod archive carried, kept for a later repair.
	ModSHA256 string `json:"mod_sha256,omitempty"`

	CachePaths []string `json:"cache_paths,omitempty"`
}

// Progress is what a run reports through, restated from package ui so this
// package does not depend on the reporters; ui's extras are probed by assertion.
type Progress interface {
	Start(total int, label string)
	Step(label string)
	Finish(message string, ok bool)
}

// State reports the condition of a game directory before a run.
type State struct {
	Installed      bool   `json:"installed"`
	FilesPresent   bool   `json:"files_present"`
	ModVersion     string `json:"mod_version,omitempty"`
	BepInExVersion string `json:"bepinex_version,omitempty"`
	Platform       string `json:"platform,omitempty"`
	Release        string `json:"latest_version,omitempty"`
	UpToDate       *bool  `json:"up_to_date,omitempty"`
	Reason         string `json:"reason,omitempty"`
	// OverrideSet says the run wrote the winhttp override into OverridePrefix, and
	// OverrideVia names the route that did it.
	OverrideSet    bool   `json:"override_set,omitempty"`
	OverrideVia    string `json:"override_via,omitempty"`
	OverridePrefix string `json:"override_prefix,omitempty"`
}

// Fetcher hands over one verified archive; tests use it instead of a network.
type Fetcher func(kind, version, digest, target string) (*thunderstore.Downloaded, error)

// ModPin is a known-good SHA-256 for one release of the mod.
type ModPin struct {
	Version string
	SHA256  string
}

// Install resolves, verifies and places the mod and its loader, then applies the
// platform's winhttp override. reporter may be nil.
func Install(client *thunderstore.Client, options Options, reporter Progress) (*Result, error) {
	return install(client, options, reporter, nil)
}

// InstallWithFetcher is Install with the archive fetcher a test supplies.
func InstallWithFetcher(client *thunderstore.Client, options Options, reporter Progress, fetch Fetcher) (*Result, error) {
	return install(client, options, reporter, fetch)
}

func install(client *thunderstore.Client, options Options, reporter Progress, fetch Fetcher) (*Result, error) {
	if client == nil {
		return nil, fail("no Thunderstore client, so the mod cannot be resolved")
	}
	gameDir := ppath.Normalize(options.Game)
	if gameDir == "" {
		return nil, fail("no game directory was given")
	}
	if err := checkGameDir(gameDir); err != nil {
		return nil, err
	}
	platform, err := resolvePlatform(options)
	if err != nil {
		return nil, err
	}
	if platform != PlatformNative {
		if err := checkPrefix(options.Prefix, platform); err != nil {
			return nil, err
		}
	}

	result := &Result{Game: gameDir, Platform: platform, Prefix: givenPrefix(options), DryRun: options.DryRun}

	// Read the record before the network: an installed run answers without a fetch.
	record := content.LoadRecord(gameDir)

	if options.DryRun {
		result.ModVersion, result.BepInExVersion = recordVersions(record)
		result.Planned = planLabels()
		result.LaunchOption = launchOptionFor(platform)
		start(reporter, len(result.Planned), "planned install")
		for _, label := range result.Planned {
			step(reporter, label)
		}
		finish(reporter, "dry run: nothing was changed", true)
		return result, nil
	}

	// A run over an existing install answers from the record alone.
	if alreadyInstalled(gameDir, record) {
		result.ModVersion = record.ModVersion
		result.BepInExVersion = record.BepinexVersion
		result.Noop = true
		step(reporter, "MegabonkLevels "+result.ModVersion+" is already installed")
		finish(reporter, "nothing to do", true)
		return result, nil
	}

	// Resolve next: nothing is downloaded or written until the release and the
	// loader pack version it depends on are both known.
	resolution, err := client.Resolve()
	if err != nil {
		return nil, err
	}
	result.ModVersion = resolution.Version
	result.BepInExVersion = resolution.BepInExVersion

	digest, err := packDigest(options, resolution)
	if err != nil {
		return nil, err
	}
	// The caller's pin, or the digest the install being repaired recorded.
	wantedModDigest := modDigest(options, resolution.Version, options.ModPins)
	if wantedModDigest == "" && record != nil && record.ModVersion == resolution.Version {
		wantedModDigest = recordedModDigest(record)
	}

	cache, err := cacheDir(options)
	if err != nil {
		return nil, err
	}
	get := func(kind, version, want, target string) (*thunderstore.Downloaded, error) {
		if fetch != nil {
			return fetch(kind, version, want, target)
		}
		if kind == "pack" {
			return client.DownloadBepInEx(version, want, target)
		}
		return client.DownloadMod(version, want, target)
	}

	if options.OverrideOnly {
		return overrideOnly(options, reporter, result, resolution)
	}

	start(reporter, len(planLabels()), "installing MegabonkLevels "+result.ModVersion)

	// Both archives are fetched before the game directory is touched.
	pack, err := get("pack", resolution.BepInExVersion, digest, filepath.Join(cache,
		thunderstore.ArchiveName(thunderstore.BepInExNamespace, thunderstore.BepInExName,
			resolution.BepInExVersion)))
	if err != nil {
		return nil, err
	}
	result.CachePaths = append(result.CachePaths, pack.Path)
	step(reporter, "verified the BepInEx pack "+resolution.BepInExVersion)

	mod, err := get("mod", resolution.Version, wantedModDigest, filepath.Join(cache,
		thunderstore.ArchiveName(thunderstore.ModNamespace, thunderstore.ModName, resolution.Version)))
	if err != nil {
		return nil, err
	}
	result.CachePaths = append(result.CachePaths, mod.Path)
	result.ModSHA256 = mod.SHA256
	step(reporter, "verified "+thunderstore.ModName+" "+resolution.Version)

	// Verified so far: the game directory is only touched from here, and the
	// plugin set is staged where the game cannot read it before any of it is placed.
	staging, err := os.MkdirTemp("", "megabonk-levels-mod")
	if err != nil {
		return nil, fail("cannot create a folder to check the %s archive in: %s",
			thunderstore.ModName, err.Error())
	}
	defer os.RemoveAll(staging)
	staged, err := unpackModArchive(mod.Path, staging)
	if err != nil {
		return nil, err
	}

	run := newTransaction(gameDir, reporter)

	packResult, err := content.InstallBepInEx(gameDir, pack.Path, resolution.BepInExVersion)
	if err != nil {
		return nil, err
	}
	run.adoptPack(packResult)
	result.PackFiles = packResult.PackFiles
	result.Placed = append(result.Placed, packResult.PackFiles...)
	result.ProxyParked = packResult.Parked
	step(reporter, "installed the BepInEx pack and its .NET 6 runtime")

	modFiles, err := run.placeMod(staging, staged)
	if err != nil {
		return nil, run.abort(err)
	}
	result.ModFiles = modFiles
	step(reporter, "installed the MegabonkLevels plugin")

	if cancelled(reporter) {
		return nil, run.abort(ErrCancelled)
	}

	switch platform {
	case PlatformProton:
		result.LaunchOption = proton.WinHTTPLaunchOption
		step(reporter, "prepared the Steam launch option to copy")
	case PlatformWine:
		via := proton.SetDllOverride(options.Prefix, proton.WinHTTPDLLName, proton.WinHTTPValue,
			"", options.WineBin, options.Runner)
		run.markOverride(options.Prefix, via)
		step(reporter, "set the winhttp override in the Wine prefix ("+via+")")
	default:
		step(reporter, "no DLL override needed on Windows")
	}
	result.OverrideApplied, result.OverrideVia = run.overrideSet, run.overrideVia

	if err := run.writeRecord(result); err != nil {
		return nil, run.abort(err)
	}
	if !options.SkipRecord {
		step(reporter, "wrote the install record")
	}
	run.commit()

	if result.LaunchOption != "" {
		showLaunchOption(reporter, result.LaunchOption)
	}
	finish(reporter, "MegabonkLevels "+result.ModVersion+" installed", true)
	return result, nil
}

// overrideOnly applies just the platform winhttp override for a loader and plugin
// set somebody else placed, so a foreign install is never rewritten.
func overrideOnly(options Options, reporter Progress, result *Result,
	resolution *thunderstore.Resolution) (*Result, error) {
	start(reporter, 2, "enabling MegabonkLevels "+result.ModVersion)
	run := newTransaction(result.Game, reporter)
	switch result.Platform {
	case PlatformProton:
		result.LaunchOption = proton.WinHTTPLaunchOption
		step(reporter, "prepared the Steam launch option to copy")
	case PlatformWine:
		via := proton.SetDllOverride(options.Prefix, proton.WinHTTPDLLName, proton.WinHTTPValue,
			"", options.WineBin, options.Runner)
		run.markOverride(options.Prefix, via)
		step(reporter, "set the winhttp override in the Wine prefix ("+via+")")
	default:
		step(reporter, "no DLL override needed on Windows")
	}
	result.OverrideApplied, result.OverrideVia = run.overrideSet, run.overrideVia
	if err := run.writeOverrideRecord(result); err != nil {
		return nil, run.abort(err)
	}
	step(reporter, "wrote the install record")
	run.commit()
	if result.LaunchOption != "" {
		showLaunchOption(reporter, result.LaunchOption)
	}
	finish(reporter, "MegabonkLevels "+result.ModVersion+" enabled", true)
	return result, nil
}

// Uninstall removes what the record names, clears the winhttp override, and
// restores a parked version.dll. reporter may be nil.
func Uninstall(gameDir string, reporter Progress) ([]string, error) {
	gameDir = ppath.Normalize(gameDir)
	record := content.LoadRecord(gameDir)
	if record == nil {
		return nil, nil
	}
	loaderOwned := record.Loader != nil && record.Loader.Installed
	override := record.DllOverride
	parked := record.Loader != nil && record.Loader.ProxyParked

	// Cleared from the record, so the prefix is clean even if the loader stays.
	if override != nil {
		prefix := gameDir
		if override.Prefix != nil {
			prefix = *override.Prefix
		}
		via := proton.ClearDllOverride(prefix, proton.WinHTTPDLLName, "", "", nil)
		step(reporter, "removed the winhttp override from the prefix ("+via+")")
	}

	removed, err := content.UninstallRecorded(gameDir, record)
	if err != nil {
		return removed, err
	}
	if loaderOwned && content.InstalledBepInExVersion(gameDir) != "" {
		return removed, fail("the loader files are still in place, so the install record was kept")
	}
	// content.UninstallRecorded restored the proxy; this package renames none.
	if parked {
		step(reporter, "restored "+content.VersionDLLName)
	}
	finish(reporter, "MegabonkLevels uninstalled", true)
	return removed, nil
}

// Detect reports what is installed. Files with no record are another tool's, so
// they are reported present but not installed.
func Detect(gameDir string) State {
	gameDir = ppath.Normalize(gameDir)
	record := content.LoadRecord(gameDir)
	state := State{FilesPresent: content.ModInstalled(gameDir)}
	if record == nil {
		if state.FilesPresent {
			state.Reason = "the plugin files are in place but there is no install record, " +
				"so they were installed by something else"
		} else {
			state.Reason = "the mod is not installed"
		}
		return state
	}
	state.Installed = content.ModInstalled(gameDir)
	state.ModVersion = record.ModVersion
	state.BepInExVersion = record.BepinexVersion
	state.Platform = PlatformNative
	if record.DllOverride != nil {
		state.Platform = PlatformWine
	}
	if !state.Installed {
		state.Reason = "the install record is there but " + content.ModDLLName + " is not"
	}
	return state
}

// DetectAgainst compares an install with the latest release. client may be nil,
// which leaves the release fields empty.
func DetectAgainst(client *thunderstore.Client, gameDir string) State {
	state := Detect(gameDir)
	if client == nil {
		return state
	}
	resolution, err := client.Resolve()
	if err != nil {
		state.Reason = err.Error()
		return state
	}
	state.Release = resolution.Version
	upToDate := state.Installed && state.ModVersion == resolution.Version
	state.UpToDate = &upToDate
	return state
}

// State reports the install a run just made, so a caller can show its own result
// without a second look at the disk.
func (r *Result) State() State {
	return State{
		Installed:      true,
		FilesPresent:   true,
		ModVersion:     r.ModVersion,
		BepInExVersion: r.BepInExVersion,
		Platform:       r.Platform,
		Release:        r.ModVersion,
		OverrideSet:    r.OverrideApplied,
		OverrideVia:    r.OverrideVia,
		OverridePrefix: r.Prefix,
	}
}

// checkGameDir accepts only a Windows bundle; the native Linux build loads nothing.
func checkGameDir(gameDir string) error {
	if !ppath.IsDir(gameDir) {
		return fail("%s is not a directory", strconv.Quote(gameDir))
	}
	build := gamebuild.Classify(gameDir)
	if build.Kind == gamebuild.NativeLinux {
		return fail("%s is the native Linux build of Megabonk, which this mod cannot load. Switch the "+
			"install to the Windows build in Steam (Properties, Compatibility, Proton), launch it once, "+
			"and run the installer against that directory", strconv.Quote(gameDir))
	}
	if !build.HasWindowsExe && !build.HasDataDir {
		return fail("%s does not look like a Megabonk install: no %s and no %s/",
			strconv.Quote(gameDir), gamebuild.WindowsExe, gamebuild.DataDir)
	}
	return nil
}

// resolvePlatform takes the caller's choice, or picks the one the host and the
// paths it was given describe.
func resolvePlatform(options Options) (string, error) {
	if raw := strings.ToLower(strings.TrimSpace(options.Platform)); raw != "" {
		switch raw {
		case PlatformProton, PlatformWine, PlatformNative:
			return raw, nil
		default:
			return "", fail("%s is not a platform this installer knows: use %s, %s or %s",
				strconv.Quote(raw), PlatformProton, PlatformWine, PlatformNative)
		}
	}
	switch {
	case isProtonPrefix(options.Prefix):
		return PlatformProton, nil
	case isWinePrefix(options.Prefix):
		return PlatformWine, nil
	case runtime.GOOS == "windows":
		return PlatformNative, nil
	}
	return "", fail("no usable Proton or Wine prefix for %s. Pass --prefix with the "+
		"steamapps/compatdata/%s/pfx folder for a Proton install, or with the Wine prefix "+
		"folder for a plain Wine or CrossOver bottle",
		strconv.Quote(ppath.Normalize(options.Game)), steam.AppID)
}

// isProtonPrefix recognises Steam's layout, where the prefix is
// <library>/steamapps/compatdata/<appid>/pfx.
func isProtonPrefix(prefix string) bool {
	normal := filepath.ToSlash(ppath.Normalize(prefix))
	if normal == "" || !strings.HasSuffix(normal, "/pfx") {
		return false
	}
	if !ppath.IsDir(filepath.Join(prefix, "drive_c")) {
		return false
	}
	return strings.Contains(normal, "/compatdata/")
}

// isWinePrefix recognises any directory holding a drive_c, Wine or CrossOver.
func isWinePrefix(prefix string) bool {
	if ppath.Normalize(prefix) == "" {
		return false
	}
	return ppath.IsDir(filepath.Join(prefix, "drive_c"))
}

// givenPrefix is the caller's prefix, or "" for none; Normalize reads "" as ".".
func givenPrefix(options Options) string {
	if strings.TrimSpace(options.Prefix) == "" {
		return ""
	}
	return ppath.Normalize(options.Prefix)
}

func checkPrefix(prefix, platform string) error {
	normal := ppath.Normalize(prefix)
	if normal == "" {
		return fail("a %s install needs a prefix: pass the Proton compatdata/pfx folder, or the Wine "+
			"prefix folder for a plain Wine or CrossOver bottle", platform)
	}
	if !ppath.IsDir(filepath.Join(normal, "drive_c")) {
		return fail("%s is not a usable %s prefix: there is no drive_c folder inside it",
			strconv.Quote(normal), platform)
	}
	return nil
}

// packDigest is the SHA-256 the pack archive must carry: caller pin, then the
// built-in table, then refusal.
func packDigest(options Options, resolution *thunderstore.Resolution) (string, error) {
	version := strings.TrimSpace(resolution.BepInExVersion)
	if pinned, found := options.Pins[version]; found && strings.TrimSpace(pinned) != "" {
		return strings.ToLower(strings.TrimSpace(pinned)), nil
	}
	if pinned, found := thunderstore.PinnedBepInExDigest(version); found {
		return pinned, nil
	}
	return "", fail("no SHA-256 is known for %s-%s %s, so its archive cannot be verified; "+
		"pass the digest you expect with --bepinex-sha256",
		thunderstore.BepInExNamespace, thunderstore.BepInExName, version)
}

// modDigest is the caller's pin for this mod version, or "" when it holds none.
func modDigest(options Options, version string, pins []ModPin) string {
	version = strings.TrimSpace(version)
	for _, pin := range pins {
		if strings.TrimSpace(pin.Version) == version && strings.TrimSpace(pin.SHA256) != "" {
			return strings.ToLower(strings.TrimSpace(pin.SHA256))
		}
	}
	return ""
}

// recordedModDigest is the digest the record kept, letting a repair reuse a cache.
func recordedModDigest(record *content.Record) string {
	if record == nil || record.Loader == nil {
		return ""
	}
	return strings.ToLower(strings.TrimSpace(record.Loader.ModSHA256))
}

// recordVersions names what a dry run would place, read off the record.
func recordVersions(record *content.Record) (string, string) {
	if record == nil {
		return "", ""
	}
	return record.ModVersion, record.BepinexVersion
}

func launchOptionFor(platform string) string {
	if platform == PlatformProton {
		return proton.WinHTTPLaunchOption
	}
	return ""
}

// unpackModArchive writes an archive's plugin set into staging, in the archive's
// own layout, and returns those members by their archive path.
func unpackModArchive(archive, staging string) ([]string, error) {
	members, bundle, err := content.ModPluginFiles(archive)
	if err != nil {
		return nil, err
	}
	defer bundle.Close()
	var names []string
	for _, name := range sortedMemberNames(members) {
		if !modPluginFile(name) {
			continue
		}
		// Keys are relative to the plugin folder, the same in archive and game dir.
		archivePath := content.ModPluginPrefix + name
		if !ppath.SafeRelative(name) {
			return nil, fail("the %s archive carries an unsafe member name: %s",
				thunderstore.ModName, strconv.Quote(archivePath))
		}
		if err := zipx.ExtractMember(members[name], staging, archivePath, 0); err != nil {
			return nil, fail("%s: %s", ppath.Name(archive), err.Error())
		}
		names = append(names, archivePath)
	}
	if len(names) == 0 {
		return nil, fail("mod archive carries nothing under %s",
			strconv.Quote(strings.TrimRight(content.ModPluginPrefix, "/")))
	}
	return names, nil
}

// modPluginFile reports whether an archive member belongs in the plugin folder.
func modPluginFile(name string) bool {
	switch path.Base(name) {
	case content.ModDLLName, content.NLayerName, content.LicenseName:
		return true
	}
	switch strings.ToLower(path.Ext(name)) {
	case ".dll", ".json", ".pdb":
		return true
	}
	return false
}

func sortedMemberNames(members map[string]*zip.File) []string {
	names := make([]string, 0, len(members))
	for name := range members {
		names = append(names, name)
	}
	sort.Strings(names)
	return names
}

// cacheDir is where archives are kept; a caller that passes none gets a temp folder.
func cacheDir(options Options) (string, error) {
	cache := strings.TrimSpace(options.Cache)
	if cache == "" {
		// "" means no folder was named, not the process's working directory.
		dir, err := os.MkdirTemp("", "megabonk-installer-cache")
		if err != nil {
			return "", fail("cannot create a temporary folder for the archives: %s", err.Error())
		}
		return dir, nil
	}
	cache = ppath.Normalize(cache)
	if ppath.Exists(cache) && !ppath.IsDir(cache) {
		return "", fail("%s is not a directory, so it cannot hold the archive cache", strconv.Quote(cache))
	}
	if err := os.MkdirAll(cache, 0o755); err != nil {
		return "", fail("cannot create the archive cache at %s: %s", strconv.Quote(cache), err.Error())
	}
	return cache, nil
}

// planLabels is what a run says it will do, in the order it does it.
func planLabels() []string {
	return []string{
		"verify the BepInEx pack archive against its SHA-256",
		"verify the " + thunderstore.ModName + " archive",
		"move any MelonLoader " + content.VersionDLLName + " aside",
		thunderstore.PackRoot + "/core, " + thunderstore.PackRoot + "/patchers, " + thunderstore.PackRoot + "/plugins",
		"doorstop_config.ini, winhttp.dll, run_winhttp.bepinex.cmd",
		"changelog.txt, .doorstop_version",
		content.RuntimeDirName + "/ (the .NET 6 runtime)",
		content.PluginsDir + "/" + content.ModFolderName + "/ (the MegabonkLevels plugin)",
		"the winhttp DLL override, where the platform needs one",
		content.RecordName,
	}
}

// alreadyInstalled reports a run with nothing left to do, decided by the record.
func alreadyInstalled(gameDir string, record *content.Record) bool {
	return record != nil && record.Loader != nil && record.Loader.Installed && record.ModVersion != "" &&
		record.BepinexVersion != "" && content.ModInstalled(gameDir)
}

// transaction places files and can take them all back, restoring overwrites from
// a pre-write backup rather than deleting through them.
type transaction struct {
	gameDir        string
	placed         []string
	packFiles      []string
	backups        map[string]fileBackup
	rollbacks      []string
	parkedProxy    bool
	overrideSet    bool
	overrideVia    string
	overridePrefix string
	reporter       Progress
	committed      bool
}

// fileBackup names a file a write replaces and the copy kept of its old bytes.
type fileBackup struct {
	backup string
	target string
}

func newTransaction(gameDir string, reporter Progress) *transaction {
	return &transaction{gameDir: gameDir, backups: map[string]fileBackup{}, reporter: reporter}
}

// adoptPack takes over the undo of a loader pack install content just carried out.
func (t *transaction) adoptPack(pack *content.BepInExResult) {
	if pack == nil {
		return
	}
	t.parkedProxy = pack.Parked
	for _, name := range pack.PackFiles {
		if !ppath.SafeRelative(name) {
			continue
		}
		t.packFiles = append(t.packFiles, name)
	}
}

// placeMod moves the already-unpacked plugin set into the game folder beside the
// loader that reads it.
func (t *transaction) placeMod(staging string, staged []string) ([]string, error) {
	var placed []string
	for _, relative := range staged {
		// The archive path is already where the loader looks for the plugin.
		if err := t.copyIn(filepath.Join(staging, filepath.FromSlash(relative)), relative); err != nil {
			return nil, err
		}
		placed = append(placed, relative)
	}
	sort.Strings(placed)
	return placed, nil
}

// copyIn puts one unpacked file into the game directory, backing up what it replaces.
func (t *transaction) copyIn(source, relative string) error {
	destination := filepath.Join(t.gameDir, filepath.FromSlash(relative))
	if !inside(destination, t.gameDir) {
		return fail("%s is not inside the game directory", strconv.Quote(relative))
	}
	if err := os.MkdirAll(filepath.Dir(destination), 0o755); err != nil {
		return fail("cannot create the folder for %s: %s", strconv.Quote(relative), err.Error())
	}
	if _, seen := t.backups[relative]; !seen {
		if ppath.IsFile(destination) {
			backup, err := t.backup(destination, relative)
			if err != nil {
				return err
			}
			t.backups[relative] = fileBackup{backup: backup, target: destination}
		} else {
			t.placed = append(t.placed, relative)
		}
	}
	body, err := os.ReadFile(source)
	if err != nil {
		return fail("cannot read the unpacked %s: %s", strconv.Quote(relative), err.Error())
	}
	if err := os.WriteFile(destination, body, 0o644); err != nil {
		return fail("cannot write %s: %s", strconv.Quote(relative), err.Error())
	}
	return nil
}

func (t *transaction) backup(destination, relative string) (string, error) {
	body, err := os.ReadFile(destination)
	if err != nil {
		return "", fail("cannot read %s before replacing it: %s", strconv.Quote(relative), err.Error())
	}
	backup := filepath.Join(t.gameDir, backupDir, filepath.FromSlash(relative))
	if err := os.MkdirAll(filepath.Dir(backup), 0o755); err != nil {
		return "", fail("cannot create a folder to keep %s in: %s", strconv.Quote(relative), err.Error())
	}
	if err := os.WriteFile(backup, body, 0o600); err != nil {
		return "", fail("cannot keep %s aside: %s", strconv.Quote(relative), err.Error())
	}
	return backup, nil
}

// markOverride notes that this run pointed the prefix at the loader's winhttp
// proxy. Any route that wrote the key counts, so uninstall can clear either.
func (t *transaction) markOverride(prefix, via string) {
	t.overrideSet = true
	t.overrideVia = via
	t.overridePrefix = ppath.Normalize(prefix)
}

// record notes a file this run created, so a rollback removes rather than restores.
func (t *transaction) record(relative string) {
	t.placed = append(t.placed, relative)
}

// writeRecord writes this run's loader state, leaving levels and packs alone.
func (t *transaction) writeRecord(result *Result) error {
	record := content.LoadRecord(t.gameDir)
	if record == nil {
		record = &content.Record{Schema: content.RecordSchema}
	}
	record.ModVersion = result.ModVersion
	record.BepinexVersion = result.BepInExVersion
	record.Loader = &content.LoaderState{
		BepInExVersion: result.BepInExVersion,
		ModVersion:     result.ModVersion,
		Installed:      true,
		PackFiles:      append([]string{}, result.PackFiles...),
		ProxyParked:    t.parkedProxy,
		ModSHA256:      result.ModSHA256,
	}
	if t.parkedProxy {
		backup := content.ProxyBackupName
		record.Loader.ProxyBackup = &backup
	}
	record.Runtime = &content.Runtime{Mode: "gamedir", Path: content.RuntimeDirName, Version: "6"}
	if result.OverrideApplied {
		prefix := t.overridePrefix
		via := result.OverrideVia
		record.DllOverride = &content.DllOverride{
			Applied: true,
			Name:    proton.WinHTTPDLLName,
			Value:   proton.WinHTTPValue,
			Via:     &via,
			Prefix:  &prefix,
		}
	} else {
		record.DllOverride = nil
	}
	_, err := content.SaveRecord(t.gameDir, record)
	return err
}

// writeOverrideRecord records only the prefix override this run applied.
func (t *transaction) writeOverrideRecord(result *Result) error {
	record := content.LoadRecord(t.gameDir)
	if record == nil {
		record = &content.Record{Schema: content.RecordSchema}
	}
	if result.OverrideApplied {
		prefix := t.overridePrefix
		via := result.OverrideVia
		record.DllOverride = &content.DllOverride{
			Applied: true,
			Name:    proton.WinHTTPDLLName,
			Value:   proton.WinHTTPValue,
			Via:     &via,
			Prefix:  &prefix,
		}
	} else {
		record.DllOverride = nil
	}
	_, err := content.SaveRecord(t.gameDir, record)
	return err
}

func (t *transaction) commit() {
	t.committed = true
	t.dropBackups()
}

// abort rolls the run back and names anything the rollback could not restore.
func (t *transaction) abort(err error) error {
	t.rollback()
	if len(t.rollbacks) > 0 {
		left := strings.Join(t.rollbacks, ", ")
		return fail("%s (and these files could not be restored: %s)", err.Error(), left)
	}
	if errors.Is(err, ErrCancelled) {
		return ErrCancelled
	}
	return err
}

func (t *transaction) rollback() {
	if t.committed {
		return
	}
	// Keep going through every backup; stopping early would leave the rest broken.
	for _, kept := range t.backups {
		if body, err := os.ReadFile(kept.backup); err == nil {
			if err := os.MkdirAll(filepath.Dir(kept.target), 0o755); err != nil {
				t.rollbacks = append(t.rollbacks, kept.target)
			} else if err := os.WriteFile(kept.target, body, 0o644); err != nil {
				t.rollbacks = append(t.rollbacks, kept.target)
			}
		} else {
			t.rollbacks = append(t.rollbacks, kept.target)
		}
		_ = os.Remove(kept.backup)
	}
	// One inventory, pack and mod alike, removed deepest first.
	names := append(append([]string{}, t.packFiles...), t.placed...)
	sort.Sort(sort.Reverse(sort.StringSlice(names)))
	for _, relative := range names {
		target := filepath.Join(t.gameDir, filepath.FromSlash(relative))
		// Already-gone is fine; anything else was left behind by this run.
		if err := os.Remove(target); err != nil && !errors.Is(err, os.ErrNotExist) {
			t.rollbacks = append(t.rollbacks, target)
		}
	}
	// Then the folders they filled, each dropped only once nothing else is left.
	for _, folder := range packFolders(names) {
		dropIfEmpty(filepath.Join(t.gameDir, filepath.FromSlash(folder)))
	}
	t.placed = nil
	t.packFiles = nil
	t.backups = map[string]fileBackup{}
	t.rollbacks = nil
	t.dropBackups()
	if t.overrideSet {
		proton.ClearDllOverride(t.overridePrefix, proton.WinHTTPDLLName, "", "", nil)
		t.overrideSet = false
	}
	if t.parkedProxy {
		// content.UninstallRecorded restored the proxy; nothing else moves it.
		t.parkedProxy = false
	}
	// A stale record beats a claim there is nothing left to clean up.
	_ = content.ClearRecord(t.gameDir)
}

// packFolders are the folders the placed files filled, deepest first.
func packFolders(names []string) []string {
	folders := map[string]bool{}
	for _, name := range names {
		for parent := ppath.Parent(filepath.ToSlash(name)); parent != "" && parent != "."; parent = ppath.Parent(parent) {
			folders[parent] = true
		}
	}
	order := make([]string, 0, len(folders))
	for folder := range folders {
		order = append(order, folder)
	}
	// Deepest first, so a folder is visited after its contents were dropped.
	sort.Slice(order, func(i, j int) bool {
		left, right := strings.Count(order[i], "/"), strings.Count(order[j], "/")
		if left != right {
			return left > right
		}
		return order[i] > order[j]
	})
	return order
}

// dropIfEmpty removes a folder that holds nothing.
func dropIfEmpty(directory string) {
	entries, err := os.ReadDir(directory)
	if err != nil || len(entries) > 0 {
		return
	}
	_ = os.Remove(directory)
}

func (t *transaction) dropBackups() {
	folder := filepath.Join(t.gameDir, backupDir)
	if ppath.IsDir(folder) {
		_ = os.RemoveAll(folder)
	}
}

// inside reports whether destination sits under root.
func inside(destination, root string) bool {
	clean := filepath.Clean(root)
	resolved := filepath.Clean(destination)
	return resolved == clean || strings.HasPrefix(resolved, clean+string(filepath.Separator))
}

func start(reporter Progress, total int, label string) {
	if reporter != nil {
		reporter.Start(total, label)
	}
}

func step(reporter Progress, label string) {
	if reporter != nil {
		reporter.Step(label)
	}
}

func finish(reporter Progress, message string, ok bool) {
	if reporter != nil {
		reporter.Finish(message, ok)
	}
}

func showLaunchOption(reporter Progress, option string) {
	if shower, ok := reporter.(ui.LaunchOptionShower); ok {
		shower.ShowLaunchOption(option)
	}
}

// cancelled asks whether the player stopped the run. A reporter is asked once
// its own steps have been reported, so a step counter alone is not a request.
func cancelled(reporter Progress) bool {
	if reporter == nil {
		return false
	}
	cancellable, ok := reporter.(ui.Cancellable)
	return ok && cancellable.Cancelled()
}

// PlannedStepCount is how many steps a mod install reports, so a caller that
// owns the whole run's progress can count them up front.
const PlannedStepCount = 10

// OverrideOnlyStepCount is how many steps an override-only run reports.
const OverrideOnlyStepCount = 2
