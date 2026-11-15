package cli

import (
	"archive/zip"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"testing"

	"github.com/pythoninthegrass/megabonk_mods/installer/internal/site"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/thunderstore"
)

// The CLI tests drive a whole run: a level taken from a gallery, its pack, and
// the mod with the loader it depends on. All three come from local servers, so
// no test reaches the network and a run is reproducible.

const (
	fixtureCode      = "7N1-MVB-WKF"
	fixtureFile      = "thps-warehouse.mblevel.json"
	fixturePackID    = "thps"
	fixturePackVer   = "1.2.0"
	fixtureModVer    = "0.2.0"
	fixtureLoaderVer = "6.0.788"
)

var fixtureLevelBody = `{"schema":2,"title":"THPS: Warehouse"}`

// gallery is the level site: one record, its files, and its pack archives.
type gallery struct {
	server   *httptest.Server
	requests []string
	packs    map[string]bool
}

func newGallery(t *testing.T) *gallery {
	t.Helper()
	stub := &gallery{packs: map[string]bool{fixturePackID: true}}
	stub.server = httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		path := request.URL.Path
		stub.requests = append(stub.requests, path)
		switch {
		case path == site.RecordsSuffix:
			// The gallery holds one level, and answers a lookup only when the
			// filter names it: an unknown code gets the empty page the real API
			// returns, which is what makes "level not found" testable.
			record := `{"id":"lv1","code":"` + fixtureCode + `","title":"THPS: Warehouse",` +
				`"level":"` + fixtureFile + `","cover":"cover.png","biome":"biome.png",` +
				`"packs":{"` + fixturePackID + `":"` + fixturePackVer + `"}}`
			items := []string{}
			if filter := request.URL.Query().Get("filter"); filter == "" ||
				strings.Contains(filter, "'"+fixtureCode+"'") || strings.Contains(filter, "'"+fixtureFile+"'") {
				items = append(items, record)
			}
			writer.Header().Set("Content-Type", "application/json")
			fmt.Fprint(writer, `{"page":1,"perPage":30,"totalItems":`+
				strconv.Itoa(len(items))+`,"items":[`+strings.Join(items, ",")+`]}`)
		case strings.HasPrefix(path, "/api/p/") && strings.HasSuffix(path, "/download"):
			packID := strings.TrimSuffix(strings.TrimPrefix(path, "/api/p/"), "/download")
			if !stub.packs[packID] {
				http.Error(writer, "Pack not found for that platform.", http.StatusNotFound)
				return
			}
			writer.Header().Set("Content-Type", "application/zip")
			_, _ = writer.Write(packBytes(t, packID))
		case path == fmt.Sprintf(site.LevelDownloadSuffix, fixtureCode):
			http.Redirect(writer, request, "/api/files/levels/lv1/"+fixtureFile, http.StatusFound)
		case path == "/api/files/levels/lv1/"+fixtureFile:
			_, _ = writer.Write([]byte(fixtureLevelBody))
		case path == "/api/files/levels/lv1/cover.png":
			_, _ = writer.Write([]byte("cover"))
		case path == "/api/files/levels/lv1/biome.png":
			_, _ = writer.Write([]byte("biome"))
		default:
			http.Error(writer, "unexpected path "+path, http.StatusNotFound)
		}
	}))
	t.Cleanup(stub.server.Close)
	return stub
}

func (g *gallery) client() *site.Client { return site.NewClient(g.server.URL) }

// (g *gallery) downloads returns the paths the site was asked for.
func (g *gallery) downloads() []string { return g.requests }

// store is Thunderstore: the mod's metadata and the two archives it points at.
type store struct {
	server     *httptest.Server
	packDigest string
	modDigest  string
	requests   []string
}

