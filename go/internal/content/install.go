package content

import (
	"archive/zip"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"

	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ppath"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/zipx"
)

func fail(format string, args ...any) error {
	return fmt.Errorf(format, args...)
}

func quote(text string) string { return strconv.Quote(text) }

// LevelStem is a level file's name without the suffix the loaders append, the
// stem its sidecar images are named after (level_thumbnail_sidecar.cs).
func LevelStem(name string) string {
	stem := ppath.Name(name)
	for _, suffix := range LevelSuffixes {
		if len(stem) > len(suffix) && stem[len(stem)-len(suffix):] == suffix {
			if base := stem[:len(stem)-len(suffix)]; base != "" {
				return base
			}
		}
	}
	if dot := strings.LastIndex(stem, "."); dot > 1 {
		return stem[:dot]
	}
	return stem
}

// CoverFor is the cover image name that sits beside a level file.
func CoverFor(stem string) string { return stem + ".png" }

// BiomeFor is the biome icon name that sits beside a level file.
func BiomeFor(stem string) string { return stem + ".biome.png" }

// LevelResult is what one level install placed.
type LevelResult struct {
	Code     string
	Filename string
	Cover    string
	Biome    string
	Replaced bool
	Removed  map[string]bool
	Files    []string
}

// InstallLevelInput is one level's content: the level file and the optional
// cover and biome image that go beside it.
type InstallLevelInput struct {
	Slug  string
	Level string
	Cover string
	Biome string
}

type imagePlacement struct {
	source string
	// name is the file the image lands under: the slug's .png for a cover and
	// .biome.png for a biome icon, the only names the install writes.
	name string
}

// InstallLevel writes a level and its images into UserData/Levels under the slug
// name, creating the folders the game expects. An existing level file of that
// name is replaced and reported; sidecar images left from an earlier install of
// the same level, but absent from this one, are removed and recorded.
func InstallLevel(gameDir string, input InstallLevelInput) (*LevelResult, error) {
	if !ValidPackID(input.Slug) {
		return nil, fail("level name %s: use a lowercase id of a-z, 0-9, '.', '_' or '-'", quote(input.Slug))
	}
	if problems := ValidateLevelFile(input.Level); len(problems) > 0 {
		return nil, fail("%s", strings.Join(problems, "; "))
	}
	images := []imagePlacement{}
	if input.Cover != "" {
		images = append(images, imagePlacement{input.Cover, CoverFor(input.Slug)})
	}
	if input.Biome != "" {
		images = append(images, imagePlacement{input.Biome, BiomeFor(input.Slug)})
	}
	for _, image := range images {
		if !ppath.IsFile(image.source) {
			return nil, fail("%s: no such image", image.source)
		}
		size, err := fileSize(image.source)
		if err != nil {
			return nil, err
		}
		if size > MaxImageBytes {
			return nil, fail("%s: larger than the %dMB image limit", image.source, MaxImageBytes/megabyte)
		}
	}

	dir := LevelsPath(gameDir)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return nil, err
	}
	filename := input.Slug + primaryLevelSuffix
	target := ppath.Join(dir, filename)
	replaced := ppath.IsFile(target)
	if err := copyInto(input.Level, target); err != nil {
		return nil, err
	}

	result := &LevelResult{Code: input.Slug, Filename: filename, Replaced: replaced,
		Removed: map[string]bool{}, Files: []string{relativeToGame(gameDir, filename)}}
	for _, image := range images {
		if err := copyInto(image.source, ppath.Join(dir, image.name)); err != nil {
			return nil, err
		}
		relative := relativeToGame(gameDir, image.name)
		if image.name == CoverFor(input.Slug) {
			result.Cover = relative
		} else {
			result.Biome = relative
		}
		result.Files = append(result.Files, relative)
	}
	for _, name := range staleSidecars(dir, input.Slug, images) {
		if err := os.Remove(ppath.Join(dir, name)); err != nil {
			return nil, err
		}
		result.Removed[relativeToGame(gameDir, name)] = true
	}
	return result, nil
}

// staleSidecars are the images the loaders would pick up for this level that the
// current install does not carry, so a re-install cannot serve a stale cover.
func staleSidecars(dir, slug string, placed []imagePlacement) []string {
	wanted := map[string]bool{}
	for _, image := range placed {
		wanted[image.name] = true
	}
	var stale []string
	for _, name := range sidecarCandidates(slug) {
		if wanted[name] || !ppath.IsFile(ppath.Join(dir, name)) {
			continue
		}
		stale = append(stale, name)
	}
	sort.Strings(stale)
	return stale
}

