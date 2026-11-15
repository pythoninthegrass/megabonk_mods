package content

import (
	"os"
	"sort"
	"strings"

	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ppath"
)

// StagedTreeName is the folder inside a staging run that holds the game-shaped
// tree; the run's own folder may hold nothing else a commit would place.
const StagedTreeName = "tree"

// Staging is a game directory's shape written somewhere the game cannot read;
// only a commit moves it into the real directory.
type Staging struct {
	// keep remembers what each staged file belongs to, so a commit and the
	// install record agree on which level or pack a file came from.
	owners map[string]string
	// GameDir is the game directory a commit places into.
	GameDir string
	// Dir is the staging folder holding the staged tree.
	Dir string
	// root is the folder Dir sits in, so a commit can tell the staged tree from
	// a copy the player made of it.
	root string
	// staged records the exact files this run placed, so a commit moves only
	// those and nothing a player happened to put in the same folder.
	staged map[string]bool
	// committed says the staged tree has been placed and thrown away.
	committed bool

	levels map[string]*LevelResult
	packs  map[string]*PackResult
}

// NewStaging opens a staging folder beside the game directory under the given
// name; the folder is unique to this run and belongs to it alone.
func NewStaging(gameDir, name string) (*Staging, error) {
	if !ValidPackID(name) {
		return nil, fail("staging name %s: use a lowercase id of a-z, 0-9, '.', '_' or '-'", quote(name))
	}
	game := ppath.Normalize(gameDir)
	root, err := os.MkdirTemp(ppath.Parent(game), ppath.Name(game)+"."+name+"-")
	if err != nil {
		return nil, fail("cannot create a staging folder beside %s: %s", game, err.Error())
	}
	normal := ppath.Normalize(root)
	dir := ppath.Join(normal, StagedTreeName)
	if err := os.MkdirAll(nativePath(dir), 0o755); err != nil {
		return nil, fail("cannot create the staging folder %s: %s", dir, err.Error())
	}
	return &Staging{GameDir: game, Dir: dir, root: normal,
		staged: map[string]bool{}, owners: map[string]string{},
		levels: map[string]*LevelResult{}, packs: map[string]*PackResult{}}, nil
}

// WriteLevel stages a level and its optional images under UserData/Levels.
func (s *Staging) WriteLevel(slug, level, cover, biome string) error {
	// A staging folder is a game directory's shape, so the level install writes
	// its UserData/Levels/ folder there exactly as it would in the game.
	result, err := InstallLevel(s.Dir, InstallLevelInput{Slug: slug, Level: level, Cover: cover, Biome: biome})
	if err != nil {
		return err
	}
	s.levels[slug] = result
	s.recordOwner("level:"+slug, result.Files)
	return nil
}

// InstallPack stages a pack archive as UserData/LevelPacks/<id>/ and returns what
// it placed.
func (s *Staging) InstallPack(packID, version, archive string) (*PackResult, error) {
	result, err := InstallPackFromZip(s.Dir, packID, version, archive)
	if err != nil {
		return nil, err
	}
	s.packs[packID] = result
	s.recordOwner("pack:"+packID, result.Files)
	return result, nil
}

// recordOwner notes the files a staging step placed and what placed them.
func (s *Staging) recordOwner(owner string, names []string) {
	for _, name := range names {
		s.owners[ppath.Normalize(name)] = owner
	}
	s.record(names)
}

// Owner is what placed a staged file: "level:<slug>" or "pack:<id>", and "" for
// a file written directly.
func (s *Staging) Owner(name string) string { return s.owners[ppath.Normalize(name)] }

// OwnersFor lists the staged files belonging to one owner, sorted. A pack owner
// is asked for as "pack:thps".
func (s *Staging) OwnersFor(owner string) []string {
	names := []string{}
	for name, candidate := range s.owners {
		if candidate == owner {
			names = append(names, name)
		}
	}
	sort.Strings(names)
	return names
}

// Owners are the staged files' owners by game-relative name.
func (s *Staging) Owners() map[string]string {
	owners := make(map[string]string, len(s.owners))
	for name, owner := range s.owners {
		owners[name] = owner
	}
	return owners
}

// record notes the files a staging step placed.
func (s *Staging) record(names []string) {
	for _, name := range names {
		s.staged[ppath.Normalize(name)] = true
	}
}

// WriteBytes stages one downloaded file at a game-relative name inside the
// staged tree; a name that climbs out of it is refused.
func (s *Staging) WriteBytes(name string, body []byte) error {
	return s.write(name, "", func(target string) error {
		return os.WriteFile(nativePath(target), body, 0o644)
	})
}

// StageBytes stages bytes under a game-relative name and records what they
// belong to, which is how a plan says a level file or picture is part of a level.
func (s *Staging) StageBytes(owner, name string, body []byte) error {
	return s.write(name, owner, func(target string) error {
		return os.WriteFile(nativePath(target), body, 0o644)
	})
}

// CopyIn stages one file already on disk under a game-relative name, so a plan
// can stage a player's own level file or picture.
func (s *Staging) CopyIn(owner, name, source string) error {
	return s.write(name, owner, func(target string) error {
		return copyFileInto(source, target)
	})
}

