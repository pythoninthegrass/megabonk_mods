package site

import (
	"errors"
	"fmt"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"reflect"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"testing"
)

const defaultLevelBody = `{
  "id": "lv1",
  "title": "THPS: Warehouse (v2)",
  "level": "thps-warehouse-v2.mblevel.json",
  "cover": "cover.png",
  "biome": "biome.jpg",
  "packs": {"thps": "1.2.0", "squeaker": "0.1"}
}`

// stub is a stand-in for the site API: it answers the three endpoints with
// preloaded responses and records what it was asked for.
type stub struct {
	server   *httptest.Server
	calls    []string
	metadata string
	status   int
	packs    map[string]int
}

func newStub(t *testing.T) *stub {
	t.Helper()
	stub := &stub{metadata: defaultLevelBody, packs: map[string]int{}}
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		stub.calls = append(stub.calls, request.Method+" "+request.URL.RequestURI())
		switch {
		case request.URL.Path == "/api/collections/levels/records":
			if stub.status != 0 && stub.status != 200 {
				http.Error(writer, "upstream said no", stub.status)
				return
			}
			if request.URL.Query().Get("filter") != "(code='7N1-MVB-WKF')" {
				http.Error(writer, "no such record", http.StatusOK)
				return
			}
			writer.Header().Set("Content-Type", "application/json")
			fmt.Fprint(writer, `{"page":1,"perPage":30,"totalItems":1,"items":[`+stub.metadata+`]}`)
		case request.URL.Path == "/api/l/7N1-MVB-WKF/download":
			http.Redirect(writer, request, "/api/files/levels/lv1/thps-warehouse-v2.mblevel.json?download=1", http.StatusFound)
		case request.URL.Path == "/api/files/levels/lv1/thps-warehouse-v2.mblevel.json":
			fmt.Fprint(writer, defaultLevelBody)
		case request.URL.Path == "/api/p/thps/download":
			version := request.URL.Query().Get("version")
			code, hosted := stub.packs[version]
			// The site answers 404 for an unhosted version and for a pack
			// with no windows bundle, so an entry may pin 404 explicitly.
			if !hosted || code == http.StatusNotFound {
				http.Error(writer, "Pack not found for that platform.", http.StatusNotFound)
				return
			}
			if code != 200 {
				http.Error(writer, "upstream said no", code)
				return
			}
			writer.Header().Set("Content-Type", "application/zip")
			fmt.Fprint(writer, "zip-for-thps")
		default:
			http.Error(writer, "unexpected path "+request.URL.Path, http.StatusNotFound)
		}
	}))
	t.Cleanup(server.Close)
	stub.server = server
	return stub
}

func (s *stub) client() *Client { return NewClient(s.server.URL) }

func (s *stub) ask(t *testing.T, code string) (*Level, error) {
	t.Helper()
	return s.client().LookupLevel(code)
}

func TestNormalizeCodeAcceptsCodesAndLinks(t *testing.T) {
	for _, input := range []string{
		"7N1-MVB-WKF",
		"7n1-mvb-wkf",
		"  7N1-MVB-WKF  ",
		"7N1MVBWKF",
		"https://megabonkmod.party/l/7N1-MVB-WKF",
		"http://megabonkmod.party/l/7n1-mvb-wkf/",
		"https://megabonkmod.party/l/7N1-MVB-WKF?ref=card",
		"megabonkmod.party/l/7N1-MVB-WKF",
		"https://megabonkmod.party/levels/view/?code=7N1-MVB-WKF",
		"megabonkmod.party/levels/view/?code=7n1-mvb-wkf&ref=card",
		"https://megabonkmod.party/levels/view/?filter=fun&code=7N1-MVB-WKF",
	} {
		got, err := NormalizeCode(input)
		if err != nil {
			t.Errorf("NormalizeCode(%q): unexpected error %s", input, err)
			continue
		}
		if got != "7N1-MVB-WKF" {
			t.Errorf("NormalizeCode(%q) = %q, want 7N1-MVB-WKF", input, got)
		}
	}
}

