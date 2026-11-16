package thunderstore

import (
	"archive/zip"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"testing"
)

const (
	bepinexName   = "BepInExPack_IL2CPP"
	bepinexVer    = "6.0.788"
	bepinexZip    = "BepInEx-BepInExPack_IL2CPP-" + bepinexVer + ".zip"
	pinnedBepinex = "ce25d925f9eaba817214f5d6b2083b8e135ed0592b5a61b9f75ea5d4c02f5300"
)

// packageBody is the experimental package endpoint's document, in the shape the
// live endpoint answers with.
const packageBody = `{
  "namespace": "pythoninthegrass",
  "name": "Megabonk_Level_Editor",
  "full_name": "pythoninthegrass-Megabonk_Level_Editor",
  "owner": "pythoninthegrass",
  "package_url": "https://thunderstore.io/package/pythoninthegrass/Megabonk_Level_Editor/",
  "date_created": "2026-11-09T04:13:00.711517Z",
  "date_updated": "2026-11-09T21:06:14.256961Z",
  "rating_score": -1,
  "is_pinned": false,
  "is_deprecated": false,
  "total_downloads": -1,
  "latest": {
    "namespace": "pythoninthegrass",
    "name": "Megabonk_Level_Editor",
    "version_number": "0.2.0",
    "full_name": "pythoninthegrass-Megabonk_Level_Editor-0.2.0",
    "description": "Play and build custom Megabonk levels with an in-game map editor.",
    "icon": "https://ccdn.thunderstore.io/live/repository/icons/pythoninthegrass-Megabonk_Level_Editor-0.2.0.png",
    "dependencies": ["BepInEx-BepInExPack_IL2CPP-6.0.788"],
    "download_url": "https://thunderstore.io/package/download/pythoninthegrass/Megabonk_Level_Editor/0.2.0/",
    "downloads": 86,
    "date_created": "2026-11-09T21:06:13.821991Z",
    "website_url": "https://megabonkmod.party",
    "is_active": true
  },
  "community_listings": [
    {"has_nsfw_content": false, "categories": ["Mods", "Tools"], "community": "megabonk", "review_status": "unreviewed"}
  ]
}`

const modDownloadURL = "https://thunderstore.io/package/download/pythoninthegrass/Megabonk_Level_Editor/0.2.0/"

// stub answers the metadata endpoint and the CDN archive path out of memory and
// records each request so a test can read the path and headers back.
type stub struct {
	server     *httptest.Server
	requests   []string
	userAgents []string
	body       string
	status     int
	zipBody    []byte
	zipStatus  int
	zipType    string
}

func newStub(t *testing.T) *stub {
	t.Helper()
	stub := &stub{body: packageBody}
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		stub.requests = append(stub.requests, request.Method+" "+request.URL.RequestURI())
		stub.userAgents = append(stub.userAgents, request.Header.Get("User-Agent"))
		switch request.URL.Path {
		case "/api/experimental/package/" + ModNamespace + "/" + ModName + "/":
			if stub.status != 0 && stub.status != http.StatusOK {
				http.Error(writer, "upstream said no", stub.status)
				return
			}
			writer.Header().Set("Content-Type", "application/json")
			fmt.Fprint(writer, stub.body)
		case "/live/repository/packages/" + bepinexZip:
			if stub.zipStatus != 0 && stub.zipStatus != http.StatusOK {
				http.Error(writer, "upstream said no", stub.zipStatus)
				return
			}
			contentType := stub.zipType
			if contentType == "" {
				contentType = "application/zip"
			}
			writer.Header().Set("Content-Type", contentType)
			if _, err := writer.Write(stub.zipBody); err != nil {
				t.Errorf("writing archive body: %v", err)
			}
		default:
			http.Error(writer, "unexpected path "+request.URL.Path, http.StatusNotFound)
		}
	}))
	t.Cleanup(server.Close)
	stub.server = server
	return stub
}

func (s *stub) client() *Client { return NewClient(s.server.URL, s.server.URL) }

func digest(text string) string {
	sum := sha256.Sum256([]byte(text))
	return hex.EncodeToString(sum[:])
}

func zipWith(t *testing.T, names ...string) []byte {
	t.Helper()
	var builder strings.Builder
	writer := zip.NewWriter(&builder)
	for _, name := range names {
		entry, err := writer.Create(name)
		if err != nil {
			t.Fatalf("create %s: %v", name, err)
		}
		if _, err := io.WriteString(entry, "contents of "+name); err != nil {
			t.Fatalf("write %s: %v", name, err)
		}
	}
	if err := writer.Close(); err != nil {
		t.Fatalf("close zip: %v", err)
	}
	return []byte(builder.String())
}

