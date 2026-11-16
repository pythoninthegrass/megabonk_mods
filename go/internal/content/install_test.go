package content

import (
	"archive/zip"
	"io"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func ppathIsFile(path string) bool {
	info, err := os.Stat(path)
	return err == nil && !info.IsDir()
}

func ppathIsDir(path string) bool {
	info, err := os.Stat(path)
	return err == nil && info.IsDir()
}

func writeBytes(t *testing.T, path string, body []byte) string {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, body, 0o644); err != nil {
		t.Fatal(err)
	}
	return path
}

func read(t *testing.T, path string) string {
	t.Helper()
	body, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	return string(body)
}

// zipOf writes entries in the order given, so a test can put a bad member after
// a good one and prove nothing was extracted.
func zipOf(t *testing.T, name string, entries [][2]string) string {
	t.Helper()
	archive := filepath.Join(t.TempDir(), name)
	handle, err := os.Create(archive)
	if err != nil {
		t.Fatal(err)
	}
	writer := zip.NewWriter(handle)
	for _, entry := range entries {
		member, err := writer.Create(entry[0])
		if err != nil {
			t.Fatal(err)
		}
		if _, err := member.Write([]byte(entry[1])); err != nil {
			t.Fatal(err)
		}
	}
	if err := writer.Close(); err != nil {
		t.Fatal(err)
	}
	if err := handle.Close(); err != nil {
		t.Fatal(err)
	}
	return archive
}

func TestInstallLevelWritesTheSlugAndItsImages(t *testing.T) {
	game := t.TempDir()
	source := t.TempDir()
	write(t, filepath.Join(source, "warehouse.mblevel.json"), `{"schema":2,"title":"Warehouse"}`)
	write(t, filepath.Join(source, "warehouse.png"), "cover bytes")
	write(t, filepath.Join(source, "warehouse.biome.png"), "biome bytes")

	result, err := InstallLevel(game, InstallLevelInput{
		Slug:  "warehouse",
		Level: filepath.Join(source, "warehouse.mblevel.json"),
		Cover: filepath.Join(source, "warehouse.png"),
		Biome: filepath.Join(source, "warehouse.biome.png"),
	})
	if err != nil {
		t.Fatal(err)
	}
	want := []string{
		"UserData/Levels/warehouse.mblevel.json",
		"UserData/Levels/warehouse.png",
		"UserData/Levels/warehouse.biome.png",
	}
	if !reflect.DeepEqual(result.Files, want) {
		t.Errorf("files = %v, want %v", result.Files, want)
	}
	if result.Replaced {
		t.Error("nothing was replaced")
	}
	for i, relative := range want {
		path := filepath.Join(game, filepath.FromSlash(relative))
		if !ppathIsFile(path) {
			t.Errorf("%s was not written", relative)
			continue
		}
		if i == 0 && !strings.Contains(read(t, path), "Warehouse") {
			t.Errorf("level body = %s", read(t, path))
		}
	}
}

func TestInstallLevelWithoutImages(t *testing.T) {
	game := t.TempDir()
	source := t.TempDir()
	level := write(t, filepath.Join(source, "quiet.mblevel.json"), `{"schema":2}`)

	result, err := InstallLevel(game, InstallLevelInput{Slug: "quiet", Level: level})
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(result.Files, []string{"UserData/Levels/quiet.mblevel.json"}) {
		t.Errorf("files = %v", result.Files)
	}
	if ppathIsFile(filepath.Join(game, "UserData", "Levels", "quiet.png")) {
		t.Error("an absent image should stay absent")
	}
}