func TestNormalizeCodeRejectsAnythingElse(t *testing.T) {
	for _, input := range []string{
		"",
		"   ",
		"hello",
		"7N1-MVB-WK",
		"7N1-MVB-WKFF",
		"7N1-MVB-WKU",
		"7N1-MVB-WKI",
		"l/7N1-MVB-WKF",
		"/l/7N1-MVB-WKF",
		"https://evil.example/l/7N1-MVB-WKF",
		"https://" + splitHost("megabonkmod", "party", "evil", "example") + "/l/7N1-MVB-WKF",
		"https://megabonkmod.party/levels/",
		"https://megabonkmod.party/levels/view/",
		"https://megabonkmod.party/levels/view/?code=hello",
		"https://megabonkmod.party/p/thps",
		"megabonkmod.party/l/7N1-MVB-WKF/../etc",
		"file:///etc/passwd",
		"/api/files/levels/lv1/level.json",
	} {
		if got, err := NormalizeCode(input); err == nil {
			t.Errorf("NormalizeCode(%q) = %q, want an error", input, got)
		} else if !strings.Contains(strings.ToLower(err.Error()), "share code") {
			t.Errorf("NormalizeCode(%q) error %q does not name a share code", input, err)
		}
	}
}

func TestLookupLevelReturnsMetadata(t *testing.T) {
	stub := newStub(t)
	level, err := stub.ask(t, "7n1-mvb-wkf")
	if err != nil {
		t.Fatal(err)
	}
	if level.ID != "lv1" {
		t.Errorf("ID = %q, want lv1", level.ID)
	}
	if level.Title != "THPS: Warehouse (v2)" {
		t.Errorf("Title = %q", level.Title)
	}
	if level.Slug != "thps-warehouse-v2" {
		t.Errorf("Slug = %q, want thps-warehouse-v2", level.Slug)
	}
	if level.Filename() != "thps-warehouse-v2.mblevel.json" {
		t.Errorf("Filename() = %q", level.Filename())
	}
	wantCover := stub.server.URL + "/api/files/levels/lv1/cover.png"
	if level.CoverURL() != wantCover {
		t.Errorf("CoverURL = %q, want %q", level.CoverURL(), wantCover)
	}
	wantBiome := stub.server.URL + "/api/files/levels/lv1/biome.jpg"
	if level.BiomeURL() != wantBiome {
		t.Errorf("BiomeURL = %q, want %q", level.BiomeURL(), wantBiome)
	}
	wantPacks := map[string]string{"thps": "1.2.0", "squeaker": "0.1"}
	if !reflect.DeepEqual(level.Packs, wantPacks) {
		t.Errorf("Packs = %v, want %v", level.Packs, wantPacks)
	}
}

func TestLookupLevelWithoutBiome(t *testing.T) {
	stub := newStub(t)
	stub.metadata = `{"id":"lv1","title":"Plain","level":"plain.mblevel.json","cover":"cover.png","packs":{}}`
	level, err := stub.ask(t, "7N1-MVB-WKF")
	if err != nil {
		t.Fatal(err)
	}
	if level.BiomeURL() != "" {
		t.Errorf("BiomeURL = %q, want empty", level.BiomeURL())
	}
	if len(level.Packs) != 0 {
		t.Errorf("Packs = %v, want empty", level.Packs)
	}
}

func TestLookupLevelUsesStoredLevelFileWhenTitleSlugsElsewhere(t *testing.T) {
	stub := newStub(t)
	stub.metadata = `{"id":"lv1","title":"Renamed Title","level":"original-name.mblevel.json","cover":"cover.png"}`
	level, err := stub.ask(t, "7N1-MVB-WKF")
	if err != nil {
		t.Fatal(err)
	}
	if level.Filename() != "original-name.mblevel.json" {
		t.Errorf("Filename() = %q, want the stored file name", level.Filename())
	}
	if level.Slug != "renamed-title" {
		t.Errorf("Slug = %q, want the slug of the title", level.Slug)
	}
}

func TestSlugNamesTheLevelFileOnDisk(t *testing.T) {
	for title, want := range map[string]string{
		"Bramblecrown Hill":         "bramblecrown-hill",
		"  THPS: Warehouse (v2)!  ": "thps-warehouse-v2",
		"a/b\\c..d":                 "a-b-c-d",
		"":                          "level",
		"!!!":                       "level",
		"スイッチ":                      "level",
	} {
		if got := Slug(title); got != want {
			t.Errorf("Slug(%q) = %q, want %q", title, got, want)
		}
	}
}