func TestParseDependencySplitsFromTheRight(t *testing.T) {
	for _, test := range []struct {
		in   string
		want Dependency
	}{
		{"BepInEx-BepInExPack_IL2CPP-6.0.788", Dependency{Namespace: "BepInEx", Name: "BepInExPack_IL2CPP", Version: "6.0.788"}},
		{"pythoninthegrass-Megabonk_Level_Editor-0.2.0", Dependency{Namespace: "pythoninthegrass", Name: "Megabonk_Level_Editor", Version: "0.2.0"}},
		// Version, then name, then the rest as namespace: the rule the site's
		// PackageReference.parse applies and scripts/validate_thunderstore_manifest.py ports.
		{"Dash-Ed-Team-Mythic-TestMod-1.1.0", Dependency{Namespace: "Dash-Ed-Team-Mythic", Name: "TestMod", Version: "1.1.0"}},
		{"BepInEx-BepInExPack-IL2CPP-6.0.788", Dependency{Namespace: "BepInEx-BepInExPack", Name: "IL2CPP", Version: "6.0.788"}},
		{"a-b-1.0.0", Dependency{Namespace: "a", Name: "b", Version: "1.0.0"}},
		{"team-Package_With_Underscores-10.20.300", Dependency{Namespace: "team", Name: "Package_With_Underscores", Version: "10.20.300"}},
	} {
		got, err := ParseDependency(test.in)
		if err != nil {
			t.Errorf("ParseDependency(%q): unexpected error %s", test.in, err)
			continue
		}
		if got != test.want {
			t.Errorf("ParseDependency(%q) = %+v, want %+v", test.in, got, test.want)
		}
	}
}

func TestParseDependencyRejectsMalformedStrings(t *testing.T) {
	for _, in := range []string{
		"",
		"   ",
		"BepInExPack_IL2CPP",
		"BepInEx-BepInExPack_IL2CPP",
		"BepInEx-BepInExPack_IL2CPP-6.0",
		"BepInEx-BepInExPack_IL2CPP-6.0.788.1",
		"BepInEx--6.0.788",
		"BepInEx-BepInExPack_IL2CPP-6.0.788-beta",
		"BepInEx-BepInExPack_IL2CPP-6.0.788 ",
		"BepInEx-BepInExPack_IL2CPP-v6.0.788",
		"-BepInEx-Pack-6.0.788",
	} {
		got, err := ParseDependency(in)
		if err == nil {
			t.Errorf("ParseDependency(%q) = %+v, want an error", in, got)
			continue
		}
		if !strings.Contains(err.Error(), "dependency") {
			t.Errorf("ParseDependency(%q) error %q does not name a dependency", in, err)
		}
	}
}

func TestDependencyFullNameRoundTrips(t *testing.T) {
	for _, in := range []string{
		"BepInEx-BepInExPack_IL2CPP-6.0.788",
		"pythoninthegrass-Megabonk_Level_Editor-0.2.0",
		"Dash-Ed-Team-Mythic-TestMod-1.1.0",
	} {
		dependency, err := ParseDependency(in)
		if err != nil {
			t.Fatalf("ParseDependency(%q): %v", in, err)
		}
		if got := dependency.FullName(); got != in {
			t.Errorf("FullName() = %q, want %q", got, in)
		}
	}
}

func TestLatestDependsOnReturnsTheVersion(t *testing.T) {
	latest := Latest{Dependencies: []string{"BepInEx-BepInExPack_IL2CPP-6.0.788"}}
	got, ok, err := latest.DependsOn("BepInEx", bepinexName)
	if err != nil {
		t.Fatalf("DependsOn: %v", err)
	}
	if !ok || got != bepinexVer {
		t.Errorf("DependsOn = %q, %v; want %q, true", got, ok, bepinexVer)
	}
	if version, found, err := latest.DependsOn("BepInEx", "BepInExPack_Mono"); err != nil || found {
		t.Errorf("DependsOn for an absent package = %q, %v, %v; want false with no error", version, found, err)
	}
}

func TestLatestDependsOnReportsMalformedDependency(t *testing.T) {
	latest := Latest{Dependencies: []string{"BepInEx-BepInExPack_IL2CPP-6.0"}}
	if _, _, err := latest.DependsOn("BepInEx", bepinexName); err == nil {
		t.Fatal("DependsOn accepted a malformed dependency string")
	} else if !strings.Contains(err.Error(), "6.0") {
		t.Errorf("DependsOn error %q should quote the offending string", err)
	}
}

