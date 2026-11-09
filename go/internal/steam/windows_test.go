package steam

import (
	"path/filepath"
	"reflect"
	"testing"
	"time"
)

func regOutput(name, value string) string {
	return "\r\nHKEY_CURRENT_USER\\Software\\Valve\\Steam\r\n    " + name + "    REG_SZ    " + value + "\r\n\r\n"
}

func fakeRegistry(t *testing.T, values map[string]string) {
	t.Helper()
	restore := CommandRunner
	CommandRunner = func(argv []string, timeout time.Duration) (int, string, error) {
		if len(argv) < 5 || argv[0] != "reg" || argv[1] != "query" || argv[3] != "/v" {
			t.Errorf("argv = %v", argv)
			return 1, "", nil
		}
		value, found := values[argv[2]+"\\"+argv[4]]
		if !found {
			return 1, "", nil
		}
		return 0, regOutput(argv[4], value), nil
	}
	t.Cleanup(func() { CommandRunner = restore })
}

func TestRegistryStringReadsTheValueFromRegQueryOutput(t *testing.T) {
	fakeRegistry(t, map[string]string{`HKCU\Software\Valve\Steam\SteamPath`: "c:/program files (x86)/steam"})
	value, found := RegistryString(`HKCU\Software\Valve\Steam`, "SteamPath")
	if !found || value != "c:/program files (x86)/steam" {
		t.Errorf("value = %q, found = %v", value, found)
	}
}

func TestRegistryStringReportsAMissingValue(t *testing.T) {
	fakeRegistry(t, nil)
	if value, found := RegistryString(`HKCU\Software\Valve\Steam`, "SteamPath"); found || value != "" {
		t.Errorf("value = %q, found = %v", value, found)
	}
}

func TestWindowsClientRootsUsesTheRegistrySteamPath(t *testing.T) {
	root := makeClient(t, filepath.Join(t.TempDir(), "Games", "Steam"), nil)
	fakeRegistry(t, map[string]string{`HKCU\Software\Valve\Steam\SteamPath`: slash(root)})
	clients := WindowsClientRoots(nil)
	want := []Client{{Kind: "native", Root: slash(root)}}
	if !reflect.DeepEqual(clients, want) {
		t.Fatalf("clients = %+v, want %+v", clients, want)
	}
}

func TestWindowsClientRootsFallsBackToTheProgramFilesDefault(t *testing.T) {
	programFiles := filepath.Join(t.TempDir(), "Program Files (x86)")
	root := makeClient(t, filepath.Join(programFiles, "Steam"), nil)
	fakeRegistry(t, nil)
	clients := WindowsClientRoots([]string{programFiles})
	want := []Client{{Kind: "native", Root: slash(root)}}
	if !reflect.DeepEqual(clients, want) {
		t.Fatalf("clients = %+v, want %+v", clients, want)
	}
}

func TestWindowsClientRootsDoesNotRepeatTheRegistryRoot(t *testing.T) {
	programFiles := filepath.Join(t.TempDir(), "Program Files (x86)")
	root := makeClient(t, filepath.Join(programFiles, "Steam"), nil)
	fakeRegistry(t, map[string]string{`HKCU\Software\Valve\Steam\SteamPath`: slash(root)})
	if clients := WindowsClientRoots([]string{programFiles}); len(clients) != 1 {
		t.Fatalf("clients = %+v", clients)
	}
}

func TestWindowsClientRootsFindsNothingWithoutASteamInstall(t *testing.T) {
	fakeRegistry(t, map[string]string{`HKCU\Software\Valve\Steam\SteamPath`: slash(filepath.Join(t.TempDir(), "gone"))})
	if clients := WindowsClientRoots([]string{t.TempDir()}); len(clients) != 0 {
		t.Fatalf("clients = %+v", clients)
	}
}

func TestWindowsLibraryOnAnotherDriveIsFoundThroughTheClientsVdf(t *testing.T) {
	base := t.TempDir()
	other := makeLibrary(t, filepath.Join(base, "D", "SteamLibrary"), true)
	root := makeClient(t, filepath.Join(base, "C", "Steam"), []string{other})
	fakeRegistry(t, map[string]string{`HKCU\Software\Valve\Steam\SteamPath`: slash(root)})
	roots := LibraryRoots(WindowsClientRoots(nil), nil, nil, nil, false)
	if got := FindGameDir(roots, ""); got != slash(filepath.Join(other, "steamapps", "common", GameName)) {
		t.Errorf("game dir = %q", got)
	}
}

func TestProgramFilesDirsReadsTheEnvironment(t *testing.T) {
	env := map[string]string{"ProgramFiles(x86)": `C:\Program Files (x86)`, "ProgramFiles": `C:\Program Files`}
	got := ProgramFilesDirs(func(key string) string { return env[key] })
	want := []string{"C:/Program Files (x86)", "C:/Program Files"}
	if !reflect.DeepEqual(got, want) {
		t.Errorf("dirs = %v, want %v", got, want)
	}
}

func TestLibraryFoldersTurnsEscapedWindowsPathsIntoSlashForm(t *testing.T) {
	root := filepath.Join(t.TempDir(), "Steam")
	mustMkdirAll(t, filepath.Join(root, "steamapps"))
	mustWrite(t, filepath.Join(root, "steamapps", "libraryfolders.vdf"),
		"\"libraryfolders\"\n{\n\t\"0\"\n\t{\n\t\t\"path\"\t\t\"C:\\\\Program Files (x86)\\\\Steam\"\n\t}\n\t\"1\"\n\t{\n\t\t\"path\"\t\t\"D:\\\\SteamLibrary\"\n\t}\n}\n")
	got := LibraryFolders(Client{Kind: "native", Root: slash(root)})
	want := []string{"C:/Program Files (x86)/Steam", "D:/SteamLibrary"}
	if !reflect.DeepEqual(got, want) {
		t.Errorf("libraries = %v, want %v", got, want)
	}
}