func TestNotFoundErrorForUnknownOrHiddenCode(t *testing.T) {
	for _, status := range []int{http.StatusNotFound, http.StatusForbidden} {
		stub := newStub(t)
		stub.status = status
		_, err := stub.ask(t, "7N1-MVB-WKF")
		if err == nil {
			t.Fatalf("status %d: want an error", status)
		}
		notFound := asNotFoundError(t, err)
		if notFound.Code != "7N1-MVB-WKF" {
			t.Errorf("status %d: NotFoundError.Code = %q", status, notFound.Code)
		}
		if !strings.Contains(strings.ToLower(err.Error()), "level not found") {
			t.Errorf("status %d: error %q does not say level not found", status, err)
		}
		if strings.Contains(strings.ToLower(err.Error()), "http "+fmt.Sprint(status)) {
			t.Errorf("status %d: error %q leaks a generic HTTP status", status, err)
		}
	}
}

func TestLookupLevelErrorsOnEmptyPageAndBadJSON(t *testing.T) {
	for name, body := range map[string]string{
		"empty page":   `{"page":1,"perPage":30,"totalItems":0,"items":[]}`,
		"bad json":     `not json`,
		"wrong shape":  `"a string"`,
		"missing id":   `{"title":"No ID","level":"no-id.mblevel.json"}`,
		"missing file": `{"id":"lv1","title":"No File"}`,
	} {
		stub := newStub(t)
		stub.metadata = body
		_, err := stub.ask(t, "7N1-MVB-WKF")
		if err == nil {
			t.Fatalf("%s: want an error", name)
		}
		if errors.As(err, new(*NotFoundError)) {
			t.Errorf("%s: error %q should not read as level not found", name, err)
		}
	}
}

func TestLevelDownloadFollowsRedirectAndCounts(t *testing.T) {
	stub := newStub(t)
	level, err := stub.ask(t, "7N1-MVB-WKF")
	if err != nil {
		t.Fatal(err)
	}
	body, err := level.Download()
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(body), `"title"`) {
		t.Errorf("downloaded body is %q", body)
	}
	want := []string{
		"GET /api/collections/levels/records?filter=%28code%3D%277N1-MVB-WKF%27%29",
		"GET /api/l/7N1-MVB-WKF/download",
		"GET /api/files/levels/lv1/thps-warehouse-v2.mblevel.json?download=1",
	}
	if !reflect.DeepEqual(stub.calls, want) {
		t.Fatalf("calls = %v, want %v", stub.calls, want)
	}
}

func TestLevelDownload404IsNotFound(t *testing.T) {
	stub := newStub(t)
	stub.server.Config.Handler = http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		if request.URL.Path == "/api/l/7N1-MVB-WKF/download" {
			http.Error(writer, "Level not found.", http.StatusNotFound)
			return
		}
		http.Error(writer, "unexpected", http.StatusInternalServerError)
	})
	level := stub.client().withClient(&Level{ID: "lv1", Code: "7N1-MVB-WKF", Title: "Gone", Slug: "gone"})
	_, err := level.Download()
	asNotFoundError(t, err)
	if !strings.Contains(strings.ToLower(err.Error()), "level not found") {
		t.Errorf("error %q does not say level not found", err)
	}
}

func TestPackDownloadSuccess(t *testing.T) {
	stub := newStub(t)
	stub.packs["1.2.0"] = 200
	body, err := stub.client().DownloadPack("thps", "1.2.0")
	if err != nil {
		t.Fatal(err)
	}
	if string(body) != "zip-for-thps" {
		t.Errorf("body = %q", body)
	}
	want := "GET /api/p/thps/download?platform=windows&version=1.2.0"
	if stub.calls[0] != want {
		t.Errorf("call = %q, want %q", stub.calls[0], want)
	}
}