func TestCDNPackageURLBuildsTheArchivePath(t *testing.T) {
	want := "https://gcdn.thunderstore.io/live/repository/packages/" + bepinexZip
	for _, cdn := range []string{"https://gcdn.thunderstore.io", "https://gcdn.thunderstore.io/"} {
		if got := CDNPackageURL(cdn, "BepInEx", bepinexName, bepinexVer); got != want {
			t.Errorf("CDNPackageURL(%q) = %q, want %q", cdn, got, want)
		}
	}
	if got := CDNPackageURL(DefaultCDNBaseURL, "BepInEx", bepinexName, bepinexVer); got != want {
		t.Errorf("CDNPackageURL with the default CDN = %q, want %q", got, want)
	}
}

func TestResolveReturnsVersionDownloadURLAndDependency(t *testing.T) {
	stub := newStub(t)
	got, err := stub.client().Resolve()
	if err != nil {
		t.Fatalf("Resolve: %v", err)
	}
	if got.Version != "0.2.0" {
		t.Errorf("Version = %q, want 0.2.0", got.Version)
	}
	if got.DownloadURL != modDownloadURL {
		t.Errorf("DownloadURL = %q, want %q", got.DownloadURL, modDownloadURL)
	}
	if got.BepInExVersion != bepinexVer {
		t.Errorf("BepInExVersion = %q, want %s", got.BepInExVersion, bepinexVer)
	}
	if got.FullName != "pythoninthegrass-Megabonk_Level_Editor-0.2.0" {
		t.Errorf("FullName = %q, want the published full name", got.FullName)
	}
	if len(got.Dependencies) != 1 || got.Dependencies[0].Name != bepinexName {
		t.Errorf("Dependencies = %+v, want the BepInEx pack", got.Dependencies)
	}
	wantArchive := "/live/repository/packages/" + bepinexZip
	if !strings.HasSuffix(got.BepInExArchiveURL, wantArchive) {
		t.Errorf("BepInExArchiveURL = %q, want it to end in %s", got.BepInExArchiveURL, wantArchive)
	}
	want := "GET /api/experimental/package/" + ModNamespace + "/" + ModName + "/"
	if len(stub.requests) != 1 || stub.requests[0] != want {
		t.Errorf("requests = %v, want just %q", stub.requests, want)
	}
}

func TestResolveSendsBrowserUserAgent(t *testing.T) {
	stub := newStub(t)
	if _, err := stub.client().Resolve(); err != nil {
		t.Fatalf("Resolve: %v", err)
	}
	if len(stub.userAgents) != 1 {
		t.Fatalf("requests = %v, want one", stub.requests)
	}
	if got := stub.userAgents[0]; got != UserAgent {
		t.Errorf("User-Agent = %q, want %q", got, UserAgent)
	}
	if !strings.HasPrefix(UserAgent, "Mozilla/5.0") {
		t.Errorf("UserAgent = %q, want a browser User-Agent", UserAgent)
	}
	if strings.Contains(UserAgent, "Go-http-client") || strings.Contains(strings.ToLower(UserAgent), "python") {
		t.Errorf("UserAgent %q is a scripting client, which Cloudflare answers with error 1010", UserAgent)
	}
}

func TestResolveReportsEveryBadResponse(t *testing.T) {
	for _, test := range []struct {
		name   string
		status int
		body   string
		want   string
	}{
		{name: "not found", status: http.StatusNotFound, body: packageBody, want: "404"},
		{name: "server error", status: http.StatusBadGateway, body: packageBody, want: "502"},
		{name: "html error page", body: "<html><body>Cloudflare error 1010</body></html>", want: "json"},
		{name: "no latest", body: `{"namespace":"pythoninthegrass"}`, want: "latest"},
		{name: "dependencies not a list", body: `{"latest":{"version_number":"0.2.0","download_url":"` + modDownloadURL + `","dependencies":"BepInEx-BepInExPack_IL2CPP-6.0.788"}}`, want: "dependencies"},
		{name: "blank download url", body: `{"latest":{"version_number":"0.2.0","download_url":"","dependencies":[]}}`, want: "download_url"},
		{name: "blank version", body: `{"latest":{"version_number":"","download_url":"` + modDownloadURL + `","dependencies":[]}}`, want: "version"},
		{name: "no bepinex dependency", body: `{"latest":{"version_number":"0.2.0","download_url":"` + modDownloadURL + `","dependencies":["OtherTeam-Pack-1.2.3"]}}`, want: "BepInEx-BepInExPack_IL2CPP"},
		{name: "malformed dependency", body: `{"latest":{"version_number":"0.2.0","download_url":"` + modDownloadURL + `","dependencies":["BepInEx-BepInExPack_IL2CPP-6.0"]}}`, want: "dependency"},
	} {
		t.Run(test.name, func(t *testing.T) {
			stub := newStub(t)
			stub.status = test.status
			stub.body = test.body
			_, err := stub.client().Resolve()
			if err == nil {
				t.Fatal("Resolve accepted the response")
			}
			if !strings.Contains(strings.ToLower(err.Error()), strings.ToLower(test.want)) {
				t.Errorf("error %q should mention %q", err, test.want)
			}
		})
	}
}

