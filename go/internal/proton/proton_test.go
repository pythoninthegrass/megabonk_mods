package proton

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func write(t *testing.T, path, text string) string {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(text), 0o644); err != nil {
		t.Fatal(err)
	}
	return path
}

func prefixDir(t *testing.T) string {
	t.Helper()
	prefix := filepath.Join(t.TempDir(), "compatdata", "3405340", "pfx")
	if err := os.MkdirAll(filepath.Join(prefix, "drive_c"), 0o755); err != nil {
		t.Fatal(err)
	}
	return prefix
}

const wineUserReg = `WINE REGISTRY Version 2
;; All keys relative to REGISTRY\User\S-1-5-21-1
` + "\n" + `#arch=win64

[Software\\Wine\\AppDefaults\\ffxvi.exe\\DllOverrides] 1793463286
"#time=1dd6952f286302a"
"atiadlxx"="builtin"

[Software\\Wine\\DllOverrides] 1793463301
"#time=1dd6952fb51ad38"
"api-ms-win-crt-heap-l1-1-0"="native,builtin"
"version"="native,builtin"

[Software\\Wine\\Fonts] 1793463286
"#time=1dd6952f285031c"
'@=""
`

func TestReadDllOverrideReadsWhatWineWrote(t *testing.T) {
	prefix := prefixDir(t)
	write(t, filepath.Join(prefix, "user.reg"), wineUserReg)
	if got, ok := ReadDllOverride(prefix, "version", ""); !ok || got != "native,builtin" {
		t.Errorf("version = %q, %v", got, ok)
	}
	if got, ok := ReadDllOverride(prefix, "VERSION", ""); !ok || got != "native,builtin" {
		t.Errorf("the name should be case-insensitive: %q, %v", got, ok)
	}
	if _, ok := ReadDllOverride(prefix, "atiadlxx", ""); ok {
		t.Error("an AppDefaults section is not the game's DllOverrides")
	}
	if _, ok := ReadDllOverride(prefix, "nope", ""); ok {
		t.Error("an unknown name has no value")
	}

	missing := prefixDir(t)
	if _, ok := ReadDllOverride(missing, "version", ""); ok {
		t.Error("a prefix with no user.reg has no override")
	}
	write(t, filepath.Join(missing, "user.reg"), `REGEDIT4

[Software\\Wine\\AppDefaults]
"foo"="bar"
`)
	if _, ok := ReadDllOverride(missing, "version", ""); ok {
		t.Error("no DllOverrides section means no override")
	}
}

func TestSetDllOverrideCreatesTheSectionAndEntry(t *testing.T) {
	prefix := prefixDir(t)
	write(t, filepath.Join(prefix, "user.reg"), "REGEDIT4\n\n[Software\\\\Wine\\\\AppDefaults]\n\"foo\"=\"bar\"\n")
	if got := SetDllOverride(prefix, "version", "native,builtin", "", "", nil); got != "registry" {
		t.Fatalf("via = %q", got)
	}
	text, err := os.ReadFile(filepath.Join(prefix, "user.reg"))
	if err != nil {
		t.Fatal(err)
	}
	body := string(text)
	if !strings.Contains(body, `[Software\Wine\DllOverrides]`) {
		t.Errorf("the section is missing:\n%s", body)
	}
	if !strings.Contains(body, `"foo"="bar"`) {
		t.Errorf("the other section was lost:\n%s", body)
	}
	if got, ok := ReadDllOverride(prefix, "version", ""); !ok || got != "native,builtin" {
		t.Errorf("round trip = %q, %v", got, ok)
	}
}