func TestPackNotHostedIsDistinctFromNetworkFailure(t *testing.T) {
	stub := newStub(t)
	_, hostedErr := stub.client().DownloadPack("thps", "9.9.9")
	asPackNotHosted(t, hostedErr)
	if !strings.Contains(hostedErr.Error(), "9.9.9") || !strings.Contains(hostedErr.Error(), "thps") {
		t.Errorf("error %q should name the pack and version", hostedErr)
	}

	missing, ok := hostedErr.(interface{ PackNotHosted() bool })
	if !ok || !missing.PackNotHosted() {
		t.Errorf("a 404 must answer PackNotHosted() true")
	}
}

// TestOfflineHostIsUnreachable points the client at a loopback port nothing
// listens on: the failure is a connect error, and a pack is never reported as
// merely unhosted because the site could not be reached.
func TestOfflineHostIsUnreachable(t *testing.T) {
	client := NewClient("http://127.0.0.1:1")
	if _, err := client.LookupLevel("7N1-MVB-WKF"); err == nil {
		t.Error("want an error for an unreachable API")
	}
	_, err := client.DownloadPack("thps", "1.2.0")
	if err == nil {
		t.Fatal("want an error for an unreachable API")
	}
	if verdict, ok := err.(interface{ PackNotHosted() bool }); ok && verdict.PackNotHosted() {
		t.Errorf("an unreachable API must not report PackNotHosted(): %v", err)
	}
	if verdict, ok := err.(interface{ RateLimited() bool }); ok && verdict.RateLimited() {
		t.Errorf("an unreachable API must not report RateLimited(): %v", err)
	}
}

func TestPackServerErrorIsNotNotHosted(t *testing.T) {
	stub := newStub(t)
	stub.packs["1.2.0"] = http.StatusInternalServerError
	_, err := stub.client().DownloadPack("thps", "1.2.0")
	if err == nil {
		t.Fatal("want an error")
	}
	if verdict, ok := err.(interface{ PackNotHosted() bool }); ok && verdict.PackNotHosted() {
		t.Errorf("a 500 must not report PackNotHosted(): %v", err)
	}
	if _, ok := err.(interface{ RateLimited() bool }); ok {
		t.Errorf("a 500 must not report RateLimited(): %v", err)
	}
}

func TestPackRejectsAnUnsafeID(t *testing.T) {
	stub := newStub(t)
	for _, id := range []string{"", "Thps", "../etc", "a b", "thps/.."} {
		if _, err := stub.client().DownloadPack(id, "1.2.0"); err == nil {
			t.Errorf("DownloadPack(%q): want an error", id)
		}
	}
	if len(stub.calls) != 0 {
		t.Errorf("an unsafe pack id should not reach the server: %v", stub.calls)
	}
}

func TestRateLimitedResponseTellsThePlayerToWait(t *testing.T) {
	t.Run("lookup", func(t *testing.T) {
		stub := newStub(t)
		stub.status = http.StatusTooManyRequests
		_, err := stub.ask(t, "7N1-MVB-WKF")
		assertRateLimited(t, err)
	})
	t.Run("level download", func(t *testing.T) {
		stub := newStub(t)
		stub.server.Config.Handler = http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
			http.Error(writer, "Too Many Requests", http.StatusTooManyRequests)
		})
		level := stub.client().withClient(&Level{ID: "lv1", Code: "7N1-MVB-WKF", Title: "Busy", Slug: "busy"})
		_, err := level.Download()
		assertRateLimited(t, err)
	})
	t.Run("pack download", func(t *testing.T) {
		stub := newStub(t)
		stub.packs["1.2.0"] = http.StatusTooManyRequests
		_, err := stub.client().DownloadPack("thps", "1.2.0")
		assertRateLimited(t, err)
	})
}

func assertRateLimited(t *testing.T, err error) {
	t.Helper()
	if err == nil {
		t.Fatal("want an error")
	}
	limited, ok := err.(interface{ RateLimited() bool })
	if !ok || !limited.RateLimited() {
		t.Fatalf("error %v (%T) does not report RateLimited()", err, err)
	}
	message := strings.ToLower(err.Error())
	if !strings.Contains(message, "wait") || !strings.Contains(message, "retry") {
		t.Errorf("error %q should tell the player to wait and retry", err)
	}
}

