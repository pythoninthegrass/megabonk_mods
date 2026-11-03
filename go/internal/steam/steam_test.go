package steam

import (
	"os"
	"path/filepath"
	"reflect"
	"strconv"
	"strings"
	"testing"
	"time"

	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ppath"
)

func mustMkdirAll(t *testing.T, path string) {
	t.Helper()
	if err := os.MkdirAll(path, 0o755); err != nil {
		t.Fatal(err)
	}
}

func mustWrite(t *testing.T, path, text string) {
	t.Helper()
	mustMkdirAll(t, filepath.Dir(path))
	if err := os.WriteFile(path, []byte(text), 0o644); err != nil {
		t.Fatal(err)
	}
}

func makeClient(t *testing.T, root string, libraryPaths []string) string {
	t.Helper()
	mustMkdirAll(t, filepath.Join(root, "steamapps"))
	mustMkdirAll(t, filepath.Join(root, "config"))
	var body strings.Builder
	for index, path := range libraryPaths {
		body.WriteString("\t\"" + strconv.Itoa(index) + "\"\n\t{\n\t\t\"path\"\t\t\"" + filepath.ToSlash(path) + "\"\n\t}\n")
	}
	mustWrite(t, filepath.Join(root, "steamapps", "libraryfolders.vdf"), "\"libraryfolders\"\n{\n"+body.String()+"}\n")
	return root
}

func makeLibrary(t *testing.T, root string, withGame bool) string {
	t.Helper()
	mustMkdirAll(t, filepath.Join(root, "steamapps", "common"))
	if withGame {
		mustMkdirAll(t, filepath.Join(root, "steamapps", "common", GameName, DataDir))
	}
	return root
}

func slash(path string) string { return filepath.ToSlash(path) }

func grantedText(candidate Candidate) string {
	if candidate.Granted == nil {
		return "nil"
	}
	if *candidate.Granted {
		return "true"
	}
	return "false"
}

func TestClientRootsFindsNativeSteam(t *testing.T) {
	home := filepath.Join(t.TempDir(), "home")
	root := makeClient(t, filepath.Join(home, ".local", "share", "Steam"), nil)
	clients := ClientRoots(home, "", nil)
	if len(clients) != 1 || clients[0].Kind != "native" || clients[0].Root != slash(root) {
		t.Fatalf("clients = %+v", clients)
	}
}

func TestClientRootsDedupesSymlinkedSteamDirs(t *testing.T) {
	home := filepath.Join(t.TempDir(), "home")
	real := makeClient(t, filepath.Join(home, ".local", "share", "Steam"), nil)
	link := filepath.Join(home, ".steam", "steam")
	mustMkdirAll(t, filepath.Dir(link))
	if err := os.Symlink(real, link); err != nil {
		t.Skipf("symlinks unavailable: %v", err)
	}
	clients := ClientRoots(home, "", nil)
	matches := 0
	for _, client := range clients {
		if resolve(client.Root) == resolve(real) {
			matches++
		}
	}
	if matches != 1 {
		t.Errorf("the symlinked root was counted %d times: %+v", matches, clients)
	}
}

func TestClientRootsIgnoresADirectoryThatIsNotASteamRoot(t *testing.T) {
	home := filepath.Join(t.TempDir(), "home")
	mustMkdirAll(t, filepath.Join(home, ".local", "share", "Steam"))
	if clients := ClientRoots(home, "", nil); len(clients) != 0 {
		t.Errorf("clients = %+v", clients)
	}
}

func TestClientRootsFindsFlatpakSteam(t *testing.T) {
	home := filepath.Join(t.TempDir(), "home")
	root := makeClient(t, filepath.Join(home, ".var", "app", FlatpakID, ".local", "share", "Steam"), nil)
	clients := ClientRoots(home, "", nil)
	var kinds []string
	for _, client := range clients {
		kinds = append(kinds, client.Kind)
	}
	if !reflect.DeepEqual(kinds, []string{"flatpak"}) {
		t.Errorf("kinds = %v", kinds)
	}
	if clients[0].Root != slash(root) {
		t.Errorf("root = %q", clients[0].Root)
	}
}

func TestClientRootsHonoursXDGDataHome(t *testing.T) {
	home := filepath.Join(t.TempDir(), "home")
	root := makeClient(t, filepath.Join(home, "games", "Steam"), nil)
	clients := ClientRoots(home, filepath.Join(home, "games"), nil)
	found := false
	for _, client := range clients {
		if client.Root == slash(root) {
			found = true
		}
	}
	if !found {
		t.Errorf("the configured data home was ignored: %+v", clients)
	}
}

