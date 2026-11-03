// Package content is where the installer's files live inside the game, what it
// validates before copying, and the record it leaves behind.
//
// The game reads player levels from UserData/Levels and asset packs from
// UserData/LevelPacks/<id>/ (docs/asset-bundles.md). The record file is what
// makes uninstall safe: it names exactly what this installer placed, so nothing
// of the player's own is touched.
package content

import (
	"bytes"
	"encoding/json"
	"os"
	"regexp"
	"sort"
	"strconv"
	"strings"

	"github.com/pythoninthegrass/megabonk_mods/installer/internal/jsonx"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ppath"
)

const (
	// UserData is the game's user tree, relative to the game directory.
	UserData = "UserData"
	// LevelsDir is the folder player levels are read from.
	LevelsDir = "Levels"
	// LevelPacksDir is the folder asset packs are read from.
	LevelPacksDir = "LevelPacks"
	// RuntimeSubdir holds the private .NET 6 runtime.
	RuntimeSubdir = "dotnet6-win"
	// RecordName is the install record, the contract uninstall reads.
	RecordName = "MegabonkLevels.installer.json"
	// LoaderDir is MelonLoader's directory.
	LoaderDir = "MelonLoader"
	// ModsDir holds the mod assemblies.
	ModsDir = "Mods"
	// UserLibsDir holds extra assemblies the game probes early.
	UserLibsDir = "UserLibs"
	// VersionMarkerName records the MelonLoader version already installed.
	VersionMarkerName = "MegabonkLevels.melonloader_version"
	manifestName      = "manifest.json"
	attachmentsName   = "attachments.json"
	// AttachmentsSchema is the only attachments sidecar document the game reads.
	AttachmentsSchema = "pack-attachments/1"
	prefabSuffix      = ".bundle"
	// MaxFileBytes is the largest file the installer will copy.
	MaxFileBytes = 256 * 1024 * 1024
	// RecordSchema is the install record's own schema tag.
	RecordSchema = "megabonk-levels-install/1"
)

// LevelSuffixes are the file extensions a player level may carry.
var LevelSuffixes = []string{".mblevel.json", ".level.json"}

var packIDPattern = regexp.MustCompile(`^[a-z0-9][a-z0-9._-]*$`)

var requiredManifestFields = []string{"id", "name", "author", "version"}

// Runtime is the record's entry for the private .NET runtime.
type Runtime struct {
	Mode         string  `json:"mode"`
	Path         string  `json:"path"`
	Version      string  `json:"version"`
	LaunchOption *string `json:"launch_option"`
}

// DllOverride is the record's entry for the Wine version.dll override.
type DllOverride struct {
	Applied bool    `json:"applied"`
	Name    string  `json:"name"`
	Value   string  `json:"value"`
	Prefix  *string `json:"prefix"`
	Via     *string `json:"via"`
}

// PackEntry is what the installer placed for one asset pack.
type PackEntry struct {
	Files []string `json:"files"`
	Dir   string   `json:"dir"`
}

// Record is MegabonkLevels.installer.json: exactly what this installer placed,
// so uninstall can remove it and nothing else.
type Record struct {
	Schema             string               `json:"schema"`
	PackageID          string               `json:"package_id"`
	ModVersion         string               `json:"mod_version"`
	MelonloaderVersion string               `json:"melonloader_version"`
	GameBuildID        string               `json:"game_buildid"`
	InstalledAt        string               `json:"installed_at"`
	GameDir            string               `json:"game_dir"`
	Files              []string             `json:"files"`
	Levels             []string             `json:"levels"`
	Packs              map[string]PackEntry `json:"packs"`
	Runtime            *Runtime             `json:"runtime"`
	DllOverride        *DllOverride         `json:"dll_override"`
}

// UserDataDir is the game's UserData directory.
func UserDataDir(gameDir string) string { return ppath.Join(gameDir, UserData) }

// LevelsPath is the directory player levels are read from.
func LevelsPath(gameDir string) string { return ppath.Join(UserDataDir(gameDir), LevelsDir) }

// LevelPacksPath is the directory asset packs are read from.
func LevelPacksPath(gameDir string) string { return ppath.Join(UserDataDir(gameDir), LevelPacksDir) }

// PackDest is where a pack id lands.
func PackDest(gameDir, packID string) string { return ppath.Join(LevelPacksPath(gameDir), packID) }

// RuntimePath is the private runtime directory.
func RuntimePath(gameDir string) string { return ppath.Join(gameDir, RuntimeSubdir) }

// VersionMarkerPath is the file recording the installed MelonLoader version.
func VersionMarkerPath(gameDir string) string {
	return ppath.Join(gameDir, LoaderDir, VersionMarkerName)
}