func TestRateLimitHonoursRetryAfter(t *testing.T) {
	stub := newStub(t)
	stub.server.Config.Handler = http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		writer.Header().Set("Retry-After", "42")
		http.Error(writer, "Too Many Requests", http.StatusTooManyRequests)
	})
	if _, err := stub.ask(t, "7N1-MVB-WKF"); err == nil {
		t.Fatal("want an error")
	} else {
		var limited *RateLimitedError
		if !errors.As(err, &limited) {
			t.Fatalf("error %v (%T) is not a RateLimitedError", err, err)
		}
		if limited.Seconds != 42 {
			t.Errorf("Seconds = %d, want the server's 42", limited.Seconds)
		}
		if !strings.Contains(err.Error(), "42") {
			t.Errorf("error %q should name the wait", err)
		}
	}
}

func TestServerErrorMessageIsCarried(t *testing.T) {
	stub := newStub(t)
	stub.server.Config.Handler = http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		writer.Header().Set("Content-Type", "application/json")
		writer.WriteHeader(http.StatusBadRequest)
		fmt.Fprint(writer, `{"code":"validation_bad","message":"platform must be windows or linux."}`)
	})
	_, err := stub.client().DownloadPack("thps", "1.2.0")
	if err == nil {
		t.Fatal("want an error")
	}
	if !strings.Contains(err.Error(), "platform must be windows or linux.") {
		t.Errorf("error %q should carry the server's own message", err)
	}
}

func TestFileNamesCannotEscapeTheFileRoute(t *testing.T) {
	stub := newStub(t)
	stub.metadata = `{"id":"lv1","title":"Twisty","level":"twisty.mblevel.json","cover":"../../etc/passwd","biome":"a b/../c.png"}`
	level, err := stub.ask(t, "7N1-MVB-WKF")
	if err != nil {
		t.Fatal(err)
	}
	// Nothing survives that could climb out of the record's own folder: no
	// separator, and no run of dots either.
	wantCover := stub.server.URL + "/api/files/levels/lv1/....etcpasswd"
	if level.CoverURL() != wantCover {
		t.Errorf("CoverURL = %q, want %q", level.CoverURL(), wantCover)
	}
	wantBiome := stub.server.URL + "/api/files/levels/lv1/ab..c.png"
	if level.BiomeURL() != wantBiome {
		t.Errorf("BiomeURL = %q, want %q", level.BiomeURL(), wantBiome)
	}
	for _, url := range []string{level.CoverURL(), level.BiomeURL()} {
		name := url[strings.LastIndex(url, "/")+1:]
		if strings.Contains(name, "..") && strings.ContainsAny(name, "/\\") {
			t.Errorf("%q keeps a traversal-capable file name", url)
		}
	}
}

func TestPackVersionIsEscapedIntoTheQuery(t *testing.T) {
	stub := newStub(t)
	stub.packs["1.0 &platform=linux"] = 200
	if _, err := stub.client().DownloadPack("thps", "1.0 &platform=linux"); err != nil {
		t.Fatal(err)
	}
	want := "GET /api/p/thps/download?platform=windows&version=1.0+%26platform%3Dlinux"
	if stub.calls[0] != want {
		t.Errorf("call = %q, want %q", stub.calls[0], want)
	}
}

func TestPackIDsWithoutABundleAreNotHosted(t *testing.T) {
	stub := newStub(t)
	// The site answers 404 both for an unknown version and for a record with
	// no windows bundle; both read as "not hosted here".
	for _, version := range []string{"0.0.1", "1.2.0"} {
		stub.packs[version] = http.StatusNotFound
		_, err := stub.client().DownloadPack("thps", version)
		notHosted := asPackNotHosted(t, err)
		if notHosted.PackID != "thps" || notHosted.Version != version {
			t.Errorf("PackNotHostedError = %+v, want thps %s", notHosted, version)
		}
	}
}

func TestPackWithoutAVersionAsksForTheNewest(t *testing.T) {
	stub := newStub(t)
	stub.packs[""] = 200
	if _, err := stub.client().DownloadPack("thps", ""); err != nil {
		t.Fatal(err)
	}
	want := "GET /api/p/thps/download?platform=windows"
	if stub.calls[0] != want {
		t.Errorf("call = %q, want %q", stub.calls[0], want)
	}
}