func TestClientRootsAcceptsAGrantedPathAsTheFlatpakRoot(t *testing.T) {
	home := filepath.Join(t.TempDir(), "home")
	mustMkdirAll(t, home)
	relocated := makeClient(t, filepath.Join(t.TempDir(), "media", "steam"), nil)
	if clients := ClientRoots(home, "", nil); len(clients) != 0 {
		t.Fatalf("without a grant there is no client: %+v", clients)
	}
	clients := ClientRoots(home, "", []string{relocated})
	if len(clients) != 1 || clients[0].Kind != "flatpak" || clients[0].Root != slash(relocated) {
		t.Errorf("clients = %+v", clients)
	}
}

func TestClientRootsKeepsNativeFirstAndDoesNotRepeatAGrantedRoot(t *testing.T) {
	home := filepath.Join(t.TempDir(), "home")
	native := makeClient(t, filepath.Join(home, ".local", "share", "Steam"), nil)
	granted := makeClient(t, filepath.Join(t.TempDir(), "media", "steam"), nil)
	clients := ClientRoots(home, "", []string{granted, native})
	want := []Client{{Kind: "native", Root: slash(native)}, {Kind: "flatpak", Root: slash(granted)}}
	if !reflect.DeepEqual(clients, want) {
		t.Errorf("clients = %+v, want %+v", clients, want)
	}
}

func TestFlatpakOverridePathsReadsGrantedFilesystems(t *testing.T) {
	text := "[Context]\nfilesystems=/media/steam;\nfilesystems=!/secret;/data;\n"
	got := FlatpakOverridePaths(text, "/home/user")
	if !reflect.DeepEqual(got, []string{"/media/steam", "/data"}) {
		t.Errorf("paths = %v", got)
	}
}

func TestFlatpakOverridePathsSkipsSpecialTokensAndResolvesHomeRelative(t *testing.T) {
	text := "[Context]\nfilesystems=host;xdg-config;~/games;relative/dir;\n"
	got := FlatpakOverridePaths(text, "/home/user")
	if !reflect.DeepEqual(got, []string{"/home/user/games", "/home/user/relative/dir"}) {
		t.Errorf("paths = %v", got)
	}
}

func TestFlatpakOverridePathsIgnoresOtherSectionsAndKeys(t *testing.T) {
	text := "[Application]\nname=com.valvesoftware.Steam;\n[Context]\nsession-tell-filesystems=true;\nfilesystems=/ok;\n[Environment]\nfilesystems=/nope;\n"
	if got := FlatpakOverridePaths(text, "/home/user"); !reflect.DeepEqual(got, []string{"/ok"}) {
		t.Errorf("paths = %v", got)
	}
}

func TestLibraryFoldersReadsEveryClientLibrary(t *testing.T) {
	root := t.TempDir()
	client := makeClient(t, filepath.Join(root, "steam"), []string{filepath.Join(root, "lib1"), filepath.Join(root, "lib2")})
	libraries := LibraryFolders(Client{Kind: "native", Root: slash(client)})
	if !reflect.DeepEqual(libraries, []string{slash(filepath.Join(root, "lib1")), slash(filepath.Join(root, "lib2"))}) {
		t.Fatalf("folders = %v", libraries)
	}
	roots := LibraryRoots([]Client{{Kind: "native", Root: slash(client)}}, nil, nil, nil, false)
	if len(roots) != 2 || roots[0].Source != "client" || roots[1].Source != "client" {
		t.Errorf("roots = %+v", roots)
	}
}

func TestLibraryRootsMarksAClientLibraryTheFlatpakIsGranted(t *testing.T) {
	root := t.TempDir()
	library := filepath.Join(root, "media", "steam")
	client := makeClient(t, filepath.Join(root, "steam"), []string{library})
	mustMkdirAll(t, filepath.Join(library, "steamapps"))
	roots := LibraryRoots([]Client{{Kind: "flatpak", Root: slash(client)}}, []string{library}, nil, nil, false)
	if len(roots) != 1 || roots[0].Path != slash(library) || roots[0].Source != "client" ||
		roots[0].Granted == nil || !*roots[0].Granted {
		t.Errorf("roots = %+v", roots)
	}
}

