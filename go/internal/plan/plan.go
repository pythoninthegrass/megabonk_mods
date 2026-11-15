// Package plan works out what a level install consists of before anything is
// written, and carries it out step by step.
package plan

import (
	"errors"
	"fmt"
	"net/url"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/pythoninthegrass/megabonk_mods/installer/internal/content"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/gamebuild"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/modinstall"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ppath"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/proton"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/site"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/steam"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/thunderstore"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ui"
)

// ModChoice is what the player said about the level editor mod.
type ModChoice int

const (
	// ModAuto installs the mod only when it is not already installed.
	ModAuto ModChoice = iota
	// ModForced installs or updates the mod whatever the record says.
	ModForced
	// ModRefused leaves the mod alone.
	ModRefused
)

// Asked reports whether the player named a choice at all, which is what tells
// --mod and --no-mod apart from saying nothing.
func (m ModChoice) Asked() bool { return m != ModAuto }

// String names the choice for a usage message.
func (m ModChoice) String() string {
	switch m {
	case ModForced:
		return "mod"
	case ModRefused:
		return "no-mod"
	}
	return "auto"
}

// Platforms the installer sets up; detection picks one when the caller does not.
const (
	PlatformProton = modinstall.PlatformProton
	PlatformWine   = modinstall.PlatformWine
	PlatformNative = modinstall.PlatformNative

	platformProton = PlatformProton
	platformWine   = PlatformWine
	platformNative = PlatformNative
)

// Action kinds a plan can contain.
const (
	KindFetchLevel   = "fetch-level"
	KindFetchImage   = "fetch-image"
	KindFetchPack    = "fetch-pack"
	KindInstallLevel = "install-level"
	KindInstallImage = "install-image"
	KindInstallPack  = "install-pack"
	KindInstallMod   = "install-mod"
	KindSetOverride  = "set-winhttp-override"
)

// stagingName is the folder a staged tree is built under, beside (never inside)
// the game directory.
const stagingName = "megabonk-levels-staging"

// Error means the install cannot be planned: an input is unusable, the site
// refused, or the game directory is not one this installer writes to.
type Error struct{ message string }

func (e *Error) Error() string { return e.message }

func fail(format string, args ...any) error {
	return &Error{message: fmt.Sprintf(format, args...)}
}

// UnsupportedBuildError refuses a build this installer cannot write to. The exit
// code tells "wrong build" apart from any other failure.
type UnsupportedBuildError struct{ message string }

func (e *UnsupportedBuildError) Error() string { return e.message }

func unsupportedBuild(format string, args ...any) error {
	return &UnsupportedBuildError{message: fmt.Sprintf(format, args...)}
}

// IsUnsupportedBuild reports a refusal caused by the installed build itself.
func IsUnsupportedBuild(err error) bool {
	var unsupported *UnsupportedBuildError
	return errors.As(err, &unsupported)
}

// MissingPrefixError means the platform needed a prefix the player did not name:
// an error about the invocation, so the exit code says usage.
type MissingPrefixError struct{ message string }

func (e *MissingPrefixError) Error() string { return e.message }

func missingPrefix(format string, args ...any) error {
	return &MissingPrefixError{message: fmt.Sprintf(format, args...)}
}

// IsMissingPrefix reports a run refused for want of --prefix.
func IsMissingPrefix(err error) bool {
	var missing *MissingPrefixError
	return errors.As(err, &missing)
}

// Input is one positional argument: a share code, a level link, or the path of
// a local .mblevel.json file.
type Input struct {
	Raw string
}

// Action is one step of a plan.
type Action struct {
	Kind   string
	Path   string
	Detail string
	Source string
	// HasSource tells an empty Source apart from no source at all.
	HasSource bool
	// PackID and LevelCode name what the action installs, for the record.
	PackID    string
	PackVer   string
	LevelCode string
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
	Kind      string  `json:"kind"`
	Path      string  `json:"path"`
	Detail    string  `json:"detail"`
	Source    *string `json:"source,omitempty"`
	PackID    string  `json:"pack_id,omitempty"`
	Version   string  `json:"version,omitempty"`
	LevelCode string  `json:"level_code,omitempty"`
}

// Document renders the action for --json.
func (a Action) Document() ActionDocument {
	entry := ActionDocument{Kind: a.Kind, Path: a.Path, Detail: a.Detail,
		PackID: a.PackID, Version: a.PackVer, LevelCode: a.LevelCode}
	if a.HasSource {
		source := a.Source
		entry.Source = &source
	}
	return entry
}

// Document is a plan in the shape --json prints.
type Document struct {
	GameDir  string   `json:"game_dir"`
	Build    string   `json:"build"`
	Prefix   *string  `json:"prefix"`
	Platform string   `json:"platform"`
	Levels   []string `json:"levels"`
	Packs    []string `json:"packs"`
	Mod      bool     `json:"mod"`
	// ModStatus is what --check reports about the mod.
	ModStatus      *modinstall.State `json:"mod_status,omitempty"`
	ModVersion     string            `json:"mod_version,omitempty"`
	BepInExVersion string            `json:"bepinex_version,omitempty"`
	LaunchOption   *string           `json:"launch_option"`
	Actions        []ActionDocument  `json:"actions"`
	Warnings       []string          `json:"warnings"`
}

// Plan is what a run would do, built before anything is written.
type Plan struct {
	GameDir  string
	Build    string
	Prefix   string
	Platform string
	Levels   []string
	Packs    []string
	// Mod says this run installs or enables the level editor mod.
	Mod bool
	// ModOwned says the mod files are this installer's to place, rather than
	// another tool's to leave in place.
	ModOwned       bool
	ModVersion     string
	BepInExVersion string
	ModStatus      *modinstall.State
	LaunchOption   *string
	// OverrideNote says how a Wine run edited the prefix itself. Empty where
	// nothing was set.
	OverrideNote string
	Actions      []Action
	Warnings     []string

	options      Options
	resolved     []*level
	overrideVia  string
	modResult    *modinstall.Result
	stagedOwners map[string]string
	staging      *content.Staging
	download     *downloader
}

// IsNoop reports whether the game already holds everything the inputs ask for.
func (p *Plan) IsNoop() bool { return len(p.Actions) == 0 }