func TestErrorMessagesNameTheCode(t *testing.T) {
	stub := newStub(t)
	stub.status = http.StatusNotFound
	if _, err := stub.ask(t, "7N1-MVB-WKF"); err == nil || !strings.Contains(err.Error(), "7N1-MVB-WKF") {
		t.Errorf("error %q should name the share code", err)
	}
}

func TestBaseURLEnvironmentOverride(t *testing.T) {
	stub := newStub(t)
	t.Setenv(BaseURLEnv, stub.server.URL)
	level, err := NewClientFromEnv().LookupLevel("7N1-MVB-WKF")
	if err != nil {
		t.Fatal(err)
	}
	if level.CoverURL() != stub.server.URL+"/api/files/levels/lv1/cover.png" {
		t.Errorf("CoverURL = %q should use the overridden base", level.CoverURL())
	}
}

func TestDefaultBaseURLOverridable(t *testing.T) {
	if got, err := NormalizeBaseURL(""); err != nil || got != DefaultBaseURL {
		t.Errorf("NormalizeBaseURL(\"\") = %q, %v; want %q", got, err, DefaultBaseURL)
	}
	if DefaultBaseURL != "https://api.megabonkmod.party" {
		t.Errorf("DefaultBaseURL = %q", DefaultBaseURL)
	}
	t.Setenv(BaseURLEnv, "")
	if got := NewClientFromEnv().BaseURL(); got != DefaultBaseURL {
		t.Errorf("blank %s = %q, want the default", BaseURLEnv, got)
	}
}

func TestBaseURLValidation(t *testing.T) {
	for _, raw := range []string{
		"https://api.megabonkmod.party",
		"http://127.0.0.1:8090",
		"http://127.0.0.1:8090/",
		"api.megabonkmod.party",
	} {
		got, err := NormalizeBaseURL(raw)
		if err != nil {
			t.Errorf("NormalizeBaseURL(%q): %s", raw, err)
			continue
		}
		if !strings.HasPrefix(got, "http") || strings.HasSuffix(got, "/") {
			t.Errorf("NormalizeBaseURL(%q) = %q", raw, got)
		}
	}
	for _, raw := range []string{"not a url", "ftp://api.example", "//api.example", "https://", "https://api.example/path"} {
		if got, err := NormalizeBaseURL(raw); err == nil {
			t.Errorf("NormalizeBaseURL(%q) = %q, want an error", raw, got)
		}
	}
}

func TestClientKeepsRedirectsOnTheAPIHost(t *testing.T) {
	client := NewClient("https://api.example")
	check := client.HTTPClient().CheckRedirect
	if check == nil {
		t.Fatal("the client must limit where redirects may go")
	}
	via, _ := http.NewRequest(http.MethodGet, "https://api.example/api/l/7N1-MVB-WKF/download", nil)
	offHost, _ := http.NewRequest(http.MethodGet, "https://evil.example/level.json", nil)
	if err := check(offHost, []*http.Request{via}); err == nil {
		t.Error("a redirect off the API host should be refused")
	}
	same, _ := http.NewRequest(http.MethodGet, "https://api.example/api/files/levels/lv1/level.json", nil)
	if err := check(same, []*http.Request{via}); err != nil {
		t.Errorf("a redirect within the API host should be allowed: %s", err)
	}
}

// SourceScan reads the package's own sources, so the check below stays a
// package-level fact rather than a walk of whatever directory the test happens
// to run in.
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