// RecordFilePath is the install record.
func RecordFilePath(gameDir string) string { return ppath.Join(gameDir, RecordName) }

// LoadRecord reads the install record, or nil when there is nothing readable: a
// missing, unreadable, malformed, or non-object record all mean "no install".
// Fields are read leniently so a record written by another version still loads.
func LoadRecord(gameDir string) *Record {
	path := RecordFilePath(gameDir)
	if !ppath.IsFile(path) {
		return nil
	}
	text, err := ppath.ReadText(path)
	if err != nil {
		return nil
	}
	value, err := jsonx.Decode(text)
	if err != nil {
		return nil
	}
	fields, ok := jsonx.AsMap(value)
	if !ok {
		return nil
	}
	record := &Record{
		Schema:             stringField(fields, "schema"),
		PackageID:          stringField(fields, "package_id"),
		ModVersion:         stringField(fields, "mod_version"),
		MelonloaderVersion: stringField(fields, "melonloader_version"),
		GameBuildID:        stringField(fields, "game_buildid"),
		InstalledAt:        stringField(fields, "installed_at"),
		GameDir:            stringField(fields, "game_dir"),
		Files:              stringListField(fields, "files"),
		Levels:             stringListField(fields, "levels"),
	}
	if entries, ok := jsonx.AsMap(fields["packs"]); ok {
		record.Packs = map[string]PackEntry{}
		for name, raw := range entries {
			entry, ok := jsonx.AsMap(raw)
			if !ok {
				entry = map[string]any{}
			}
			record.Packs[name] = PackEntry{
				Files: stringListField(entry, "files"),
				Dir:   stringField(entry, "dir"),
			}
		}
	}
	if runtime, ok := jsonx.AsMap(fields["runtime"]); ok && len(runtime) > 0 {
		record.Runtime = &Runtime{
			Mode:    stringField(runtime, "mode"),
			Path:    stringField(runtime, "path"),
			Version: stringField(runtime, "version"),
		}
		if value, found := runtime["launch_option"]; found && value != nil {
			launchOption := jsonx.Text(value)
			record.Runtime.LaunchOption = &launchOption
		}
	}
	if override, ok := jsonx.AsMap(fields["dll_override"]); ok && len(override) > 0 {
		record.DllOverride = &DllOverride{
			Applied: jsonx.Truthy(override["applied"]),
			Name:    stringField(override, "name"),
			Value:   stringField(override, "value"),
		}
		for _, pair := range []struct {
			key   string
			field **string
		}{
			{"prefix", &record.DllOverride.Prefix},
			{"via", &record.DllOverride.Via},
		} {
			if value, found := override[pair.key]; found && value != nil {
				text := jsonx.Text(value)
				*pair.field = &text
			}
		}
	}
	return record
}

func stringField(fields map[string]any, key string) string {
	value, found := fields[key]
	if !found || value == nil {
		return ""
	}
	if text, ok := value.(string); ok {
		return text
	}
	return jsonx.Text(value)
}

func stringListField(fields map[string]any, key string) []string {
	items, ok := jsonx.AsList(fields[key])
	if !ok {
		return nil
	}
	texts := make([]string, 0, len(items))
	for _, item := range items {
		if text, ok := item.(string); ok {
			texts = append(texts, text)
			continue
		}
		if item != nil {
			texts = append(texts, jsonx.Text(item))
		}
	}
	return texts
}

// SaveRecord writes the install record with two-space indent, sorted keys, and
// a trailing newline, then returns the path.
func SaveRecord(gameDir string, record *Record) (string, error) {
	path := RecordFilePath(gameDir)
	if err := os.MkdirAll(ppath.Parent(path), 0o755); err != nil {
		return "", err
	}
	var buffer bytes.Buffer
	encoder := json.NewEncoder(&buffer)
	encoder.SetEscapeHTML(false)
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(record); err != nil {
		return "", err
	}
	if err := os.WriteFile(path, buffer.Bytes(), 0o644); err != nil {
		return "", err
	}
	return path, nil
}

// ClearRecord removes the install record, ignoring a missing file.
func ClearRecord(gameDir string) error {
	err := os.Remove(RecordFilePath(gameDir))
	if err != nil && !os.IsNotExist(err) {
		return err
	}
	return nil
}

// InstalledLoaderVersion is the version the marker file names, or "" when there
// is no marker.
func InstalledLoaderVersion(gameDir string) string {
	marker := VersionMarkerPath(gameDir)
	if !ppath.IsFile(marker) {
		return ""
	}
	text, err := ppath.ReadTextReplace(marker)
	if err != nil {
		return ""
	}
	return strings.TrimSpace(text)
}