func sidecarCandidates(slug string) []string {
	var names []string
	for _, suffix := range []string{"", ".biome"} {
		for _, ext := range []string{".png", ".jpg", ".jpeg"} {
			names = append(names, slug+suffix+ext)
		}
	}
	return names
}

// relativeToGame is a level folder file name as the record keeps it, relative to
// the game directory.
func relativeToGame(gameDir, name string) string {
	return relativeFrom(gameDir, ppath.Join(LevelsPath(gameDir), name))
}

// relativeFrom is a path under base in base-relative form.
func relativeFrom(base, path string) string {
	clean := ppath.Normalize(path)
	prefix := ppath.Normalize(base) + "/"
	if strings.HasPrefix(clean, prefix) {
		return clean[len(prefix):]
	}
	return clean
}

// PackResult is what one pack install placed.
type PackResult struct {
	ID      string
	Version string
	Dir     string
	Files   []string
}

// InstallPackFromZip unpacks a pack archive as UserData/LevelPacks/<id>/, the
// layout the pack loaders read. Members are checked before anything is written:
// no name may escape the pack folder, and the unpacked directory has to pass
// ValidatePackSource, so a broken pack never lands where the game would show it
// as a placeholder.
func InstallPackFromZip(gameDir, packID, version, archive string) (*PackResult, error) {
	if !ValidPackID(packID) {
		return nil, fail("pack id %s: use a lowercase id of a-z, 0-9, '.', '_' or '-'", quote(packID))
	}
	members, bundle, err := packMembers(archive, packID)
	if err != nil {
		return nil, err
	}
	defer bundle.Close()
	dest := PackDest(gameDir, packID)
	if err := preparePackDir(dest); err != nil {
		return nil, err
	}
	written := []string{}
	// manifest, sidecar, then bundles: the order the loaders read them in.
	for _, name := range packOrder(sortedMembers(members)) {
		if err := zipx.ExtractMember(members[name], dest, name, MaxFileBytes); err != nil {
			discardPackDir(dest)
			return nil, err
		}
		written = append(written, ppath.Join(UserData, LevelPacksDir, packID, name))
	}
	if problems := ValidatePackSource(dest); len(problems) > 0 {
		if err := discardPackDir(dest); err != nil {
			return nil, fail("pack %s: %s (its partial folder could not be removed: %s)",
				packID, strings.Join(problems, "; "), err.Error())
		}
		return nil, fail("pack %s: %s", packID, strings.Join(problems, "; "))
	}
	return &PackResult{ID: packID, Version: version,
		Dir: ppath.Join(UserData, LevelPacksDir, packID), Files: written}, nil
}

// packMembers is the archive's installable members, every name vetted before a
// single byte is written.
func packMembers(archive, packID string) (map[string]*zip.File, *zip.ReadCloser, error) {
	bundle, err := zip.OpenReader(archive)
	if err != nil {
		return nil, nil, fail("%s: %s", ppath.Name(archive), err.Error())
	}
	prefix := packID + "/"
	members := map[string]*zip.File{}
	seen := 0
	for _, member := range bundle.File {
		name, err := memberInside(member.Name, prefix, packID)
		if err != nil {
			bundle.Close()
			return nil, nil, err
		}
		if member.FileInfo().IsDir() || name == "" {
			continue
		}
		seen++
		if !packWants(name) {
			continue
		}
		if member.UncompressedSize64 > MaxFileBytes {
			bundle.Close()
			return nil, nil, fail("%s/%s: larger than the %dMB limit", packID, name, MaxFileBytes/megabyte)
		}
		if err := checkMember(member, packID, name); err != nil {
			bundle.Close()
			return nil, nil, err
		}
		members[name] = member
	}
	if seen == 0 {
		bundle.Close()
		return nil, nil, fail("%s: the archive has no files under %s/", ppath.Name(archive), packID)
	}
	if len(members) == 0 {
		bundle.Close()
		return nil, nil, fail("%s: the archive has no manifest, sidecar or bundle under %s/",
			ppath.Name(archive), packID)
	}
	return members, bundle, nil
}