func TestLibraryRootsSkipsStaleLibrariesThatAreGone(t *testing.T) {
	root := t.TempDir()
	client := makeClient(t, filepath.Join(root, "steam"), []string{
		filepath.Join(root, "lib1"),
		filepath.Join(root, "mnt", "games", "GameLibrary", "Steam"),
	})
	makeLibrary(t, filepath.Join(root, "lib1"), true)
	roots := LibraryRoots([]Client{{Kind: "native", Root: slash(client)}}, nil, nil, nil, false)
	if len(roots) != 1 || roots[0].Path != slash(filepath.Join(root, "lib1")) {
		t.Errorf("roots = %+v", roots)
	}
}

func TestLibraryRootsKeepsGrantedPathsWithoutAVdfEntry(t *testing.T) {
	root := t.TempDir()
	client := makeClient(t, filepath.Join(root, "steam"), nil)
	relocated := makeLibrary(t, filepath.Join(root, "media", "steam"), true)
	roots := LibraryRoots([]Client{{Kind: "native", Root: slash(client)}}, []string{relocated}, nil, nil, false)
	if len(roots) == 0 || roots[0].Path != slash(relocated) || roots[0].Source != "flatpak-override" {
		t.Errorf("roots = %+v", roots)
	}
}

func TestLibraryRootsFindsALibraryOnRemovableMedia(t *testing.T) {
	media := filepath.Join(t.TempDir(), "media")
	library := makeLibrary(t, filepath.Join(media, "sdcard", "SteamLibrary"), true)
	roots := LibraryRoots(nil, nil, nil, []string{media}, false)
	if len(roots) != 1 || roots[0].Path != slash(library) || roots[0].Source != "scan" {
		t.Errorf("roots = %+v", roots)
	}
}

func TestLibraryRootsDedupesAndPrefersTheFirstSource(t *testing.T) {
	root := t.TempDir()
	library := makeLibrary(t, filepath.Join(root, "lib1"), true)
	client := makeClient(t, filepath.Join(root, "steam"), []string{library})
	roots := LibraryRoots([]Client{{Kind: "native", Root: slash(client)}}, []string{library}, []string{library}, nil, false)
	if len(roots) != 1 || roots[0].Source != "client" {
		t.Errorf("roots = %+v", roots)
	}
}

func TestLibraryRootsHonoursAnExplicitPathAsALastResort(t *testing.T) {
	root := t.TempDir()
	missing := filepath.Join(root, "nope")
	roots := LibraryRoots(nil, nil, []string{missing}, nil, true)
	if len(roots) != 1 || roots[0].Path != slash(missing) {
		t.Errorf("roots = %+v", roots)
	}
	// A path whose parent is also gone reads as an unmounted drive unless the
	// caller asks for missing libraries too.
	gone := filepath.Join(root, "gone", "SteamLibrary")
	if roots := LibraryRoots(nil, nil, []string{gone}, nil, false); len(roots) != 0 {
		t.Errorf("a library with no parent should be refused: %+v", roots)
	}
	roots = LibraryRoots(nil, nil, []string{gone}, nil, true)
	if len(roots) != 1 || roots[0].Path != slash(gone) {
		t.Errorf("include_missing should keep it: %+v", roots)
	}
}

func TestLibraryCandidatesNamesAnUnmountedLibrary(t *testing.T) {
	root := t.TempDir()
	missing := filepath.Join(root, "mnt", "games", "SteamLibrary")
	client := makeClient(t, filepath.Join(root, "steam"), []string{missing})
	candidates := LibraryCandidates([]Client{{Kind: "native", Root: slash(client)}}, nil, nil, nil, false)
	if len(candidates) != 1 || candidates[0].Accepted {
		t.Fatalf("candidates = %+v", candidates)
	}
	if candidates[0].Reason != reasonUnmounted(slash(filepath.Join(root, "mnt", "games"))) {
		t.Errorf("reason = %q", candidates[0].Reason)
	}
	if !strings.Contains(candidates[0].Reason, "drive not attached") ||
		!strings.Contains(candidates[0].Reason, "mnt/games") {
		t.Errorf("reason should name the missing parent: %q", candidates[0].Reason)
	}
}

func TestLibraryCandidatesFlagsAFlatpakLibraryTheSandboxCannotRead(t *testing.T) {
	root := t.TempDir()
	library := filepath.Join(root, "media", "steam")
	mustMkdirAll(t, filepath.Join(library, "steamapps"))
	client := makeClient(t, filepath.Join(root, "steam"), []string{library})
	candidates := LibraryCandidates([]Client{{Kind: "flatpak", Root: slash(client)}}, nil, nil, nil, false)
	if len(candidates) != 1 || !candidates[0].Accepted || grantedText(candidates[0]) != "false" {
		t.Errorf("candidates = %+v (%s)", candidates, grantedText(candidates[0]))
	}
}

