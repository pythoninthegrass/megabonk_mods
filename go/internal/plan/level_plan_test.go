package plan

import (
	"archive/zip"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"reflect"
	"strconv"
	"strings"
	"testing"

	"github.com/pythoninthegrass/megabonk_mods/installer/internal/content"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/gamebuild"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/modinstall"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ppath"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/proton"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/site"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/thunderstore"
)

const (
	stubCode       = "7N1-MVB-WKF"
	stubLevelBody  = `{"schema":2,"title":"THPS: Warehouse"}`
	stubCover      = "cover-bytes"
	stubBiome      = "biome-bytes"
	stubModVersion = "0.2.0"
	stubPackVer    = "1.2.0"
	stubBepInExVer = "9.9.9"
)

type gallery struct {
	server    *httptest.Server
	items     string
	packBody  map[string][]byte
	packFail  map[string]int
	levelBody string
	requests  []string
}

// matches reports whether a level record answers the filter the client asked
// for, so a gallery holding several levels answers each lookup with the one the
// player named.
func recordMatches(item, filter string) bool {
	field, value, found := strings.Cut(filter, "=")
	if !found {
		return true
	}
	value = strings.Trim(value, "'()")
	switch field {
	case "code":
		return strings.Contains(item, `"code":"`+value+`"`)
	case "level":
		return strings.Contains(item, `"level":"`+value+`"`)
	}
	return true
}

// filterOf pulls the filter out of the query the client sent.
func filterOf(request *http.Request) string {
	filter := request.URL.Query().Get("filter")
	if filter == "" {
		return ""
	}
	inner := strings.TrimSuffix(strings.TrimPrefix(filter, "("), ")")
	field, value, found := strings.Cut(inner, "=")
	if !found {
		return ""
	}
	return field + "=" + strings.Trim(value, "'")
}

func newGallery(t *testing.T) *gallery {
	t.Helper()
	stub := &gallery{packBody: map[string][]byte{}, packFail: map[string]int{}}
	stub.items = `[{"id":"lv1","code":"` + stubCode + `","title":"THPS: Warehouse (v2)",` +
		`"level":"thps-warehouse.mblevel.json","cover":"cover.png","biome":"biome.png",` +
		`"packs":{"thps":"` + stubPackVer + `"}}]`
	stub.levelBody = stubLevelBody
	stub.packBody["thps"] = packZip(t, "thps")
	stub.server = httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		path := request.URL.Path
		stub.requests = append(stub.requests, path)
		switch {
		case path == "/api/collections/levels/records":
			filter := filterOf(request)
			matched := []string{}
			for _, item := range splitRecords(stub.items) {
				if filter == "" || recordMatches(item, filter) {
					matched = append(matched, item)
				}
			}
			writer.Header().Set("Content-Type", "application/json")
			fmt.Fprint(writer, `{"page":1,"perPage":30,"totalItems":`+
				strconv.Itoa(len(matched))+`,"items":[`+strings.Join(matched, ",")+`]}`)
		case strings.HasPrefix(path, "/api/p/") && strings.HasSuffix(path, "/download"):
			packID := strings.TrimSuffix(strings.TrimPrefix(path, "/api/p/"), "/download")
			if code, failed := stub.packFail[packID]; failed {
				http.Error(writer, "upstream said no", code)
				return
			}
			body, hosted := stub.packBody[packID]
			if !hosted {
				http.Error(writer, "Pack not found for that platform.", http.StatusNotFound)
				return
			}
			writer.Header().Set("Content-Type", "application/zip")
			_, _ = writer.Write(body)
		case path == "/api/l/"+stubCode+"/download":
			http.Redirect(writer, request, "/api/files/levels/lv1/thps-warehouse.mblevel.json", http.StatusFound)
		case path == "/api/files/levels/lv1/thps-warehouse.mblevel.json":
			fmt.Fprint(writer, stub.levelBody)
		case path == "/api/files/levels/lv1/cover.png":
			fmt.Fprint(writer, stubCover)
		case path == "/api/files/levels/lv1/biome.png":
			fmt.Fprint(writer, stubBiome)
		default:
			http.Error(writer, "unexpected path "+path, http.StatusNotFound)
		}
	}))
	t.Cleanup(stub.server.Close)
	return stub
}

// splitRecords breaks the gallery's items document into one string per record.
func splitRecords(items string) []string {
	inner := strings.TrimSpace(items)
	inner = strings.TrimPrefix(inner, "[")
	inner = strings.TrimSuffix(inner, "]")
	if strings.TrimSpace(inner) == "" {
		return nil
	}
	parts := []string{}
	depth, start := 0, 0
	for index := 0; index < len(inner); index++ {
		switch inner[index] {
		case '{':
			if depth == 0 {
				start = index
			}
			depth++
		case '}':
			depth--
			if depth == 0 {
				parts = append(parts, inner[start:index+1])
			}
		}
	}
	return parts
}

func (g *gallery) count(path string) int {
	total := 0
	for _, seen := range g.requests {
		if seen == path {
			total++
		}
	}
	return total
}

func (g *gallery) client() *site.Client { return site.NewClient(g.server.URL) }

type store struct {
	server     *httptest.Server
	packBody   []byte
	modBody    []byte
	packDigest string
	modDigest  string
}