// checkMember reads a member through and reports anything its header did not
// promise. The whole archive is proven this way before the installed pack folder
// is replaced, so a truncated or tampered download never touches the game.
func checkMember(member *zip.File, packID, name string) error {
	promised := member.UncompressedSize64
	reader, err := member.Open()
	if err != nil {
		return fail("%s/%s: holds fewer bytes than the %d its header declared", packID, name, promised)
	}
	defer reader.Close()
	read, err := io.Copy(io.Discard, io.LimitReader(reader, MaxFileBytes+1))
	if err != nil || uint64(read) != promised {
		return fail("%s/%s: holds %d bytes, not the %d its header declared", packID, name, read, promised)
	}
	return nil
}

// packWants reports whether a pack member is one of the files the loaders read:
// the manifest, its attachments sidecar, and the bundles.
func packWants(name string) bool {
	switch name {
	case manifestName, attachmentsName:
		return true
	}
	return IsBundleName(name)
}

// memberInside is a zip member's path inside the pack folder. Every member is
// vetted, wherever it sits: names that climb out of the destination, use a drive
// letter or a backslash separator, or bury the pack folder under another name
// are refused before any file is opened.
func memberInside(entry, prefix, packID string) (string, error) {
	slash := filepath.ToSlash(entry)
	if strings.Contains(slash, "\\") || hasDriveLetter(slash) {
		return "", zipEscape(packID, entry)
	}
	if !strings.HasPrefix(slash, prefix) {
		if climbsOut(slash) || strings.HasPrefix(slash, "/") || slash == "" {
			return "", zipEscape(packID, entry)
		}
		return "", nil
	}
	if len(slash) == len(prefix) {
		return "", nil
	}
	relative := slash[len(prefix):]
	if relative == "" || strings.HasPrefix(relative, "/") || strings.Contains(relative, ":") ||
		climbsOut(relative) {
		return "", zipEscape(packID, entry)
	}
	return relative, nil
}

func zipEscape(packID, entry string) error {
	return fail("%s: entry %s would escape its target directory", packID, quote(entry))
}

// climbsOut reports whether a member name walks up out of the destination.
func climbsOut(name string) bool {
	for _, part := range strings.Split(name, "/") {
		if part == ".." {
			return true
		}
	}
	return false
}

func hasDriveLetter(name string) bool {
	if len(name) < 2 || name[1] != ':' {
		return false
	}
	return (name[0] >= 'a' && name[0] <= 'z') || (name[0] >= 'A' && name[0] <= 'Z')
}

// preparePackDir makes the destination hold nothing but the pack about to be
// written, so a re-install never leaves an old bundle beside the new one.
func preparePackDir(dest string) error {
	if err := os.MkdirAll(ppath.Parent(dest), 0o755); err != nil {
		return err
	}
	if err := os.RemoveAll(dest); err != nil {
		return err
	}
	return os.MkdirAll(dest, 0o755)
}

func discardPackDir(dest string) error {
	if err := os.RemoveAll(dest); err != nil {
		return err
	}
	if ppath.IsDir(dest) {
		return fmt.Errorf("%s is still there", dest)
	}
	return nil
}

func copyInto(source, target string) error {
	handle, err := os.Open(source)
	if err != nil {
		return err
	}
	defer handle.Close()
	info, err := handle.Stat()
	if err != nil {
		return err
	}
	out, err := os.OpenFile(target, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, 0o644)
	if err != nil {
		return err
	}
	copied, err := io.Copy(out, io.LimitReader(handle, info.Size()))
	if err != nil {
		out.Close()
		return err
	}
	if copied != info.Size() {
		out.Close()
		return fail("%s: shrank while it was being copied", source)
	}
	return out.Close()
}

func fileSize(path string) (int64, error) {
	info, err := os.Stat(path)
	if err != nil {
		return 0, err
	}
	return info.Size(), nil
}

func sortedMembers(members map[string]*zip.File) []string {
	keys := make([]string, 0, len(members))
	for key := range members {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}

// packOrder puts the manifest first, then its attachments sidecar, then the
// bundles in name order.
func packOrder(names []string) []string {
	ordered := make([]string, 0, len(names))
	for _, first := range []string{manifestName, attachmentsName} {
		for _, name := range names {
			if name == first {
				ordered = append(ordered, name)
			}
		}
	}
	for _, name := range names {
		if name != manifestName && name != attachmentsName {
			ordered = append(ordered, name)
		}
	}
	return ordered
}