func newStore(t *testing.T) *store {
	t.Helper()
	loader := packArchive(t, "BepInExPack")
	mod := modArchive(t)
	stub := &store{packDigest: digest(loader), modDigest: digest(mod)}
	stub.server = httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		path := request.URL.Path
		stub.requests = append(stub.requests, path)
		switch {
		case strings.Contains(path, "/package/pythoninthegrass/Megabonk_Level_Editor/"):
			metadata, err := json.Marshal(map[string]any{
				"namespace": thunderstore.ModNamespace,
				"name":      thunderstore.ModName,
				"latest": map[string]any{
					"namespace":      thunderstore.ModNamespace,
					"name":           thunderstore.ModName,
					"version_number": fixtureModVer,
					"full_name":      thunderstore.ModNamespace + "-" + thunderstore.ModName + "-" + fixtureModVer,
					"dependencies":   []string{"BepInEx-" + thunderstore.BepInExName + "-" + fixtureLoaderVer},
					"download_url": "https://thunderstore.io/package/download/" + thunderstore.ModNamespace +
						"/" + thunderstore.ModName + "/" + fixtureModVer + "/",
				},
			})
			if err != nil {
				http.Error(writer, err.Error(), http.StatusInternalServerError)
				return
			}
			writer.Header().Set("Content-Type", "application/json")
			_, _ = writer.Write(metadata)
		case strings.Contains(path, "BepInExPack_IL2CPP-"+fixtureLoaderVer+".zip"):
			writer.Header().Set("Content-Type", "application/zip")
			_, _ = writer.Write(loader)
		case strings.Contains(path, "Megabonk_Level_Editor-"+fixtureModVer+".zip"):
			writer.Header().Set("Content-Type", "application/zip")
			_, _ = writer.Write(mod)
		default:
			http.Error(writer, "unexpected path "+path, http.StatusNotFound)
		}
	}))
	t.Cleanup(stub.server.Close)
	return stub
}

func (s *store) client() *thunderstore.Client {
	return thunderstore.NewClient(s.server.URL, s.server.URL)
}

// packArchive is a loader pack: the doorstop config, the proxy, the BepInEx
// cores, and the .NET runtime the loader needs.
func packArchive(t *testing.T, root string) []byte {
	t.Helper()
	return archive(t, [][2]string{
		{root + "/doorstop_config.ini", "[UnityDoorstop]"},
		{root + "/winhttp.dll", "winhttp proxy"},
		{root + "/changelog.txt", fixtureLoaderVer},
		{root + "/.doorstop_version", "3.5.2"},
		{root + "/BepInEx/core/BepInEx.dll", "MZ core"},
		{root + "/BepInEx/core/BepInEx.Unity.IL2CPP.dll", "MZ il2cpp"},
		{root + "/BepInEx/core/0Harmony.dll", "MZ harmony"},
		{root + "/dotnet/coreclr.dll", "MZ coreclr"},
		{root + "/dotnet/host/fxr/6.0.36/hostfxr.dll", "MZ hostfxr"},
		{root + "/dotnet/shared/Microsoft.NETCore.App/6.0.36/System.Private.CoreLib.dll", "MZ corelib"},
	})
}

// modArchive is the level editor's release: its manifest and plugin folder.
func modArchive(t *testing.T) []byte {
	t.Helper()
	return archive(t, [][2]string{
		{"manifest.json", `{"name":"MegabonkLevels","version_number":"` + fixtureModVer + `"}`},
		{"icon.png", "icon"},
		{"BepInEx/plugins/MegabonkLevels/MegabonkLevels.Mod.dll", "MZ mod"},
		{"BepInEx/plugins/MegabonkLevels/NLayer.dll", "MZ nlayer"},
		{"BepInEx/plugins/MegabonkLevels/NLayer.LICENSE.txt", "license"},
	})
}

// packBytes is a level pack's own archive, as the site zips one version.
func packBytes(t *testing.T, packID string) []byte {
	t.Helper()
	return archive(t, [][2]string{
		{packID + "/manifest.json", `{"id":"` + packID + `","name":"` + packID +
			`","author":"a","version":"1","assets":["a"]}`},
		{packID + "/" + packID, "bundle bytes"},
	})
}

func archive(t *testing.T, entries [][2]string) []byte {
	t.Helper()
	path := filepath.Join(t.TempDir(), "archive.zip")
	handle, err := os.Create(path)
	if err != nil {
		t.Fatal(err)
	}
	writer := zip.NewWriter(handle)
	names := make([]string, 0, len(entries))
	for _, entry := range entries {
		names = append(names, entry[0])
	}
	sort.Strings(names)
	byName := map[string]string{}
	for _, entry := range entries {
		byName[entry[0]] = entry[1]
	}
	for _, name := range names {
		member, err := writer.Create(name)
		if err != nil {
			t.Fatal(err)
		}
		if _, err := member.Write([]byte(byName[name])); err != nil {
			t.Fatal(err)
		}
	}
	if err := writer.Close(); err != nil {
		t.Fatal(err)
	}
	if err := handle.Close(); err != nil {
		t.Fatal(err)
	}
	body, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	return body
}

func digest(body []byte) string {
	sum := sha256.Sum256(body)
	return hex.EncodeToString(sum[:])
}