func TestSetDllOverrideReplacesWithoutDuplicating(t *testing.T) {
	prefix := prefixDir(t)
	write(t, filepath.Join(prefix, "user.reg"), "REGEDIT4\n\n[Software\\\\Wine\\\\DllOverrides]\n\"version\"=\"builtin\"\n")
	SetDllOverride(prefix, "version", "native,builtin", "", "", nil)
	SetDllOverride(prefix, "version", "native,builtin", "", "", nil)
	text, err := os.ReadFile(filepath.Join(prefix, "user.reg"))
	if err != nil {
		t.Fatal(err)
	}
	if count := strings.Count(string(text), `"version"=`); count != 1 {
		t.Errorf("the entry appears %d times:\n%s", count, text)
	}
	if got, ok := ReadDllOverride(prefix, "version", ""); !ok || got != "native,builtin" {
		t.Errorf("value = %q, %v", got, ok)
	}
}

func TestSetDllOverrideEditsARealWineFileInPlace(t *testing.T) {
	prefix := prefixDir(t)
	write(t, filepath.Join(prefix, "user.reg"), strings.Replace(wineUserReg, "\n\"version\"=\"native,builtin\"", "", 1))
	if got := SetDllOverride(prefix, "version", "native,builtin", "", "", nil); got != "registry" {
		t.Fatalf("via = %q", got)
	}
	text, err := os.ReadFile(filepath.Join(prefix, "user.reg"))
	if err != nil {
		t.Fatal(err)
	}
	body := string(text)
	if count := strings.Count(body, `[Software\\Wine\\DllOverrides]`); count != 1 {
		t.Errorf("the section appears %d times:\n%s", count, body)
	}
	start := strings.Index(body, `[Software\\Wine\\DllOverrides]`)
	end := strings.Index(body, `[Software\\Wine\\Fonts]`)
	if !strings.Contains(body[start:end], `"version"="native,builtin"`) {
		t.Errorf("the entry is not in the section:\n%s", body[start:end])
	}
	if got, ok := ReadDllOverride(prefix, "version", ""); !ok || got != "native,builtin" {
		t.Errorf("value = %q, %v", got, ok)
	}
}

func TestSetDllOverrideAddsAWineStyleHeaderWhenMissing(t *testing.T) {
	without := wineUserReg[:strings.Index(wineUserReg, `[Software\\Wine\\DllOverrides]`)] + "[Software\\\\Wine\\\\Fonts] 1793463286\n"
	prefix := prefixDir(t)
	write(t, filepath.Join(prefix, "user.reg"), without)
	if _, ok := ReadDllOverride(prefix, "version", ""); ok {
		t.Fatal("the fixture should start without the section")
	}
	SetDllOverride(prefix, "version", "native,builtin", "", "", nil)
	text, err := os.ReadFile(filepath.Join(prefix, "user.reg"))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(text), `[Software\\Wine\\DllOverrides]`) {
		t.Errorf("a WINE REGISTRY file needs the escaped header:\n%s", text)
	}
	if got, ok := ReadDllOverride(prefix, "version", ""); !ok || got != "native,builtin" {
		t.Errorf("value = %q, %v", got, ok)
	}
}

func TestSetDllOverrideCreatesUserRegWhenAbsent(t *testing.T) {
	prefix := prefixDir(t)
	if got := SetDllOverride(prefix, "version", "native,builtin", "", "", nil); got != "registry" {
		t.Fatalf("via = %q", got)
	}
	if got, ok := ReadDllOverride(prefix, "version", ""); !ok || got != "native,builtin" {
		t.Errorf("value = %q, %v", got, ok)
	}
	text, err := os.ReadFile(filepath.Join(prefix, "user.reg"))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.HasPrefix(string(text), "REGEDIT4\n\n[Software\\Wine\\DllOverrides]\n") {
		t.Errorf("new file:\n%s", text)
	}
}

func TestSetDllOverrideWritesBackWithoutGrowth(t *testing.T) {
	prefix := prefixDir(t)
	write(t, filepath.Join(prefix, "user.reg"), wineUserReg)
	SetDllOverride(prefix, "version", "native,builtin", "", "", nil)
	first, err := os.ReadFile(filepath.Join(prefix, "user.reg"))
	if err != nil {
		t.Fatal(err)
	}
	SetDllOverride(prefix, "version", "native,builtin", "", "", nil)
	second, err := os.ReadFile(filepath.Join(prefix, "user.reg"))
	if err != nil {
		t.Fatal(err)
	}
	if string(first) != string(second) {
		t.Errorf("a second write changed the file:\n%s\n---\n%s", first, second)
	}
}

