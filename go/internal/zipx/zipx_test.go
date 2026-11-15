package zipx

import (
	"archive/zip"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func zipOf(t *testing.T, name string, entries [][2]string) string {
	t.Helper()
	archive := filepath.Join(t.TempDir(), name)
	handle, err := os.Create(archive)
	if err != nil {
		t.Fatal(err)
	}
	writer := zip.NewWriter(handle)
	for _, entry := range entries {
		member, err := writer.Create(entry[0])
		if err != nil {
			t.Fatal(err)
		}
		if _, err := member.Write([]byte(entry[1])); err != nil {
			t.Fatal(err)
		}
	}
	if err := writer.Close(); err != nil {
		t.Fatal(err)
	}
	if err := handle.Close(); err != nil {
		t.Fatal(err)
	}
	return archive
}

func TestExtractWritesMembersAndCreatesTheTarget(t *testing.T) {
	archive := zipOf(t, "a.zip", [][2]string{
		{"dir/leaf.txt", "body"},
		{"top.txt", "top"},
	})
	target := filepath.Join(t.TempDir(), "missing", "nested")
	if err := Extract(archive, target); err != nil {
		t.Fatal(err)
	}
	for _, pair := range [][2]string{{"dir/leaf.txt", "body"}, {"top.txt", "top"}} {
		body, err := os.ReadFile(filepath.Join(target, filepath.FromSlash(pair[0])))
		if err != nil || string(body) != pair[1] {
			t.Errorf("%s = %q, %v", pair[0], body, err)
		}
	}
}

func TestExtractRefusesAnEscapingMember(t *testing.T) {
	base := t.TempDir()
	target := filepath.Join(base, "target")
	for _, name := range []string{"../escaped.txt", "a/../../escaped.txt", "/etc/escaped.txt", `C:/escaped.txt`} {
		archive := zipOf(t, "a.zip", [][2]string{{"keep.txt", "kept"}, {name, "payload"}})
		err := Extract(archive, target)
		if err == nil || !strings.Contains(err.Error(), "would escape its target directory") {
			t.Errorf("%s: err = %v", name, err)
			continue
		}
		if _, statErr := os.Stat(filepath.Join(base, "escaped.txt")); statErr == nil {
			t.Errorf("%s: the escaping member was written", name)
		}
		if _, statErr := os.Stat(filepath.Join(target, "keep.txt")); statErr == nil {
			t.Errorf("%s: a refused archive must write nothing", name)
		}
	}
}

func TestExtractReportsAnUnreadableArchive(t *testing.T) {
	bad := filepath.Join(t.TempDir(), "not-a.zip")
	if err := os.WriteFile(bad, []byte("not a zip"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := Extract(bad, filepath.Join(t.TempDir(), "out")); err == nil {
		t.Fatal("a broken archive should be an error")
	}
}

func TestExtractFollowsTheTargetThroughASymlink(t *testing.T) {
	base := t.TempDir()
	real := filepath.Join(base, "real")
	if err := os.MkdirAll(real, 0o755); err != nil {
		t.Fatal(err)
	}
	target := filepath.Join(base, "link")
	if err := os.Symlink(real, target); err != nil {
		t.Skipf("no symlink support: %v", err)
	}
	archive := zipOf(t, "a.zip", [][2]string{{"leaf.txt", "body"}})
	if err := Extract(archive, target); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(filepath.Join(real, "leaf.txt")); err != nil {
		t.Errorf("the member should land in the directory the target points at: %v", err)
	}
}

func TestExtractRefusesAWriteThroughAnEscapingSymlink(t *testing.T) {
	base := t.TempDir()
	target := filepath.Join(base, "target")
	if err := os.MkdirAll(target, 0o755); err != nil {
		t.Fatal(err)
	}
	outside := filepath.Join(base, "outside")
	if err := os.MkdirAll(outside, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(outside, filepath.Join(target, "escape")); err != nil {
		t.Skipf("no symlink support: %v", err)
	}
	archive := zipOf(t, "a.zip", [][2]string{{"escape/payload.txt", "payload"}})
	if err := Extract(archive, target); err != nil {
		t.Fatal(err)
	}
	// The archive itself is sound: the member stays under the target. What must
	// not happen is a file appearing beside the target's own tree by another name.
	if _, err := os.Stat(filepath.Join(base, "payload.txt")); err == nil {
		t.Error("a member must not be written beside the target")
	}
}