func TestDownloadBepInExChecksTheDigestBeforeInstalling(t *testing.T) {
	body := zipWith(t, "BepInExPack/.doorstop_version", "BepInExPack/changelog.txt")
	for _, test := range []struct {
		name    string
		pin     string
		wantErr string
	}{
		{name: "matching pin", pin: strings.ToUpper(digest(string(body)))},
		{name: "mismatching pin", pin: digest("some other archive"), wantErr: "checksum"},
		{name: "unpinned version", pin: "", wantErr: "pinned"},
	} {
		t.Run(test.name, func(t *testing.T) {
			stub := newStub(t)
			stub.zipBody = body
			target := filepath.Join(t.TempDir(), bepinexZip)
			got, err := stub.client().DownloadBepInEx(bepinexVer, test.pin, target)
			if test.wantErr != "" {
				if err == nil {
					t.Fatalf("DownloadBepInEx accepted the %s case", test.name)
				}
				if !strings.Contains(strings.ToLower(err.Error()), test.wantErr) {
					t.Errorf("error %q should mention %q", err, test.wantErr)
				}
				for _, path := range []string{target, target + ".part"} {
					if _, statErr := os.Stat(path); !os.IsNotExist(statErr) {
						t.Errorf("the rejected download left %s behind", path)
					}
				}
				return
			}
			if err != nil {
				t.Fatalf("DownloadBepInEx: %v", err)
			}
			if got.Path != target {
				t.Errorf("Path = %q, want %q", got.Path, target)
			}
			if got.SHA256 != digest(string(body)) {
				t.Errorf("SHA256 = %q, want the lowercase digest %q", got.SHA256, digest(string(body)))
			}
			if got.Size != int64(len(body)) {
				t.Errorf("Size = %d, want %d", got.Size, len(body))
			}
			if got.Version != bepinexVer {
				t.Errorf("Version = %q, want %s", got.Version, bepinexVer)
			}
			wantURL := stub.server.URL + "/live/repository/packages/" + bepinexZip
			if got.URL != wantURL {
				t.Errorf("URL = %q, want %q", got.URL, wantURL)
			}
			stored, err := os.ReadFile(target)
			if err != nil {
				t.Fatalf("read archive: %v", err)
			}
			if string(stored) != string(body) {
				t.Error("the stored archive differs from what the CDN served")
			}
			if _, statErr := os.Stat(target + ".part"); !os.IsNotExist(statErr) {
				t.Error("the temporary file was left behind")
			}
		})
	}
}

func TestPinnedDigestsMatchTheRepairScript(t *testing.T) {
	got, ok := PinnedBepInExDigest(bepinexVer)
	if !ok {
		t.Fatalf("no pinned digest for %s", bepinexVer)
	}
	if got != pinnedBepinex {
		t.Errorf("pinned digest = %q, want %q", got, pinnedBepinex)
	}
	if _, ok := PinnedBepInExDigest("6.0.0"); ok {
		t.Error("an unpinned version reported a digest")
	}
	if err := CheckDigest([]byte("not the pack"), pinnedBepinex); err == nil {
		t.Error("CheckDigest accepted the wrong bytes")
	}
	if err := CheckDigest(zipWith(t, "BepInExPack/changelog.txt"), pinnedBepinex); err == nil {
		t.Error("CheckDigest accepted an archive that is not the pinned pack")
	}
	body := zipWith(t, "BepInExPack/changelog.txt")
	upper := strings.ToUpper(digest(string(body)))
	if err := CheckDigest(body, upper); err != nil {
		t.Errorf("CheckDigest should compare case-insensitively: %v", err)
	}
}

func TestDownloadBepInExUsesCDNPathAndBrowserUserAgent(t *testing.T) {
	body := zipWith(t, "BepInExPack/dotnet/coreclr.dll")
	stub := newStub(t)
	stub.zipBody = body
	target := filepath.Join(t.TempDir(), bepinexZip)
	if _, err := stub.client().DownloadBepInEx(bepinexVer, digest(string(body)), target); err != nil {
		t.Fatalf("DownloadBepInEx: %v", err)
	}
	want := "GET /live/repository/packages/" + bepinexZip
	if len(stub.requests) != 1 || stub.requests[0] != want {
		t.Errorf("requests = %v, want just %q", stub.requests, want)
	}
	if len(stub.userAgents) != 1 || stub.userAgents[0] != UserAgent {
		t.Errorf("User-Agent = %v, want %q", stub.userAgents, UserAgent)
	}
}

