// Package zipx unpacks an archive into one directory. Every member name is
// checked against the destination before anything is written, so an archive that
// climbs out of its target fails as an error rather than as files in the wrong
// place.
package zipx

import (
	"archive/zip"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

// Error is an archive that cannot be unpacked where it was asked to go.
type Error struct{ message string }

func (e *Error) Error() string { return e.message }

func fail(format string, args ...any) error {
	return &Error{message: fmt.Sprintf(format, args...)}
}

// Extract unpacks archive into target, creating target when it is missing. The
// whole archive is checked first, so a refusing run writes nothing.
func Extract(archive, target string) error {
	if err := os.MkdirAll(target, 0o755); err != nil {
		return err
	}
	root, err := filepath.EvalSymlinks(target)
	if err != nil {
		root = target
	}
	reader, err := zip.OpenReader(archive)
	if err != nil {
		return fail("%s: %s", filepath.Base(archive), err.Error())
	}
	defer reader.Close()
	name := filepath.Base(archive)
	for _, member := range reader.File {
		if err := checkInside(member.Name, root, name); err != nil {
			return err
		}
	}
	for _, member := range reader.File {
		if err := ExtractMember(member, root, filepath.ToSlash(member.Name), 0); err != nil {
			return fail("%s: %s", name, err.Error())
		}
	}
	return nil
}

// ExtractMember writes one already-vetted member at relative under root, keeping
// its mode. A positive limit caps how much is copied, so a member whose declared
// size lies about it cannot fill the disk.
func ExtractMember(member *zip.File, root, relative string, limit int64) error {
	destination := filepath.Join(root, filepath.FromSlash(filepath.ToSlash(relative)))
	if member.FileInfo().IsDir() {
		return os.MkdirAll(destination, 0o755)
	}
	if err := os.MkdirAll(filepath.Dir(destination), 0o755); err != nil {
		return err
	}
	source, err := member.Open()
	if err != nil {
		return err
	}
	defer source.Close()
	handle, err := os.OpenFile(destination, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, member.Mode().Perm())
	if err != nil {
		return err
	}
	var reader io.Reader = source
	if limit > 0 {
		reader = io.LimitReader(source, limit+1)
	}
	copied, err := io.Copy(handle, reader)
	if err != nil {
		handle.Close()
		return err
	}
	if limit > 0 && uint64(copied) != member.UncompressedSize64 {
		handle.Close()
		return fail("%s: %s is not the %d bytes its header declared",
			filepath.Base(root), relative, member.UncompressedSize64)
	}
	if err := handle.Close(); err != nil {
		return err
	}
	return os.Chmod(destination, member.Mode().Perm())
}

func checkInside(entry, root, archive string) error {
	slash := filepath.ToSlash(entry)
	if strings.HasPrefix(slash, "/") || driveLetter(slash) || strings.Contains(slash, "\\") {
		return escapeError(archive, entry)
	}
	clean := filepath.Clean(root)
	resolved := filepath.Clean(filepath.Join(clean, filepath.FromSlash(slash)))
	if resolved != clean && !strings.HasPrefix(resolved, clean+string(filepath.Separator)) {
		return escapeError(archive, entry)
	}
	return nil
}

func driveLetter(slash string) bool {
	if len(slash) < 2 || slash[1] != ':' {
		return false
	}
	return (slash[0] >= 'a' && slash[0] <= 'z') || (slash[0] >= 'A' && slash[0] <= 'Z')
}

func escapeError(archive, entry string) error {
	return &Error{message: archive + ": entry " + strconv.Quote(entry) + " would escape its target directory"}
}
