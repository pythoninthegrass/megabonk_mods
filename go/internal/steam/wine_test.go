package steam

import (
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

func makeWinePrefix(t *testing.T, prefix string, libraryPaths []string) string {
	t.Helper()
	root := filepath.Join(prefix, filepath.FromSlash(wineSteamSubpath))
	mustMkdirAll(t, filepath.Join(root, "steamapps"))
	body := ""
	for index, path := range libraryPaths {
		body += "\t\"" + string(rune('0'+index)) + "\"\n\t{\n\t\t\"path\"\t\t\"" + path + "\"\n\t}\n"
	}
	mustWrite(t, filepath.Join(root, "steamapps", "libraryfolders.vdf"), "\"libraryfolders\"\n{\n"+body+"}\n")
	return root
}

func TestWineClientRootsPrefersPlainWineOverCrossOver(t *testing.T) {
	home := filepath.Join(t.TempDir(), "home")
	bottle := filepath.Join(home, "Library", "Application Support", "CrossOver", "Bottles", "Steam")
	makeWinePrefix(t, bottle, nil)
	plain := filepath.Join(home, ".local", "share", "megabonk", "wine")
	makeWinePrefix(t, plain, nil)
	dotWine := filepath.Join(home, ".wine")
	makeWinePrefix(t, dotWine, nil)

	got := WineClientRoots(slash(home))
	want := []Client{
		{Kind: "wine", Root: slash(plain) + "/" + wineSteamSubpath, Prefix: slash(plain)},
		{Kind: "wine", Root: slash(dotWine) + "/" + wineSteamSubpath, Prefix: slash(dotWine)},
		{Kind: "crossover", Root: slash(bottle) + "/" + wineSteamSubpath, Prefix: slash(bottle)},
	}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("clients = %+v, want %+v", got, want)
	}
}

func TestWineClientRootsSkipsPrefixesWithoutSteam(t *testing.T) {
	home := filepath.Join(t.TempDir(), "home")
	mustMkdirAll(t, filepath.Join(home, ".wine", "drive_c"))
	bottles := filepath.Join(home, "Library", "Application Support", "CrossOver", "Bottles")
	mustMkdirAll(t, filepath.Join(bottles, "dw21", "drive_c"))
	steamBottle := filepath.Join(bottles, "Steam")
	makeWinePrefix(t, steamBottle, nil)

	got := WineClientRoots(slash(home))
	want := []Client{{Kind: "crossover", Root: slash(steamBottle) + "/" + wineSteamSubpath, Prefix: slash(steamBottle)}}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("clients = %+v, want %+v", got, want)
	}
}

func TestWineClientRootsFindsNothingOnAMachineWithoutWine(t *testing.T) {
	if got := WineClientRoots(slash(t.TempDir())); len(got) != 0 {
		t.Fatalf("clients = %+v", got)
	}
}

func TestWineLibraryFoldersMapDriveLettersIntoThePrefix(t *testing.T) {
	prefix := filepath.Join(t.TempDir(), "wine")
	root := makeWinePrefix(t, prefix, []string{`C:\\Program Files (x86)\\Steam`, `Z:\\Volumes\\Games\\SteamLibrary`})
	got := LibraryFolders(Client{Kind: "wine", Root: slash(root), Prefix: slash(prefix)})
	want := []string{slash(prefix) + "/" + wineSteamSubpath, "/Volumes/Games/SteamLibrary"}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("libraries = %v, want %v", got, want)
	}
}

func TestWineLibraryFoldersFollowTheDosdevicesLink(t *testing.T) {
	base := t.TempDir()
	prefix := filepath.Join(base, "wine")
	external := filepath.Join(base, "external")
	mustMkdirAll(t, external)
	root := makeWinePrefix(t, prefix, []string{`D:\\SteamLibrary`})
	mustMkdirAll(t, filepath.Join(prefix, "dosdevices"))
	if err := os.Symlink(external, filepath.Join(prefix, "dosdevices", "d:")); err != nil {
		t.Fatal(err)
	}
	got := LibraryFolders(Client{Kind: "wine", Root: slash(root), Prefix: slash(prefix)})
	resolved, err := filepath.EvalSymlinks(external)
	if err != nil {
		t.Fatal(err)
	}
	if want := []string{slash(resolved) + "/SteamLibrary"}; !reflect.DeepEqual(got, want) {
		t.Fatalf("libraries = %v, want %v", got, want)
	}
}

func TestWineLibraryOnZDriveIsFoundWithTheGame(t *testing.T) {
	base := t.TempDir()
	library := makeLibrary(t, filepath.Join(base, "SteamLibrary"), true)
	prefix := filepath.Join(base, "wine")
	makeWinePrefix(t, prefix, []string{`Z:` + escapeSlashes(slash(library))})
	clients := []Client{{Kind: "wine", Root: slash(prefix) + "/" + wineSteamSubpath, Prefix: slash(prefix)}}
	roots := LibraryRoots(clients, nil, nil, nil, false)
	if got := FindGameDir(roots, ""); got != slash(filepath.Join(library, "steamapps", "common", GameName)) {
		t.Errorf("game dir = %q", got)
	}
}

func escapeSlashes(path string) string {
	out := ""
	for _, r := range path {
		if r == '/' {
			out += `\\`
			continue
		}
		out += string(r)
	}
	return out
}

func TestPrefixOfGameDirIsTheDirectoryAboveDriveC(t *testing.T) {
	cases := map[string]string{
		"/h/wine/drive_c/Program Files (x86)/Steam/steamapps/common/Megabonk": "/h/wine",
		"/h/Bottles/Steam/drive_c/games/Megabonk":                             "/h/Bottles/Steam",
		"/Volumes/Games/SteamLibrary/steamapps/common/Megabonk":               "",
	}
	for gameDir, want := range cases {
		if got := PrefixOfGameDir(gameDir); got != want {
			t.Errorf("PrefixOfGameDir(%q) = %q, want %q", gameDir, got, want)
		}
	}
}