// TestNoResolvableHostInSources proves the client's host always comes from
// DefaultBaseURL or the environment: nothing in the package names a host the
// client could resolve, so go test can only reach a local server or a closed
// loopback port.
func TestNoResolvableHostInSources(t *testing.T) {
	original := SourceScan
	defer func() { SourceScan = original }()
	SourceScan = plantedSources(
		// A spelling of the constants is not a host the client could resolve.
		"good.go", "const host = DefaultBaseURL\nconst site = SiteHost\n",
		// An escaped literal would hide the host from a plain scan, so the
		// check decodes string literals too.
		"bad.go", "const live = \"https://"+splitHost("api", "megabonkmod", "party", "evil", "example")+"\n",
	)
	offenders := resolvableHostLines()
	if len(offenders) != 1 || !strings.Contains(offenders[0], "bad.go") {
		t.Fatalf("resolvableHostLines() = %v, want only the planted host name", offenders)
	}

	// A marker only excuses its own line, never the file's other ones.
	SourceScan = plantedSources(
		"mixed.go", "const a = \""+splitHost("api", "megabonkmod", "party")+"\"\n"+
			"const b = \""+splitHost("cdn", "megabonkmod", "party")+"\"\n",
	)
	if offenders := resolvableHostLines(); len(offenders) != 1 ||
		!strings.Contains(offenders[0], splitHost("cdn", "megabonkmod", "party")) {
		t.Fatalf("resolvableHostLines() = %v, want only the unmarked host", offenders)
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

// plantedSources builds fake package sources from alternating name and content
// strings. The contents spell hosts with splitHost so the fixture's own text
// does not read as a host the client could resolve.
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

// allowedHosts are the hostnames spelled by the package's own constants.
var allowedHosts = hostnamesOf(DefaultBaseURL, SiteHost)

var backtickLiterals = regexp.MustCompile("`[^`]*`")

var quotedLiterals = regexp.MustCompile(`"(?:[^"\\]|\\.)*"`)

// resolvableHostLines names every source line carrying an API hostname other
// than DefaultBaseURL or SiteHost. String literals are decoded first, because
// an escaped spelling is exactly what would hide a host from a plain scan.
func resolvableHostLines() []string {
	sources, err := SourceScan()
	if err != nil {
		return []string{err.Error()}
	}
	var offenders []string
	names := make([]string, 0, len(sources))
	for name := range sources {
		names = append(names, name)
	}
	sort.Strings(names)
	for _, file := range names {
		for number, line := range strings.Split(sources[file], "\n") {
			if host := unexpectedHost(decodedSourceText(line)); host != "" {
				offenders = append(offenders, fmt.Sprintf("%s:%d resolves %s: %s",
					file, number+1, host, strings.TrimSpace(line)))
			}
		}
	}
	return offenders
}

// unexpectedHost returns the first hostname in text that the package is not
// allowed to name, or "" when every host in it is one of the constants.
func unexpectedHost(text string) string {
	for _, name := range hostLikeName.FindAllString(strings.ToLower(text), -1) {
		if strings.Contains(name, SiteHost) && !allowedHosts[name] {
			return name
		}
	}
	return ""
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

// decodedSourceText adds a line's string-literal contents to its raw text, so
// a host written as "api\.megabonkmod\.party" is still seen.
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

func TestEveryRequestGoesToTheConfiguredHost(t *testing.T) {
	spy := &spyTransport{}
	client := NewClient(DefaultBaseURL)
	client.HTTPClient().Transport = spy
	if _, err := client.LookupLevel("7N1-MVB-WKF"); err == nil {
		t.Fatal("want the error the spy answers")
	}
	if len(spy.hosts) == 0 {
		t.Fatal("the client made no request")
	}
	for _, host := range spy.hosts {
		if host != "api.megabonkmod.party" {
			t.Errorf("the client went to %s, not the configured API host", host)
		}
	}
}

type spyTransport struct {
	hosts []string
}

func (s *spyTransport) RoundTrip(request *http.Request) (*http.Response, error) {
	s.hosts = append(s.hosts, request.URL.Host)
	recorder := httptest.NewRecorder()
	recorder.WriteHeader(http.StatusNotFound)
	return recorder.Result(), nil
}

func asNotFoundError(t *testing.T, err error) *NotFoundError {
	t.Helper()
	var notFound *NotFoundError
	if errors.As(err, &notFound) {
		return notFound
	}
	t.Fatalf("error %v (%T) is not a NotFoundError", err, err)
	return nil
}

func asPackNotHosted(t *testing.T, err error) *PackNotHostedError {
	t.Helper()
	var notHosted *PackNotHostedError
	if errors.As(err, &notHosted) {
		return notHosted
	}
	t.Fatalf("error %v (%T) is not a PackNotHostedError", err, err)
	return nil
}