// Document renders the plan for --json.
func (p *Plan) Document() Document {
	document := Document{
		GameDir: p.GameDir, Build: p.Build, Platform: p.Platform,
		Levels: p.Levels, Packs: p.Packs, Mod: p.Mod, ModStatus: p.ModStatus,
		ModVersion: p.ModVersion, BepInExVersion: p.BepInExVersion,
		LaunchOption: p.LaunchOption,
		Actions:      []ActionDocument{},
		Warnings:     p.Warnings,
	}
	if document.Levels == nil {
		document.Levels = []string{}
	}
	if document.Packs == nil {
		document.Packs = []string{}
	}
	if document.Warnings == nil {
		document.Warnings = []string{}
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

// Options carries the caller's choices; the zero value plans a content-only run
// for the platform the host and paths describe.
type Options struct {
	// Game is the directory holding Megabonk.exe.
	Game string
	// Prefix is the Proton or Wine prefix the override is written into.
	Prefix string
	// Platform is one of the platform constants, or "" to detect it.
	Platform string
	// Inputs are the player's positional arguments.
	Inputs []Input
	// Mod is what the player said about the level editor mod.
	Mod ModChoice
	// ModOwned places the loader pack and plugin set rather than only enabling
	// ones already in the game folder. Tests set it; a build works it out.
	ModOwned bool
	// APIClient talks to the gallery API; nil uses the environment's location.
	APIClient *site.Client
	// Thunder talks to Thunderstore; nil uses the environment's locations.
	Thunder *thunderstore.Client
	// Pins are known-good loader pack digests by version.
	Pins map[string]string
	// ModPins are known-good digests for the mod's own releases.
	ModPins []modinstall.ModPin
	// WineBin names the wine binary for prefix edits; "" uses the registry writer.
	WineBin string
	// WineRunner runs the wine command, which tests supply.
	WineRunner proton.Runner
	// Cache holds downloaded archives; empty means a temporary folder.
	Cache string
	// FetchMod fetches a mod archive; nil uses Thunderstore. Tests inject it.
	FetchMod ModFetcher
	// FetchPack fetches a loader pack archive; nil uses Thunderstore.
	FetchPack PackFetcher
	// OverrideOnly enables a mod somebody else installed instead of placing one.
	OverrideOnly bool
}

// ModFetcher hands over one verified mod archive.
type ModFetcher func(version, digest, target string) (*thunderstore.Downloaded, error)

// PackFetcher hands over one verified loader pack archive.
type PackFetcher func(version, digest, target string) (*thunderstore.Downloaded, error)

// BuildPlan turns the player's inputs into the steps a run would take, fetching
// nothing and writing nothing. A shared pack appears once.
func BuildPlan(options Options) (*Plan, error) {
	game := ppath.Normalize(options.Game)
	if game == "" || game == "." {
		return nil, fail("no game directory: pass --game-dir, or install Megabonk in Steam first")
	}
	// The build is classified before the network is used, so a native Linux
	// game is refused without a download and a player is not kept waiting.
	build := gamebuild.Classify(game)
	if !build.Supported() {
		return nil, unsupportedBuild("%s", gamebuild.UnsupportedBuildMessage(game, build.Kind, melonloaderVersion))
	}
	if len(options.Inputs) == 0 {
		return nil, fail("nothing to install: pass a share code, a %s level link or a .mblevel.json file",
			site.SiteHost)
	}
	// What the player asked for is read before the prefix is judged, so a bad
	// file or an unknown code is told to them rather than a folder complaint.
	resolved, err := resolveInputs(options)
	if err != nil {
		return nil, err
	}
	platform, prefix, prefixWarning, err := resolvePlatform(options, game)
	if err != nil {
		return nil, err
	}
	warnings := []string{}
	if prefixWarning != "" {
		warnings = append(warnings, prefixWarning)
	}

	built := &Plan{GameDir: game, Build: build.Kind, Prefix: prefix, Platform: platform, options: options}
	built.resolved = resolved

	packs := map[string]string{}
	for _, level := range resolved {
		for packID, version := range level.packs {
			if known, seen := packs[packID]; seen && known != version {
				return nil, fail("two of the requested levels need different versions of pack %s (%s and %s); "+
					"install them separately", strconv.Quote(packID), known, version)
			}
			if _, seen := packs[packID]; !seen {
				packs[packID] = version
			}
		}
	}
	// A pack already installed at the version every level asks for is skipped;
	// a pack another level wants at a different version is reinstalled.
	skipped := map[string]bool{}
	for packID, version := range packs {
		if len(wantedVersions(packID, resolved)) > 1 {
			continue
		}
		if installedPackVersion(game, packID) == version && version != "" {
			skipped[packID] = true
		}
	}

	actions := []Action{}
	record := content.LoadRecord(game)

	for _, level := range resolved {
		// A level the game already holds exactly is left alone: no download, no
		// placement, and a run that asks for nothing is reported as a no-op.
		if level.uptodate(game, record) {
			continue
		}
		actions = append(actions, level.fetchActions(game, options, record)...)
		// Every fetched file needs a placement step: a file that already exists
		// under the same name still has to be overwritten with what was fetched.
		actions = append(actions, level.installActions(game, record)...)
	}

	for _, packID := range sortedPackIDs(packs) {
		if skipped[packID] {
			continue
		}
		version := packs[packID]
		// A pack the site does not offer for this platform is a warning, not a
		// step: the level still installs and the player hears why it may not load.
		if !packIsHosted(options, packID, version) {
			warnings = append(warnings, "pack "+packID+" is not on "+site.SiteHost+" for this platform, "+
				"so it was not installed; the levels that need it may not load")
			continue
		}
		actions = append(actions, Action{
			Kind: KindFetchPack, Path: packID, Detail: "download pack " + packID + " " + orUnknown(version) +
				" from " + site.SiteHost,
			Source: packDownloadURL(options, packID, version), HasSource: true, PackID: packID, PackVer: version,
		})
		actions = append(actions, Action{
			Kind: KindInstallPack, Path: packTarget(packID),
			Detail: "install pack " + packID + " " + orUnknown(version) + " into " + content.LevelPacksPath(game),
			PackID: packID, PackVer: version,
		})
	}

	if built.Mod = modWanted(options, game, record); built.Mod {
		built.ModOwned = options.ModOwned || modinstall.Detect(game).Installed ||
			!content.ModInstalled(game) || options.Mod == ModForced
		owner := "install " + thunderstore.ModName + " and the BepInEx loader pack"
		if !built.ModOwned {
			owner = "enable " + thunderstore.ModName + " for the loader already in place"
		}
		actions = append(actions, Action{Kind: KindInstallMod, Path: content.BepInExPluginsPath(game), Detail: owner})
		if platform == platformProton {
			option := proton.WinHTTPLaunchOption
			built.LaunchOption = &option
			actions = append(actions, Action{
				Kind: KindSetOverride, Path: game,
				Detail: "prepare the Steam launch option to copy",
			})
		} else if platform == platformWine {
			// Which way the prefix can be edited is known before the run: wine reg
			// when there is a wine to run, the registry writer otherwise.
			via := "the registry file"
			if options.WineBin != "" {
				via = "wine reg"
			}
			built.overrideVia = via
			built.OverrideNote = proton.WinHTTPDLLName + " = " + proton.WinHTTPValue +
				" in " + prefix + " (" + via + ")"
			actions = append(actions, Action{
				Kind: KindSetOverride, Path: prefix,
				Detail: "set " + proton.WinHTTPDLLName + " = " + proton.WinHTTPValue + " in " + prefix +
					" (" + via + ")",
			})
		}
	}

	built.Actions = actions
	built.Warnings = warnings
	built.Levels = levelCodes(resolved)
	built.Packs = sortedPackIDs(packs)
	// What is in the game folder now is reported whether or not this run would
	// touch it: --check answers "is the editor there" on a game it will not change.
	state := modinstall.DetectAgainst(options.Thunder, game)
	built.ModStatus = &state
	return built, nil
}

// resolvePlatform takes the caller's platform, or picks the one the prefix it was
// given describes. The third result is a warning, not a refusal.
func resolvePlatform(options Options, game string) (string, string, string, error) {
	prefix := ppath.Normalize(strings.TrimSpace(options.Prefix))
	if prefix == "." {
		prefix = ""
	}
	if raw := strings.ToLower(strings.TrimSpace(options.Platform)); raw != "" {
		switch raw {
		case platformProton, platformWine:
			if usable := usablePrefix(prefix); usable != "" {
				return raw, usable, "", nil
			}
			if prefix == "" {
				return "", "", "", missingPrefix("a %s install needs a prefix: pass --prefix with the "+
					"steamapps/compatdata/%s/pfx folder for a Proton install, or with the Wine "+
					"prefix folder for a plain Wine or CrossOver bottle", raw, steam.AppID)
			}
			return platformNative, "", unusablePrefixWarning(prefix), nil
		case platformNative:
			return platformNative, "", "", nil
		default:
			return "", "", "", fail("%s is not a platform this installer knows: use %s, %s or %s",
				strconv.Quote(raw), platformProton, platformWine, platformNative)
		}
	}
	switch {
	case isProtonPrefix(prefix):
		return platformProton, prefix, "", nil
	case prefix != "" && ppath.IsDir(filepath.Join(prefix, "drive_c")):
		return platformWine, prefix, "", nil
	case prefix == "":
		// Nothing was named, and the Windows build runs on its own; only a
		// prefix edit still needs one, which the mod step asks for by name.
		return platformNative, "", "", nil
	}
	return platformNative, "", unusablePrefixWarning(prefix), nil
}

// usablePrefix returns prefix when it can be edited for platform, or "".
func usablePrefix(prefix string) string {
	if prefix != "" && ppath.IsDir(filepath.Join(prefix, "drive_c")) {
		return prefix
	}
	return ""
}

// unusablePrefixWarning is what a run says when the prefix it was handed has no
// drive_c, which is what Steam leaves until the game first runs under Proton.
func unusablePrefixWarning(prefix string) string {
	return "warning: no usable Proton prefix at " + prefix + ": there is no drive_c folder inside " +
		"it, which Steam creates the first time the game runs under Proton. The BepInEx loader " +
		"pack carries its own .NET 6 runtime, so the install continues beside the game and " +
		"nothing is written to the prefix; the winhttp override is what is missing. Start " +
		"Megabonk once under Proton, quit, and run this installer again to set it, or pass " +
		"--prefix <path to the pfx directory> to install into an existing Proton prefix."
}

func isProtonPrefix(prefix string) bool {
	normal := ppath.Normalize(prefix)
	if normal == "" || !strings.HasSuffix(normal, "/pfx") || !ppath.IsDir(filepath.Join(prefix, "drive_c")) {
		return false
	}
	return strings.Contains(normal, "/compatdata/")
}

// modWanted decides whether the mod is part of this run: --mod always, --no-mod
// never, and otherwise only when the mod is not already installed.
func modWanted(options Options, game string, record *content.Record) bool {
	switch options.Mod {
	case ModForced:
		return true
	case ModRefused:
		return false
	}
	if content.ModInstalled(game) {
		return false
	}
	return record == nil || record.Loader == nil || !record.Loader.Installed
}

// level is one resolved input: what lands under UserData/Levels, the images that
// go beside it, and the packs it needs.
type level struct {
	slug     string
	heading  string
	code     string
	hosted   bool
	source   string
	fileName string
	// body is the downloaded level file; nil until fetched.
	body   []byte
	images []image
	packs  map[string]string
	// pending names what this run still has to write.
	pendingLevels []string
	pendingImages []string
}

// image is one sidecar picture and where it lands.
type image struct {
	name   string
	url    string
	source string
	body   []byte
}

func (l *level) heading_() string {
	if l.heading != "" {
		return l.heading
	}
	return l.slug
}

// filename is the level's file name as it will sit in UserData/Levels.
func (l *level) filename() string {
	if l.fileName != "" {
		return l.fileName
	}
	return l.slug + ".mblevel.json"
}

// resolveInputs reads a record for every input, in the order the player gave
// them, and folds duplicate spellings of one level into a single install.
func resolveInputs(options Options) ([]*level, error) {
	client := options.APIClient
	if client == nil {
		client = site.NewClientFromEnv()
	}
	seen := map[string]*level{}
	resolved := []*level{}
	for _, raw := range options.Inputs {
		text := strings.TrimSpace(raw.Raw)
		if text == "" {
			continue
		}
		next, err := resolveInput(options, client, text)
		if err != nil {
			return nil, err
		}
		if known, again := seen[next.slug]; again {
			// The same level asked for twice: the one already read is kept, and a
			// local file is preferred over the site's copy of the same name.
			if known.source == "" && next.source != "" {
				known.source = next.source
				known.images = next.images
			}
			continue
		}
		seen[next.slug] = next
		resolved = append(resolved, next)
	}
	if len(resolved) == 0 {
		return nil, fail("nothing to install: pass a share code, a %s level link or a .mblevel.json file",
			site.SiteHost)
	}
	return resolved, nil
}

// resolveInput works out which of the four kinds of input the player gave, and
// reads its record.
func resolveInput(options Options, client *site.Client, text string) (*level, error) {
	if local, found := localInput(text); found {
		return resolveLocal(options, client, local)
	}
	code, codeErr := site.NormalizeCode(text)
	if codeErr != nil {
		// Not a code or a link: a bare level name is looked up by its file name,
		// which is what a player sees in the game's own level list.
		if strings.ContainsAny(text, "/\\") || !plainName(text) {
			return nil, fail("%s is not a level: pass a share code such as 7N1-MVB-WKF, a %s level "+
				"link, a %s file on disk, or the name of a level on %s",
				strconv.Quote(text), site.SiteHost, LevelFileSuffix, site.SiteHost)
		}
		found, err := client.LookupLevelByFilename(storedLevelName(text))
		if err != nil {
			if site.IsNotFound(err) {
				// Quote what the player typed, not the file name it was turned into:
				// they have to see which of their words the site did not know.
				return nil, fail("%s is not a level on %s: pass a share code, a %s level link, a "+
					"%s file on disk, or the name a level on %s is listed under",
					strconv.Quote(text), site.SiteHost, site.SiteHost, LevelFileSuffix, site.SiteHost)
			}
			return nil, err
		}
		return hostedLevel(found), nil
	}
	found, err := client.LookupLevel(code)
	if err != nil {
		return nil, err
	}
	return hostedLevel(found), nil
}

// LevelFileSuffix is the extension a Megabonk level file carries.
const LevelFileSuffix = ".mblevel.json"

// plainName reports whether an input is a bare name rather than a path or a
// stray option, which is the only thing worth looking up by file name.
func plainName(name string) bool {
	return name != "" && !strings.HasPrefix(name, "-") && !strings.HasPrefix(name, ".") &&
		!strings.Contains(name, "..")
}

// storedLevelName is the file name a level the player named is stored under.
func storedLevelName(name string) string {
	for _, suffix := range content.LevelSuffixes {
		if strings.HasSuffix(strings.ToLower(name), suffix) {
			return name
		}
	}
	return name + LevelFileSuffix
}

// localInput reports whether an input is a path to a file on disk rather than a
// code or a link.
func localInput(text string) (string, bool) {
	candidate := ppath.ExpandUser(text)
	if ppath.IsFile(candidate) {
		return candidate, true
	}
	return "", false
}

// hostedLevel turns a site record into what this run will place.
func hostedLevel(found *site.Level) *level {
	slug := content.LevelStem(found.Filename())
	if slug == "" {
		slug = site.Slug(found.Title)
	}
	next := &level{
		slug: slug, heading: found.Title, hosted: true, fileName: found.Filename(),
		code: strings.TrimSpace(found.Code), packs: found.Packs,
	}
	// A record found by file name carries no code of its own, and the code is
	// what the counting download route needs.
	if next.code == "" {
		if _, err := site.NormalizeCode(next.fileName); err != nil {
			next.code = next.fileName
		}
	}
	for _, pair := range []struct {
		name string
		url  string
	}{
		{content.CoverFor(slug), found.CoverURL()},
		{content.BiomeFor(slug), found.BiomeURL()},
	} {
		if pair.url != "" {
			next.images = append(next.images, image{name: pair.name, url: pair.url})
		}
	}
	return next
}

// resolveLocal reads a level the player supplied. Its packs still come from the
// site, matched on the file name; it has no cover unless an image sits beside it.
func resolveLocal(options Options, client *site.Client, path string) (*level, error) {
	if problems := content.ValidateLevelFile(path); len(problems) > 0 {
		return nil, fail("%s", strings.Join(problems, "; "))
	}
	slug := content.LevelStem(path)
	if !content.ValidPackID(slug) {
		slug = ppath.SanitizeName(content.LevelStem(path))
	}
	if slug == "" || !content.ValidPackID(slug) {
		return nil, fail("%s: the file name is not a level name the game can list", strconv.Quote(path))
	}
	next := &level{slug: slug, source: path, fileName: content.LevelStem(path) + LevelFileSuffix, packs: map[string]string{}}
	for _, image := range localImages(path, slug) {
		next.images = append(next.images, image)
	}
	found, err := client.LookupLevelByFilename(ppath.Name(path))
	if err == nil && found != nil {
		next.packs = found.Packs
		next.heading = found.Title
	} else if err != nil && !site.IsNotFound(err) {
		return nil, err
	}
	return next, nil
}

// localImages are the pictures that sit beside a local level file: the cover and
// biome image named after its stem.
func localImages(path, slug string) []image {
	dir := ppath.Parent(path)
	found := []image{}
	for _, candidate := range []struct {
		name   string
		source string
	}{
		{content.CoverFor(slug), ppath.Join(dir, content.CoverFor(slug))},
		{content.BiomeFor(slug), ppath.Join(dir, content.BiomeFor(slug))},
	} {
		if ppath.IsFile(candidate.source) {
			found = append(found, image{name: candidate.name, source: candidate.source})
		}
	}
	return found
}

// pending says whether this run still has anything to write for the level.
func (l *level) pending(game string, record *content.Record) bool {
	if l.wants(game, record, levelTarget(l.filename())) {
		return true
	}
	for _, want := range l.images {
		if l.wants(game, record, imageTarget(want.name)) {
			return true
		}
	}
	return false
}

// uptodate reports whether the game already holds exactly this level and the
// images this run would write.
func (l *level) uptodate(game string, record *content.Record) bool {
	if !l.pending(game, record) {
		return true
	}
	if record == nil {
		return false
	}
	entry, found := record.Levels[l.slug]
	if !found {
		return false
	}
	if l.body == nil && l.source == "" {
		return true
	}
	target := content.LevelsPath(game)
	if l.source != "" {
		if !sameFileOnDisk(ppath.Join(target, l.filename()), l.source) {
			return false
		}
	} else if !ppath.IsFile(ppath.Join(target, l.filename())) {
		return false
	}
	for _, want := range l.images {
		if want.body == nil && want.source == "" {
			continue
		}
		current := entry.Cover
		if want.name == content.BiomeFor(l.slug) {
			current = entry.Biome
		}
		if current != imageTarget(want.name) {
			return false
		}
		if !ppath.IsFile(ppath.Join(target, want.name)) {
			return false
		}
	}
	return true
}

// fetchActions are the steps that take this level's files out of the site, or
// read them off disk. Only files the run has not got already are asked for.
func (l *level) fetchActions(game string, options Options, record *content.Record) []Action {
	actions := []Action{}
	if l.writesLevelFile() && l.body == nil {
		// A local file is read from disk and a hosted one comes from the site's
		// counting route; either way the plan says where the bytes come from.
		detail := "read " + l.heading_() + " from " + ppath.Parent(l.source)
		source := l.source
		if l.hosted {
			detail = "download " + l.heading_() + " from " + site.SiteHost
			source = l.downloadURL(options)
		}
		actions = append(actions, Action{
			Kind: KindFetchLevel, Path: levelTarget(l.filename()), Detail: detail,
			Source: source, HasSource: true, LevelCode: l.slug,
		})
	}
	for _, want := range l.images {
		if want.source != "" || want.body != nil || !l.wants(game, record, imageTarget(want.name)) {
			continue
		}
		actions = append(actions, Action{
			Kind: KindFetchImage, Path: imageTarget(want.name),
			Detail: "download " + want.name + " from " + site.SiteHost,
			Source: want.url, HasSource: true, LevelCode: l.slug,
		})
	}
	return actions
}

// installActions are the steps that place this level and its images.
func (l *level) installActions(game string, record *content.Record) []Action {
	actions := []Action{}
	target := content.LevelsPath(game)
	if l.writesLevelFile() {
		actions = append(actions, Action{
			Kind: KindInstallLevel, Path: levelTarget(l.filename()),
			Detail: l.filename() + " -> " + target, LevelCode: l.slug,
		})
	}
	for _, want := range l.images {
		if !l.wants(game, record, imageTarget(want.name)) {
			continue
		}
		actions = append(actions, Action{
			Kind: KindInstallImage, Path: imageTarget(want.name),
			Detail: want.name + " -> " + target, LevelCode: l.slug,
		})
	}
	return actions
}

// sameFileOnDisk reports whether two paths hold the same bytes.
func sameFileOnDisk(left, right string) bool {
	if !ppath.IsFile(left) || !ppath.IsFile(right) {
		return false
	}
	leftBody, err := os.ReadFile(left)
	if err != nil {
		return false
	}
	rightBody, err := os.ReadFile(right)
	if err != nil {
		return false
	}
	return string(leftBody) == string(rightBody)
}

// installedPackVersion is the version of a pack this installer put in the game
// folder, or "" when it did not place it.
func installedPackVersion(game, packID string) string {
	record := content.LoadRecord(game)
	if record == nil {
		return ""
	}
	entry, found := record.Packs[packID]
	if !found {
		return ""
	}
	if !ppath.IsDir(content.PackDest(game, packID)) {
		return ""
	}
	return entry.Version
}

// packIsHosted asks the site whether it offers the pack at all. An unreachable
// API is left to the download: it is not the same thing as a missing pack.
func packIsHosted(options Options, packID, version string) bool {
	client := options.APIClient
	if client == nil {
		client = site.NewClientFromEnv()
	}
	if _, err := client.DownloadPack(packID, version); err != nil {
		return !site.IsPackNotHosted(err)
	}
	return true
}

// packDownloadURL is where a pack archive comes from, for the plan listing.
func packDownloadURL(options Options, packID, version string) string {
	client := options.APIClient
	if client == nil {
		client = site.NewClientFromEnv()
	}
	return client.PackDownloadURL(packID, version)
}

// wantedVersions are the distinct versions the resolved levels ask a pack to be
// at; more than one means the pack has to be installed even if it is present.
func wantedVersions(packID string, levels []*level) []string {
	seen := []string{}
	for _, level := range levels {
		version, found := level.packs[packID]
		if !found {
			continue
		}
		duplicate := false
		for _, known := range seen {
			if known == version {
				duplicate = true
			}
		}
		if !duplicate {
			seen = append(seen, version)
		}
	}
	sort.Strings(seen)
	return seen
}

func sortedPackIDs(packs map[string]string) []string {
	ids := make([]string, 0, len(packs))
	for id := range packs {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	return ids
}

func levelCodes(levels []*level) []string {
	codes := make([]string, 0, len(levels))
	for _, level := range levels {
		codes = append(codes, level.slug)
	}
	sort.Strings(codes)
	return codes
}

func orUnknown(version string) string {
	if version == "" {
		return "(latest)"
	}
	return version
}

// ErrCancelled reports a between-steps cancel. A cancelled run is rolled back
// before it surfaces, and is the value the mod half reports too.
var ErrCancelled = modinstall.ErrCancelled

// stopped reports whether the player asked the run to stop. Only the window
// reporter can be asked, and only before any of this run's own steps are counted.
func stopped(progress ui.Progress) bool {
	cancellable, ok := progress.(ui.Cancellable)
	return ok && cancellable.Cancelled()
}

// ApplyPlan carries out a plan the caller has already inspected and confirmed,
// then records what was installed. A cancel rolls the run back first.
func ApplyPlan(built *Plan, progress ui.Progress) ([]Action, error) {
	if len(built.Actions) == 0 {
		if progress != nil {
			progress.Start(1, "install Megabonk Levels")
			progress.Finish("nothing to do", true)
		}
		return nil, nil
	}
	downloads, err := prepareDownloads(built)
	if err != nil {
		return nil, err
	}
	downloads.progress = progress
	defer downloads.close()
	if progress != nil {
		progress.Start(fetchSteps(built)+placeSteps(built)+modSteps(built), "install Megabonk Levels")
	}

	placed := []string{}
	for _, action := range built.Actions {
		if stopped(progress) {
			if err := rollback(built, placed); err != nil {
				return nil, err
			}
			return nil, ErrCancelled
		}
		switch action.Kind {
		case KindFetchLevel:
			if err := downloads.fetchLevel(built, action); err != nil {
				return nil, err
			}
		case KindFetchImage:
			if err := downloads.fetchImage(built, action); err != nil {
				return nil, err
			}
		case KindFetchPack:
			if err := downloads.fetchPack(built, action); err != nil {
				return nil, err
			}
		case KindInstallLevel, KindInstallImage, KindInstallPack:
			// Placement happens once, after every fetch has run, so a plan that
			// fails halfway leaves the game directory as it was.
			continue
		case KindInstallMod, KindSetOverride:
			// The mod and its override are carried out after the content they
			// belong with, by the one call that owns both.
			continue
		default:
			return nil, fail("unknown action kind %s", strconv.Quote(action.Kind))
		}
		if progress != nil {
			progress.Step(action.Label())
		}
	}
	committed, err := downloads.commit()
	if err != nil {
		if rollErr := rollback(built, committed); rollErr != nil {
			return nil, rollErr
		}
		return nil, err
	}
	placed = append(placed, committed...)
	for _, action := range built.Actions {
		if !installKind(action.Kind) {
			continue
		}
		if progress != nil {
			progress.Step(action.Label())
		}
		if !covers(committed, action) {
			if rollErr := rollback(built, placed); rollErr != nil {
				return nil, rollErr
			}
			return nil, fail("%s was planned but never placed", action.Label())
		}
	}
	// The mod goes in before the record is written, so the one record the run
	// leaves behind describes the content and the loader together.
	if err := built.applyMod(reporterFor(progress)); err != nil {
		if rollErr := rollback(built, placed); rollErr != nil {
			return nil, rollErr
		}
		return nil, err
	}
	if err := built.writeRecord(placed, built.modResult); err != nil {
		return nil, err
	}
	if progress != nil {
		progress.Finish("installed", true)
	}
	return built.Actions, nil
}

// rollback throws away the staged tree and removes every file this run placed,
// so a run that never finished leaves the game directory as it found it.
func rollback(built *Plan, placed []string) error {
	if built.staging != nil {
		_ = built.staging.Discard()
		built.staging = nil
	}
	return removePlaced(built.GameDir, placed)
}

// removePlaced deletes the files a run wrote, together with the folders it made
// for them and the record it saved.
func removePlaced(game string, placed []string) error {
	for _, name := range placed {
		if !ppath.SafeRelative(name) {
			continue
		}
		if err := os.Remove(toNativePath(ppath.Join(game, name))); err != nil && !os.IsNotExist(err) {
			return fail("cannot undo %s: %s", name, err.Error())
		}
	}
	for _, name := range []string{content.LevelsDir, content.LevelPacksDir} {
		dropEmptyFolders(ppath.Join(game, content.UserData, name))
	}
	_ = os.Remove(ppath.Join(game, content.RecordName))
	return nil
}

// dropEmptyFolders removes folders the rollback emptied, never one still holding
// something the player put there.
func dropEmptyFolders(root string) {
	entries, err := os.ReadDir(root)
	if err != nil {
		return
	}
	for _, entry := range entries {
		if entry.IsDir() {
			dropEmptyFolders(ppath.Join(root, entry.Name()))
		}
	}
	_ = os.Remove(root)
}

// relativeToGame is a game-directory path in the record's game-relative form.
func relativeToGame(game, path string) string {
	clean := ppath.Normalize(path)
	prefix := ppath.Normalize(game) + "/"
	if strings.HasPrefix(clean, prefix) {
		return clean[len(prefix):]
	}
	return clean
}

// applyMod runs the Thunderstore half of the plan: the loader pack and plugin
// set, and the platform's winhttp override.
func (p *Plan) applyMod(progress ui.Progress) error {
	if !p.Mod {
		return nil
	}
	options := modinstall.Options{
		Game: p.GameDir, Prefix: p.Prefix, Platform: p.Platform, Cache: p.modCache(),
		Pins: p.options.Pins, ModPins: p.options.ModPins,
		WineBin: p.options.WineBin, Runner: p.options.WineRunner,
		OverrideOnly: !p.ModOwned,
		// The plan owns the record: one write covers content, loader and override.
		SkipRecord: true,
	}
	client := p.options.Thunder
	if client == nil {
		client = thunderstore.NewClientFromEnv()
	}
	result, err := modinstall.Install(client, options, progress)
	if err != nil {
		return err
	}
	p.modResult = result
	// The override route the run took is the truth for the record: a Proton run
	// sets no prefix key at all and must not leave the plan's earlier guess behind.
	p.overrideVia = result.OverrideVia
	p.ModVersion = result.ModVersion
	p.BepInExVersion = result.BepInExVersion
	if result.LaunchOption != "" {
		option := result.LaunchOption
		p.LaunchOption = &option
	}
	state := result.State()
	p.ModStatus = &state
	return nil
}

// downloader holds the bytes a run fetched, and the staging folder it writes
// them into. Nothing reaches the game directory until the plan commits.
type downloader struct {
	plan     *Plan
	site     *site.Client
	staging  *content.Staging
	progress ui.Progress
	// levels are the fetched level files by game-relative target, so a level
	// several inputs named is taken from the site once.
	levels map[string][]byte
}

func prepareDownloads(built *Plan) (*downloader, error) {
	client := built.options.APIClient
	if client == nil {
		client = site.NewClientFromEnv()
	}
	staging, err := content.NewStaging(built.GameDir, stagingName)
	if err != nil {
		return nil, err
	}
	built.staging = staging
	return &downloader{plan: built, site: client, staging: staging, levels: map[string][]byte{}}, nil
}

// close throws away whatever is still staged; a committed run has nothing left.
func (d *downloader) close() {
	if d.staging != nil {
		_ = d.staging.Discard()
		d.staging = nil
	}
	if d.plan.staging != nil {
		_ = d.plan.staging.Discard()
		d.plan.staging = nil
	}
}

// fetchLevel takes the level file through the counting route, which is what
// counts the download.
func (d *downloader) fetchLevel(built *Plan, action Action) error {
	level := built.levelFor(action.LevelCode)
	if level == nil {
		return fail("no level %s in the plan", strconv.Quote(action.LevelCode))
	}
	target := levelTarget(level.filename())
	if level.source != "" {
		return d.staging.CopyIn("level:"+level.slug, target, level.source)
	}
	// One level file is taken from the site once, however many inputs named it.
	body, fetched := d.levels[target]
	if !fetched {
		if err := d.checkCancelled(); err != nil {
			return err
		}
		fresh, err := level.fetch(d.site)
		if err != nil {
			return err
		}
		d.levels[target] = fresh
		body = fresh
	}
	return d.staging.StageBytes("level:"+level.slug, target, body)
}

// checkCancelled stops a long fetch when the player asked the run to stop; the
// reporter is the only one who knows.
func (d *downloader) checkCancelled() error {
	if stopped(d.progress) {
		return ErrCancelled
	}
	return nil
}

// fetchImage puts a cover or biome picture under the name the loaders look up.
func (d *downloader) fetchImage(built *Plan, action Action) error {
	level := built.levelFor(action.LevelCode)
	if level == nil {
		return fail("no level %s in the plan", strconv.Quote(action.LevelCode))
	}
	for _, want := range level.images {
		if imageTarget(want.name) != action.Path {
			continue
		}
		if want.source != "" {
			return d.staging.CopyIn("level:"+level.slug, imageTarget(want.name), want.source)
		}
		body, err := d.site.DownloadFile(want.url)
		if err != nil {
			return err
		}
		return d.staging.StageBytes("level:"+level.slug, imageTarget(want.name), body)
	}
	return fail("no image %s in the plan", strconv.Quote(action.Path))
}

// fetchPack gets one pack archive and unpacks it into the staged tree.
func (d *downloader) fetchPack(built *Plan, action Action) error {
	body, err := d.site.DownloadPack(action.PackID, action.PackVer)
	if err != nil {
		if site.IsPackNotHosted(err) {
			built.Warnings = append(built.Warnings, err.Error())
			return nil
		}
		return err
	}
	archive, err := os.CreateTemp("", "megabonk-pack-*.zip")
	if err != nil {
		return err
	}
	name := archive.Name()
	defer os.Remove(name)
	if _, err := archive.Write(body); err != nil {
		archive.Close()
		return err
	}
	if err := archive.Close(); err != nil {
		return err
	}
	if _, err := d.staging.InstallPack(action.PackID, action.PackVer, name); err != nil {
		return err
	}
	return nil
}

// commit places every file the run staged, in the order the plan asked for them,
// and remembers what staged each one so the record can attribute them.
func (d *downloader) commit() ([]string, error) {
	d.plan.stagedOwners = d.staging.Owners()
	// Pack folders are cleared first, so a pack whose version changed never keeps
	// a bundle the old version left behind.
	for _, entry := range d.staging.PackResults() {
		if err := os.RemoveAll(toNativePath(ppath.Join(d.plan.GameDir, entry.Dir))); err != nil {
			return nil, fail("cannot clear %s: %s", entry.Dir, err.Error())
		}
	}
	names := d.orderedNames()
	placed := []string{}
	for _, name := range names {
		if err := copyIntoGame(d.plan.GameDir, d.staging.Dir, name); err != nil {
			return nil, err
		}
		placed = append(placed, name)
	}
	return placed, nil
}

// copyIntoGame puts one staged file where the game reads it.
func copyIntoGame(game, staging, name string) error {
	if !ppath.SafeRelative(name) {
		return fail("%s is not a safe path inside the game directory", strconv.Quote(name))
	}
	source := ppath.Join(staging, name)
	target := ppath.Join(game, name)
	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		return err
	}
	body, err := os.ReadFile(source)
	if err != nil {
		return err
	}
	return os.WriteFile(target, body, 0o644)
}

func readFileOrEmpty(path string) []byte {
	body, err := os.ReadFile(path)
	if err != nil {
		return nil
	}
	return body
}

// levelFor finds a resolved level by the code its action carries, which is the
// slug the plan labels it with.
func (p *Plan) levelFor(code string) *level {
	for _, candidate := range p.resolved {
		if candidate.slug == code || candidate.code == code || candidate.fileName == code {
			return candidate
		}
	}
	return nil
}

// writeRecord records what this run placed, keeping whatever an earlier run
// recorded.
func (p *Plan) writeRecord(placed []string, mod *modinstall.Result) error {
	record := content.LoadRecord(p.GameDir)
	if record == nil {
		record = &content.Record{Schema: content.RecordSchema}
	}
	record.Schema = content.RecordSchema
	record.GameDir = p.GameDir
	record.InstalledAt = time.Now().UTC().Format(time.RFC3339)
	// Steam's own appmanifest says which build is installed; the record notes what
	// was running when this install was made.
	if build := steam.InstalledBuildID(p.GameDir); build != "" {
		record.GameBuildID = build
		installed := build
		record.InstalledGameBuildID = &installed
	}
	levels := map[string]content.LevelRecord{}
	for code, entry := range record.Levels {
		levels[code] = entry
	}
	packs := map[string]content.PackRecord{}
	for id, entry := range record.Packs {
		packs[id] = entry
	}
	// What each file belongs to comes from the staged tree, so the record and the
	// files that landed agree on which level or pack a file came from.
	for _, relative := range placed {
		switch owner := p.owner(relative); {
		case strings.HasPrefix(owner, "level:"):
			recordLevel(levels, strings.TrimPrefix(owner, "level:"), relative)
		case strings.HasPrefix(owner, "pack:"):
			recordPack(packs, p, strings.TrimPrefix(owner, "pack:"), relative)
		default:
			if !contains(record.Files, relative) {
				record.Files = append(record.Files, relative)
			}
		}
	}
	record.Levels = levels
	record.Packs = packs
	if mod != nil {
		record.ModVersion = mod.ModVersion
		record.BepinexVersion = mod.BepInExVersion
	}
	// What the record says about the override comes from the run that made it, so a
	// Proton install keeps no Wine-shaped key it never wrote.
	switch {
	case mod != nil && mod.OverrideApplied:
		prefix, via := p.Prefix, mod.OverrideVia
		if mod.Prefix != "" {
			prefix = mod.Prefix
		}
		record.DllOverride = &content.DllOverride{
			Applied: true, Name: proton.WinHTTPDLLName, Value: proton.WinHTTPValue,
			Prefix: &prefix, Via: &via,
		}
	case mod != nil:
		record.DllOverride = nil
	case p.overrideVia != "":
		prefix, via := p.Prefix, p.overrideVia
		record.DllOverride = &content.DllOverride{
			Applied: true, Name: proton.WinHTTPDLLName, Value: proton.WinHTTPValue,
			Prefix: &prefix, Via: &via,
		}
	}
	_, err := content.SaveRecord(p.GameDir, record)
	return err
}

// owner is what staged a placed file.
func (p *Plan) owner(name string) string {
	if p.stagedOwners == nil {
		return ""
	}
	return p.stagedOwners[name]
}

// packVersion is the version the plan installs a pack at.
func (p *Plan) packVersion(packID string) string {
	for _, action := range p.Actions {
		if action.Kind == KindInstallPack && action.PackID == packID {
			return action.PackVer
		}
	}
	return ""
}

// recordPack notes one file of a pack, keeping the version the plan installs.
func recordPack(packs map[string]content.PackRecord, p *Plan, packID, name string) {
	entry := packs[packID]
	files := append([]string{}, entry.Files...)
	if !contains(files, name) {
		files = append(files, name)
	}
	entry.Files = files
	entry.Dir = ppath.Parent(name)
	if version := p.packVersion(packID); version != "" {
		entry.Version = version
	}
	packs[packID] = entry
}

func recordLevel(levels map[string]content.LevelRecord, code, name string) {
	entry := levels[code]
	if entry.Code == "" {
		entry.Code = code
	}
	switch ppath.Name(name) {
	case content.CoverFor(code):
		entry.Cover = name
	case content.BiomeFor(code):
		entry.Biome = name
	default:
		entry.Filename = name
	}
	levels[code] = entry
}

func contains(items []string, wanted string) bool {
	for _, item := range items {
		if item == wanted {
			return true
		}
	}
	return false
}

// Uninstall removes exactly what the installer recorded placing; a folder with no
// record is left alone, so another tool's files and the player's own survive.
func Uninstall(game string, progress ui.Progress) ([]string, error) {
	game = ppath.Normalize(game)
	record := content.LoadRecord(game)
	if record == nil {
		return nil, nil
	}
	if progress != nil {
		progress.Start(2, "uninstall Megabonk Levels")
	}
	if stopped(progress) {
		return nil, ErrCancelled
	}
	removed, err := content.UninstallRecorded(game, record)
	if progress != nil {
		progress.Step("levels, packs and mod files")
	}
	if err != nil {
		return removed, err
	}
	if stopped(progress) {
		// A stopped run keeps the record even though the removal pass cleared it, so
		// a rerun still knows the prefix and the parked proxy it has to clear.
		if _, err := content.SaveRecord(game, record); err != nil {
			return removed, err
		}
		return removed, ErrCancelled
	}
	clearRecordOverride(game, record)
	if progress != nil {
		progress.Step("winhttp override")
		progress.Finish("uninstalled", true)
	}
	return removed, nil
}

// clearRecordOverride drops the prefix edit the record says this installer made.
func clearRecordOverride(game string, record *content.Record) {
	if record.DllOverride == nil || !record.DllOverride.Applied {
		return
	}
	prefix := game
	if record.DllOverride.Prefix != nil && *record.DllOverride.Prefix != "" {
		prefix = *record.DllOverride.Prefix
	}
	proton.ClearWinHTTPOverride(prefix, "", nil)
}

// melonloaderVersion is the loader version named in the refusal for a build the
// installer will not touch.
const melonloaderVersion = "0.7.3"

// downloadInput is what names the level to the site: its share code when the
// record carried one, and its stored file name otherwise.
func (l *level) downloadInput() string {
	if l.code != "" {
		return l.code
	}
	return l.fileName
}

// fetch takes the level file through the counting route, which is what counts the
// download.
func (l *level) fetch(client *site.Client) ([]byte, error) {
	if l.code != "" {
		return client.DownloadLevel(l.code)
	}
	found, err := client.LookupLevelByFilename(l.fileName)
	if err != nil {
		return nil, err
	}
	return found.Download()
}

// downloadURL is where a hosted level file is served, which is what a plan lists
// as the source of its fetch step.
func (l *level) downloadURL(options Options) string {
	client := options.APIClient
	if client == nil {
		client = site.NewClientFromEnv()
	}
	return client.BaseURL() + fmt.Sprintf(site.LevelDownloadSuffix,
		url.PathEscape(siteCode(options, l)))
}

// siteCode is the share code a level is fetched with, worked out from its stored
// file name when the record did not carry one.
func siteCode(options Options, l *level) string {
	if l.code != "" {
		return l.code
	}
	client := options.APIClient
	if client == nil {
		client = site.NewClientFromEnv()
	}
	if found, err := client.LookupLevelByFilename(l.fileName); err == nil && found.Code != "" {
		return found.Code
	}
	return l.fileName
}

// toNativePath turns a game-relative name into a path the OS understands.
func toNativePath(path string) string { return filepath.FromSlash(path) }

// modSteps counts the steps the mod half of a run reports.
func modSteps(built *Plan) int {
	if !built.Mod {
		return 0
	}
	if built.ModOwned {
		return modinstall.PlannedStepCount
	}
	return modinstall.OverrideOnlyStepCount
}

// fetchSteps counts what the run takes out of the site: level files, images and
// pack archives.
func fetchSteps(built *Plan) int {
	total := 0
	for _, action := range built.Actions {
		if fetchKind(action.Kind) {
			total++
		}
	}
	return total
}

// placeSteps counts what the run puts into the game directory. A pack counts as
// the one step the player sees for it, which is what commit reports.
func placeSteps(built *Plan) int {
	total := 0
	for _, action := range built.Actions {
		if installKind(action.Kind) {
			total++
		}
	}
	return total
}

// fetchKind reports whether an action takes bytes out of the site.
func fetchKind(kind string) bool {
	return kind == KindFetchLevel || kind == KindFetchImage || kind == KindFetchPack
}

// reporterFor hands the mod half the caller's reporter. A run that reports
// nothing needs nothing reported.
func reporterFor(progress ui.Progress) ui.Progress {
	if progress == nil {
		return nil
	}
	return progress
}

// levelTarget is the game-relative name a level file is placed under.
func levelTarget(name string) string {
	return ppath.Join(content.UserData, content.LevelsDir, name)
}

// imageTarget is the game-relative name a level's picture is placed under.
func imageTarget(name string) string {
	return ppath.Join(content.UserData, content.LevelsDir, name)
}

// packTarget is the game-relative folder a pack is placed under.
func packTarget(packID string) string {
	return ppath.Join(content.UserData, content.LevelPacksDir, packID)
}

// installKind reports whether an action is one of the placement steps.
func installKind(kind string) bool {
	return kind == KindInstallLevel || kind == KindInstallImage || kind == KindInstallPack
}

// covers reports whether the committed files include what a placement step
// promised: one file for a level or image, the whole folder for a pack.
func covers(committed []string, action Action) bool {
	for _, name := range committed {
		if name == action.Path || strings.HasPrefix(name, action.Path+"/") {
			return true
		}
	}
	return false
}

// plannedFile reports whether a fetch step named this game-relative file.
func plannedFetch(actions []Action, name string) bool {
	for _, action := range actions {
		if (action.Kind == KindFetchLevel || action.Kind == KindFetchImage) && action.Path == name {
			return true
		}
	}
	return false
}

// orderedNames are the staged files in the order the plan asked for them, so the
// level of a shared file is the level the player listed first.
func (d *downloader) orderedNames() []string {
	pending := map[string]bool{}
	for _, name := range d.staging.Staged() {
		pending[name] = true
	}
	ordered := []string{}
	take := func(name string) {
		if pending[name] {
			ordered = append(ordered, name)
			delete(pending, name)
		}
	}
	for _, action := range d.plan.Actions {
		switch action.Kind {
		case KindInstallLevel, KindInstallImage:
			take(action.Path)
		case KindInstallPack:
			for _, name := range d.staging.Staged() {
				if strings.HasPrefix(name, action.Path+"/") {
					take(name)
				}
			}
		}
	}
	for _, name := range d.staging.Staged() {
		take(name)
	}
	return ordered
}

// modCache is where this run keeps the mod and loader archives, in a folder of
// its own rather than one an earlier run may have filled.
func (p *Plan) modCache() string {
	if p.options.Cache == "" {
		return ""
	}
	return ppath.Join(p.options.Cache, "install")
}

// writesLevelFile says whether the run has a level file to place: a hosted one
// is downloaded, and a local one is read from disk.
func (l *level) writesLevelFile() bool { return l.hosted || l.source != "" }

// wants reports whether this run still has to write one of the level's files:
// the level file itself, or one of its pictures under the name the loader reads.
func (l *level) wants(game string, record *content.Record, name string) bool {
	if name == levelTarget(l.filename()) {
		return l.writesLevelFile()
	}
	for _, want := range l.images {
		if imageTarget(want.name) != name {
			continue
		}
		if want.source != "" {
			return true
		}
		if want.url == "" {
			return false
		}
		return !pictureInstalled(game, record, l.slug, want.name)
	}
	return false
}

// pictureInstalled reports whether the game already holds a level's picture under
// the name its loader reads, as the record says and as the disk confirms.
func pictureInstalled(game string, record *content.Record, slug, name string) bool {
	if record == nil {
		return false
	}
	entry, found := record.Levels[slug]
	if !found {
		return false
	}
	current := entry.Cover
	if name == content.BiomeFor(slug) {
		current = entry.Biome
	}
	return current == imageTarget(name) && ppath.IsFile(ppath.Join(game, imageTarget(name)))
}
