package ppath

import (
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func TestNormalizeMatchesStrPurePosixPath(t *testing.T) {
	cases := map[string]string{
		"":           ".",
		".":          ".",
		"/":          "/",
		"//":         "//",
		"///":        "/",
		"a/./b":      "a/b",
		"a//b":       "a/b",
		"a/b/":       "a/b",
		"/a/":        "/a",
		"a/b/../c":   "a/b/../c",
		"~/x":        "~/x",
		"~":          "~",
		"/a/b":       "/a/b",
		"//a/b":      "//a/b",
		"./a/./b/./": "a/b",
	}
	for in, want := range cases {
		if got := Normalize(in); got != want {
			t.Errorf("Normalize(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestJoinMatchesPathSlashOperator(t *testing.T) {
	cases := []struct {
		base  string
		parts []string
		want  string
	}{
		{"a", []string{"b"}, "a/b"},
		{"", []string{"x"}, "x"},
		{".", []string{"x"}, "x"},
		{"a", []string{"/b"}, "/b"},
		{"a", []string{""}, "a"},
		{"/", []string{"x"}, "/x"},
		{"//", []string{"x"}, "//x"},
		{"a", []string{"b", "c"}, "a/b/c"},
		{"a/", []string{"b"}, "a/b"},
		{"..", []string{"x"}, "../x"},
		{"a", []string{"../b"}, "a/../b"},
		{"UserData", []string{"LevelPacks", "thps"}, "UserData/LevelPacks/thps"},
	}
	for _, item := range cases {
		if got := Join(item.base, item.parts...); got != item.want {
			t.Errorf("Join(%q, %v) = %q, want %q", item.base, item.parts, got, item.want)
		}
	}
}

func TestParentNameExtParents(t *testing.T) {
	cases := []struct {
		path    string
		name    string
		parent  string
		ext     string
		parents []string
	}{
		{"a", "a", ".", "", []string{"."}},
		{"a/b", "b", "a", "", []string{"a", "."}},
		{"/a/b", "b", "/a", "", []string{"/a", "/"}},
		{"/", "", "/", "", nil},
		{".", "", ".", "", nil},
		{"..", "..", ".", "", []string{"."}},
		{"/a", "a", "/", "", []string{"/"}},
		{"//a/b", "b", "//a", "", []string{"//a", "//"}},
		{"a/b/c", "c", "a/b", "", []string{"a/b", "a", "."}},
		{"x/y.tar.gz", "y.tar.gz", "x", ".gz", []string{"x", "."}},
		{"x/.hidden", ".hidden", "x", "", []string{"x", "."}},
		{"x/trailing.", "trailing.", "x", "", []string{"x", "."}},
		{"Megabonk.x86_64", "Megabonk.x86_64", ".", ".x86_64", []string{"."}},
	}
	for _, item := range cases {
		if got := Name(item.path); got != item.name {
			t.Errorf("Name(%q) = %q, want %q", item.path, got, item.name)
		}
		if got := Parent(item.path); got != item.parent {
			t.Errorf("Parent(%q) = %q, want %q", item.path, got, item.parent)
		}
		if got := Ext(item.path); got != item.ext {
			t.Errorf("Ext(%q) = %q, want %q", item.path, got, item.ext)
		}
		if got := Parents(item.path); !reflect.DeepEqual(got, item.parents) && !(len(got) == 0 && len(item.parents) == 0) {
			t.Errorf("Parents(%q) = %v, want %v", item.path, got, item.parents)
		}
	}
}

func TestStatHelpersSwallowPermissionErrors(t *testing.T) {
	dir := t.TempDir()
	hidden := filepath.Join(dir, "locked")
	if err := os.Mkdir(hidden, 0o700); err != nil {
		t.Fatal(err)
	}
	if !IsDir(hidden) || IsFile(hidden) || !Exists(hidden) {
		t.Fatalf("a directory should be a directory: is_dir=%v is_file=%v exists=%v", IsDir(hidden), IsFile(hidden), Exists(hidden))
	}
	missing := filepath.Join(dir, "gone")
	if IsDir(missing) || IsFile(missing) || Exists(missing) {
		t.Error("nothing should report as present")
	}
	file := filepath.Join(dir, "f.txt")
	if err := os.WriteFile(file, []byte("x"), 0o644); err != nil {
		t.Fatal(err)
	}
	if !IsFile(file) || IsDir(file) || !Exists(file) {
		t.Error("a file should be a file")
	}
	if os.Geteuid() == 0 {
		t.Skip("unreadable-directory behaviour needs a non-root user")
	}
	secret := filepath.Join(dir, "secret")
	if err := os.Mkdir(secret, 0o000); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chmod(secret, 0o700) })
	blocked := filepath.Join(secret, "inside")
	if IsDir(blocked) || IsFile(blocked) || Exists(blocked) {
		t.Error("an EACCES probe must read as absent, not raise")
	}
}

func TestReadTextReportsUndecodableFiles(t *testing.T) {
	dir := t.TempDir()
	good := filepath.Join(dir, "good.txt")
	if err := os.WriteFile(good, []byte("café ☃"), 0o644); err != nil {
		t.Fatal(err)
	}
	text, err := ReadText(good)
	if err != nil || text != "café ☃" {
		t.Fatalf("ReadText = %q, %v", text, err)
	}

	cases := []struct {
		name string
		raw  []byte
	}{
		{"invalid start byte", []byte{0xff}},
		{"later byte", []byte("a\xffb")},
		{"truncated sequence", []byte{0xe2, 0x98}},
		{"bad continuation", []byte{0xe2, 0x98, 'z'}},
		{"single lead byte", []byte{0xc3}},
		{"surrogate half", []byte{0xed, 0xa0, 0x80}},
	}
	for _, item := range cases {
		path := filepath.Join(dir, item.name+".bin")
		if err := os.WriteFile(path, item.raw, 0o644); err != nil {
			t.Fatal(err)
		}
		if _, err := ReadText(path); err == nil {
			t.Errorf("ReadText(%s) should fail", item.name)
		}
		replaced, err := ReadTextReplace(path)
		if err != nil {
			t.Errorf("ReadTextReplace(%s) = %v", item.name, err)
		}
		if !strings.Contains(replaced, string(rune(0xfffd))) {
			t.Errorf("ReadTextReplace(%s) = %q, want the replacement character", item.name, replaced)
		}
	}
}

func TestExpandUser(t *testing.T) {
	home, err := os.UserHomeDir()
	if err != nil || home == "" {
		t.Skip("no home directory for this user")
	}
	if got := ExpandUser("~"); got != home {
		t.Errorf("ExpandUser(~) = %q, want %q", got, home)
	}
	if got := ExpandUser("~/Steam"); got == "~/Steam" || !strings.HasSuffix(got, "/Steam") {
		t.Errorf("ExpandUser(~/Steam) = %q", got)
	}
	for _, plain := range []string{"/media/steam", "a/~/b", "."} {
		if got := ExpandUser(plain); got != Normalize(plain) {
			t.Errorf("ExpandUser(%q) = %q", plain, got)
		}
	}
}