func TestDownloadBepInExRejectsBadResponsesWithoutWriting(t *testing.T) {
	for _, test := range []struct {
		name    string
		status  int
		zipType string
		want    string
	}{
		{name: "missing archive", status: http.StatusNotFound, want: "404"},
		{name: "server error", status: http.StatusBadGateway, want: "502"},
		{name: "html page", zipType: "text/html", want: "zip"},
	} {
		t.Run(test.name, func(t *testing.T) {
			stub := newStub(t)
			body := zipWith(t, "BepInExPack/changelog.txt")
			if test.zipType != "" {
				body = []byte("<html><body>Not Found</body></html>")
			}
			stub.zipBody = body
			stub.zipStatus = test.status
			stub.zipType = test.zipType
			target := filepath.Join(t.TempDir(), "nested", bepinexZip)
			_, err := stub.client().DownloadBepInEx(bepinexVer, digest(string(body)), target)
			if err == nil {
				t.Fatal("DownloadBepInEx accepted a bad response")
			}
			if !strings.Contains(err.Error(), test.want) {
				t.Errorf("error %q should mention %q", err, test.want)
			}
			for _, path := range []string{target, target + ".part"} {
				if _, statErr := os.Stat(path); !os.IsNotExist(statErr) {
					t.Errorf("the failed download left %s behind", path)
				}
			}
		})
	}
}

func TestDownloadBepInExRejectsABodyThatIsNotAnArchive(t *testing.T) {
	notAZip := []byte("<html><body>Not Found</body></html>")
	stub := newStub(t)
	stub.zipBody = notAZip
	target := filepath.Join(t.TempDir(), bepinexZip)
	_, err := stub.client().DownloadBepInEx(bepinexVer, digest(string(notAZip)), target)
	if err == nil {
		t.Fatal("DownloadBepInEx accepted a body that is not a zip")
	}
	if !strings.Contains(err.Error(), "zip") {
		t.Errorf("error %q should say the archive is not a zip", err)
	}
	if _, statErr := os.Stat(target); !os.IsNotExist(statErr) {
		t.Errorf("the rejected archive left %s behind", target)
	}
}

func TestDownloadBepInExChecksTheDigestBeforeTheArchiveLayout(t *testing.T) {
	notAZip := []byte("this is not a zip archive")
	stub := newStub(t)
	stub.zipBody = notAZip
	target := filepath.Join(t.TempDir(), bepinexZip)
	_, err := stub.client().DownloadBepInEx(bepinexVer, digest("a different body"), target)
	if err == nil {
		t.Fatal("DownloadBepInEx accepted an archive whose digest does not match")
	}
	if !strings.Contains(strings.ToLower(err.Error()), "checksum") {
		t.Errorf("error %q should report the digest mismatch, not the unparseable body", err)
	}
}

func TestDownloadBepInExCapsTheArchiveSize(t *testing.T) {
	big := []byte(strings.Repeat("x", MaxArchiveBytes+1))
	stub := newStub(t)
	stub.zipBody = big
	target := filepath.Join(t.TempDir(), bepinexZip)
	_, err := stub.client().DownloadBepInEx(bepinexVer, digest(string(big)), target)
	if err == nil {
		t.Fatal("DownloadBepInEx accepted an oversized archive")
	}
	if !strings.Contains(err.Error(), "larger") {
		t.Errorf("error %q should name the size limit", err)
	}
}

func TestDownloadBepInExRefusesForeignArchiveLayout(t *testing.T) {
	for _, test := range []struct {
		name   string
		member string
	}{
		{name: "no pack root", member: "BepInEx/core/BepInEx.Unity.IL2CPP.dll"},
		{name: "escaping path", member: "BepInExPack/../../evil.dll"},
	} {
		t.Run(test.name, func(t *testing.T) {
			body := zipWith(t, test.member)
			stub := newStub(t)
			stub.zipBody = body
			target := filepath.Join(t.TempDir(), bepinexZip)
			_, err := stub.client().DownloadBepInEx(bepinexVer, digest(string(body)), target)
			if err == nil {
				t.Fatalf("DownloadBepInEx accepted the %s case", test.name)
			}
			if !strings.Contains(err.Error(), "BepInExPack") {
				t.Errorf("error %q should name the expected archive layout", err)
			}
			if _, statErr := os.Stat(target); !os.IsNotExist(statErr) {
				t.Errorf("the rejected archive left %s behind", target)
			}
		})
	}
}

