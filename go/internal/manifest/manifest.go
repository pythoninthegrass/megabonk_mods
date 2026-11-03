// Package manifest reads the install package's manifest: what the player
// downloaded, and the proof that it is intact. One JSON document at the package
// root names the vendor archives and mod files with a sha256 each, so a
// truncated or tampered download is caught before anything touches the game.
package manifest

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"regexp"
	"sort"
	"strconv"
	"strings"

	"github.com/pythoninthegrass/megabonk_mods/installer/internal/jsonx"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ppath"
)

const (
	// PackageSchema is the only manifest schema this installer understands.
	PackageSchema = "megabonk-player-package/1"
	// VendorDir holds the vendor archives beside the manifest.
	VendorDir    = "vendor"
	manifestName = "manifest.json"
)

var hex64 = regexp.MustCompile(`^[0-9a-f]{64}$`)

var requiredTopLevel = []string{
	"schema",
	"platform",
	"package_id",
	"mod_version",
	"melonloader_version",
	"game_buildid",
	"generated",
	"verified_on",
	"vendors",
	"files",
}

var requiredVendorKeys = []string{"name", "url", "sha256", "kind", "version"}
var requiredFileKeys = []string{"path", "sha256", "dest"}

// Error is a manifest that is missing, malformed, or not one this installer can
// use. The wording is the contract the parity harness anchors on.
type Error struct{ message string }

func (e *Error) Error() string { return e.message }

func fail(format string, args ...any) error {
	return &Error{message: fmt.Sprintf(format, args...)}
}

// Vendor is one third-party archive the package ships.
type Vendor struct {
	Name    string `json:"name"`
	URL     string `json:"url"`
	SHA256  string `json:"sha256"`
	Kind    string `json:"kind"`
	Version string `json:"version"`
}

// Path is where the archive sits inside the package.
func (v Vendor) Path(packageRoot string) string {
	return ppath.Join(packageRoot, VendorDir, v.Name)
}

// FileEntry is one file the installer copies into the game directory.
type FileEntry struct {
	Path   string `json:"path"`
	SHA256 string `json:"sha256"`
	Dest   string `json:"dest"`
}

// Source is where the file sits inside the package.
func (f FileEntry) Source(packageRoot string) string {
	return ppath.Join(packageRoot, f.Path)
}

// Target is where the file lands in the game directory.
func (f FileEntry) Target(gameDir string) string {
	return ppath.Join(gameDir, f.Dest)
}

// Package is a validated manifest. Field order is the order manifest.json
// writes them back out.
type Package struct {
	Schema             string      `json:"schema"`
	Platform           string      `json:"platform"`
	PackageID          string      `json:"package_id"`
	ModVersion         string      `json:"mod_version"`
	MelonloaderVersion string      `json:"melonloader_version"`
	GameBuildID        string      `json:"game_buildid"`
	Generated          string      `json:"generated"`
	VerifiedOn         []any       `json:"verified_on"`
	Vendors            []Vendor    `json:"vendors"`
	Files              []FileEntry `json:"files"`
}

// Label is the one-line description the installer prints.
func (p *Package) Label() string {
	return "MegabonkLevels " + p.ModVersion + " (MelonLoader " + p.MelonloaderVersion + ")"
}

// Vendor returns the archive of a kind, or an Error naming the missing kind.
func (p *Package) Vendor(kind string) (Vendor, error) {
	for _, vendor := range p.Vendors {
		if vendor.Kind == kind {
			return vendor, nil
		}
	}
	return Vendor{}, fail("the package has no %s component", strconv.Quote(kind))
}

// FromDoc validates a decoded manifest document.
func FromDoc(document any) (*Package, error) {
	root, ok := jsonx.AsMap(document)
	if !ok {
		return nil, fail("the package manifest is not a JSON object")
	}
	for _, key := range requiredTopLevel {
		if _, found := root[key]; !found {
			return nil, fail("the package manifest is missing '%s'", key)
		}
	}
	if text, ok := root["schema"].(string); !ok || text != PackageSchema {
		return nil, fail("unrecognised package manifest schema %s (this installer understands %s)",
			strconv.Quote(jsonx.Text(root["schema"])), strconv.Quote(PackageSchema))
	}
	platform, ok := root["platform"].(string)
	if !ok || platform != "linux" {
		return nil, fail("this package is for %s; the Linux installer needs a linux package",
			strconv.Quote(jsonx.Text(root["platform"])))
	}
	vendors, err := vendorsFrom(root)
	if err != nil {
		return nil, err
	}
	files, err := filesFrom(root)
	if err != nil {
		return nil, err
	}
	verified, _ := jsonx.AsList(root["verified_on"])
	if verified == nil {
		verified = []any{}
	}
	return &Package{
		Schema:             jsonx.Text(root["schema"]),
		Platform:           platform,
		PackageID:          jsonx.Text(root["package_id"]),
		ModVersion:         jsonx.Text(root["mod_version"]),
		MelonloaderVersion: jsonx.Text(root["melonloader_version"]),
		GameBuildID:        jsonx.Text(root["game_buildid"]),
		Generated:          jsonx.Text(root["generated"]),
		VerifiedOn:         verified,
		Vendors:            vendors,
		Files:              files,
	}, nil
}

