// Package ppath mirrors the slice of pathlib the Python installer relies on:
// slash-separated joins, the str(Path(...)) normalisation every message and
// record path carries, and parent/name accessors. Slashes are deliberate on
// every target so the install record and the byte-parity messages match the
// reference on all platforms.
package ppath

import (
	"os"
	"strings"
	"unicode/utf8"
)

// Normalize is str(PurePosixPath(p)): collapse repeated slashes, drop "."
// segments and any trailing slash, and render an empty path as ".".
func Normalize(p string) string {
	if p == "" {
		return "."
	}
	absolute := strings.HasPrefix(p, "/")
	doubled := strings.HasPrefix(p, "//") && !strings.HasPrefix(p, "///")
	var kept []string
	for _, part := range strings.Split(p, "/") {
		if part == "" || part == "." {
			continue
		}
		kept = append(kept, part)
	}
	joined := strings.Join(kept, "/")
	switch {
	case absolute && doubled:
		return "//" + joined
	case absolute:
		return "/" + joined
	case joined == "":
		return "."
	default:
		return joined
	}
}

// Join builds a path from segments; an absolute later segment wins, as in pathlib.
func Join(base string, parts ...string) string {
	result := base
	for _, part := range parts {
		if strings.HasPrefix(part, "/") {
			result = part
			continue
		}
		if result == "" || result == "." {
			result = part
			continue
		}
		result = strings.TrimSuffix(result, "/") + "/" + part
	}
	return Normalize(result)
}

// Parent is Path.parent; the parent of a single component is ".". The POSIX
// double-slash root keeps its spelling, as pathlib's does.
func Parent(p string) string {
	clean := Normalize(p)
	if clean == "/" || clean == "." || clean == "//" {
		return clean
	}
	if at := strings.LastIndex(clean, "/"); at > 1 || (at == 1 && !strings.HasPrefix(clean, "//")) {
		return clean[:at]
	}
	if strings.HasPrefix(clean, "//") {
		return "//"
	}
	if strings.HasPrefix(clean, "/") {
		return "/"
	}
	return "."
}

// Name is Path.name: the final component.
func Name(p string) string {
	clean := Normalize(p)
	if clean == "/" || clean == "." {
		return ""
	}
	if at := strings.LastIndex(clean, "/"); at >= 0 {
		return clean[at+1:]
	}
	return clean
}

// Ext is Path.suffix: the last dot of the name, or "".
func Ext(p string) string {
	name := Name(p)
	if at := strings.LastIndex(name, "."); at > 0 && at < len(name)-1 {
		return name[at:]
	}
	return ""
}

// Parents is Path.parents: every ancestor, nearest first, down to "/" or ".".
func Parents(p string) []string {
	var parents []string
	current := Normalize(p)
	for {
		parent := Parent(current)
		if parent == current {
			return parents
		}
		parents = append(parents, parent)
		current = parent
	}
}

// IsDir is Path.is_dir with the PermissionError pathlib re-raises swallowed.
func IsDir(p string) bool {
	info, err := os.Stat(p)
	return err == nil && info.IsDir()
}

// IsFile is Path.is_file with permission errors swallowed.
func IsFile(p string) bool {
	info, err := os.Stat(p)
	return err == nil && !info.IsDir()
}

// Exists is Path.exists with permission errors swallowed.
func Exists(p string) bool {
	_, err := os.Stat(p)
	return err == nil
}

// DecodeError says a file was read but its bytes are not UTF-8 text.
type DecodeError struct{ message string }

func (e *DecodeError) Error() string { return e.message }

// ReadText is Path.read_text(encoding="utf-8"): the bytes must be valid UTF-8.
func ReadText(p string) (string, error) {
	raw, err := os.ReadFile(p)
	if err != nil {
		return "", err
	}
	if !utf8.Valid(raw) {
		return "", &DecodeError{message: "not valid UTF-8 text"}
	}
	return string(raw), nil
}

// ReadTextReplace is Path.read_text(encoding="utf-8", errors="replace"):
// undecodable bytes become the replacement character instead of failing.
func ReadTextReplace(p string) (string, error) {
	raw, err := os.ReadFile(p)
	if err != nil {
		return "", err
	}
	return strings.ToValidUTF8(string(raw), string(rune(0xfffd))), nil
}

// ExpandUser is Path.expanduser: only a leading ~ or ~/ expands.
func ExpandUser(p string) string {
	if p != "~" && !strings.HasPrefix(p, "~/") {
		return p
	}
	home, err := os.UserHomeDir()
	if err != nil || home == "" {
		return p
	}
	if p == "~" {
		return home
	}
	return Join(home, p[2:])
}