func TestDownloadBepInExReusesAnIntactArchive(t *testing.T) {
	body := zipWith(t, "BepInExPack/changelog.txt")
	stub := newStub(t)
	stub.zipBody = body
	target := filepath.Join(t.TempDir(), bepinexZip)
	if _, err := stub.client().DownloadBepInEx(bepinexVer, digest(string(body)), target); err != nil {
		t.Fatalf("first DownloadBepInEx: %v", err)
	}
	if len(stub.requests) != 1 {
		t.Fatalf("requests = %v, want the one archive call", stub.requests)
	}
	got, err := stub.client().DownloadBepInEx(bepinexVer, digest(string(body)), target)
	if err != nil {
		t.Fatalf("second DownloadBepInEx: %v", err)
	}
	if !got.FromCache {
		t.Error("the intact archive should be reused rather than refetched")
	}
	if len(stub.requests) != 1 {
		t.Errorf("requests after the cache hit = %v, want no extra request", stub.requests)
	}
}

func TestDownloadBepInExReplacesADigestMismatchOnDisk(t *testing.T) {
	body := zipWith(t, "BepInExPack/changelog.txt")
	stub := newStub(t)
	stub.zipBody = body
	target := filepath.Join(t.TempDir(), bepinexZip)
	if err := os.WriteFile(target, []byte("stale download"), 0o644); err != nil {
		t.Fatalf("seed archive: %v", err)
	}
	got, err := stub.client().DownloadBepInEx(bepinexVer, digest(string(body)), target)
	if err != nil {
		t.Fatalf("DownloadBepInEx: %v", err)
	}
	if got.FromCache {
		t.Error("a refetched archive should not be reported as cached")
	}
	stored, err := os.ReadFile(target)
	if err != nil {
		t.Fatalf("read archive: %v", err)
	}
	if string(stored) != string(body) {
		t.Error("the stale archive was left in place")
	}
	if len(stub.requests) != 1 {
		t.Errorf("requests = %v, want the one refetched archive call", stub.requests)
	}
}

func TestDownloadBepInExValidatesArguments(t *testing.T) {
	stub := newStub(t)
	dir := t.TempDir()
	for _, test := range []struct {
		name    string
		version string
		pin     string
		target  string
	}{
		{name: "blank version", version: "", pin: digest("x"), target: filepath.Join(dir, "a.zip")},
		{name: "path in version", version: "../6.0.788", pin: digest("x"), target: filepath.Join(dir, "b.zip")},
		{name: "blank digest", version: bepinexVer, pin: "nope", target: filepath.Join(dir, "c.zip")},
		{name: "blank target", version: bepinexVer, pin: digest("x"), target: "   "},
		{name: "directory traversal in target", version: bepinexVer, pin: digest("x"), target: dir + "/../escaped.zip"},
		{name: "dot as target", version: bepinexVer, pin: digest("x"), target: "."},
		{name: "dot as file name", version: bepinexVer, pin: digest("x"), target: dir + "/sub/."},
		{name: "backslash in target", version: bepinexVer, pin: digest("x"), target: dir + "\\" + "escaped.zip"},
		{name: "colon in target", version: bepinexVer, pin: digest("x"), target: dir + "/pack:zip"},
		{name: "NUL in target", version: bepinexVer, pin: digest("x"), target: dir + "/bad\x00.zip"},
	} {
		if _, err := stub.client().DownloadBepInEx(test.version, test.pin, test.target); err == nil {
			t.Errorf("%s: DownloadBepInEx accepted it", test.name)
		}
	}
	if len(stub.requests) != 0 {
		t.Errorf("requests = %v, want none for rejected arguments", stub.requests)
	}
}

func TestDefaultClientPointsAtThunderstore(t *testing.T) {
	client := NewClientFromEnv()
	if client.APIBase() != DefaultAPIBaseURL {
		t.Errorf("APIBase() = %q, want %q", client.APIBase(), DefaultAPIBaseURL)
	}
	if client.CDNBase() != DefaultCDNBaseURL {
		t.Errorf("CDNBase() = %q, want %q", client.CDNBase(), DefaultCDNBaseURL)
	}
	want := DefaultAPIBaseURL + "/api/experimental/package/" + ModNamespace + "/" + ModName + "/"
	if got := client.MetadataURL(); got != want {
		t.Errorf("MetadataURL() = %q, want %q", got, want)
	}
	blanked := NewClient("  ", " ")
	if blanked.APIBase() != DefaultAPIBaseURL || blanked.CDNBase() != DefaultCDNBaseURL {
		t.Errorf("blank overrides fell back to %q / %q", blanked.APIBase(), blanked.CDNBase())
	}
}