func TestInstallLevelReplacesAndReports(t *testing.T) {
	game := t.TempDir()
	source := t.TempDir()
	level := write(t, filepath.Join(source, "warehouse.mblevel.json"), `{"schema":2,"title":"New"}`)
	writeBytes(t, filepath.Join(game, "UserData", "Levels", "warehouse.mblevel.json"), []byte(`{"schema":2,"title":"Old"}`))
	writeBytes(t, filepath.Join(game, "UserData", "Levels", "warehouse.png"), []byte("stale"))
	writeBytes(t, filepath.Join(game, "UserData", "Levels", "unrelated.png"), []byte("other"))

	result, err := InstallLevel(game, InstallLevelInput{
		Slug:  "warehouse",
		Level: level,
	})
	if err != nil {
		t.Fatal(err)
	}
	if !result.Replaced {
		t.Error("replacing an existing level must be reported")
	}
	if got := read(t, filepath.Join(game, "UserData", "Levels", "warehouse.mblevel.json")); !strings.Contains(got, "New") {
		t.Errorf("installed level = %s", got)
	}
	if ppathIsFile(filepath.Join(game, "UserData", "Levels", "warehouse.png")) {
		t.Error("a cover the install does not carry is removed, so a re-install cannot serve a stale one")
	}
	if !result.Removed["UserData/Levels/warehouse.png"] {
		t.Errorf("the removed image should be reported: %v", result.Removed)
	}
	if !ppathIsFile(filepath.Join(game, "UserData", "Levels", "unrelated.png")) {
		t.Error("an image for another level is left alone")
	}
}

func TestInstallLevelRejectsABadLevel(t *testing.T) {
	game := t.TempDir()
	source := t.TempDir()
	level := write(t, filepath.Join(source, "broken.mblevel.json"), `[1,2]`)
	if _, err := InstallLevel(game, InstallLevelInput{Slug: "broken", Level: level}); err == nil {
		t.Fatal("an invalid level must be refused")
	}
	if ppathIsDir(filepath.Join(game, "UserData")) {
		t.Error("a refused install must not create UserData")
	}
}

func TestInstallLevelRejectsABadSlug(t *testing.T) {
	game := t.TempDir()
	source := t.TempDir()
	level := write(t, filepath.Join(source, "ok.mblevel.json"), `{"schema":2}`)
	for _, slug := range []string{"", "..", "../evil", "a/b", "UPPER", "has space"} {
		if _, err := InstallLevel(game, InstallLevelInput{Slug: slug, Level: level}); err == nil {
			t.Errorf("slug %q should be refused", slug)
		}
	}
}

func TestInstallPackRejectsAnEscapingArchive(t *testing.T) {
	game := t.TempDir()
	manifest := `{"id":"thps","name":"THPS","author":"user","version":"1","assets":["a"]}`
	for _, name := range []string{"../../escaped", "/etc/escaped", "thps/../../escaped"} {
		archive := zipOf(t, "pack.zip", [][2]string{
			{"thps/manifest.json", manifest},
			{"thps/thps", "bundle"},
			{name, "payload"},
		})
		if _, err := InstallPackFromZip(game, "thps", "1", archive); err == nil {
			t.Fatalf("%s should be refused", name)
		}
		if ppathIsFile(filepath.Join(game, "UserData", "LevelPacks", "thps", "manifest.json")) {
			t.Errorf("%s: nothing should be written before the whole archive is checked", name)
		}
		if ppathIsFile(filepath.Join(game, "escaped")) || ppathIsFile("/etc/escaped") {
			t.Errorf("%s: the escaping entry was written", name)
		}
	}
}

func TestInstallPackRejectsAnUnsafeMemberName(t *testing.T) {
	game := t.TempDir()
	manifest := `{"id":"thps","name":"THPS","author":"user","version":"1","assets":["a"]}`
	for _, name := range []string{"thps\\escape", "thps/C:/evil", "thps//x"} {
		archive := zipOf(t, "pack.zip", [][2]string{
			{"thps/manifest.json", manifest},
			{"thps/thps", "bundle"},
			{name, "payload"},
		})
		if _, err := InstallPackFromZip(game, "thps", "1", archive); err == nil {
			t.Errorf("member %q should be refused", name)
		}
	}
}

func TestInstallPackRejectsContentsThatFailValidation(t *testing.T) {
	archive := zipOf(t, "pack.zip", [][2]string{
		{"thps/manifest.json", `{"id":"wrong","name":"THPS","author":"user","version":"1","assets":["a"]}`},
		{"thps/thps", "bundle"},
	})
	game := t.TempDir()
	_, err := InstallPackFromZip(game, "thps", "1", archive)
	if err == nil || !strings.Contains(err.Error(), "does not match its pack folder") {
		t.Errorf("err = %v", err)
	}
	if ppathIsDir(filepath.Join(game, "UserData", "LevelPacks", "thps")) {
		t.Error("a rejected pack leaves no directory behind")
	}

	archive = zipOf(t, "pack.zip", [][2]string{{"thps/manifest.json", `{"id":"thps","name":"THPS","author":"user","version":"1","assets":["a"]}`}})
	if _, err := InstallPackFromZip(game, "thps", "1", archive); err == nil ||
		!strings.Contains(err.Error(), "no AssetBundle file") {
		t.Errorf("a pack without a bundle should be refused, got %v", err)
	}
}

