package proton

import (
	"path/filepath"
	"sort"

	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ppath"
)

// FindWineBinary is a wine executable that can edit a prefix's registry: the
// explicit path when it exists, then wine64 or wine on the search path, then a
// Wine.app bundle under one of the application folders. Empty means none, and
// the override falls back to editing user.reg.
func FindWineBinary(explicit string, pathDirs, appRoots []string) string {
	if explicit != "" && ppath.IsFile(explicit) {
		return ppath.Normalize(explicit)
	}
	for _, dir := range pathDirs {
		for _, name := range []string{"wine64", "wine"} {
			if candidate := filepath.ToSlash(filepath.Join(dir, name)); ppath.IsFile(candidate) {
				return candidate
			}
		}
	}
	for _, root := range appRoots {
		matches, _ := filepath.Glob(filepath.Join(root, "*", "Wine*.app", "Contents", "Resources", "wine", "bin", "wine"))
		direct, _ := filepath.Glob(filepath.Join(root, "Wine*.app", "Contents", "Resources", "wine", "bin", "wine"))
		matches = append(matches, direct...)
		sort.Strings(matches)
		for _, candidate := range matches {
			if candidate = filepath.ToSlash(candidate); ppath.IsFile(candidate) {
				return candidate
			}
		}
	}
	return ""
}