func vendorsFrom(root map[string]any) ([]Vendor, error) {
	entries, err := listField(root, "vendors")
	if err != nil {
		return nil, err
	}
	vendors := make([]Vendor, 0, len(entries))
	for index, entry := range entries {
		what := "vendor entry " + strconv.Itoa(index)
		values, err := requireFields(entry, requiredVendorKeys, what)
		if err != nil {
			return nil, err
		}
		if extra := extraFields(entry, requiredVendorKeys); len(extra) > 0 {
			return nil, fail("%s has unknown field(s): %s", what, strings.Join(extra, ", "))
		}
		digest := strings.ToLower(jsonx.Text(values["sha256"]))
		if !hex64.MatchString(digest) {
			return nil, fail("%s (%s): sha256 is not 64 hex characters", what, jsonx.Text(values["name"]))
		}
		vendors = append(vendors, Vendor{
			Name:    jsonx.Text(values["name"]),
			URL:     jsonx.Text(values["url"]),
			SHA256:  digest,
			Kind:    jsonx.Text(values["kind"]),
			Version: jsonx.Text(values["version"]),
		})
	}
	kinds := map[string]bool{}
	for _, vendor := range vendors {
		kinds[vendor.Kind] = true
	}
	for _, required := range []string{"melonloader", "dotnet"} {
		if !kinds[required] {
			return nil, fail("the package manifest lists no %s component", strconv.Quote(required))
		}
	}
	return vendors, nil
}

func filesFrom(root map[string]any) ([]FileEntry, error) {
	entries, err := listField(root, "files")
	if err != nil {
		return nil, err
	}
	files := make([]FileEntry, 0, len(entries))
	for index, entry := range entries {
		what := "file entry " + strconv.Itoa(index)
		values, err := requireFields(entry, requiredFileKeys, what)
		if err != nil {
			return nil, err
		}
		if extra := extraFields(entry, requiredFileKeys); len(extra) > 0 {
			return nil, fail("%s has unknown field(s): %s", what, strings.Join(extra, ", "))
		}
		digest := strings.ToLower(jsonx.Text(values["sha256"]))
		if !hex64.MatchString(digest) {
			return nil, fail("%s (%s): sha256 is not 64 hex characters", what, jsonx.Text(values["path"]))
		}
		relative, err := safeRelative(jsonx.Text(values["path"]), what)
		if err != nil {
			return nil, err
		}
		dest, err := safeRelative(jsonx.Text(values["dest"]), what)
		if err != nil {
			return nil, err
		}
		files = append(files, FileEntry{Path: relative, SHA256: digest, Dest: dest})
	}
	if len(files) == 0 {
		return nil, fail("the package manifest lists no files to install")
	}
	return files, nil
}

func requireFields(entry any, keys []string, what string) (map[string]any, error) {
	object, ok := jsonx.AsMap(entry)
	if !ok {
		return nil, fail("%s is not a JSON object", what)
	}
	values := map[string]any{}
	for _, key := range keys {
		value, found := object[key]
		if !found {
			return nil, fail("%s is missing '%s'", what, key)
		}
		values[key] = value
	}
	return values, nil
}

func extraFields(entry any, keys []string) []string {
	object, ok := jsonx.AsMap(entry)
	if !ok {
		return nil
	}
	var extra []string
	for key := range object {
		known := false
		for _, wanted := range keys {
			if key == wanted {
				known = true
				break
			}
		}
		if !known {
			extra = append(extra, key)
		}
	}
	sort.Strings(extra)
	return extra
}