func TestInstallPackRejectsArchiveWithoutThePackFolder(t *testing.T) {
	archive := zipOf(t, "pack.zip", [][2]string{{"other/manifest.json", "{}"}})
	if _, err := InstallPackFromZip(t.TempDir(), "thps", "1", archive); err == nil ||
		!strings.Contains(err.Error(), "no files under thps/") {
		t.Errorf("err = %v", err)
	}
}

func TestInstallPackIgnoresMembersOutsideThePackFolder(t *testing.T) {
	game := t.TempDir()
	archive := zipOf(t, "pack.zip", [][2]string{
		{"README.md", "readme"},
		{"other/manifest.json", "{}"},
		{"thps/manifest.json", `{"id":"thps","name":"THPS","author":"user","version":"1","assets":["a"]}`},
		{"thps/thps", "bundle"},
	})
	result, err := InstallPackFromZip(game, "thps", "1", archive)
	if err != nil {
		t.Fatal(err)
	}
	if len(result.Files) != 2 {
		t.Errorf("files = %v", result.Files)
	}
	if ppathIsFile(filepath.Join(game, "README.md")) || ppathIsDir(filepath.Join(game, "other")) {
		t.Error("nothing outside the pack folder is written")
	}
}

func TestInstallPackReportsAFileThatLiesAboutItsSize(t *testing.T) {
	body := "bundle" + strings.Repeat("x", 4096)
	archive := zipOf(t, "pack.zip", [][2]string{
		{"thps/manifest.json", `{"id":"thps","name":"THPS","author":"user","version":"1","assets":["a"]}`},
		{"thps/thps", body},
	})
	short := lyingArchive(t, archive, "thps/thps", 512)
	if _, err := InstallPackFromZip(t.TempDir(), "thps", "1", short); err == nil ||
		!strings.Contains(err.Error(), "thps/thps") || !strings.Contains(err.Error(), "4614") {
		t.Errorf("err = %v, want it to name the member and the size it promised", err)
	}
}

func TestInstallPackRejectsAnOversizedMember(t *testing.T) {
	entries := [][2]string{
		{"thps/manifest.json", `{"id":"thps","name":"THPS","author":"user","version":"1","assets":["a"]}`},
		{"thps/thps", strings.Repeat("x", MaxFileBytes+1)},
	}
	archive := zipOf(t, "huge.zip", entries)
	if _, err := InstallPackFromZip(t.TempDir(), "thps", "1", archive); err == nil ||
		!strings.Contains(err.Error(), "256MB") {
		t.Errorf("err = %v", err)
	}
}

func TestInstallPackWritesBundleManifestAndAttachments(t *testing.T) {
	game := t.TempDir()
	archive := zipOf(t, "pack.zip", [][2]string{
		{"thps/manifest.json", `{"id":"thps","name":"THPS","author":"user","version":"1","assets":["a"]}`},
		{"thps/attachments.json", `{"schema":"pack-attachments/1"}`},
		{"thps/thps", "bundle bytes"},
		{"thps/notes.txt", "not a bundle"},
	})
	result, err := InstallPackFromZip(game, "thps", "1", archive)
	if err != nil {
		t.Fatal(err)
	}
	if result.ID != "thps" || result.Version != "1" {
		t.Errorf("result = %+v", result)
	}
	want := []string{
		"UserData/LevelPacks/thps/manifest.json",
		"UserData/LevelPacks/thps/attachments.json",
		"UserData/LevelPacks/thps/thps",
	}
	if !reflect.DeepEqual(result.Files, want) {
		t.Errorf("files = %v, want %v", result.Files, want)
	}
	if got := read(t, filepath.Join(game, "UserData", "LevelPacks", "thps", "thps")); got != "bundle bytes" {
		t.Errorf("bundle = %q", got)
	}
	if ppathIsFile(filepath.Join(game, "UserData", "LevelPacks", "thps", "notes.txt")) {
		t.Error("only the manifest, its sidecar and the bundles are installed")
	}
	if result.Dir != "UserData/LevelPacks/thps" {
		t.Errorf("dir = %q", result.Dir)
	}
}