func newStore(t *testing.T) *store {
	t.Helper()
	stub := &store{}
	stub.packBody = slurpBytes(t, writeZipArchive(t, filepath.Join(t.TempDir(), "pack.zip"), [][2]string{
		{"BepInExPack/doorstop_config.ini", "[UnityDoorstop]"},
		{"BepInExPack/winhttp.dll", "winhttp proxy"},
		{"BepInExPack/BepInEx/core/BepInEx.dll", "core"},
		{"BepInExPack/BepInEx/core/BepInEx.Unity.IL2CPP.dll", "il2cpp core"},
		{"BepInExPack/dotnet/coreclr.dll", "coreclr"},
		{"BepInExPack/dotnet/host/fxr/6.0.36/libhostfxr.dylib", "hostfxr dylib"},
		{"BepInExPack/dotnet/shared/Microsoft.NETCore.App/6.0.36/System.Private.CoreLib.dll", "corelib"},
		{"BepInExPack/BepInEx/core/0Harmony.dll", "harmony"},
		{"BepInExPack/run_winhttp.bepinex.cmd", "launch"},
		{"BepInExPack/dotnet/host/fxr/6.0.36/hostfxr.dll", "hostfxr"},
		{"BepInExPack/.doorstop_version", "3.5.2"},
		{"BepInExPack/changelog.txt", "6.0.788"},
	}))
	stub.packDigest = digestText(stub.packBody)
	stub.modBody = slurpBytes(t, writeZipArchive(t, filepath.Join(t.TempDir(), "mod.zip"), [][2]string{
		{"manifest.json", `{"name":"MegabonkLevels"}`},
		{"BepInEx/plugins/MegabonkLevels/MegabonkLevels.Mod.dll", "mod dll"},
		{"BepInEx/plugins/MegabonkLevels/NLayer.dll", "nlayer"},
		{"BepInEx/plugins/MegabonkLevels/NLayer.LICENSE.txt", "license"},
	}))
	stub.modDigest = digestText(stub.modBody)
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		path := request.URL.Path
		switch {
		case strings.HasPrefix(path, "/api/experimental/package/"):
			metadata, err := json.Marshal(map[string]any{
				"namespace": thunderstore.ModNamespace,
				"name":      thunderstore.ModName,
				"latest": map[string]any{
					"namespace":      thunderstore.ModNamespace,
					"name":           thunderstore.ModName,
					"version_number": stubModVersion,
					"full_name":      thunderstore.ModNamespace + "-" + thunderstore.ModName + "-" + stubModVersion,
					"dependencies":   []string{"BepInEx-BepInExPack_IL2CPP-" + stubBepInExVer},
					"download_url": "https://thunderstore.io/package/download/" + thunderstore.ModNamespace +
						"/" + thunderstore.ModName + "/" + stubModVersion + "/",
				},
			})
			if err != nil {
				http.Error(writer, err.Error(), http.StatusInternalServerError)
				return
			}
			writer.Header().Set("Content-Type", "application/json")
			_, _ = writer.Write(metadata)
		case strings.Contains(path, "BepInEx-BepInExPack_IL2CPP-"+stubBepInExVer+".zip"):
			_, _ = writer.Write(stub.packBody)
		case strings.Contains(path, "Megabonk_Level_Editor-"+stubModVersion+".zip"):
			_, _ = writer.Write(stub.modBody)
		default:
			http.Error(writer, "unexpected path "+path, http.StatusNotFound)
		}
	}))
	t.Cleanup(server.Close)
	stub.server = server
	return stub
}

func (s *store) client() *thunderstore.Client {
	return thunderstore.NewClient(s.server.URL, s.server.URL)
}

func packZip(t *testing.T, packID string) []byte {
	t.Helper()
	return slurpBytes(t, writeZipArchive(t, filepath.Join(t.TempDir(), packID+".zip"), [][2]string{
		{packID + "/manifest.json", `{"id":"` + packID + `","name":"THPS","author":"a","version":"1","assets":["a"]}`},
		{packID + "/" + packID, "bundle bytes"},
	}))
}

func writeZipArchive(t *testing.T, path string, entries [][2]string) string {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	handle, err := os.Create(path)
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
	return path
}

func slurpBytes(t *testing.T, path string) []byte {
	t.Helper()
	body, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	return body
}

func digestText(body []byte) string {
	sum := sha256.Sum256(body)
	return hex.EncodeToString(sum[:])
}

func readText(t *testing.T, path string) string {
	t.Helper()
	body, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	return string(body)
}

func vanillaDir(t *testing.T) string {
	t.Helper()
	game := filepath.Join(t.TempDir(), "Megabonk")
	write(t, filepath.Join(game, "Megabonk.exe"), "MZ")
	if err := os.MkdirAll(filepath.Join(game, "Megabonk_Data"), 0o755); err != nil {
		t.Fatal(err)
	}
	return game
}

func mustPlan(t *testing.T, options Options) *Plan {
	t.Helper()
	built, err := BuildPlan(options)
	if err != nil {
		t.Fatalf("BuildPlan: %v", err)
	}
	return built
}

func details(actions []Action) []string {
	out := []string{}
	for _, action := range actions {
		out = append(out, action.Kind+" "+action.Label())
	}
	return out
}

func find(actions []Action, kind string) []Action {
	found := []Action{}
	for _, action := range actions {
		if action.Kind == kind {
			found = append(found, action)
		}
	}
	return found
}

func walkedFiles(t *testing.T, root string) []string {
	t.Helper()
	found := []string{}
	_ = filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		if err == nil && !info.IsDir() {
			if relative, relErr := filepath.Rel(root, path); relErr == nil {
				found = append(found, filepath.ToSlash(relative))
			}
		}
		return nil
	})
	return found
}