func TestLibraryCandidatesMarksAGrantedLibraryGranted(t *testing.T) {
	root := t.TempDir()
	library := filepath.Join(root, "media", "steam")
	mustMkdirAll(t, filepath.Join(library, "steamapps"))
	client := makeClient(t, filepath.Join(root, "steam"), []string{library})
	candidates := LibraryCandidates([]Client{{Kind: "flatpak", Root: slash(client)}}, []string{library}, nil, nil, false)
	var accepted, rejected []Candidate
	for _, candidate := range candidates {
		if candidate.Accepted {
			accepted = append(accepted, candidate)
		} else {
			rejected = append(rejected, candidate)
		}
	}
	if len(accepted) != 1 || accepted[0].Path != slash(library) || grantedText(accepted[0]) != "true" {
		t.Errorf("accepted = %+v (%s)", accepted, grantedText(accepted[0]))
	}
	if len(rejected) != 1 || rejected[0].Reason != ReasonDuplicate {
		t.Errorf("rejected = %+v", rejected)
	}
}

func TestLibraryCandidatesRecordsDuplicatesAgainstTheFirstSource(t *testing.T) {
	root := t.TempDir()
	library := makeLibrary(t, filepath.Join(root, "lib1"), true)
	client := makeClient(t, filepath.Join(root, "steam"), []string{library})
	candidates := LibraryCandidates([]Client{{Kind: "native", Root: slash(client)}}, []string{library}, nil, nil, false)
	if len(candidates) != 2 {
		t.Fatalf("candidates = %+v", candidates)
	}
	if !candidates[0].Accepted || candidates[0].Kind != "client" {
		t.Errorf("the client source should win: %+v", candidates[0])
	}
	if candidates[1].Accepted || candidates[1].Reason != ReasonDuplicate {
		t.Errorf("the repeat should be refused: %+v", candidates[1])
	}
}

func TestClientCandidatesNamesEveryDefaultLocation(t *testing.T) {
	home := filepath.Join(t.TempDir(), "home")
	mustMkdirAll(t, home)
	candidates := ClientCandidates(home, "", nil)
	wanted := []string{
		ppath.Join(home, ".local", "share", "Steam"),
		ppath.Join(home, ".steam", "root"),
		ppath.Join(home, ".steam", "steam"),
		ppath.Join(home, ".var", "app", FlatpakID, ".local", "share", "Steam"),
		ppath.Join(home, ".var", "app", FlatpakID, "data", "Steam"),
	}
	byPath := map[string]Candidate{}
	for _, candidate := range candidates {
		byPath[candidate.Path] = candidate
	}
	for _, path := range wanted {
		candidate, found := byPath[path]
		if !found {
			t.Errorf("%s is not among the candidates", path)
			continue
		}
		if candidate.Accepted || candidate.Reason != ReasonMissing {
			t.Errorf("%s = %+v", path, candidate)
		}
	}
}

func TestClientCandidatesNamesWhyACandidateIsNotASteamRoot(t *testing.T) {
	home := filepath.Join(t.TempDir(), "home")
	mustMkdirAll(t, filepath.Join(home, ".local", "share", "Steam"))
	for _, candidate := range ClientCandidates(home, "", nil) {
		if candidate.Path != ppath.Join(home, ".local", "share", "Steam") {
			continue
		}
		if candidate.Accepted || candidate.Reason != ReasonNoSteamapps {
			t.Errorf("candidate = %+v", candidate)
		}
		return
	}
	t.Error("the default location is missing from the candidates")
}

func TestClientCandidatesAcceptsAGrantedRootAndFlagsARepeat(t *testing.T) {
	home := filepath.Join(t.TempDir(), "home")
	mustMkdirAll(t, home)
	granted := makeClient(t, filepath.Join(t.TempDir(), "media", "steam"), nil)
	candidates := ClientCandidates(home, "", []string{granted, granted})
	var accepted, repeats []Candidate
	for _, candidate := range candidates {
		if candidate.Accepted {
			accepted = append(accepted, candidate)
		} else if candidate.Path == slash(granted) {
			repeats = append(repeats, candidate)
		}
	}
	if len(accepted) != 1 || accepted[0].Path != slash(granted) || accepted[0].Kind != "flatpak" {
		t.Errorf("accepted = %+v", accepted)
	}
	if len(repeats) == 0 || repeats[0].Reason != ReasonDuplicate {
		t.Errorf("repeats = %+v", repeats)
	}
}