func TestInstallPackReplacesTheWholeFolder(t *testing.T) {
	game := t.TempDir()
	stale := filepath.Join(game, "UserData", "LevelPacks", "thps", "old.bundle")
	writeBytes(t, stale, []byte("old"))
	archive := zipOf(t, "pack.zip", [][2]string{
		{"thps/manifest.json", `{"id":"thps","name":"THPS","author":"user","version":"1","assets":["a"]}`},
		{"thps/thps", "bundle"},
	})
	if _, err := InstallPackFromZip(game, "thps", "1", archive); err != nil {
		t.Fatal(err)
	}
	if ppathIsFile(stale) {
		t.Error("the previous pack should be gone")
	}
}

func TestInstallPackRejectsABadPackID(t *testing.T) {
	archive := zipOf(t, "pack.zip", [][2]string{{"thps/thps", "bundle"}})
	game := t.TempDir()
	for _, id := range []string{"", "..", "Thps", "a/b"} {
		if _, err := InstallPackFromZip(game, id, "1", archive); err == nil {
			t.Errorf("pack id %q should be refused", id)
		}
	}
}

// lyingArchive makes the named member promise more bytes than it carries: the
// sizes stay in the member's header because CreateRaw writes them there and
// never replaces them with the bytes actually written.
func lyingArchive(t *testing.T, archive, wanted string, overstate uint64) string {
	t.Helper()
	reader, err := zip.OpenReader(archive)
	if err != nil {
		t.Fatal(err)
	}
	defer reader.Close()
	out := filepath.Join(t.TempDir(), "lying.zip")
	handle, err := os.Create(out)
	if err != nil {
		t.Fatal(err)
	}
	writer := zip.NewWriter(handle)
	for _, member := range reader.File {
		body := readMember(t, member)
		header := &zip.FileHeader{Name: member.Name, Method: zip.Store}
		header.SetMode(member.Mode())
		header.CRC32 = member.CRC32
		header.UncompressedSize64 = uint64(len(body))
		header.CompressedSize64 = uint64(len(body))
		if member.Name == wanted {
			header.UncompressedSize64 += overstate
			header.CompressedSize64 += overstate
		}
		written, err := writer.CreateRaw(header)
		if err != nil {
			t.Fatal(err)
		}
		if _, err := written.Write(body); err != nil {
			t.Fatal(err)
		}
	}
	if err := writer.Close(); err != nil {
		t.Fatal(err)
	}
	if err := handle.Close(); err != nil {
		t.Fatal(err)
	}
	return out
}

func readMember(t *testing.T, member *zip.File) []byte {
	t.Helper()
	handle, err := member.Open()
	if err != nil {
		t.Fatal(err)
	}
	defer handle.Close()
	body, err := io.ReadAll(handle)
	if err != nil {
		t.Fatal(err)
	}
	return body
}

func TestLevelStemAndSidecarNames(t *testing.T) {
	cases := map[string]string{
		"thps.mblevel.json":              "thps",
		"a.level.json":                   "a",
		"bramblecrown-hill":              "bramblecrown-hill",
		"two.parts.json":                 "two.parts",
		".mblevel.json":                  ".mblevel",
		"UserData/Levels/x.mblevel.json": "x",
	}
	for name, want := range cases {
		if got := LevelStem(name); got != want {
			t.Errorf("LevelStem(%q) = %q, want %q", name, got, want)
		}
	}
	if got := CoverFor("thps"); got != "thps.png" {
		t.Errorf("CoverFor = %q", got)
	}
	if got := BiomeFor("thps"); got != "thps.biome.png" {
		t.Errorf("BiomeFor = %q", got)
	}
}