func TestPlanAcceptsShareCodesURLsAndLocalFiles(t *testing.T) {
	gallery := newGallery(t)
	game := vanillaDir(t)
	// A file with its own name is its own level: the gallery only holds a record
	// for thps-warehouse, so this one installs with no packs of its own.
	local := write(t, filepath.Join(t.TempDir(), "home-ramp.mblevel.json"), `{"schema":2,"title":"Home Ramp"}`)
	built := mustPlan(t, Options{
		APIClient: gallery.client(),
		Game:      game,
		Mod:       ModRefused,
		Inputs: []Input{
			{Raw: stubCode},
			{Raw: "https://megabonkmod.party/l/" + stubCode},
			{Raw: local},
		},
	})
	levels := find(built.Actions, "install-level")
	if len(levels) != 2 {
		t.Fatalf("one hosted level plus one local file: %v", details(built.Actions))
	}
	if !strings.Contains(levels[0].Label(), "thps-warehouse") {
		t.Errorf("first level = %s", levels[0].Label())
	}
	if !strings.Contains(levels[1].Label(), "home-ramp") {
		t.Errorf("second level = %s", levels[1].Label())
	}
	if got := len(find(built.Actions, "install-pack")); got != 1 {
		t.Errorf("packs = %v", details(built.Actions))
	}
	if got := len(find(built.Actions, "install-image")); got != 2 {
		t.Errorf("images = %v, want the hosted level's cover and biome", details(built.Actions))
	}
	if got := len(find(built.Actions, "install-mod")); got != 0 {
		t.Errorf("mod actions = %v", details(built.Actions))
	}
	if built.LaunchOption != nil {
		t.Errorf("a run with no mod has no launch option, got %v", *built.LaunchOption)
	}
	// The plan is what the player confirms, so it promises one counting-route
	// download per distinct level: the two spellings of the hosted level are one
	// step, and the local file is the other, read from disk.
	fetches := find(built.Actions, "fetch-level")
	if len(fetches) != 2 {
		t.Fatalf("fetch steps = %v", details(built.Actions))
	}
	routes := 0
	for _, fetch := range fetches {
		if strings.Contains(fetch.Source, "/api/l/") {
			routes++
		}
	}
	if routes != 1 {
		t.Errorf("a level asked for as a code and as a link is downloaded once; routes = %d", routes)
	}
}

func TestLocalLevelResolvesItsPacksFromTheSite(t *testing.T) {
	gallery := newGallery(t)
	game := vanillaDir(t)
	local := write(t, filepath.Join(t.TempDir(), "thps-warehouse.mblevel.json"), stubLevelBody)
	built := mustPlan(t, Options{APIClient: gallery.client(), Game: game, Inputs: []Input{{Raw: local}}})
	if got := len(find(built.Actions, "install-pack")); got != 1 {
		t.Errorf("a local level's packs come from the site: %v", details(built.Actions))
	}
	if got := len(find(built.Actions, "install-image")); got != 0 {
		t.Errorf("a local level has no cover unless an image sits beside it: %v", details(built.Actions))
	}
	if got := gallery.count("/api/l/" + stubCode + "/download"); got != 0 {
		t.Errorf("a local level is read from disk, not downloaded again; calls = %d", got)
	}
	write(t, filepath.Join(filepath.Dir(local), "thps-warehouse.png"), "picture")
	withImage := mustPlan(t, Options{APIClient: gallery.client(), Game: game, Inputs: []Input{{Raw: local}}})
	if got := len(find(withImage.Actions, "install-image")); got != 1 {
		t.Errorf("an image beside a local level is installed with it: %v", details(withImage.Actions))
	}
}

func TestModFlagDecidesTheModStep(t *testing.T) {
	gallery := newGallery(t)
	local := write(t, filepath.Join(t.TempDir(), "quiet.mblevel.json"), `{"schema":2}`)
	cases := []struct {
		name    string
		present bool
		mod     ModChoice
		want    int
	}{
		{"asked for", false, ModForced, 1},
		{"asked for, already installed", true, ModForced, 1},
		{"refused", false, ModRefused, 0},
		{"auto, not installed", false, ModAuto, 1},
		{"auto, already installed", true, ModAuto, 0},
	}
	for _, testCase := range cases {
		game := vanillaDir(t)
		if testCase.present {
			for _, name := range []string{content.ModDLLName, content.NLayerName, content.LicenseName} {
				write(t, filepath.Join(game, content.PluginsDir, content.ModFolderName, name), "MZ")
			}
		}
		built := mustPlan(t, Options{APIClient: gallery.client(), Game: game,
			Inputs: []Input{{Raw: local}}, Mod: testCase.mod})
		if got := len(find(built.Actions, "install-mod")); got != testCase.want {
			t.Errorf("%s: install-mod steps = %d, want %d: %v", testCase.name, got, testCase.want, details(built.Actions))
		}
	}
}