// write puts one file into the staged tree under a game-relative name.
func (s *Staging) write(name, owner string, place func(target string) error) error {
	clean := ppath.Normalize(name)
	if !ppath.SafeRelative(clean) {
		return fail("%s is not a safe path inside the staged tree", quote(name))
	}
	target := ppath.Join(s.Dir, clean)
	if err := os.MkdirAll(nativePath(ppath.Parent(target)), 0o755); err != nil {
		return err
	}
	if err := place(target); err != nil {
		return err
	}
	s.recordOwner(owner, []string{clean})
	return nil
}

// Has reports whether this run staged a game-relative name.
func (s *Staging) Has(name string) bool { return s.staged[ppath.Normalize(name)] }

// Staged are the game-relative names this run placed, in order.
func (s *Staging) Staged() []string {
	names := make([]string, 0, len(s.staged))
	for name := range s.staged {
		names = append(names, name)
	}
	sort.Strings(names)
	return names
}

// LevelResults are the staged levels by slug.
func (s *Staging) LevelResults() map[string]*LevelResult { return s.levels }

// PackResults are the staged packs by id.
func (s *Staging) PackResults() map[string]*PackResult { return s.packs }

// Commit replaces the game directory's levels and pack folders with the staged
// ones and reports what landed, game-relative.
func (s *Staging) Commit() ([]string, error) {
	if s.committed {
		return nil, fail("this staging folder has already been committed")
	}
	if s.root == "" || ppath.Parent(s.Dir) != s.root {
		return nil, fail("%s is not the staging folder this run opened", s.Dir)
	}
	for _, entry := range s.levels {
		for _, name := range entry.Files {
			if err := s.checkStaged(name); err != nil {
				return nil, err
			}
		}
	}
	for _, entry := range s.packs {
		for _, name := range entry.Files {
			if err := s.checkStaged(name); err != nil {
				return nil, err
			}
		}
	}
	for name := range s.staged {
		if err := s.checkStaged(name); err != nil {
			return nil, err
		}
	}
	// Nothing is written until every staged file is accounted for.
	for _, entry := range s.packs {
		target := ppath.Join(s.GameDir, entry.Dir)
		if err := os.RemoveAll(nativePath(target)); err != nil {
			return nil, fail("cannot clear %s: %s", entry.Dir, err.Error())
		}
	}
	placed := []string{}
	for _, entry := range s.levels {
		for _, name := range entry.Files {
			if err := copyFileInto(ppath.Join(s.Dir, name), ppath.Join(s.GameDir, name)); err != nil {
				return nil, err
			}
			placed = append(placed, name)
		}
	}
	for _, entry := range s.packs {
		if err := os.MkdirAll(nativePath(ppath.Join(s.GameDir, entry.Dir)), 0o755); err != nil {
			return nil, err
		}
		for _, name := range entry.Files {
			if err := copyFileInto(ppath.Join(s.Dir, name), ppath.Join(s.GameDir, name)); err != nil {
				return nil, err
			}
			placed = append(placed, name)
		}
	}
	for _, name := range s.Staged() {
		if levelStaged(s, name) || packStaged(s, name) {
			continue
		}
		if err := copyFileInto(ppath.Join(s.Dir, name), ppath.Join(s.GameDir, name)); err != nil {
			return nil, err
		}
		placed = append(placed, name)
	}
	for _, entry := range s.packs {
		if problems := ValidatePackSource(ppath.Join(s.GameDir, entry.Dir)); len(problems) > 0 {
			return nil, fail("pack %s: %s", entry.ID, strings.Join(problems, "; "))
		}
	}
	sort.Strings(placed)
	s.committed = true
	if err := s.Discard(); err != nil {
		return nil, err
	}
	return placed, nil
}

// checkStaged refuses to place a file this run did not stage itself.
func (s *Staging) checkStaged(name string) error {
	clean := ppath.Normalize(name)
	if !s.staged[clean] {
		return fail("%s was not staged by this run", name)
	}
	if !ppath.SafeRelative(clean) || !ppath.IsFile(ppath.Join(s.Dir, clean)) {
		return fail("%s was staged but is no longer there", name)
	}
	return nil
}

// levelStaged reports whether a level install is what placed this name.
func levelStaged(s *Staging, name string) bool {
	for _, entry := range s.levels {
		for _, placed := range entry.Files {
			if ppath.Normalize(placed) == ppath.Normalize(name) {
				return true
			}
		}
	}
	return false
}

// packStaged reports whether a pack install is what placed this name.
func packStaged(s *Staging, name string) bool {
	for _, entry := range s.packs {
		for _, placed := range entry.Files {
			if ppath.Normalize(placed) == ppath.Normalize(name) {
				return true
			}
		}
	}
	return false
}

// copyFileInto puts one staged file where the game reads it, creating its
// folders on the way.
func copyFileInto(source, target string) error {
	if err := os.MkdirAll(nativePath(ppath.Parent(target)), 0o755); err != nil {
		return err
	}
	return copyInto(source, target)
}

// Discard throws the staged tree away, including the folder it was staged in.
func (s *Staging) Discard() error {
	folder := s.root
	if folder == "" {
		if s.Dir == "" {
			return nil
		}
		folder = s.Dir
	}
	if err := os.RemoveAll(nativePath(folder)); err != nil {
		return fail("cannot remove the staging folder %s: %s", folder, err.Error())
	}
	s.root = ""
	s.Dir = ""
	s.staged = map[string]bool{}
	s.owners = map[string]string{}
	return nil
}
