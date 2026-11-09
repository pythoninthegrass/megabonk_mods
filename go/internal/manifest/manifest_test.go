package manifest

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"

	"github.com/pythoninthegrass/megabonk_mods/installer/internal/jsonx"
)

func digest(text string) string {
	sum := sha256.Sum256([]byte(text))
	return hex.EncodeToString(sum[:])
}

func vendorMap(name, url, sha, kind, version string) map[string]any {
	return map[string]any{"name": name, "url": url, "sha256": sha, "kind": kind, "version": version}
}

func fileMap(path, sha, dest string) map[string]any {
	return map[string]any{"path": path, "sha256": sha, "dest": dest}
}

func manifestDoc() map[string]any {
	return map[string]any{
		"schema":              PackageSchema,
		"platform":            "linux",
		"package_id":          "megabonk-levels-0.0.1-ml0.7.3-linux",
		"mod_version":         "0.0.1",
		"melonloader_version": "0.7.3",
		"game_buildid":        "21750826",
		"generated":           "2026-10-31T03:30:00Z",
		"verified_on":         []any{"macOS Wine (reference)"},
		"vendors": []any{
			vendorMap("MelonLoader.x64.zip", "https://example.invalid/MelonLoader.x64.zip", strings.Repeat("a", 64), "melonloader", "0.7.3"),
			vendorMap("dotnet-runtime-6.0.36-win-x64.zip", "https://example.invalid/dotnet.zip", strings.Repeat("b", 64), "dotnet", "6.0.36"),
		},
		"files": []any{
			fileMap("mod/MegabonkLevels.Mod.dll", strings.Repeat("c", 64), "Mods/MegabonkLevels.Mod.dll"),
			fileMap("mod/NLayer.dll", strings.Repeat("d", 64), "Mods/NLayer.dll"),
			fileMap("mod/NLayer.dll", strings.Repeat("d", 64), "UserLibs/NLayer.dll"),
		},
	}
}

func decoded(t *testing.T, document map[string]any) any {
	t.Helper()
	text, err := json.Marshal(document)
	if err != nil {
		t.Fatalf("encode fixture: %v", err)
	}
	value, err := jsonx.Decode(string(text))
	if err != nil {
		t.Fatalf("decode fixture: %v", err)
	}
	return value
}

func mustManifest(t *testing.T, document map[string]any) *Package {
	t.Helper()
	loaded, err := FromDoc(decoded(t, document))
	if err != nil {
		t.Fatalf("FromDoc: %v", err)
	}
	return loaded
}