func TestPackSharedBySeveralLevelsIsFetchedOnce(t *testing.T) {
	gallery := newGallery(t)
	gallery.items = `[{"id":"lv1","code":"1QN-111-AAA","title":"One","level":"one.mblevel.json",` +
		`"cover":"","biome":"","packs":{"thps":"` + stubPackVer + `"}},` +
		`{"id":"lv2","code":"2TW-222-BBB","title":"Two","level":"two.mblevel.json",` +
		`"cover":"","biome":"","packs":{"thps":"` + stubPackVer + `"}}]`
	game := vanillaDir(t)
	built := mustPlan(t, Options{APIClient: gallery.client(), Game: game,
		Inputs: []Input{{Raw: "1QN-111-AAA"}, {Raw: "2TW-222-BBB"}}, Mod: ModRefused})
	if got := len(find(built.Actions, "install-level")); got != 2 {
		t.Fatalf("levels = %v", details(built.Actions))
	}
	packs := find(built.Actions, "install-pack")
	if len(packs) != 1 {
		t.Fatalf("packs = %v", details(built.Actions))
	}
	if !strings.Contains(packs[0].Detail, "thps") {
		t.Errorf("pack detail = %q", packs[0].Detail)
	}
}

func TestPackAlreadyInstalledAtThatVersionIsSkipped(t *testing.T) {
	gallery := newGallery(t)
	game := vanillaDir(t)
	built := mustPlan(t, Options{APIClient: gallery.client(), Game: game, Inputs: []Input{{Raw: stubCode}}, Mod: ModRefused})
	if got := len(find(built.Actions, "install-pack")); got != 1 {
		t.Fatalf("packs = %v", details(built.Actions))
	}
	if _, err := ApplyPlan(built, nil); err != nil {
		t.Fatal(err)
	}
	again := mustPlan(t, Options{APIClient: gallery.client(), Game: game,
		Inputs: []Input{{Raw: stubCode}}, Mod: ModRefused})
	if got := len(find(again.Actions, "install-pack")); got != 0 {
		t.Errorf("a pack installed at the required version is skipped: %v", details(again.Actions))
	}
	if !again.IsNoop() {
		t.Errorf("a second run with nothing changed is a no-op: %v", details(again.Actions))
	}
}

func TestPackAtANewVersionIsInstalledAgain(t *testing.T) {
	gallery := newGallery(t)
	game := vanillaDir(t)
	first := mustPlan(t, Options{APIClient: gallery.client(), Game: game, Inputs: []Input{{Raw: stubCode}}, Mod: ModRefused})
	if _, err := ApplyPlan(first, nil); err != nil {
		t.Fatal(err)
	}
	gallery.items = `[{"id":"lv1","code":"` + stubCode + `","title":"THPS: Warehouse (v2)",` +
		`"level":"thps-warehouse.mblevel.json","cover":"","biome":"","packs":{"thps":"1.3.0"}}]`
	second := mustPlan(t, Options{APIClient: gallery.client(), Game: game,
		Inputs: []Input{{Raw: stubCode}}, Mod: ModRefused})
	if got := len(find(second.Actions, "install-pack")); got != 1 {
		t.Errorf("a pack at a new version is installed again: %v", details(second.Actions))
	}
}

func TestUnhostedPackStillInstallsTheLevelAndWarns(t *testing.T) {
	gallery := newGallery(t)
	gallery.packFail["thps"] = http.StatusNotFound
	game := vanillaDir(t)
	built := mustPlan(t, Options{APIClient: gallery.client(), Game: game,
		Inputs: []Input{{Raw: stubCode}}, Mod: ModRefused})
	if got := len(find(built.Actions, "install-level")); got != 1 {
		t.Errorf("the level still installs: %v", details(built.Actions))
	}
	if got := len(find(built.Actions, "install-pack")); got != 0 {
		t.Errorf("an unhosted pack is not an action: %v", details(built.Actions))
	}
	if len(built.Warnings) == 0 || !strings.Contains(built.Warnings[0], "thps") {
		t.Errorf("warnings = %v", built.Warnings)
	}
	if _, err := ApplyPlan(built, nil); err != nil {
		t.Fatal(err)
	}
	want := filepath.Join(game, content.UserData, content.LevelsDir, "thps-warehouse.mblevel.json")
	if !ppath.IsFile(want) {
		t.Error("the level was not installed alongside the missing pack")
	}
}

func TestUnreachableSiteIsNotReportedAsAMissingPack(t *testing.T) {
	_, err := BuildPlan(Options{
		APIClient: site.NewClient("http://127.0.0.1:1"),
		Game:      vanillaDir(t),
		Inputs:    []Input{{Raw: stubCode}},
	})
	if err == nil {
		t.Fatal("an unreachable site must not read as a missing level")
	}
	if !strings.Contains(err.Error(), "cannot reach") {
		t.Errorf("err = %v", err)
	}
}

func TestUnknownShareCodeNamesTheCode(t *testing.T) {
	gallery := newGallery(t)
	gallery.items = `[]`
	_, err := BuildPlan(Options{APIClient: gallery.client(), Game: vanillaDir(t), Inputs: []Input{{Raw: stubCode}}})
	if err == nil {
		t.Fatal("an unknown code is an error")
	}
	if !strings.Contains(err.Error(), "level not found") || !strings.Contains(err.Error(), stubCode) {
		t.Errorf("err = %v", err)
	}
}

func TestBadLocalFileIsRefusedBeforeTheSiteIsAsked(t *testing.T) {
	gallery := newGallery(t)
	bad := write(t, filepath.Join(t.TempDir(), "broken.mblevel.json"), `{"schema": "two"}`)
	_, err := BuildPlan(Options{APIClient: gallery.client(), Game: vanillaDir(t), Inputs: []Input{{Raw: bad}}})
	if err == nil || !strings.Contains(err.Error(), "'schema' must be an integer") {
		t.Errorf("err = %v", err)
	}
}