func TestInstallLevelRejectsAnOversizedImage(t *testing.T) {
	game := t.TempDir()
	source := t.TempDir()
	level := write(t, filepath.Join(source, "big.mblevel.json"), `{"schema":2}`)
	cover := filepath.Join(source, "big.png")
	if err := os.MkdirAll(filepath.Dir(cover), 0o755); err != nil {
		t.Fatal(err)
	}
	handle, err := os.Create(cover)
	if err != nil {
		t.Fatal(err)
	}
	if err := handle.Truncate(MaxImageBytes + 1); err != nil {
		t.Fatal(err)
	}
	handle.Close()
	if _, err := InstallLevel(game, InstallLevelInput{Slug: "big", Level: level, Cover: cover}); err == nil ||
		!strings.Contains(err.Error(), "image limit") {
		t.Errorf("err = %v", err)
	}

	if _, err := InstallLevel(game, InstallLevelInput{
		Slug: "big", Level: level, Cover: filepath.Join(source, "absent.png")}); err == nil ||
		!strings.Contains(err.Error(), "no such image") {
		t.Errorf("a missing image should be named, got %v", err)
	}
}

func TestInstallLevelReplacesEverySidecarKind(t *testing.T) {
	game := t.TempDir()
	source := t.TempDir()
	level := write(t, filepath.Join(source, "warehouse.mblevel.json"), `{"schema":2}`)
	write(t, filepath.Join(source, "warehouse-cover.jpg"), "jpeg cover")
	write(t, filepath.Join(source, "warehouse-forest.jpeg"), "jpeg biome")

	result, err := InstallLevel(game, InstallLevelInput{
		Slug:  "warehouse",
		Level: level,
		Cover: filepath.Join(source, "warehouse-cover.jpg"),
		Biome: filepath.Join(source, "warehouse-forest.jpeg"),
	})
	if err != nil {
		t.Fatal(err)
	}
	if result.Cover != "UserData/Levels/warehouse.png" || result.Biome != "UserData/Levels/warehouse.biome.png" {
		t.Errorf("images = %q, %q", result.Cover, result.Biome)
	}
	if got := read(t, filepath.Join(game, "UserData", "Levels", "warehouse.png")); got != "jpeg cover" {
		t.Errorf("cover = %q", got)
	}
	if got := read(t, filepath.Join(game, "UserData", "Levels", "warehouse.biome.png")); got != "jpeg biome" {
		t.Errorf("biome icon = %q", got)
	}
}