// HasInstalledLoaderVersion tells the two states InstalledLoaderVersion
// collapses: a marker that exists but is blank still counts as installed.
func HasInstalledLoaderVersion(gameDir string) bool {
	return ppath.IsFile(VersionMarkerPath(gameDir))
}

// IsBundleName reports whether a file in a pack directory is a bundle. Pack
// bundles are built without an extension; .bundle is the explicit form
// (pack_catalog.cs).
func IsBundleName(name string) bool {
	suffix := ppath.Ext(name)
	return suffix == "" || suffix == prefabSuffix
}

// PackFiles is the manifest, the optional attachments sidecar, and the bundles
// that make up a pack, in the order the reference returns them.
func PackFiles(source string) []string {
	if !ppath.IsDir(source) {
		return nil
	}
	var files []string
	for _, name := range []string{manifestName, attachmentsName} {
		candidate := ppath.Join(source, name)
		if ppath.IsFile(candidate) {
			files = append(files, candidate)
		}
	}
	var bundles []string
	for _, name := range readDirNames(source) {
		child := ppath.Join(source, name)
		if !ppath.IsFile(child) || !IsBundleName(name) || contains(files, child) {
			continue
		}
		bundles = append(bundles, child)
	}
	sort.Strings(bundles)
	return append(files, bundles...)
}

func contains(items []string, wanted string) bool {
	for _, item := range items {
		if item == wanted {
			return true
		}
	}
	return false
}

func readDirNames(dir string) []string {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil
	}
	names := make([]string, 0, len(entries))
	for _, entry := range entries {
		names = append(names, entry.Name())
	}
	return names
}

// ValidateLevelFile is what a level file must satisfy to be worth installing.
func ValidateLevelFile(path string) []string {
	if !ppath.Exists(path) {
		return []string{path + ": no such file"}
	}
	if !ppath.IsFile(path) {
		return []string{path + ": not a file"}
	}
	name := ppath.Name(path)
	var problems []string
	if !hasAnySuffix(name, LevelSuffixes) {
		problems = append(problems, name+": expected a "+LevelSuffixes[0]+" file")
	}
	if info, err := os.Stat(path); err == nil && info.Size() > MaxFileBytes {
		problems = append(problems, name+": larger than the 256MB limit")
	}
	text, err := ppath.ReadText(path)
	if err != nil {
		return append(problems, name+": cannot be read as text: "+err.Error())
	}
	payload, err := jsonx.Decode(text)
	if err != nil {
		return append(problems, name+": invalid JSON: "+err.Error())
	}
	if _, ok := jsonx.AsMap(payload); !ok {
		problems = append(problems, name+": the top level must be a JSON object")
	} else if schema, found := payload.(map[string]any)["schema"]; found && !jsonx.IsInt(schema) {
		problems = append(problems, name+": 'schema' must be an integer")
	}
	return problems
}

func hasAnySuffix(name string, suffixes []string) bool {
	for _, suffix := range suffixes {
		if strings.HasSuffix(name, suffix) {
			return true
		}
	}
	return false
}

// ValidatePackSource checks a pack directory the way the game will, so a broken
// pack never reaches the Warehouse.
func ValidatePackSource(source string) []string {
	if !ppath.Exists(source) {
		return []string{source + ": no such directory"}
	}
	if !ppath.IsDir(source) {
		return []string{source + ": not a directory"}
	}
	var problems []string
	packID := ppath.Name(source)
	manifestPath := ppath.Join(source, manifestName)
	if !ppath.IsFile(manifestPath) {
		problems = append(problems, source+"/"+manifestName+": a pack directory needs a "+manifestName)
	} else {
		text, err := ppath.ReadText(manifestPath)
		if err != nil {
			return append(problems, manifestName+": "+err.Error())
		}
		value, err := jsonx.Decode(text)
		if err != nil {
			return append(problems, manifestName+": "+err.Error())
		}
		manifest, ok := jsonx.AsMap(value)
		if !ok {
			return append(problems, manifestName+": the top level must be a JSON object")
		}
		for _, field := range requiredManifestFields {
			if !jsonx.IsNonBlankString(manifest[field]) {
				problems = append(problems, manifestName+": missing required string field '"+field+"'")
			}
		}
		if !jsonx.IsStringList(manifest["assets"]) {
			problems = append(problems, manifestName+": missing required array field 'assets'")
		}
		if declared, ok := manifest["id"].(string); ok && strings.TrimSpace(declared) != "" && strings.TrimSpace(declared) != packID {
			problems = append(problems, manifestName+": manifest id '"+declared+"' does not match its pack folder '"+packID+"'")
		}
		if attachments, found := manifest["attachments"]; found && attachments != nil && !jsonx.IsString(attachments) {
			problems = append(problems, manifestName+": 'attachments' must be a string when present")
		}
	}

	if !packIDPattern.MatchString(packID) {
		problems = append(problems, "pack folder name '"+packID+"': use a lowercase id of a-z, 0-9, '.', '_' or '-'")
	}

	if len(bundlesIn(source)) == 0 {
		problems = append(problems, source+": no AssetBundle file — expected the bundle named after the pack id (or a .bundle file)")
	}

	sidecar := ppath.Join(source, attachmentsName)
	if ppath.IsFile(sidecar) {
		text, err := ppath.ReadText(sidecar)
		if err != nil {
			problems = append(problems, attachmentsName+": "+err.Error())
		} else if payload, err := jsonx.Decode(text); err != nil {
			problems = append(problems, attachmentsName+": "+err.Error())
		} else {
			document, ok := jsonx.AsMap(payload)
			if !ok || document["schema"] != AttachmentsSchema {
				problems = append(problems, attachmentsName+": expected a "+AttachmentsSchema+" document")
			}
		}
	}

	for _, relative := range oversizedFiles(source) {
		problems = append(problems, relative+": larger than the 256MB limit")
	}
	return problems
}