func TestNoInputsIsAnError(t *testing.T) {
	gallery := newGallery(t)
	_, err := BuildPlan(Options{APIClient: gallery.client(), Game: vanillaDir(t)})
	if err == nil || !strings.Contains(err.Error(), "nothing to install") {
		t.Errorf("err = %v", err)
	}
}

func TestPlanRefusesANativeLinuxBuild(t *testing.T) {
	gallery := newGallery(t)
	game := filepath.Join(t.TempDir(), "Megabonk")
	write(t, filepath.Join(game, content.NativeExeName), "ELF")
	if err := os.MkdirAll(filepath.Join(game, "Megabonk_Data"), 0o755); err != nil {
		t.Fatal(err)
	}
	local := write(t, filepath.Join(t.TempDir(), "quiet.mblevel.json"), `{"schema":2}`)
	_, err := BuildPlan(Options{APIClient: gallery.client(), Game: game, Inputs: []Input{{Raw: local}}})
	if err == nil {
		t.Fatal("a native Linux build is refused")
	}
	// The refusal is typed, so the exit code can single it out from any other
	// plan-level failure.
	if !IsUnsupportedBuild(err) {
		t.Fatalf("err = %T %v", err, err)
	}
	var unsupported *UnsupportedBuildError
	if !errors.As(err, &unsupported) {
		t.Fatalf("err = %T %v", err, err)
	}
	if !strings.Contains(err.Error(), gamebuild.NativeExe) {
		t.Errorf("the refusal should be gamebuild's: %v", err)
	}
	if gamebuild.Classify(game).Kind != gamebuild.NativeLinux {
		t.Fatal("the fixture is not a native build")
	}
}

func TestBuildingAPlanChangesNothingOnDisk(t *testing.T) {
	gallery := newGallery(t)
	thunder := newStore(t)
	game := vanillaDir(t)
	before := walkedFiles(t, game)
	built := mustPlan(t, Options{
		APIClient: gallery.client(),
		Thunder:   thunder.client(),
		Pins:      map[string]string{stubBepInExVer: thunder.packDigest},
		ModPins:   []modinstall.ModPin{{Version: stubModVersion, SHA256: thunder.modDigest}},
		Game:      game,
		Inputs:    []Input{{Raw: stubCode}},
		Mod:       ModForced,
		Platform:  platformNative,
	})
	if len(find(built.Actions, "install-mod")) != 1 {
		t.Fatalf("actions = %v", details(built.Actions))
	}
	if after := walkedFiles(t, game); !reflect.DeepEqual(before, after) {
		t.Errorf("building a plan changed the game directory: %v -> %v", before, after)
	}
}

func TestApplyPlacesLevelsImagesPacksAndTheRecord(t *testing.T) {
	gallery := newGallery(t)
	game := vanillaDir(t)
	built := mustPlan(t, Options{APIClient: gallery.client(), Game: game,
		Inputs: []Input{{Raw: stubCode}}, Mod: ModRefused})
	taken, err := ApplyPlan(built, nil)
	if err != nil {
		t.Fatal(err)
	}
	if len(taken) != len(built.Actions) {
		t.Errorf("taken = %d of %d", len(taken), len(built.Actions))
	}
	for _, name := range []string{
		"UserData/Levels/thps-warehouse.mblevel.json",
		"UserData/Levels/thps-warehouse.png",
		"UserData/Levels/thps-warehouse.biome.png",
		"UserData/LevelPacks/thps/manifest.json",
		"UserData/LevelPacks/thps/thps",
	} {
		if !ppath.IsFile(filepath.Join(game, filepath.FromSlash(name))) {
			t.Errorf("%s was not installed", name)
		}
	}
	if body := readText(t, filepath.Join(game, "UserData", "Levels", "thps-warehouse.mblevel.json")); body != stubLevelBody {
		t.Errorf("level body = %q", body)
	}
	record := content.LoadRecord(game)
	if record == nil {
		t.Fatal("no install record")
	}
	if !record.HasLevel("thps-warehouse") {
		t.Errorf("record levels = %v", record.LevelCodes())
	}
	if !record.HasPack("thps") || record.Packs["thps"].Version != stubPackVer {
		t.Errorf("record packs = %+v", record.Packs)
	}
}

func TestCancelPartWayRollsBackTheFilesAlreadyWritten(t *testing.T) {
	gallery := newGallery(t)
	game := vanillaDir(t)
	built := mustPlan(t, Options{APIClient: gallery.client(), Game: game,
		Inputs: []Input{{Raw: stubCode}}, Mod: ModRefused})
	built.Actions = append(built.Actions, Action{
		Kind: KindInstallImage, Path: ppath.Join(content.UserData, content.LevelsDir, "doomed.png"),
		Detail: "doomed",
	})
	progress := &recordingProgress{cancelAfter: 2}
	_, err := ApplyPlan(built, progress)
	if !errors.Is(err, ErrCancelled) {
		t.Fatalf("err = %v", err)
	}
	if len(progress.steps) != 2 {
		t.Errorf("steps = %v, want exactly the two that ran", progress.steps)
	}
	if left := walkedFiles(t, game); len(left) != 1 || left[0] != "Megabonk.exe" {
		t.Errorf("the rollback left %v behind", left)
	}
	if content.LoadRecord(game) != nil {
		t.Error("the rollback left an install record behind")
	}
	if !ppath.IsFile(filepath.Join(game, "Megabonk.exe")) {
		t.Error("the game's own files must survive")
	}
}