func safeRelative(value, what string) (string, error) {
	normalised := strings.ReplaceAll(value, `\`, "/")
	if normalised == "" || strings.HasPrefix(normalised, "/") || containsComponent(normalised, "..") {
		return "", fail("%s: unsafe path %s", what, strconv.Quote(value))
	}
	return normalised, nil
}

func containsComponent(path, wanted string) bool {
	for _, part := range strings.Split(path, "/") {
		if part == wanted {
			return true
		}
	}
	return false
}

func listField(object map[string]any, key string) ([]any, error) {
	value, found := object[key]
	if !found || value == nil {
		return nil, nil
	}
	items, ok := jsonx.AsList(value)
	if !ok {
		return nil, fail("the package manifest's %s field is not a JSON list", strconv.Quote(key))
	}
	return items, nil
}

// LoadDocument reads and decodes a manifest.json file.
func LoadDocument(path string) (any, error) {
	if !ppath.IsFile(path) {
		return nil, fail("no manifest.json in %s — pass --package pointing at the unzipped download", ppath.Parent(path))
	}
	text, err := ppath.ReadText(path)
	if err != nil {
		return nil, err
	}
	document, err := jsonx.Decode(text)
	if err != nil {
		return nil, fail("%s is not valid JSON: %s", path, err.Error())
	}
	return document, nil
}

// LoadManifest reads a manifest file and validates it.
func LoadManifest(path string) (*Package, error) {
	document, err := LoadDocument(path)
	if err != nil {
		return nil, err
	}
	return FromDoc(document)
}

// SaveManifest writes the manifest document with two-space indent and a
// trailing newline, and returns the path.
func SaveManifest(path string, manifest *Package) (string, error) {
	if err := os.MkdirAll(ppath.Parent(path), 0o755); err != nil {
		return "", err
	}
	var buffer bytes.Buffer
	encoder := json.NewEncoder(&buffer)
	encoder.SetEscapeHTML(false)
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(manifest); err != nil {
		return "", err
	}
	if err := os.WriteFile(path, buffer.Bytes(), 0o644); err != nil {
		return "", err
	}
	return path, nil
}

// Pair is one package-relative file and the digest it must have.
type Pair struct {
	Relative string
	SHA256   string
}

// ExpectedFiles is every (package-relative path, sha256) the package must
// contain, each path once, in sorted order.
func ExpectedFiles(manifest *Package) []Pair {
	seen := map[string]string{}
	var order []string
	add := func(relative, digest string) {
		if _, done := seen[relative]; !done {
			order = append(order, relative)
		}
		seen[relative] = digest
	}
	for _, vendor := range manifest.Vendors {
		add(VendorDir+"/"+vendor.Name, vendor.SHA256)
	}
	for _, entry := range manifest.Files {
		add(entry.Path, entry.SHA256)
	}
	sort.Strings(order)
	pairs := make([]Pair, 0, len(order))
	for _, relative := range order {
		pairs = append(pairs, Pair{Relative: relative, SHA256: seen[relative]})
	}
	return pairs
}

// Sha256File digests a file the way the reference does, in 1 MiB blocks.
func Sha256File(path string) (string, error) {
	handle, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer handle.Close()
	digest := sha256.New()
	buffer := make([]byte, 1<<20)
	for {
		read, err := handle.Read(buffer)
		if read > 0 {
			digest.Write(buffer[:read])
		}
		if err != nil {
			break
		}
	}
	return hex.EncodeToString(digest.Sum(nil)), nil
}

// VerifyPackage checks every file the manifest names and returns a message per
// problem, empty when the package is sound.
func VerifyPackage(packageRoot string) ([]string, error) {
	manifest, err := LoadManifest(ppath.Join(packageRoot, manifestName))
	if err != nil {
		return nil, err
	}
	var problems []string
	for _, pair := range ExpectedFiles(manifest) {
		target := ppath.Join(packageRoot, pair.Relative)
		if !ppath.IsFile(target) {
			problems = append(problems, pair.Relative+": missing from the package")
			continue
		}
		actual, err := Sha256File(target)
		if err != nil {
			return nil, err
		}
		if actual != pair.SHA256 {
			problems = append(problems, pair.Relative+": checksum mismatch (expected "+pair.SHA256[:12]+"…, got "+actual[:12]+"…)")
		}
	}
	return problems, nil
}

// VerifyVendor raises an Error unless one archive is present and matches its pin.
func VerifyVendor(manifest *Package, vendor Vendor, packageRoot string) error {
	target := vendor.Path(packageRoot)
	if !ppath.IsFile(target) {
		return fail("%s is missing from the package", vendor.Name)
	}
	actual, err := Sha256File(target)
	if err != nil {
		return err
	}
	if actual != vendor.SHA256 {
		return fail("%s: checksum mismatch (expected %s…, got %s…)", vendor.Name, vendor.SHA256[:12], actual[:12])
	}
	return nil
}