func TestEnvironmentOverridesPointTheClientAtTheStub(t *testing.T) {
	stub := newStub(t)
	body := zipWith(t, "BepInExPack/changelog.txt")
	stub.zipBody = body
	t.Setenv(APIBaseURLEnv, stub.server.URL)
	t.Setenv(CDNBaseURLEnv, stub.server.URL)
	if _, err := NewClientFromEnv().Resolve(); err != nil {
		t.Fatalf("Resolve through the environment: %v", err)
	}
	target := filepath.Join(t.TempDir(), bepinexZip)
	if _, err := NewClientFromEnv().DownloadBepInEx(bepinexVer, digest(string(body)), target); err != nil {
		t.Fatalf("DownloadBepInEx through the environment: %v", err)
	}
	if len(stub.requests) != 2 {
		t.Errorf("requests = %v, want the metadata call and the archive call", stub.requests)
	}
}

func TestNormalizeBaseRefusesNonHTTPOrigins(t *testing.T) {
	for _, in := range []string{"ftp://gcdn.thunderstore.io", "https://", "//gcdn.thunderstore.io", "file:///etc/passwd", "gcdn thunderstore"} {
		if got, err := normalizeBase(in); err == nil {
			t.Errorf("normalizeBase(%q) = %q, want an error", in, got)
		}
	}
	for _, in := range []string{"http://127.0.0.1:8080/", "https://gcdn.thunderstore.io/"} {
		got, err := normalizeBase(in)
		if err != nil {
			t.Errorf("normalizeBase(%q): %v", in, err)
			continue
		}
		if strings.HasSuffix(got, "/") {
			t.Errorf("normalizeBase(%q) = %q, want no trailing slash", in, got)
		}
	}
}

func TestErrorsAreTyped(t *testing.T) {
	_, err := ParseDependency("nonsense")
	var typeError *Error
	if !errors.As(err, &typeError) {
		t.Fatalf("ParseDependency error %q is not a *Error", err)
	}
	if typeError.Message == "" {
		t.Error("the error carries no message")
	}
}

// SourceScan reads the package's own sources, so the check below stays a
// package-level fact rather than a walk of whatever directory the test runs in.
var SourceScan = packageSources

func packageSources() (map[string]string, error) {
	entries, err := os.ReadDir(".")
	if err != nil {
		return nil, err
	}
	sources := map[string]string{}
	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".go") {
			continue
		}
		body, err := os.ReadFile(entry.Name())
		if err != nil {
			return nil, err
		}
		sources[entry.Name()] = string(body)
	}
	return sources, nil
}

// TestNoResolvableHostInSources proves the client's hosts always come from the
// two constants or the environment overrides: nothing in the package names a
// host it could resolve, so go test can only reach a local server.
func TestNoResolvableHostInSources(t *testing.T) {
	original := SourceScan
	defer func() { SourceScan = original }()
	SourceScan = plantedSources(
		// A spelling of the constants is not a host the client could resolve.
		"good.go", "const api = DefaultAPIBaseURL\nconst cdn = DefaultCDNBaseURL\n",
		// An escaped literal would hide the host from a plain scan, so string
		// literals are decoded as well.
		"bad.go", "const live = \"https://"+splitHost("cdn", "evil", "example")+"\"\n",
	)
	offenders := resolvableHostLines()
	if len(offenders) != 1 || !strings.Contains(offenders[0], "bad.go") {
		t.Fatalf("resolvableHostLines() = %v, want only the planted host name", offenders)
	}
	SourceScan = original
	if offenders := resolvableHostLines(); len(offenders) != 0 {
		for _, offender := range offenders {
			t.Error(offender)
		}
	}
}

// splitHost joins hostname labels, so a test can name a host in the data it
// builds without writing the dotted form into this file's own source.
func splitHost(labels ...string) string { return strings.Join(labels, ".") }

func plantedSources(pairs ...string) func() (map[string]string, error) {
	return func() (map[string]string, error) {
		sources := map[string]string{}
		for index := 0; index+1 < len(pairs); index += 2 {
			sources[pairs[index]] = pairs[index+1]
		}
		return sources, nil
	}
}

// hostLikeName matches a whole hostname greedily, so a lookalike host is seen
// as one host rather than as an allowed host plus a suffix.
var hostLikeName = regexp.MustCompile(`[A-Za-z0-9][-A-Za-z0-9.]*\.[A-Za-z]{2,}`)