func TestFailurePartWayRollsBackTheFilesAlreadyWritten(t *testing.T) {
	gallery := newGallery(t)
	thunder := newStore(t)
	game := vanillaDir(t)
	built := mustPlan(t, Options{
		APIClient: gallery.client(),
		Thunder:   thunder.client(),
		Pins:      map[string]string{stubBepInExVer: strings.Repeat("00", 32)},
		ModPins:   []modinstall.ModPin{{Version: stubModVersion, SHA256: thunder.modDigest}},
		Game:      game,
		Inputs:    []Input{{Raw: stubCode}},
		Mod:       ModForced,
		Platform:  platformNative,
	})
	if _, err := ApplyPlan(built, nil); err == nil {
		t.Fatal("a pack whose digest does not match must fail the run")
	}
	if left := walkedFiles(t, game); len(left) != 1 || left[0] != "Megabonk.exe" {
		t.Errorf("a failed run left %v behind", left)
	}
	if content.LoadRecord(game) != nil {
		t.Error("a failed run left an install record behind")
	}
}

func TestUninstallRemovesOnlyWhatTheRecordLists(t *testing.T) {
	gallery := newGallery(t)
	thunder := newStore(t)
	game := vanillaDir(t)
	built := mustPlan(t, Options{
		APIClient: gallery.client(),
		Thunder:   thunder.client(),
		Pins:      map[string]string{stubBepInExVer: thunder.packDigest},
		ModPins:   []modinstall.ModPin{{Version: stubModVersion, SHA256: thunder.modDigest}},
		Game:      game,
		Inputs:    []Input{{Raw: stubCode}},
		Mod:       ModForced,
		Platform:  platformNative,
	})
	if _, err := ApplyPlan(built, nil); err != nil {
		t.Fatal(err)
	}
	ownLevel := filepath.Join(game, content.UserData, content.LevelsDir, "mine.mblevel.json")
	write(t, ownLevel, `{"schema":2,"title":"Mine"}`)
	ownPack := filepath.Join(game, content.UserData, content.LevelPacksDir, "mine", "manifest.json")
	write(t, ownPack, `{"id":"mine"}`)
	ownMod := filepath.Join(game, content.BepInExDir, "plugins", "Other", "Other.dll")
	write(t, ownMod, "MZ")

	removed, err := Uninstall(game, nil)
	if err != nil {
		t.Fatal(err)
	}
	// Uninstall removes what the record names: the content this run placed, and
	// the loader and plugin files it placed too. What it never recorded stays.
	for _, want := range []string{
		"UserData/LevelPacks/thps",
		"UserData/Levels/thps-warehouse.biome.png",
		"UserData/Levels/thps-warehouse.mblevel.json",
		"UserData/Levels/thps-warehouse.png",
		content.PluginsDir + "/" + content.ModFolderName,
		content.WinHTTPProxyName,
		content.DoorstopConfigName,
	} {
		if !contains(removed, want) {
			t.Errorf("%s was not reported as removed: %v", want, removed)
		}
	}
	for _, kept := range []string{ownLevel, ownPack, ownMod, filepath.Join(game, "Megabonk.exe")} {
		if !ppath.IsFile(kept) {
			t.Errorf("%s was removed", kept)
		}
	}
	if content.LoadRecord(game) != nil {
		t.Error("the record survived a complete uninstall")
	}
	if ppath.IsDir(filepath.Join(game, content.UserData, content.LevelPacksDir, "thps")) {
		t.Error("the recorded pack folder survived")
	}
	again, err := Uninstall(game, nil)
	if err != nil || len(again) != 0 {
		t.Errorf("a second uninstall removed %v (%v)", again, err)
	}
}

func TestUninstallLeavesAForeignModAlone(t *testing.T) {
	game := vanillaDir(t)
	mod := filepath.Join(game, content.BepInExDir, "plugins", content.ModFolderName, content.ModDLLName)
	write(t, mod, "MZ")
	removed, err := Uninstall(game, nil)
	if err != nil {
		t.Fatal(err)
	}
	if len(removed) != 0 {
		t.Errorf("removed = %v with no record", removed)
	}
	if !ppath.IsFile(mod) {
		t.Error("a mod this installer never recorded was removed")
	}
}

func TestModInstallPlacesTheLoaderAndThePlugin(t *testing.T) {
	gallery := newGallery(t)
	thunder := newStore(t)
	game := vanillaDir(t)
	built := mustPlan(t, Options{
		APIClient: gallery.client(),
		Thunder:   thunder.client(),
		Pins:      map[string]string{stubBepInExVer: thunder.packDigest},
		ModPins:   []modinstall.ModPin{{Version: stubModVersion, SHA256: thunder.modDigest}},
		Game:      game,
		Inputs:    []Input{{Raw: stubCode}},
		Mod:       ModForced,
		Platform:  platformNative,
	})
	if _, err := ApplyPlan(built, nil); err != nil {
		t.Fatal(err)
	}
	for _, name := range []string{
		content.PluginsDir + "/" + content.ModFolderName + "/" + content.ModDLLName,
		content.PluginsDir + "/" + content.ModFolderName + "/" + content.NLayerName,
		content.WinHTTPProxyName,
		content.DoorstopConfigName,
		"UserData/Levels/thps-warehouse.mblevel.json",
	} {
		if !ppath.IsFile(filepath.Join(game, filepath.FromSlash(name))) {
			t.Errorf("%s was not installed", name)
		}
	}
	record := content.LoadRecord(game)
	if record == nil || record.Loader == nil || !record.Loader.Installed || record.ModVersion != stubModVersion {
		t.Fatalf("record = %+v", record)
	}
	if !record.HasLevel("thps-warehouse") || !record.HasPack("thps") {
		t.Errorf("the record lost its content: %+v", record)
	}
	removed, err := Uninstall(game, nil)
	if err != nil {
		t.Fatal(err)
	}
	if ppath.IsFile(filepath.Join(game, filepath.FromSlash(content.PluginsDir+"/"+content.ModFolderName+"/"+content.ModDLLName))) {
		t.Error("the plugin survived the uninstall")
	}
	if len(removed) == 0 {
		t.Error("nothing was reported as removed")
	}
}

