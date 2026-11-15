package proton

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ppath"
)

func winePrefix(t *testing.T) string {
	t.Helper()
	prefix := filepath.Join(t.TempDir(), ".wine")
	if err := os.MkdirAll(filepath.Join(prefix, "drive_c"), 0o755); err != nil {
		t.Fatal(err)
	}
	return prefix
}

func TestWineHTTPOverrideNamesTheProxyWineMustLoad(t *testing.T) {
	if DLLName != "version" {
		t.Errorf("the MelonLoader shim override uses %q", DLLName)
	}
	if WinHTTPDLLName != "winhttp" {
		t.Errorf("WinHTTPDLLName = %q", WinHTTPDLLName)
	}
	if WinHTTPValue != "native,builtin" {
		t.Errorf("WinHTTPValue = %q", WinHTTPValue)
	}
	if WinHTTPLaunchOption != `WINEDLLOVERRIDES="winhttp=n,b" %command%` {
		t.Errorf("WinHTTPLaunchOption = %q", WinHTTPLaunchOption)
	}
}

func TestSetWinHTTPOverrideWritesThePrefixRegistry(t *testing.T) {
	prefix := winePrefix(t)
	if value, found := ReadDllOverride(prefix, WinHTTPDLLName, ""); found {
		t.Fatalf("a fresh prefix already has winhttp = %q", value)
	}
	via := SetDllOverride(prefix, WinHTTPDLLName, WinHTTPValue, "", "", nil)
	if via != "registry" {
		t.Errorf("via = %q", via)
	}
	value, found := ReadDllOverride(prefix, WinHTTPDLLName, "")
	if !found || value != WinHTTPValue {
		t.Errorf("winhttp = %q, found = %v", value, found)
	}
	body, err := ppath.ReadText(UserRegPath(prefix))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(body, `"winhttp"="native,builtin"`) {
		t.Errorf("user.reg:\n%s", body)
	}
	if strings.Contains(body, `"version"=`) {
		t.Errorf("the MelonLoader override leaked into a BepInEx prefix:\n%s", body)
	}
}

func TestSetWinHTTPOverrideThroughWine(t *testing.T) {
	prefix := winePrefix(t)
	var calls [][]string
	runner := func(argv []string, env map[string]string) int {
		calls = append(calls, argv)
		if env["WINEPREFIX"] != ppath.Normalize(prefix) {
			t.Errorf("WINEPREFIX = %q", env["WINEPREFIX"])
		}
		return 0
	}
	via := SetDllOverride(prefix, WinHTTPDLLName, WinHTTPValue, "", "/usr/bin/wine", runner)
	if via != "wine" {
		t.Errorf("via = %q", via)
	}
	if len(calls) != 1 {
		t.Fatalf("calls = %v", calls)
	}
	joined := strings.Join(calls[0], " ")
	for _, want := range []string{`HKCU\Software\Wine\DllOverrides`, "/v", "winhttp", "/d", "native,builtin"} {
		if !strings.Contains(joined, want) {
			t.Errorf("the registry command %q should carry %q", joined, want)
		}
	}
}

func TestSetWinHTTPOverrideIsIdempotent(t *testing.T) {
	prefix := winePrefix(t)
	SetDllOverride(prefix, WinHTTPDLLName, WinHTTPValue, "", "", nil)
	SetDllOverride(prefix, WinHTTPDLLName, WinHTTPValue, "", "", nil)
	body, err := ppath.ReadText(UserRegPath(prefix))
	if err != nil {
		t.Fatal(err)
	}
	if got := strings.Count(body, `"winhttp"=`); got != 1 {
		t.Errorf("user.reg carries %d winhttp entries:\n%s", got, body)
	}
}

func TestClearWinHTTPOverrideRemovesOnlyItsOwnEntry(t *testing.T) {
	prefix := winePrefix(t)
	write(t, UserRegPath(prefix), "WINE REGISTRY Version 6\n\n"+
		"[Software\\\\Wine\\\\DllOverrides] 1700000000\n"+
		`"winhttp"="native,builtin"`+"\n"+
		`"d3d11"="builtin"`+"\n")
	if _, found := ReadDllOverride(prefix, WinHTTPDLLName, ""); !found {
		t.Fatal("the prefix has no winhttp entry to clear")
	}
	via := ClearDllOverride(prefix, WinHTTPDLLName, "", "", nil)
	if via != "registry" {
		t.Errorf("via = %q", via)
	}
	if _, found := ReadDllOverride(prefix, WinHTTPDLLName, ""); found {
		t.Error("the winhttp override survived")
	}
	if value, found := ReadDllOverride(prefix, "d3d11", ""); !found || value != "builtin" {
		t.Errorf("another player override was taken with it: %q, %v", value, found)
	}
}

func TestClearWinHTTPOverrideOnAMissingPrefixDoesNothing(t *testing.T) {
	missing := filepath.Join(t.TempDir(), "nope", "pfx")
	if value, found := ReadDllOverride(missing, WinHTTPDLLName, ""); found {
		t.Errorf("a prefix that is not there has winhttp = %q", value)
	}
	if via := ClearDllOverride(missing, WinHTTPDLLName, "", "", nil); via != "registry" {
		t.Errorf("via = %q", via)
	}
	if ppath.Exists(UserRegPath(missing)) {
		t.Error("clearing a prefix that is not there created one")
	}
}

func TestWinHTTPOverrideInAHandWrittenRegedit4Prefix(t *testing.T) {
	prefix := winePrefix(t)
	write(t, UserRegPath(prefix), "REGEDIT4\n\n[Software\\\\Wine\\\\DllOverrides]\n"+
		`"d3d9"="builtin"`+"\n")
	SetDllOverride(prefix, WinHTTPDLLName, WinHTTPValue, "", "", nil)
	value, found := ReadDllOverride(prefix, WinHTTPDLLName, "")
	if !found || value != WinHTTPValue {
		t.Errorf("winhttp = %q, found = %v", value, found)
	}
	if value, found := ReadDllOverride(prefix, "d3d9", ""); !found || value != "builtin" {
		t.Errorf("the existing entry was lost: %q, %v", value, found)
	}
	ClearDllOverride(prefix, WinHTTPDLLName, "", "", nil)
	if _, found := ReadDllOverride(prefix, WinHTTPDLLName, ""); found {
		t.Error("the override survived")
	}
	if _, found := ReadDllOverride(prefix, "d3d9", ""); !found {
		t.Error("clearing the override took the player's entry with it")
	}
}