func containsToken(tokens []string, wanted string) bool {
	for _, token := range tokens {
		if token == wanted {
			return true
		}
	}
	return false
}

func TestSetDllOverridePrefersTheWineBinary(t *testing.T) {
	prefix := prefixDir(t)
	type call struct {
		argv []string
		env  map[string]string
	}
	var calls []call
	runner := func(argv []string, env map[string]string) int {
		calls = append(calls, call{argv, env})
		return 0
	}
	wine := filepath.Join(t.TempDir(), "wine")
	if got := SetDllOverride(prefix, "version", "native,builtin", "", wine, runner); got != "wine" {
		t.Fatalf("via = %q", got)
	}
	if len(calls) != 1 {
		t.Fatalf("calls = %d", len(calls))
	}
	argv := calls[0].argv
	if argv[0] != wine || argv[1] != "reg" || argv[2] != "add" {
		t.Errorf("argv = %v", argv)
	}
	if !strings.Contains(strings.Join(argv, " "), `HKCU\Software\Wine\DllOverrides`) {
		t.Errorf("the key is missing from %v", argv)
	}
	if !containsToken(argv, "version") || !containsToken(argv, "native,builtin") {
		t.Errorf("name and value should be arguments: %v", argv)
	}
	if calls[0].env["WINEPREFIX"] != filepath.ToSlash(prefix) || calls[0].env["WINEDEBUG"] != "-all" {
		t.Errorf("env = %v", calls[0].env)
	}
	if _, ok := ReadDllOverride(prefix, "version", ""); ok {
		t.Error("the wine path should not also edit the file")
	}
}

func TestSetDllOverrideFallsBackWhenWineFails(t *testing.T) {
	prefix := prefixDir(t)
	runner := func(argv []string, env map[string]string) int { return 1 }
	if got := SetDllOverride(prefix, "version", "native,builtin", "", filepath.Join(t.TempDir(), "wine"), runner); got != "registry" {
		t.Fatalf("via = %q", got)
	}
	if got, ok := ReadDllOverride(prefix, "version", ""); !ok || got != "native,builtin" {
		t.Errorf("value = %q, %v", got, ok)
	}
}

func TestClearDllOverrideRemovesOnlyThatEntry(t *testing.T) {
	prefix := prefixDir(t)
	write(t, filepath.Join(prefix, "user.reg"), wineUserReg)
	if got := ClearDllOverride(prefix, "version", "", "", nil); got != "registry" {
		t.Fatalf("via = %q", got)
	}
	if _, ok := ReadDllOverride(prefix, "version", ""); ok {
		t.Error("the entry should be gone")
	}
	text, err := os.ReadFile(filepath.Join(prefix, "user.reg"))
	if err != nil {
		t.Fatal(err)
	}
	body := string(text)
	if !strings.Contains(body, `"api-ms-win-crt-heap-l1-1-0"="native,builtin"`) {
		t.Errorf("a sibling entry was lost:\n%s", body)
	}
	if !strings.Contains(body, `[Software\\Wine\\DllOverrides]`) {
		t.Errorf("the section header should stay:\n%s", body)
	}

	runner := func(argv []string, env map[string]string) int { return 0 }
	via := ClearDllOverride(prefix, "version", "", filepath.Join(t.TempDir(), "wine"), runner)
	if via != "wine" {
		t.Errorf("via = %q", via)
	}
}

func TestRunReportsAFailureForAMissingBinary(t *testing.T) {
	if got := run([]string{filepath.Join(t.TempDir(), "no-such-wine"), "reg"}, map[string]string{}); got != 1 {
		t.Errorf("run = %d, want 1", got)
	}
	if got := run(nil, nil); got != 1 {
		t.Errorf("run(nil) = %d, want 1", got)
	}
}