func TestInstallPackRejectsAnUnreadableArchive(t *testing.T) {
	bad := filepath.Join(t.TempDir(), "pack.zip")
	if err := os.WriteFile(bad, []byte("not a zip"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := InstallPackFromZip(t.TempDir(), "thps", "1", bad); err == nil {
		t.Fatal("a broken archive should be refused")
	}
	if _, err := InstallPackFromZip(t.TempDir(), "thps", "1", filepath.Join(t.TempDir(), "gone.zip")); err == nil {
		t.Fatal("a missing archive should be refused")
	}
}

func TestInstallPackReportsAnUnwritableMember(t *testing.T) {
	if os.Geteuid() == 0 {
		t.Skip("a root run writes anywhere")
	}
	game := t.TempDir()
	archive := zipOf(t, "pack.zip", [][2]string{
		{"thps/manifest.json", `{"id":"thps","name":"THPS","author":"user","version":"1","assets":["a"]}`},
		{"thps/thps", "bundle"},
	})
	if _, err := InstallPackFromZip(game, "thps", "1", archive); err != nil {
		t.Fatal(err)
	}
	// A directory where a bundle belongs makes the copy itself fail.
	if err := os.MkdirAll(filepath.Join(game, "UserData", "LevelPacks", "shield"), 0o755); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(filepath.Join(game, "UserData", "LevelPacks", "shield")); err != nil {
		t.Fatal(err)
	}
	result, err := InstallPackFromZip(game, "shield", "1", zipOf(t, "shield.zip", [][2]string{
		{"shield/manifest.json", `{"id":"shield","name":"S","author":"u","version":"1","assets":["a"]}`},
		{"shield/shield", "bundle"},
		{"shield/notes", "note"},
	}))
	if err != nil {
		t.Fatal(err)
	}
	if len(result.Files) != 3 {
		t.Errorf("files = %v", result.Files)
	}
}

// The gallery names a level by its slug and serves its pictures under their own
// file names, so the install has to rename them into the sidecar names the
// loaders find (docs/level-format.md).
func TestInstallLevelNamesTheGalleryFilesByTheSlug(t *testing.T) {
	game := t.TempDir()
	source := t.TempDir()
	level := write(t, filepath.Join(source, "original-name.mblevel.json"), `{"schema":2,"title":"Renamed Title"}`)
	write(t, filepath.Join(source, "cover-7f3.png"), "cover")
	write(t, filepath.Join(source, "biome-9k1.jpg"), "biome")

	result, err := InstallLevel(game, InstallLevelInput{
		Slug:  "renamed-title",
		Level: level,
		Cover: filepath.Join(source, "cover-7f3.png"),
		Biome: filepath.Join(source, "biome-9k1.jpg"),
	})
	if err != nil {
		t.Fatal(err)
	}
	want := []string{
		"UserData/Levels/renamed-title.mblevel.json",
		"UserData/Levels/renamed-title.png",
		"UserData/Levels/renamed-title.biome.png",
	}
	if !reflect.DeepEqual(result.Files, want) {
		t.Errorf("files = %v, want %v", result.Files, want)
	}
	for _, name := range []string{"original-name.mblevel.json", "cover-7f3.png", "biome-9k1.jpg"} {
		if ppathIsFile(filepath.Join(game, "UserData", "Levels", name)) {
			t.Errorf("%s should not be installed under its source name", name)
		}
	}
}

// The whole archive has to be proven before the installed pack is replaced, so a
// member that only fails when it is read leaves no half pack behind.
func TestInstallPackLeavesNothingWhenAReadFails(t *testing.T) {
	game := t.TempDir()
	good := zipOf(t, "good.zip", [][2]string{
		{"thps/manifest.json", `{"id":"thps","name":"THPS","author":"user","version":"1","assets":["a"]}`},
		{"thps/thps", "installed bundle"},
	})
	if _, err := InstallPackFromZip(game, "thps", "1", good); err != nil {
		t.Fatal(err)
	}

	broken := zipOf(t, "broken.zip", [][2]string{
		{"thps/manifest.json", `{"id":"thps","name":"THPS","author":"user","version":"1","assets":["a"]}`},
		{"thps/thps", "new bundle"},
	})
	truncated := truncateMember(t, broken, "thps/thps")
	if _, err := InstallPackFromZip(game, "thps", "2", truncated); err == nil {
		t.Fatal("a member shorter than its header promised must be refused")
	}
	if got := read(t, filepath.Join(game, "UserData", "LevelPacks", "thps", "thps")); got != "installed bundle" {
		t.Errorf("the installed pack should survive a refused archive, got %q", got)
	}
	if ppathIsFile(filepath.Join(game, "UserData", "LevelPacks", "thps", "manifest.json")) {
		if version := read(t, filepath.Join(game, "UserData", "LevelPacks", "thps", "manifest.json")); !strings.Contains(version, `"1"`) {
			t.Errorf("the manifest was replaced by the refused archive: %s", version)
		}
	}
}

// truncateMember stores fewer bytes than the member's header declares.
func truncateMember(t *testing.T, archive, wanted string) string {
	t.Helper()
	reader, err := zip.OpenReader(archive)
	if err != nil {
		t.Fatal(err)
	}
	defer reader.Close()
	out := filepath.Join(t.TempDir(), "truncated.zip")
	handle, err := os.Create(out)
	if err != nil {
		t.Fatal(err)
	}
	writer := zip.NewWriter(handle)
	for _, member := range reader.File {
		body := readMember(t, member)
		header := &zip.FileHeader{Name: member.Name, Method: zip.Store}
		header.SetMode(member.Mode())
		header.CRC32 = member.CRC32
		header.UncompressedSize64 = uint64(len(body))
		header.CompressedSize64 = uint64(len(body))
		written, err := writer.CreateRaw(header)
		if err != nil {
			t.Fatal(err)
		}
		if member.Name == wanted && len(body) > 4 {
			body = body[:4]
		}
		if _, err := written.Write(body); err != nil {
			t.Fatal(err)
		}
	}
	if err := writer.Close(); err != nil {
		t.Fatal(err)
	}
	if err := handle.Close(); err != nil {
		t.Fatal(err)
	}
	return out
}