// bundlesIn mirrors the reference's two-pass search: .bundle files if any,
// otherwise extension-less files that are not the manifest or its sidecar.
func bundlesIn(source string) []string {
	names := readDirNames(source)
	var bundles []string
	for _, name := range names {
		child := ppath.Join(source, name)
		if ppath.IsFile(child) && IsBundleName(name) && ppath.Ext(name) == prefabSuffix {
			bundles = append(bundles, child)
		}
	}
	if len(bundles) > 0 {
		return bundles
	}
	for _, name := range names {
		child := ppath.Join(source, name)
		if !ppath.IsFile(child) || ppath.Ext(name) != "" {
			continue
		}
		if name == manifestName || name == attachmentsName {
			continue
		}
		bundles = append(bundles, child)
	}
	return bundles
}

func oversizedFiles(source string) []string {
	var relatives []string
	entries, err := os.ReadDir(source)
	if err != nil {
		return nil
	}
	for _, entry := range entries {
		child := ppath.Join(source, entry.Name())
		if entry.IsDir() {
			for _, nested := range oversizedFiles(child) {
				relatives = append(relatives, entry.Name()+"/"+nested)
			}
			continue
		}
		if info, err := os.Stat(child); err == nil && info.Size() > MaxFileBytes {
			relatives = append(relatives, entry.Name())
		}
	}
	sort.Strings(relatives)
	return relatives
}

// DescribeRecord is the human-readable description of an install record that
// --check and uninstall print.
func DescribeRecord(record *Record) []string {
	if record == nil {
		record = &Record{}
	}
	lines := []string{
		"package " + orDefault(record.PackageID, "unknown"),
		"mod " + orDefault(record.ModVersion, "?") + " / MelonLoader " + orDefault(record.MelonloaderVersion, "?"),
	}
	if record.InstalledAt != "" {
		lines = append(lines, "installed "+record.InstalledAt)
	}
	if runtime := record.Runtime; runtime != nil && (runtime.Mode != "" || runtime.Path != "" || runtime.Version != "" || runtime.LaunchOption != nil) {
		lines = append(lines, ".NET "+orDefault(runtime.Version, "?")+" in "+orDefault(runtime.Mode, "?")+
			" at "+orDefault(runtime.Path, "?"))
	}
	if override := record.DllOverride; override != nil {
		if override.Applied {
			lines = append(lines, "version.dll override: "+orDefault(override.Value, "?")+" via "+orDefault(deref(override.Via), "unknown"))
		} else {
			lines = append(lines, "version.dll override: not set")
		}
	}
	lines = append(lines, strconv.Itoa(len(record.Files))+" mod file(s)")
	if len(record.Packs) > 0 {
		names := make([]string, 0, len(record.Packs))
		for name := range record.Packs {
			names = append(names, name)
		}
		sort.Strings(names)
		lines = append(lines, "packs: "+strings.Join(names, ", "))
	}
	if len(record.Levels) > 0 {
		lines = append(lines, strconv.Itoa(len(record.Levels))+" level file(s)")
	}
	return lines
}

func orDefault(value, fallback string) string {
	if value == "" {
		return fallback
	}
	return value
}

func deref(value *string) string {
	if value == nil {
		return ""
	}
	return *value
}