func TestProbeFlatpakPrefersThePersistedFile(t *testing.T) {
	root := t.TempDir()
	home := filepath.Join(root, "home")
	granted := filepath.Join(root, "data", "steam")
	override := filepath.Join(home, ".var", "app", FlatpakID, "configuration", "flatpak", "local-overrides", FlatpakID)
	mustWrite(t, override, "[Context]\nfilesystems="+slash(granted)+";\n")
	probe := ProbeFlatpak(home)
	if !reflect.DeepEqual(probe.Paths, []string{slash(granted)}) || probe.Source != "file" || !probe.CLIFound {
		t.Errorf("probe = %+v", probe)
	}
	if paths := FlatpakGrantedPaths(home); !reflect.DeepEqual(paths, []string{slash(granted)}) {
		t.Errorf("granted = %v", paths)
	}
}

func TestProbeFlatpakReportsAMissingCLI(t *testing.T) {
	home := filepath.Join(t.TempDir(), "home")
	mustMkdirAll(t, home)
	restore := CommandRunner
	CommandRunner = func(argv []string, timeout time.Duration) (int, string, error) {
		return 0, "", &os.PathError{Op: "exec", Path: argv[0], Err: os.ErrNotExist}
	}
	defer func() { CommandRunner = restore }()

	probe := ProbeFlatpak(home)
	if len(probe.Paths) != 0 || probe.Source != "none" || probe.CLIFound {
		t.Errorf("probe = %+v", probe)
	}
}

func TestProbeFlatpakUsesTheCLIWhenNoFileExists(t *testing.T) {
	home := filepath.Join(t.TempDir(), "home")
	mustMkdirAll(t, home)
	restore := CommandRunner
	CommandRunner = func(argv []string, timeout time.Duration) (int, string, error) {
		if argv[1] != "override" || argv[3] != FlatpakID {
			t.Errorf("argv = %v", argv)
		}
		return 0, "[Context]\nfilesystems=/media/steam;\n", nil
	}
	defer func() { CommandRunner = restore }()

	probe := ProbeFlatpak(home)
	if !reflect.DeepEqual(probe.Paths, []string{"/media/steam"}) || probe.Source != "cli" || !probe.CLIFound {
		t.Errorf("probe = %+v", probe)
	}
}

func TestFindGameDirLocatesTheInstall(t *testing.T) {
	root := t.TempDir()
	library := makeLibrary(t, filepath.Join(root, "lib"), true)
	got := FindGameDir([]Library{{Path: slash(library), Source: "client"}}, "")
	if got != ppath.Join(slash(library), "steamapps", "common", GameName) {
		t.Errorf("game dir = %q", got)
	}
}

func TestFindGameDirPrefersAnEarlierRoot(t *testing.T) {
	root := t.TempDir()
	first := makeLibrary(t, filepath.Join(root, "lib1"), true)
	second := makeLibrary(t, filepath.Join(root, "lib2"), true)
	got := FindGameDir([]Library{{Path: slash(first)}, {Path: slash(second), Source: "scan"}}, "")
	if got != ppath.Join(slash(first), "steamapps", "common", GameName) {
		t.Errorf("game dir = %q", got)
	}
}

func TestFindGameDirEmptyWhenNoLibraryHasTheGame(t *testing.T) {
	root := t.TempDir()
	library := makeLibrary(t, filepath.Join(root, "lib"), false)
	if got := FindGameDir([]Library{{Path: slash(library)}}, ""); got != "" {
		t.Errorf("game dir = %q", got)
	}
}

func TestFindGameDirUsesTheAppManifest(t *testing.T) {
	root := t.TempDir()
	library := makeLibrary(t, filepath.Join(root, "lib"), false)
	game := filepath.Join(library, "steamapps", "common", "Megabonk-Renamed")
	mustMkdirAll(t, filepath.Join(game, DataDir))
	mustWrite(t, filepath.Join(library, "steamapps", "appmanifest_"+AppID+".acf"),
		"\"appmanifest_"+AppID+"\"\n{\n\t\"appid\"\t\t\"3405340\"\n\t\"installdir\"\t\t\"Megabonk-Renamed\"\n}\n")
	got := FindGameDir([]Library{{Path: slash(library)}}, "")
	if got != ppath.Join(slash(library), "steamapps", "common", "Megabonk-Renamed") {
		t.Errorf("the manifest should name the directory: %q", got)
	}
}

