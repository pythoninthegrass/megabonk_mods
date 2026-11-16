package site

import (
	"errors"
	"net/http"
	"strings"
	"testing"
)

func TestLookupLevelByFilenameMatchesTheStoredFile(t *testing.T) {
	stub := newStub(t)
	stub.records = `{"id":"lv9","title":"Home Ramp","level":"home-ramp.mblevel.json","cover":"","biome":"",` +
		`"packs":{"ramps":"2.0.0"}}`
	found, err := stub.client().LookupLevelByFilename("home-ramp.mblevel.json")
	if err != nil {
		t.Fatal(err)
	}
	if found.Title != "Home Ramp" || found.Packs["ramps"] != "2.0.0" {
		t.Errorf("found = %+v", found)
	}
	if len(stub.calls) == 0 || !strings.Contains(stub.calls[len(stub.calls)-1], "filter=") {
		t.Errorf("the lookup should filter by file name: %v", stub.calls)
	}
}

func TestLookupLevelByFilenameReportsNoMatchAsNotFound(t *testing.T) {
	stub := newStub(t)
	stub.records = ``
	_, err := stub.client().LookupLevelByFilename("absent.mblevel.json")
	if err == nil {
		t.Fatal("an empty page is no match")
	}
	var notFound *NotFoundError
	if !errors.As(err, &notFound) {
		t.Errorf("err = %T %v", err, err)
	}
}

func TestLookupLevelByFilenameRefusesAnUnsafeName(t *testing.T) {
	stub := newStub(t)
	if _, err := stub.client().LookupLevelByFilename("../etc/passwd"); err == nil {
		t.Error("a name that is not a file name is refused before the request")
	}
}

func TestDownloadFileTakesAPictureURLFromTheSameHost(t *testing.T) {
	stub := newStub(t)
	body, err := stub.client().DownloadFile(stub.server.URL + "/api/files/levels/lv1/cover.png")
	if err != nil {
		t.Fatal(err)
	}
	if string(body) != "cover" {
		t.Errorf("body = %q", body)
	}
	if _, err := stub.client().DownloadFile("http://127.0.0.1:1/cover.png"); err == nil {
		t.Error("an unreachable file is an error")
	}
	if _, err := stub.client().DownloadFile("not a url"); err == nil {
		t.Error("a URL that is not one is refused")
	}
}

func TestPackDownloadURLNamesTheRoute(t *testing.T) {
	stub := newStub(t)
	got := stub.client().PackDownloadURL("thps", "1.2.0")
	want := stub.server.URL + "/api/p/thps/download?platform=windows&version=1.2.0"
	if got != want {
		t.Errorf("PackDownloadURL = %q, want %q", got, want)
	}
	if !strings.Contains(stub.client().PackDownloadURL("thps", ""), "platform=windows") {
		t.Error("a pack with no version still names the platform")
	}
}

func TestIsPackNotHostedDistinguishesAMissingPack(t *testing.T) {
	stub := newStub(t)
	stub.packs[""] = http.StatusNotFound
	_, err := stub.client().DownloadPack("thps", "")
	if err == nil {
		t.Fatal("an unhosted pack is an error")
	}
	if !IsPackNotHosted(err) {
		t.Errorf("IsPackNotHosted(%v) = false", err)
	}
	if IsPackNotHosted(errors.New("plain")) {
		t.Error("a plain error is not a missing pack")
	}
}