// literalHosts are hostnames spelled in this package's sources that no client
// can be pointed at: the two constants' values, the Macintosh token inside the
// browser User-Agent, and the icon, website and download hosts that appear only
// as data copied from a live endpoint response. Those data hosts are listed
// deliberately: the fixtures that carry them mirror the documented response and
// no request is ever sent to them, which is what the no-network check below
// exists to keep true.
var literalHosts = map[string]bool{
	"thunderstore.io":      true,
	"gcdn.thunderstore.io": true,
	"ccdn.thunderstore.io": true,
	"megabonkmod.party":    true,
	"macintosh":            true,
}

var backtickLiterals = regexp.MustCompile("`[^`]*`")

var quotedLiterals = regexp.MustCompile(`"(?:[^"\\]|\\.)*"`)

// resolvableHostLines names every source line carrying a host the package is
// not allowed to name.
func resolvableHostLines() []string {
	sources, err := SourceScan()
	if err != nil {
		return []string{err.Error()}
	}
	allowed := hostnamesOf(DefaultAPIBaseURL, DefaultCDNBaseURL)
	names := make([]string, 0, len(sources))
	for name := range sources {
		names = append(names, name)
	}
	sort.Strings(names)
	seen := map[string]bool{}
	var offenders []string
	for _, file := range names {
		for number, line := range strings.Split(sources[file], "\n") {
			for _, host := range resolvableHosts(strings.ToLower(decodedSourceText(line))) {
				if allowed[host] {
					continue
				}
				key := file + ":" + strconv.Itoa(number) + ":" + host
				if seen[key] {
					continue
				}
				seen[key] = true
				offenders = append(offenders, fmt.Sprintf("%s:%d resolves %s: %s",
					file, number+1, host, strings.TrimSpace(line)))
			}
		}
	}
	return offenders
}

// resolvableHosts returns the hostnames in text that a client could be pointed
// at: a written-out location, and not one of the values above. Package-qualified
// calls such as fmt.Sprintf and err.Error are ordinary code, not hosts.
func resolvableHosts(text string) []string {
	var hosts []string
	for _, host := range hostLikeName.FindAllString(text, -1) {
		if literalHosts[host] {
			continue
		}
		if !strings.Contains(text, "http://"+host) && !strings.Contains(text, "https://"+host) {
			continue
		}
		hosts = append(hosts, host)
	}
	return hosts
}

// hostnamesOf pulls the host out of each constant's spelling.
func hostnamesOf(values ...string) map[string]bool {
	hosts := map[string]bool{}
	for _, value := range values {
		text := value
		if parsed, err := url.Parse(text); err == nil && parsed.Hostname() != "" {
			text = parsed.Hostname()
		}
		hosts[strings.ToLower(text)] = true
	}
	return hosts
}

// decodedSourceText adds a line's string-literal contents to its raw text, so a
// host written with escapes is still seen.
func decodedSourceText(line string) string {
	decoded := line
	for _, candidate := range backtickLiterals.FindAllString(line, -1) {
		decoded += " " + strings.Trim(candidate, "`")
	}
	for _, candidate := range quotedLiterals.FindAllString(line, -1) {
		if unquoted, err := strconv.Unquote(candidate); err == nil {
			decoded += " " + unquoted
		}
	}
	return decoded
}

func TestDownloadBepInExNeverWritesOutsideTheTargetFolder(t *testing.T) {
	body := zipWith(t, "BepInExPack/changelog.txt")
	stub := newStub(t)
	stub.zipBody = body
	dir := t.TempDir()
	intended := filepath.Join(dir, "sub")
	if err := os.MkdirAll(intended, 0o755); err != nil {
		t.Fatalf("create the intended folder: %v", err)
	}
	escaping := intended + "/../escaped.zip"
	got, err := stub.client().DownloadBepInEx(bepinexVer, digest(string(body)), escaping)
	if err == nil {
		t.Fatalf("DownloadBepInEx accepted a target that climbs out of its folder: %+v", got)
	}
	if _, statErr := os.Stat(filepath.Join(dir, "escaped.zip")); !os.IsNotExist(statErr) {
		t.Error("a rejected traversal target still wrote a file")
	}
	// The same archive through a plain path still lands where it was told to.
	plain := filepath.Join(intended, bepinexZip)
	if _, err := stub.client().DownloadBepInEx(bepinexVer, digest(string(body)), plain); err != nil {
		t.Fatalf("DownloadBepInEx on a plain target: %v", err)
	}
	if _, statErr := os.Stat(plain); statErr != nil {
		t.Errorf("the archive did not land at %s: %v", plain, statErr)
	}
}