func TestPrefixRootFollowsTheCompatdataLayout(t *testing.T) {
	library := filepath.Join(t.TempDir(), "lib")
	got := PrefixRoot(library, AppID)
	want := ppath.Join(slash(library), "steamapps", "compatdata", AppID, "pfx")
	if got != want {
		t.Errorf("prefix = %q, want %q", got, want)
	}
}

func TestPrefixForGameDir(t *testing.T) {
	root := t.TempDir()
	library := makeLibrary(t, filepath.Join(root, "lib"), true)
	game := filepath.Join(library, "steamapps", "common", GameName)
	prefix := filepath.Join(library, "steamapps", "compatdata", AppID, "pfx")
	mustMkdirAll(t, prefix)
	if got := PrefixForGameDir(game, ""); got != slash(prefix) {
		t.Errorf("prefix = %q, want %q", got, slash(prefix))
	}
	if got := CompatdataRoot(game, ""); got != slash(filepath.Join(library, "steamapps", "compatdata", AppID)) {
		t.Errorf("compatdata = %q", got)
	}

	orphan := makeLibrary(t, filepath.Join(root, "orphan"), true)
	if got := PrefixForGameDir(filepath.Join(orphan, "steamapps", "common", GameName), ""); got != "" {
		t.Errorf("a library with no compatdata has no prefix, got %q", got)
	}
	if got := PrefixForGameDir(filepath.Join(root, "elsewhere", "Megabonk"), ""); got != "" {
		t.Errorf("a path outside a common directory has no prefix, got %q", got)
	}
}

func TestSteamRunningDetectsTheProcess(t *testing.T) {
	restore := CommandRunner
	defer func() { CommandRunner = restore }()
	cases := []struct {
		stdout string
		want   bool
	}{
		{"123 /home/user/.local/share/Steam/ubuntu12_32/steam\n", true},
		{"1 python3 x.py\n", false},
		{"9 steamwebhelper --type=broker\n", true},
	}
	for _, item := range cases {
		CommandRunner = func(argv []string, timeout time.Duration) (int, string, error) { return 0, item.stdout, nil }
		if got := SteamRunning(); got != item.want {
			t.Errorf("SteamRunning(%q) = %v, want %v", item.stdout, got, item.want)
		}
	}
	CommandRunner = func(argv []string, timeout time.Duration) (int, string, error) {
		return 1, "", &os.PathError{Op: "exec", Path: "ps", Err: os.ErrNotExist}
	}
	if SteamRunning() {
		t.Error("with no ps there is no Steam")
	}
}

func TestLocalconfigIsNilWhenUnreadable(t *testing.T) {
	root := t.TempDir()
	client := makeClient(t, filepath.Join(root, "steam"), nil)
	if Localconfig(Client{Root: slash(client)}) != nil {
		t.Error("a client with no config has no localconfig")
	}
	mustWrite(t, filepath.Join(client, "config", "localconfig.vdf"), "\"unbalanced\n{\n")
	if Localconfig(Client{Root: slash(client)}) != nil {
		t.Error("a malformed localconfig should read as absent")
	}
	mustWrite(t, filepath.Join(client, "config", "localconfig.vdf"),
		"\"user\"\n{\n\t\"appidinfo\"\n\t{\n\t\t\"3405340\"\n\t\t{\n\t\t\t\"launch options\"\t\t\"x\"\n\t\t}\n\t}\n}\n")
	if Localconfig(Client{Root: slash(client)}) == nil {
		t.Error("a readable localconfig should load")
	}
}

func TestScanForLibrariesSkipsHiddenAndStopsAtALibrary(t *testing.T) {
	media := filepath.Join(t.TempDir(), "media")
	library := makeLibrary(t, filepath.Join(media, "sdcard", "SteamLibrary"), false)
	mustMkdirAll(t, filepath.Join(media, ".hidden", "steamapps", "common"))
	mustMkdirAll(t, filepath.Join(media, "sdcard", "deep", "deeper", "steamapps", "common"))
	got := ScanForLibraries(media, ScanDepth)
	if !reflect.DeepEqual(got, []string{slash(library)}) {
		t.Errorf("scan = %v, want [%s]", got, slash(library))
	}
	if got := ScanForLibraries(filepath.Join(t.TempDir(), "nope"), ScanDepth); len(got) != 0 {
		t.Errorf("a missing mount should scan to nothing: %v", got)
	}
}
