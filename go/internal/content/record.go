package content

import (
	"sort"
	"strconv"
	"strings"
)

// LevelRecord is one installed level: the name it landed under, and the sidecar
// images placed beside it.
type LevelRecord struct {
	Code     string `json:"code"`
	Filename string `json:"filename"`
	Cover    string `json:"cover,omitempty"`
	Biome    string `json:"biome,omitempty"`
}

// PackRecord is one installed asset pack.
type PackRecord struct {
	Version string   `json:"version"`
	Dir     string   `json:"dir"`
	Files   []string `json:"files"`
}

// Runtime is the record's entry for the private .NET runtime.
type Runtime struct {
	Mode         string  `json:"mode"`
	Path         string  `json:"path"`
	Version      string  `json:"version"`
	LaunchOption *string `json:"launch_option"`
}

// DllOverride is the record's entry for the Wine version.dll override.
type DllOverride struct {
	Applied bool    `json:"applied"`
	Name    string  `json:"name"`
	Value   string  `json:"value"`
	Prefix  *string `json:"prefix"`
	Via     *string `json:"via"`
}

// LoaderState is the record's entry for the BepInEx loader install: the pack and
// mod versions this installer put in the game folder, the MelonLoader proxy it
// parked, and the pack files it wrote there.
type LoaderState struct {
	BepInExVersion string `json:"bepinex_version"`
	ModVersion     string `json:"mod_version"`
	// Installed reports that this installer, and not a mod manager, put the
	// loader pack and the mod's plugin folder in the game folder.
	Installed   bool     `json:"installed"`
	PackFiles   []string `json:"pack_files"`
	ProxyParked bool     `json:"proxy_parked"`
	ProxyBackup *string  `json:"proxy_backup"`
	// ModSHA256 is the digest the mod archive carried when this install fetched
	// it. Thunderstore publishes no checksum, so this is what lets a repair reuse
	// the cached archive instead of fetching the release again.
	ModSHA256 string `json:"mod_sha256,omitempty"`
}

// Record is MegabonkLevels.installer.json: the mod and BepInEx pack versions
// that are installed, and the levels and packs this installer placed, so --check
// can report drift and uninstall can remove exactly this.
type Record struct {
	Schema               string                 `json:"schema"`
	PackageID            string                 `json:"package_id"`
	ModVersion           string                 `json:"mod_version"`
	BepinexVersion       string                 `json:"bepinex_version"`
	GameBuildID          string                 `json:"game_buildid"`
	InstalledGameBuildID *string                `json:"installed_game_buildid"`
	InstalledAt          string                 `json:"installed_at"`
	GameDir              string                 `json:"game_dir"`
	Files                []string               `json:"files"`
	Levels               map[string]LevelRecord `json:"levels"`
	Packs                map[string]PackRecord  `json:"packs"`
	Runtime              *Runtime               `json:"runtime"`
	DllOverride          *DllOverride           `json:"dll_override"`
	Loader               *LoaderState           `json:"loader,omitempty"`
}

// HasLevel reports whether the installer placed this level.
func (r *Record) HasLevel(code string) bool {
	if r == nil {
		return false
	}
	_, found := r.Levels[code]
	return found
}

// HasPack reports whether the installer placed this pack.
func (r *Record) HasPack(packID string) bool {
	if r == nil {
		return false
	}
	_, found := r.Packs[packID]
	return found
}

// LevelCodes are the installed level codes in order.
func (r *Record) LevelCodes() []string {
	if r == nil {
		return nil
	}
	codes := make([]string, 0, len(r.Levels))
	for code := range r.Levels {
		codes = append(codes, code)
	}
	sort.Strings(codes)
	return codes
}

// PackIDs are the installed pack ids in order.
func (r *Record) PackIDs() []string {
	if r == nil {
		return nil
	}
	ids := make([]string, 0, len(r.Packs))
	for id := range r.Packs {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	return ids
}

// DescribeRecord is the human-readable description of an install record that
// --check and uninstall print.
func DescribeRecord(record *Record) []string {
	if record == nil {
		record = &Record{}
	}
	lines := []string{
		"package " + orDefault(record.PackageID, "unknown"),
		"mod " + orDefault(record.ModVersion, "?") + " / BepInEx " + orDefault(record.BepinexVersion, "?"),
	}
	if record.InstalledAt != "" {
		lines = append(lines, "installed "+record.InstalledAt)
	}
	levels := record.LevelCodes()
	if len(levels) > 0 {
		lines = append(lines, strconv.Itoa(len(levels))+" level(s): "+joinLimited(levels))
	} else {
		lines = append(lines, "0 level(s)")
	}
	packs := record.PackIDs()
	if len(packs) == 0 {
		lines = append(lines, "0 pack(s)")
	} else {
		described := make([]string, 0, len(packs))
		for _, id := range packs {
			described = append(described, id+" "+orDefault(record.Packs[id].Version, "?"))
		}
		lines = append(lines, "packs: "+joinLimited(described))
	}
	return lines
}

const listedLimit = 6

func joinLimited(items []string) string {
	if len(items) <= listedLimit {
		return strings.Join(items, ", ")
	}
	return strings.Join(items[:listedLimit], ", ") + ", +" + strconv.Itoa(len(items)-listedLimit) + " more"
}