func TestDocumentDescribesThePlanForJSON(t *testing.T) {
	gallery := newGallery(t)
	gallery.packFail["thps"] = http.StatusNotFound
	game := vanillaDir(t)
	built := mustPlan(t, Options{APIClient: gallery.client(), Game: game, Inputs: []Input{{Raw: stubCode}}})
	document := built.Document()
	if document.GameDir != ppath.Normalize(game) {
		t.Errorf("game_dir = %q", document.GameDir)
	}
	if len(document.Actions) != len(built.Actions) {
		t.Errorf("actions = %v", document.Actions)
	}
	if document.Warnings == nil {
		t.Error("warnings should marshal as a list, not null")
	}
	kinds := []string{}
	for _, action := range document.Actions {
		kinds = append(kinds, action.Kind)
	}
	if !contains(kinds, "install-level") {
		t.Errorf("document kinds = %v", kinds)
	}
	body, err := json.Marshal(document)
	if err != nil {
		t.Fatal(err)
	}
	for _, want := range []string{`"actions"`, `"warnings"`, `"game_dir"`, `"levels"`, `"packs"`} {
		if !strings.Contains(string(body), want) {
			t.Errorf("document JSON has no %s: %s", want, body)
		}
	}
}

func TestProgressReportsEveryPlannedStep(t *testing.T) {
	gallery := newGallery(t)
	game := vanillaDir(t)
	built := mustPlan(t, Options{APIClient: gallery.client(), Game: game, Inputs: []Input{{Raw: stubCode}}, Mod: ModRefused})
	progress := &recordingProgress{cancelAfter: -1}
	if _, err := ApplyPlan(built, progress); err != nil {
		t.Fatal(err)
	}
	if len(progress.steps) != len(built.Actions) {
		t.Errorf("steps = %v, want one per action %v", progress.steps, details(built.Actions))
	}
	if len(progress.finishes) != 1 {
		t.Errorf("finishes = %v", progress.finishes)
	}
}

func TestUninstallClearsAnOverrideOnlyRecord(t *testing.T) {
	thunder := newStore(t)
	game := vanillaDir(t)
	prefix := filepath.Join(t.TempDir(), "compatdata", "3405340", "pfx")
	if err := os.MkdirAll(filepath.Join(prefix, "drive_c"), 0o755); err != nil {
		t.Fatal(err)
	}
	built := mustPlan(t, Options{
		Thunder:  thunder.client(),
		Pins:     map[string]string{stubBepInExVer: thunder.packDigest},
		Game:     game,
		Prefix:   prefix,
		Platform: platformWine,
		Inputs:   []Input{{Raw: write(t, filepath.Join(t.TempDir(), "quiet.mblevel.json"), `{"schema":2}`)}},
		Mod:      ModForced,
		ModOwned: true,
	})
	if _, err := ApplyPlan(built, nil); err != nil {
		t.Fatal(err)
	}
	if !proton.WinHTTPOverrideApplied(prefix) {
		t.Fatal("the wine prefix has no winhttp override")
	}
	if _, err := Uninstall(game, nil); err != nil {
		t.Fatal(err)
	}
	if proton.WinHTTPOverrideApplied(prefix) {
		t.Error("the override survived the uninstall")
	}
	if content.LoadRecord(game) != nil {
		t.Errorf("the record survived: %+v", content.LoadRecord(game))
	}
}

// recordingProgress records the reporter calls and reports a cancellation once
// the given number of steps have run, so a test can stop ApplyPlan or
// Uninstall between actions.
type recordingProgress struct {
	steps       []string
	finishes    []string
	cancelAfter int
}

func (r *recordingProgress) Start(int, string) {}
func (r *recordingProgress) Step(label string) { r.steps = append(r.steps, label) }
func (r *recordingProgress) Finish(message string, ok bool) {
	r.finishes = append(r.finishes, message)
}

// Cancelled reports a stop request only for a test that asked for one: a
// cancellable reporter is asked between every step, so counting steps is not a
// way to ask to stop.
func (r *recordingProgress) Cancelled() bool {
	return r.cancelAfter >= 0 && len(r.steps) >= r.cancelAfter
}

func TestCancelBeforeAnyActionChangesNothing(t *testing.T) {
	gallery := newGallery(t)
	game := vanillaDir(t)
	built := mustPlan(t, Options{APIClient: gallery.client(), Game: game, Inputs: []Input{{Raw: stubCode}}})
	if _, err := ApplyPlan(built, &recordingProgress{cancelAfter: 0}); !errors.Is(err, ErrCancelled) {
		t.Fatalf("err = %v, want ErrCancelled", err)
	}
	if content.LoadRecord(game) != nil {
		t.Error("a cancel before the first action must not touch the directory")
	}
}