func writePackage(t *testing.T, files map[string]string) string {
	t.Helper()
	root := t.TempDir()
	for relative, content := range files {
		target := filepath.Join(root, filepath.FromSlash(relative))
		if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(target, []byte(content), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	return root
}

func writeManifestFile(t *testing.T, root string, document map[string]any) string {
	t.Helper()
	text, err := json.Marshal(document)
	if err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(root, "manifest.json")
	if err := os.WriteFile(path, text, 0o644); err != nil {
		t.Fatal(err)
	}
	return path
}

func firstEntry(t *testing.T, document map[string]any, key string) map[string]any {
	t.Helper()
	entries, ok := document[key].([]any)
	if !ok || len(entries) == 0 {
		t.Fatalf("%s is not a non-empty list", key)
	}
	entry, ok := entries[0].(map[string]any)
	if !ok {
		t.Fatalf("%s[0] is not an object", key)
	}
	return entry
}

func TestFromDocAcceptsTheReferenceDocument(t *testing.T) {
	manifest := mustManifest(t, manifestDoc())
	if manifest.Platform != "linux" || manifest.PackageID != "megabonk-levels-0.0.1-ml0.7.3-linux" {
		t.Errorf("identity = %+v", manifest)
	}
	if len(manifest.Vendors) != 2 || len(manifest.Files) != 3 {
		t.Errorf("vendors=%d files=%d", len(manifest.Vendors), len(manifest.Files))
	}
	if !reflect.DeepEqual(manifest.VerifiedOn, []any{"macOS Wine (reference)"}) {
		t.Errorf("verified_on = %#v", manifest.VerifiedOn)
	}
	if got := manifest.Label(); got != "MegabonkLevels 0.0.1 (MelonLoader 0.7.3)" {
		t.Errorf("Label = %q", got)
	}
}

func TestFromDocRejectsANonObject(t *testing.T) {
	for _, document := range []any{"not an object", []any{}, nil, json.Number("3")} {
		if _, err := FromDoc(document); err == nil || err.Error() != "the package manifest is not a JSON object" {
			t.Errorf("FromDoc(%v) err = %v", document, err)
		}
	}
}

func TestFromDocNamesAMissingTopLevelKey(t *testing.T) {
	for _, key := range []string{"schema", "melonloader_version", "verified_on", "files"} {
		document := manifestDoc()
		delete(document, key)
		_, err := FromDoc(decoded(t, document))
		want := "the package manifest is missing '" + key + "'"
		if err == nil || err.Error() != want {
			t.Errorf("missing %s: err = %v, want %q", key, err, want)
		}
	}
}

func TestFromDocRejectsAForeignSchema(t *testing.T) {
	document := manifestDoc()
	document["schema"] = "megabonk-player-package/9"
	_, err := FromDoc(decoded(t, document))
	want := `unrecognised package manifest schema "megabonk-player-package/9" (this installer understands "megabonk-player-package/1")`
	if err == nil || err.Error() != want {
		t.Errorf("err = %v, want %q", err, want)
	}
}

func TestFromDocAcceptsAWindowsPackage(t *testing.T) {
	document := manifestDoc()
	document["platform"] = "windows"
	manifest, err := FromDoc(decoded(t, document))
	if err != nil || manifest.Platform != "windows" {
		t.Errorf("manifest = %+v, err = %v, want a windows package", manifest, err)
	}
}

func TestFromDocAcceptsAMacosPackage(t *testing.T) {
	document := manifestDoc()
	document["platform"] = "macos"
	manifest, err := FromDoc(decoded(t, document))
	if err != nil || manifest.Platform != "macos" {
		t.Errorf("manifest = %+v, err = %v, want a macos package", manifest, err)
	}
}

func TestFromDocRejectsAWrongPlatform(t *testing.T) {
	document := manifestDoc()
	document["platform"] = "darwin"
	_, err := FromDoc(decoded(t, document))
	want := `unrecognised package platform "darwin"; expected "linux", "windows" or "macos"`
	if err == nil || err.Error() != want {
		t.Errorf("err = %v, want %q", err, want)
	}
}

func TestFromDocRequiresBothVendorKinds(t *testing.T) {
	document := manifestDoc()
	document["vendors"] = []any{
		vendorMap("MelonLoader.x64.zip", "https://example.invalid/MelonLoader.x64.zip", strings.Repeat("a", 64), "melonloader", "0.7.3"),
	}
	_, err := FromDoc(decoded(t, document))
	if err == nil || err.Error() != `the package manifest lists no "dotnet" component` {
		t.Errorf("err = %v", err)
	}
}

func TestFromDocRequiresFiles(t *testing.T) {
	document := manifestDoc()
	document["files"] = []any{}
	_, err := FromDoc(decoded(t, document))
	if err == nil || err.Error() != "the package manifest lists no files to install" {
		t.Errorf("err = %v", err)
	}
}

func TestFromDocNamesANonListField(t *testing.T) {
	document := manifestDoc()
	document["vendors"] = "MelonLoader.x64.zip"
	_, err := FromDoc(decoded(t, document))
	if err == nil || err.Error() != `the package manifest's "vendors" field is not a JSON list` {
		t.Errorf("err = %v", err)
	}
}

func TestVendorEntryErrors(t *testing.T) {
	cases := []struct {
		name   string
		mutate func(entry map[string]any)
		want   string
	}{
		{
			name:   "not an object",
			mutate: func(entry map[string]any) {},
			want:   "",
		},
		{
			name:   "missing key",
			mutate: func(entry map[string]any) { delete(entry, "kind") },
			want:   "vendor entry 0 is missing 'kind'",
		},
		{
			name: "unknown fields",
			mutate: func(entry map[string]any) {
				entry["size"] = 1
				entry["mirror"] = "x"
			},
			want: "vendor entry 0 has unknown field(s): mirror, size",
		},
		{
			name:   "short digest",
			mutate: func(entry map[string]any) { entry["sha256"] = "abc" },
			want:   "vendor entry 0 (MelonLoader.x64.zip): sha256 is not 64 hex characters",
		},
	}
	for _, item := range cases {
		if item.want == "" {
			continue
		}
		t.Run(item.name, func(t *testing.T) {
			document := manifestDoc()
			item.mutate(firstEntry(t, document, "vendors"))
			if _, err := FromDoc(decoded(t, document)); err == nil || err.Error() != item.want {
				t.Errorf("err = %v, want %q", err, item.want)
			}
		})
	}
	document := manifestDoc()
	document["vendors"] = []any{"just a string"}
	if _, err := FromDoc(decoded(t, document)); err == nil || err.Error() != "vendor entry 0 is not a JSON object" {
		t.Errorf("err = %v", err)
	}
}

func TestFileEntryRejectsUnsafePaths(t *testing.T) {
	cases := []struct {
		key  string
		bad  string
		want string
	}{
		{"path", "/etc/passwd", `file entry 0: unsafe path "/etc/passwd"`},
		{"dest", "../Escape.dll", `file entry 0: unsafe path "../Escape.dll"`},
		{"path", "mod/../escape.dll", `file entry 0: unsafe path "mod/../escape.dll"`},
	}
	for _, item := range cases {
		document := manifestDoc()
		firstEntry(t, document, "files")[item.key] = item.bad
		if _, err := FromDoc(decoded(t, document)); err == nil || err.Error() != item.want {
			t.Errorf("err = %v, want %q", err, item.want)
		}
	}
}

func TestFileEntryNormalisesBackslashes(t *testing.T) {
	document := manifestDoc()
	firstEntry(t, document, "files")["path"] = `mod\NLayer.dll`
	manifest := mustManifest(t, document)
	if manifest.Files[0].Path != "mod/NLayer.dll" {
		t.Errorf("path = %q", manifest.Files[0].Path)
	}
}

func TestFromDocLowercasesAndStringifiesScalars(t *testing.T) {
	document := manifestDoc()
	firstEntry(t, document, "vendors")["sha256"] = strings.Repeat("A", 64)
	document["game_buildid"] = json.Number("21750826")
	manifest := mustManifest(t, document)
	if manifest.Vendors[0].SHA256 != strings.Repeat("a", 64) {
		t.Errorf("sha256 = %q", manifest.Vendors[0].SHA256)
	}
	if manifest.GameBuildID != "21750826" {
		t.Errorf("game_buildid = %q", manifest.GameBuildID)
	}
}

func TestVendorForKindAndMissingKind(t *testing.T) {
	manifest := mustManifest(t, manifestDoc())
	vendor, err := manifest.Vendor("dotnet")
	if err != nil || vendor.Version != "6.0.36" {
		t.Fatalf("vendor = %+v err = %v", vendor, err)
	}
	if _, err := manifest.Vendor("nope"); err == nil || err.Error() != `the package has no "nope" component` {
		t.Errorf("err = %v", err)
	}
	if got := vendor.Path("/pkg"); got != "/pkg/vendor/dotnet-runtime-6.0.36-win-x64.zip" {
		t.Errorf("Path = %q", got)
	}
}

func TestExpectedFilesDedupesAndSorts(t *testing.T) {
	manifest := mustManifest(t, manifestDoc())
	got := ExpectedFiles(manifest)
	want := []Pair{
		{"mod/MegabonkLevels.Mod.dll", strings.Repeat("c", 64)},
		{"mod/NLayer.dll", strings.Repeat("d", 64)},
		{"vendor/MelonLoader.x64.zip", strings.Repeat("a", 64)},
		{"vendor/dotnet-runtime-6.0.36-win-x64.zip", strings.Repeat("b", 64)},
	}
	if !reflect.DeepEqual(got, want) {
		t.Errorf("ExpectedFiles = %+v, want %+v", got, want)
	}
}

func TestSha256FileMatchesKnownDigest(t *testing.T) {
	root := writePackage(t, map[string]string{"f.bin": "megabonk"})
	got, err := Sha256File(filepath.Join(root, "f.bin"))
	if err != nil {
		t.Fatal(err)
	}
	if got != digest("megabonk") {
		t.Errorf("digest = %q", got)
	}
}

func TestSaveAndLoadRoundTrip(t *testing.T) {
	root := writePackage(t, nil)
	manifest := mustManifest(t, manifestDoc())
	path, err := SaveManifest(filepath.Join(root, "manifest.json"), manifest)
	if err != nil {
		t.Fatal(err)
	}
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.HasPrefix(string(raw), "{\n  \"schema\": \"megabonk-player-package/1") {
		t.Errorf("saved document starts:\n%s", string(raw)[:min(len(raw), 80)])
	}
	if !strings.HasSuffix(string(raw), "}\n") {
		t.Errorf("saved document lacks a trailing newline")
	}
	if strings.Contains(string(raw), "\\u0026") {
		t.Errorf("saved document escapes HTML characters")
	}
	reloaded, err := LoadManifest(path)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(reloaded, manifest) {
		t.Errorf("round trip differs:\n%+v\n%+v", reloaded, manifest)
	}
}

func soundDocument() map[string]any {
	document := manifestDoc()
	vendors := document["vendors"].([]any)
	vendors[0].(map[string]any)["sha256"] = digest("ml")
	vendors[1].(map[string]any)["sha256"] = digest("dn")
	files := document["files"].([]any)
	files[0].(map[string]any)["sha256"] = digest("mod dll bytes")
	files[1].(map[string]any)["sha256"] = digest("nlayer")
	files[2].(map[string]any)["sha256"] = digest("nlayer")
	return document
}

var packageTree = map[string]string{
	"vendor/MelonLoader.x64.zip":               "ml",
	"vendor/dotnet-runtime-6.0.36-win-x64.zip": "dn",
	"mod/MegabonkLevels.Mod.dll":               "mod dll bytes",
	"mod/NLayer.dll":                           "nlayer",
}

func TestVerifyPackagePassesOnMatchingDigests(t *testing.T) {
	root := writePackage(t, packageTree)
	writeManifestFile(t, root, soundDocument())
	problems, err := VerifyPackage(root)
	if err != nil {
		t.Fatal(err)
	}
	if len(problems) != 0 {
		t.Errorf("problems = %v", problems)
	}
}

func TestVerifyPackageNamesATamperedFile(t *testing.T) {
	tree := map[string]string{}
	for key, value := range packageTree {
		tree[key] = value
	}
	tree["mod/MegabonkLevels.Mod.dll"] = "tampered"
	root := writePackage(t, tree)
	writeManifestFile(t, root, soundDocument())
	problems, err := VerifyPackage(root)
	if err != nil {
		t.Fatal(err)
	}
	if len(problems) != 1 {
		t.Fatalf("problems = %v", problems)
	}
	want := "mod/MegabonkLevels.Mod.dll: checksum mismatch (expected " + digest("mod dll bytes")[:12] +
		"…, got " + digest("tampered")[:12] + "…)"
	if problems[0] != want {
		t.Errorf("problem = %q, want %q", problems[0], want)
	}
}

func TestVerifyPackageNamesAMissingVendorArchive(t *testing.T) {
	tree := map[string]string{}
	for key, value := range packageTree {
		tree[key] = value
	}
	delete(tree, "vendor/dotnet-runtime-6.0.36-win-x64.zip")
	root := writePackage(t, tree)
	writeManifestFile(t, root, soundDocument())
	problems, err := VerifyPackage(root)
	if err != nil {
		t.Fatal(err)
	}
	found := false
	for _, problem := range problems {
		if problem == "vendor/dotnet-runtime-6.0.36-win-x64.zip: missing from the package" {
			found = true
		}
	}
	if !found {
		t.Errorf("problems = %v", problems)
	}
}

func TestVerifyPackageWithoutAManifest(t *testing.T) {
	root := writePackage(t, nil)
	_, err := VerifyPackage(root)
	want := "no manifest.json in " + root + " — pass --package pointing at the unzipped download"
	if err == nil || err.Error() != want {
		t.Errorf("err = %v, want %q", err, want)
	}
}

func TestLoadDocumentReportsBadJSON(t *testing.T) {
	root := writePackage(t, map[string]string{"manifest.json": `{"schema": }`})
	_, err := LoadDocument(filepath.Join(root, "manifest.json"))
	if err == nil || !strings.HasPrefix(err.Error(), filepath.Join(root, "manifest.json")+" is not valid JSON: ") {
		t.Fatalf("err = %v", err)
	}
	if !strings.Contains(err.Error(), "invalid character") {
		t.Errorf("err = %q, want Go's own JSON error", err.Error())
	}
}

func TestVerifyVendorNamesAMissingOrTamperedArchive(t *testing.T) {
	root := writePackage(t, map[string]string{"vendor/MelonLoader.x64.zip": "ml"})
	manifest := mustManifest(t, manifestDoc())
	missing, err := manifest.Vendor("dotnet")
	if err != nil {
		t.Fatal(err)
	}
	if err := VerifyVendor(manifest, missing, root); err == nil ||
		err.Error() != "dotnet-runtime-6.0.36-win-x64.zip is missing from the package" {
		t.Errorf("err = %v", err)
	}
	present, err := manifest.Vendor("melonloader")
	if err != nil {
		t.Fatal(err)
	}
	if err := VerifyVendor(manifest, present, root); err == nil ||
		!strings.Contains(err.Error(), "checksum mismatch (expected ") ||
		!strings.Contains(err.Error(), present.Name) {
		t.Errorf("err = %v", err)
	}
	present.SHA256 = digest("ml")
	if err := VerifyVendor(manifest, present, root); err != nil {
		t.Errorf("expected a match, got %v", err)
	}
}