func TestCancelMidUninstallKeepsTheRecordForTheRerun(t *testing.T) {
	gallery := newGallery(t)
	thunder := newStore(t)
	game := vanillaDir(t)
	// A Wine prefix gives the uninstall a second group to stop before: with no
	// prefix edit to clear, one group is all there is and stopping before the end
	// would leave nothing for a rerun to do.
	built := mustPlan(t, Options{
		APIClient: gallery.client(),
		Thunder:   thunder.client(),
		Pins:      map[string]string{stubBepInExVer: thunder.packDigest},
		ModPins:   []modinstall.ModPin{{Version: stubModVersion, SHA256: thunder.modDigest}},
		Game:      game,
		Inputs:    []Input{{Raw: stubCode}},
		Mod:       ModForced,
		Platform:  platformWine,
		Prefix:    makePrefix(t),
		WineRunner: func(argv []string, env map[string]string) int {
			return 0
		},
	})
	if _, err := ApplyPlan(built, nil); err != nil {
		t.Fatal(err)
	}
	// The loader, then the content, is the one group this installer takes back; the
	// winhttp override is the second. Stopping before that second group has to
	// leave the first done and the record in place, so a rerun can finish.
	progress := &recordingProgress{cancelAfter: 1}
	removed, err := Uninstall(game, progress)
	if !errors.Is(err, ErrCancelled) {
		t.Fatalf("err = %v, want ErrCancelled", err)
	}
	if len(removed) == 0 {
		t.Error("the first uninstall group should have run")
	}
	if content.LoadRecord(game) == nil {
		t.Error("a stopped uninstall must keep the record so a rerun can finish")
	}
	if _, err := Uninstall(game, nil); err != nil {
		t.Fatal(err)
	}
	if content.LoadRecord(game) != nil {
		t.Error("the rerun did not finish the uninstall")
	}
}

// write puts a file on disk and hands back its path.
func write(t *testing.T, path, body string) string {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
	return path
}

func TestPlanCarriesTheModStateIntoTheRecord(t *testing.T) {
	gallery := newGallery(t)
	thunder := newStore(t)
	game := vanillaDir(t)
	built := mustPlan(t, Options{
		APIClient: gallery.client(),
		Thunder:   thunder.client(),
		Pins:      map[string]string{stubBepInExVer: thunder.packDigest},
		ModPins:   []modinstall.ModPin{{Version: stubModVersion, SHA256: thunder.modDigest}},
		Game:      game,
		Inputs:    []Input{{Raw: stubCode}},
		Mod:       ModForced,
		Platform:  platformNative,
	})
	if _, err := ApplyPlan(built, nil); err != nil {
		t.Fatal(err)
	}
	record := content.LoadRecord(game)
	if record == nil {
		t.Fatal("no install record")
	}
	if record.Loader == nil || !record.Loader.Installed {
		t.Errorf("the record does not own the loader: %+v", record.Loader)
	}
	if !record.HasLevel("thps-warehouse") || !record.HasPack("thps") {
		t.Errorf("the record lost its content: %+v", record)
	}
	if len(record.Packs["thps"].Files) == 0 {
		t.Errorf("the pack records no files: %+v", record.Packs["thps"])
	}
	if built.ModVersion != stubModVersion || built.BepInExVersion != stubBepInExVer {
		t.Errorf("mod %q / loader %q", built.ModVersion, built.BepInExVersion)
	}
	if built.ModStatus == nil || !built.ModStatus.Installed {
		t.Errorf("mod status = %+v", built.ModStatus)
	}
}

func TestPlanListsEveryKindForJSON(t *testing.T) {
	gallery := newGallery(t)
	thunder := newStore(t)
	game := vanillaDir(t)
	built := mustPlan(t, Options{
		APIClient: gallery.client(),
		Thunder:   thunder.client(),
		Pins:      map[string]string{stubBepInExVer: thunder.packDigest},
		ModPins:   []modinstall.ModPin{{Version: stubModVersion, SHA256: thunder.modDigest}},
		Game:      game,
		Prefix:    makePrefix(t),
		Platform:  platformWine,
		Inputs:    []Input{{Raw: stubCode}},
		Mod:       ModForced,
	})
	kinds := map[string]int{}
	for _, action := range built.Actions {
		kinds[action.Kind]++
	}
	for _, kind := range []string{KindFetchLevel, KindFetchImage, KindFetchPack, KindInstallLevel,
		KindInstallImage, KindInstallPack, KindInstallMod, KindSetOverride} {
		if kinds[kind] == 0 {
			t.Errorf("no %s step: %v", kind, details(built.Actions))
		}
	}
	// A Wine run edits the prefix itself, so the route is a note rather than a
	// Steam launch option.
	if built.LaunchOption != nil {
		t.Errorf("a wine run has no Steam entry to paste into: %q", *built.LaunchOption)
	}
	if !strings.Contains(built.OverrideNote, proton.WinHTTPDLLName) {
		t.Errorf("OverrideNote = %q", built.OverrideNote)
	}
}

// makePrefix opens a Wine prefix with the drive_c folder the installer insists on.
func makePrefix(t *testing.T) string {
	t.Helper()
	prefix := filepath.Join(t.TempDir(), "compatdata", "3405340", "pfx")
	if err := os.MkdirAll(filepath.Join(prefix, "drive_c"), 0o755); err != nil {
		t.Fatal(err)
	}
	return prefix
}
