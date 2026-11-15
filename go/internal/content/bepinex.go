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

const (
	// BepInExDir is the loader's directory beside the executable.
	BepInExDir = "BepInEx"
	// PluginsDir is the folder the loader loads plugins from.
	PluginsDir = BepInExDir + "/plugins"
	// RuntimeDirName is the folder the loader pack's .NET 6 runtime lands in
	// beside the executable.
	RuntimeDirName = "dotnet"
	// ModFolderName is this mod's folder under the plugins directory.
	ModFolderName = "MegabonkLevels"
	// ModDLLName is the plugin assembly the loader has to find.
	ModDLLName = "MegabonkLevels.Mod.dll"
	// NLayerName is the managed dependency shipped beside the plugin.
	NLayerName = "NLayer.dll"
	// LicenseName is NLayer's license, which belongs beside its DLL.
	LicenseName = "NLayer.LICENSE.txt"
	// VersionDLLName is the MelonLoader proxy the BepInEx winhttp proxy replaces.
	VersionDLLName = "version.dll"
	// ProxyBackupName is where a MelonLoader proxy is parked.
	ProxyBackupName = "version.dll.bak"
	// WinHTTPProxyName is the proxy the loader pack uses to start itself.
	WinHTTPProxyName = "winhttp.dll"
	// NativeExeName is the Linux native build's executable, the one BepInEx
	// cannot hook.
	NativeExeName = "Megabonk.x86_64"
	// DoorstopConfigName is the loader's doorstop configuration.
	DoorstopConfigName = "doorstop_config.ini"
	// DoorstopVersionName records the doorstop version the pack installed.
	DoorstopVersionName = ".doorstop_version"
	// ChangelogName is the pack's changelog, which a mod manager's Apply misses.
	ChangelogName = "changelog.txt"

	packRoot      = "BepInExPack"
	dotnetTree    = "dotnet/"
	maxPackBytes  = 400 * 1024 * 1024
	smallFileByte = 1
)

// loaderRequiredNames are the pack files whose absence means the archive is not
// a usable BepInEx install, the same set scripts/repair_bepinex.py insists on.
var loaderRequiredNames = []string{
	DoorstopConfigName, WinHTTPProxyName,
	BepInExDir + "/core/BepInEx.Unity.IL2CPP.dll",
	dotnetTree + "coreclr.dll",
}

// modRequiredNames are the files the mod archive must carry: the plugin, its
// managed dependency, and that dependency's licence beside it.
var modRequiredNames = []string{ModDLLName, NLayerName, LicenseName}

// Error is a BepInEx step that cannot be carried out as asked.
type Error struct{ message string }

func (e *Error) Error() string { return e.message }

func loaderFail(format string, args ...any) error {
	return &Error{message: fmt.Sprintf(format, args...)}
}

// BepInExPluginsPath is the folder the mod's plugin files land in.
func BepInExPluginsPath(gameDir string) string {
	return ppath.Join(gameDir, PluginsDir, ModFolderName)
}

// InstalledBepInExVersion is the loader pack version this installer recorded
// putting in the game folder, or "" when it did not install one.
func InstalledBepInExVersion(gameDir string) string {
	if state, err := DetectLoader(gameDir); err == nil && state != nil {
		return state.BepInExVersion
	}
	return ""
}

// InstalledModVersion is the recorded mod version, and only when the plugin files
// are really in place.
func InstalledModVersion(gameDir string) string {
	state, err := DetectLoader(gameDir)
	if err != nil || state == nil || !modFilesPresent(gameDir) {
		return ""
	}
	return state.ModVersion
}

// ModInstalled reports whether the mod's files are in place, manager installs
// included; InstalledModVersion is the one that insists on the record.
func ModInstalled(gameDir string) bool { return modFilesPresent(ppath.Normalize(gameDir)) }

func modFilesPresent(gameDir string) bool {
	for _, name := range modRequiredNames {
		if !ppath.IsFile(ppath.Join(BepInExPluginsPath(gameDir), name)) {
			return false
		}
	}
	return true
}

// BepInExResult is what a loader pack install placed.
type BepInExResult struct {
	Version string
	// Placed names the files this run wrote, pack-relative; a repair lists only
	// what was missing or corrupt.
	Placed []string
	// Parked reports a MelonLoader version.dll moved aside as ProxyBackup.
	Parked bool
	// PackFiles names every file the pack places, so uninstall can remove them.
	PackFiles []string
}

// InstallBepInEx unpacks the loader pack's BepInExPack/ tree beside the
// executable and parks a MelonLoader version.dll, writing nothing until vetting.
func InstallBepInEx(gameDir, archive, version string) (*BepInExResult, error) {
	if strings.TrimSpace(version) == "" {
		return nil, loaderFail("no BepInEx pack version was given for %s", ppath.Name(archive))
	}
	if !ppath.IsFile(archive) {
		return nil, loaderFail("%s: no such BepInEx pack archive", archive)
	}
	game := ppath.Normalize(gameDir)
	members, bundle, err := packMembersUnder(archive, packRoot+"/", "BepInEx pack "+version)
	if err != nil {
		return nil, err
	}
	defer bundle.Close()
	if err := checkLoaderMembers(members); err != nil {
		return nil, err
	}
	if err := checkLoaderGameDir(game); err != nil {
		return nil, err
	}
	proxy, err := inspectVersionProxy(game)
	if err != nil {
		return nil, err
	}
	packFiles := sortedMemberNames(members)
	placed := []string{}
	for _, name := range packFiles {
		if sameFile(ppath.Join(game, name), members[name]) {
			continue
		}
		if err := zipx.ExtractMember(members[name], game, name, maxPackBytes); err != nil {
			return nil, loaderFail("%s: %s", ppath.Name(archive), err.Error())
		}
		placed = append(placed, name)
	}
	// The proxy is parked only once the loader that replaces it is in place.
	parked, err := parkVersionProxy(game, proxy)
	if err != nil {
		return nil, err
	}
	return &BepInExResult{Version: version, Placed: placed, Parked: parked, PackFiles: packFiles}, nil
}

// BepInExInstallRecord builds the record entry for a loader and mod install.
func BepInExInstallRecord(bepinexVersion, modVersion string, packFiles []string, proxyParked bool) (*LoaderState, error) {
	bepinex := strings.TrimSpace(bepinexVersion)
	mod := strings.TrimSpace(modVersion)
	if bepinex == "" || mod == "" {
		return nil, loaderFail("both the BepInEx pack version and the mod version are needed to record the install")
	}
	files := make([]string, 0, len(packFiles))
	seen := map[string]bool{}
	for _, name := range packFiles {
		clean := ppath.Normalize(name)
		if clean == "" || !underPackTree(clean) || seen[clean] {
			continue
		}
		seen[clean] = true
		files = append(files, clean)
	}
	if len(files) == 0 {
		return nil, loaderFail("no BepInEx pack files were placed, so there is nothing to record")
	}
	sort.Strings(files)
	state := &LoaderState{
		BepInExVersion: bepinex,
		ModVersion:     mod,
		Installed:      true,
		PackFiles:      files,
		ProxyParked:    proxyParked,
	}
	if proxyParked {
		backup := ProxyBackupName
		state.ProxyBackup = &backup
	}
	return state, nil
}

// checkLoaderMembers refuses an archive missing what the loader needs to start.
func checkLoaderMembers(members map[string]*zip.File) error {
	for _, name := range loaderRequiredNames {
		member, found := members[name]
		if !found || member.UncompressedSize64 < smallFileByte {
			return loaderFail("the BepInEx pack is missing %s", name)
		}
	}
	return nil
}

// checkLoaderGameDir refuses a build the loader cannot hook, such as native Linux.
func checkLoaderGameDir(game string) error {
	if ppath.IsFile(ppath.Join(game, NativeExeName)) {
		return loaderFail("%s is the Linux native build of Megabonk: BepInEx hooks the "+
			"Windows build under Wine or Proton, so switch it to that build in Steam first", game)
	}
	for _, name := range []string{DoorstopConfigName, WinHTTPProxyName} {
		if ppath.Exists(ppath.Join(game, name)) && !ppath.IsFile(ppath.Join(game, name)) {
			return loaderFail("%s is not a file", ppath.Join(game, name))
		}
	}
	return nil
}

// versionProxy is a version.dll and the backup slot it would park into.
type versionProxy struct {
	present  bool
	parkable bool
	// backupFree records that nothing is parked where the proxy would go.
	backupFree bool
}

// inspectVersionProxy decides what to do with a version.dll without touching it;
// only a MelonLoader proxy may be parked.
func inspectVersionProxy(game string) (versionProxy, error) {
	proxy := ppath.Join(game, VersionDLLName)
	backup := ppath.Join(game, ProxyBackupName)
	state := versionProxy{backupFree: true}
	if ppath.Exists(backup) {
		if !ppath.IsFile(backup) {
			return state, loaderFail("%s is not a file", backup)
		}
		state.backupFree = false
	}
	if !ppath.Exists(proxy) {
		return state, nil
	}
	if !ppath.IsFile(proxy) {
		return state, loaderFail("%s is not a file", proxy)
	}
	state.present = true
	parkable := ppath.IsDir(ppath.Join(game, LoaderDir))
	if !parkable {
		return state, loaderFail("%s in %s is not a MelonLoader proxy this installer may park: there is "+
			"no %s/ behind it, so move it aside yourself first", VersionDLLName, game, LoaderDir)
	}
	if !state.backupFree {
		return state, loaderFail("%s already exists: keep both proxies or resolve them before installing",
			ProxyBackupName)
	}
	return state, nil
}

// parkVersionProxy renames the proxy the caller already inspected, so the two
// loaders are never both active.
func parkVersionProxy(game string, proxy versionProxy) (bool, error) {
	if !proxy.present {
		return false, nil
	}
	if err := os.Rename(ppath.Join(game, VersionDLLName), ppath.Join(game, ProxyBackupName)); err != nil {
		return false, loaderFail("cannot park %s as %s: %s", VersionDLLName, ProxyBackupName, err.Error())
	}
	return true, nil
}

// ModResult is what a mod install placed.
type ModResult struct {
	Version string
	Files   []string
	// Replaced reports files from an earlier install of the mod were overwritten.
	Replaced bool
}

// InstallModFromZip merges the mod archive's plugin folder into the game folder,
// refusing an archive that does not carry the complete plugin set.
func InstallModFromZip(gameDir, archive, version string) (*ModResult, error) {
	if strings.TrimSpace(version) == "" {
		return nil, loaderFail("no mod version was given for %s", ppath.Name(archive))
	}
	if !ppath.IsFile(archive) {
		return nil, loaderFail("%s: no such mod archive", archive)
	}
	game := ppath.Normalize(gameDir)
	if !ppath.IsFile(ppath.Join(game, WinHTTPProxyName)) || !ppath.IsFile(ppath.Join(game, DoorstopConfigName)) {
		return nil, loaderFail("%s has no BepInEx loader installed: install the BepInEx pack first", game)
	}
	prefix := PluginsDir + "/" + ModFolderName + "/"
	members, bundle, err := packMembersUnder(archive, prefix, "mod "+version)
	if err != nil {
		return nil, err
	}
	defer bundle.Close()
	for _, name := range modRequiredNames {
		member, found := members[name]
		if !found || member.UncompressedSize64 < smallFileByte {
			return nil, loaderFail("the mod archive has no %s under %s", name, prefix)
		}
	}
	destination := BepInExPluginsPath(game)
	replaced := false
	for _, name := range modRequiredNames {
		if ppath.IsFile(ppath.Join(destination, name)) {
			replaced = true
		}
	}
	if err := os.MkdirAll(destination, 0o755); err != nil {
		return nil, err
	}
	written := []string{}
	for _, name := range sortedMemberNames(members) {
		if err := zipx.ExtractMember(members[name], destination, name, MaxFileBytes); err != nil {
			return nil, loaderFail("%s: %s", ppath.Name(archive), err.Error())
		}
		written = append(written, PluginsDir+"/"+ModFolderName+"/"+name)
	}
	return &ModResult{Version: version, Files: written, Replaced: replaced}, nil
}

// ModPluginPrefix is the folder inside a mod archive that holds its plugin set.
const ModPluginPrefix = PluginsDir + "/" + ModFolderName + "/"

// ModPluginFiles returns an archive's vetted plugin members keyed by archive path,
// which is also their path in the game folder. The caller closes the reader.
func ModPluginFiles(archive string) (map[string]*zip.File, *zip.ReadCloser, error) {
	return packMembersUnder(archive, ModPluginPrefix, "mod archive "+ppath.Name(archive))
}

// packMembersUnder is one archive's installable members, every name vetted
// against the folder it is allowed to write into before a byte is extracted.
func packMembersUnder(archive, prefix, what string) (map[string]*zip.File, *zip.ReadCloser, error) {
	bundle, err := zip.OpenReader(archive)
	if err != nil {
		return nil, nil, loaderFail("%s is not a readable zip archive: %s", ppath.Name(archive), err.Error())
	}
	members := map[string]*zip.File{}
	total := uint64(0)
	for _, member := range bundle.File {
		name, err := memberUnder(member.Name, prefix)
		if err != nil {
			bundle.Close()
			return nil, nil, err
		}
		if name == "" || member.FileInfo().IsDir() {
			continue
		}
		if member.UncompressedSize64 > maxPackBytes {
			bundle.Close()
			return nil, nil, loaderFail("%s: %s is larger than the %dMB limit",
				what, name, maxPackBytes/megabyte)
		}
		if err := readMemberThrough(member, what, name); err != nil {
			bundle.Close()
			return nil, nil, err
		}
		total += member.UncompressedSize64
		if total > maxPackBytes {
			bundle.Close()
			return nil, nil, loaderFail("%s unpacks to more than the %dMB limit", what, maxPackBytes/megabyte)
		}
		if _, seen := members[name]; seen {
			bundle.Close()
			return nil, nil, loaderFail("%s lists %s twice", what, name)
		}
		members[name] = member
	}
	if len(members) == 0 {
		bundle.Close()
		return nil, nil, loaderFail("%s carries nothing under %s", what, strconv.Quote(strings.TrimSuffix(prefix, "/")))
	}
	return members, bundle, nil
}

// memberUnder is a member's path inside the payload folder; escaping names are
// refused and members outside it entirely are ignored.
func memberUnder(entry, prefix string) (string, error) {
	slash := filepath.ToSlash(entry)
	if strings.Contains(slash, "\\") || hasDriveLetter(slash) || strings.HasPrefix(slash, "/") {
		return "", loaderFail("entry %s is not a safe archive name", strconv.Quote(entry))
	}
	// A climbing name is refused outright, not ignored: it reaches outside.
	if climbsOut(slash) {
		return "", loaderFail("entry %s would escape its target directory", strconv.Quote(entry))
	}
	if !strings.HasPrefix(slash, prefix) {
		return "", nil
	}
	relative := slash[len(prefix):]
	if relative == "" || strings.HasPrefix(relative, "/") || strings.Contains(relative, ":") ||
		climbsOut(relative) {
		return "", loaderFail("entry %s would escape its target directory", strconv.Quote(entry))
	}
	return relative, nil
}

// readMemberThrough reads a member once so a truncated or tampered archive fails.
func readMemberThrough(member *zip.File, what, name string) error {
	reader, err := member.Open()
	if err != nil {
		return loaderFail("%s: %s cannot be opened: %s", what, name, err.Error())
	}
	defer reader.Close()
	read, err := io.Copy(io.Discard, io.LimitReader(reader, maxPackBytes+1))
	if err != nil || uint64(read) != member.UncompressedSize64 {
		return loaderFail("%s: %s holds %d bytes, not the %d its header declared",
			what, name, read, member.UncompressedSize64)
	}
	return nil
}

func sortedMemberNames(members map[string]*zip.File) []string {
	names := make([]string, 0, len(members))
	for name := range members {
		names = append(names, name)
	}
	sort.Strings(names)
	return names
}

// sameFile reports whether the target already holds the member's bytes, so a
// second install does nothing.
func sameFile(target string, member *zip.File) bool {
	info, err := os.Stat(target)
	if err != nil || !info.Mode().IsRegular() {
		return false
	}
	if uint64(info.Size()) != member.UncompressedSize64 {
		return false
	}
	handle, err := os.Open(target)
	if err != nil {
		return false
	}
	defer handle.Close()
	source, err := member.Open()
	if err != nil {
		return false
	}
	defer source.Close()
	left := make([]byte, 32*1024)
	right := make([]byte, 32*1024)
	for {
		n, leftErr := io.ReadFull(handle, left)
		m, rightErr := io.ReadFull(source, right)
		if n != m || !equalBytes(left[:n], right[:m]) {
			return false
		}
		if atEnd(leftErr) && atEnd(rightErr) {
			return true
		}
		if leftErr != nil || rightErr != nil {
			return false
		}
	}
}

// atEnd reports a clean end of stream, including a full final chunk.
func atEnd(err error) bool {
	return err == nil || err == io.EOF || err == io.ErrUnexpectedEOF
}

func equalBytes(left, right []byte) bool {
	if len(left) != len(right) {
		return false
	}
	for index := range left {
		if left[index] != right[index] {
			return false
		}
	}
	return true
}

// SaveBepInExRecord writes a record whose loader entry the caller assembled.
func SaveBepInExRecord(gameDir string, record *Record) error {
	if record == nil {
		return loaderFail("no install record to write")
	}
	if record.Loader == nil {
		return loaderFail("the record has no loader entry to write")
	}
	// The top-level versions --check and the GUI read, kept in step with loader.
	record.BepinexVersion = record.Loader.BepInExVersion
	record.ModVersion = record.Loader.ModVersion
	_, err := SaveRecord(gameDir, record)
	return err
}

// WriteBepInExInstallRecord records a loader and mod install just carried out.
func WriteBepInExInstallRecord(gameDir, bepinexVersion, modVersion string, packFiles []string, proxyParked bool) error {
	state, err := BepInExInstallRecord(bepinexVersion, modVersion, packFiles, proxyParked)
	if err != nil {
		return err
	}
	game := ppath.Normalize(gameDir)
	if !modFilesPresent(game) {
		return loaderFail("%s holds no %s to record: install the mod first",
			game, PluginsDir+"/"+ModFolderName)
	}
	record := LoadRecord(game)
	if record == nil {
		record = &Record{}
	}
	record.Schema = RecordSchema
	record.BepinexVersion = state.BepInExVersion
	record.ModVersion = state.ModVersion
	record.Loader = state
	_, err = SaveRecord(game, record)
	return err
}

// DetectLoader reports the loader install the record describes, or nil.
func DetectLoader(gameDir string) (*LoaderState, error) {
	record := LoadRecord(ppath.Normalize(gameDir))
	if record == nil || record.Loader == nil {
		return nil, nil
	}
	state := *record.Loader
	if !state.Installed || state.BepInExVersion == "" {
		return nil, nil
	}
	return &state, nil
}

// loaderInstalled says whether the record, not the files, proves this is ours.
func loaderInstalled(record *Record) bool {
	return record != nil && record.Loader != nil && record.Loader.Installed
}

// UninstallBepInEx removes the recorded pack files and plugin folder and restores
// a parked proxy; with no recorded install it removes nothing.
func UninstallBepInEx(gameDir string, record *Record) ([]string, error) {
	removed := []string{}
	if !loaderInstalled(record) {
		return removed, nil
	}
	game := ppath.Normalize(gameDir)
	if ppath.IsDir(BepInExPluginsPath(game)) {
		if err := os.RemoveAll(nativePath(BepInExPluginsPath(game))); err != nil {
			return removed, err
		}
		removed = append(removed, PluginsDir+"/"+ModFolderName)
	}
	for _, name := range recordedPackFiles(record) {
		target := ppath.Join(game, name)
		if !ppath.IsFile(target) {
			continue
		}
		if err := os.Remove(nativePath(target)); err != nil {
			return removed, err
		}
		removed = append(removed, name)
	}
	if err := restoreVersionProxy(game, record, &removed); err != nil {
		return removed, err
	}
	// Folders go last and deepest first, and only when nothing foreign is left.
	for _, directory := range recordedFolders(record) {
		if !collapsible(ppath.Join(game, directory)) {
			continue
		}
		if err := os.RemoveAll(nativePath(ppath.Join(game, directory))); err != nil {
			return removed, err
		}
		removed = append(removed, directory)
	}
	if err := clearLoaderEntryIfGone(game); err != nil {
		return removed, err
	}
	return removed, nil
}

// UninstallRecorded removes the loader, plugin folder, levels, packs and loose
// files the record names and nothing else, dropping the record only when empty.
func UninstallRecorded(gameDir string, record *Record) ([]string, error) {
	game := ppath.Normalize(gameDir)
	if record == nil {
		return nil, nil
	}
	removed, err := UninstallBepInEx(game, record)
	if err != nil {
		return removed, err
	}
	for _, entry := range record.Levels {
		for _, name := range []string{entry.Filename, entry.Cover, entry.Biome} {
			if name == "" {
				continue
			}
			target := ppath.Join(game, name)
			if !ppath.IsFile(target) {
				continue
			}
			if err := os.Remove(nativePath(target)); err != nil {
				return removed, err
			}
			removed = append(removed, name)
		}
	}
	for _, entry := range record.Packs {
		if entry.Dir == "" {
			continue
		}
		folder := ppath.Join(game, entry.Dir)
		if !ppath.IsDir(folder) {
			continue
		}
		if err := os.RemoveAll(nativePath(folder)); err != nil {
			return removed, err
		}
		removed = append(removed, entry.Dir)
	}
	for _, name := range record.Files {
		target := ppath.Join(game, name)
		if !ppath.IsFile(target) {
			continue
		}
		if err := os.Remove(nativePath(target)); err != nil {
			return removed, err
		}
		removed = append(removed, name)
	}
	// The level and pack folders the record just emptied go too: they are the
	// installer's own, and a game it made untouched should look untouched.
	for _, folder := range []string{LevelsPath(game), LevelPacksPath(game)} {
		if !collapsible(folder) {
			continue
		}
		if err := os.RemoveAll(nativePath(folder)); err != nil {
			return removed, err
		}
		removed = append(removed, ppath.Join(UserData, ppath.Name(folder)))
	}
	if err := dropRemovedEntries(game, record); err != nil {
		return removed, err
	}
	return removed, nil
}

// dropRemovedEntries writes the record back with only what is still in place, and
// removes it outright once nothing is left to describe.
func dropRemovedEntries(game string, record *Record) error {
	remaining := LoadRecord(game)
	if remaining == nil {
		return nil
	}
	for code, entry := range remaining.Levels {
		if !ppath.IsFile(ppath.Join(game, entry.Filename)) {
			delete(remaining.Levels, code)
		}
	}
	for id, entry := range remaining.Packs {
		if !ppath.IsDir(ppath.Join(game, entry.Dir)) {
			delete(remaining.Packs, id)
		}
	}
	kept := remaining.Files[:0]
	for _, name := range remaining.Files {
		if ppath.IsFile(ppath.Join(game, name)) {
			kept = append(kept, name)
		}
	}
	remaining.Files = kept
	if remaining.Loader == nil && remaining.ModVersion == "" && remaining.BepinexVersion == "" &&
		len(remaining.Levels) == 0 && len(remaining.Packs) == 0 && len(remaining.Files) == 0 {
		return ClearRecord(game)
	}
	_, err := SaveRecord(game, remaining)
	return err
}

// clearLoaderEntryIfGone drops the loader entry once nothing it named remains.
func clearLoaderEntryIfGone(game string) error {
	record := LoadRecord(game)
	if record == nil || record.Loader == nil {
		return nil
	}
	for _, name := range recordedPackFiles(record) {
		if ppath.IsFile(ppath.Join(game, name)) {
			return nil
		}
	}
	if ppath.IsDir(BepInExPluginsPath(game)) {
		return nil
	}
	record.Loader = nil
	record.BepinexVersion = ""
	record.ModVersion = ""
	_, err := SaveRecord(game, record)
	return err
}

// collapsible reports whether a folder holds nothing at all, or nothing but
// folders that are themselves collapsible.
func collapsible(directory string) bool {
	if !ppath.IsDir(directory) {
		return false
	}
	entries, err := os.ReadDir(directory)
	if err != nil {
		return false
	}
	for _, entry := range entries {
		if !entry.IsDir() {
			return false
		}
		if !collapsible(ppath.Join(directory, entry.Name())) {
			return false
		}
	}
	return true
}

// recordedPackFiles are the pack files the record says this installer placed.
func recordedPackFiles(record *Record) []string {
	names := []string{}
	seen := map[string]bool{}
	add := func(name string) {
		clean := ppath.Normalize(name)
		if clean == "" || !underPackTree(clean) || seen[clean] {
			return
		}
		seen[clean] = true
		names = append(names, clean)
	}
	if record != nil {
		for _, name := range record.Files {
			add(name)
		}
		if record.Loader != nil {
			for _, name := range record.Loader.PackFiles {
				add(name)
			}
		}
	}
	sort.Strings(names)
	return names
}

// modTree is the mod's plugin folder, the second tree the installer may remove.
const modTree = PluginsDir + "/"

// underPackTree is deliberately narrow, so nothing a player authored reads as
// the installer's to remove.
func underPackTree(name string) bool {
	switch {
	case strings.HasPrefix(name, dotnetTree):
		return true
	case strings.HasPrefix(name, BepInExDir+"/core/"):
		return true
	case strings.HasPrefix(name, modTree):
		return true
	}
	switch name {
	case DoorstopConfigName, WinHTTPProxyName, DoorstopVersionName, ChangelogName:
		return true
	}
	return false
}

// recordedFolders are the folders the recorded files sat in, deepest first.
func recordedFolders(record *Record) []string {
	folders := map[string]bool{}
	add := func(name string) {
		for parent := ppath.Parent(name); parent != "" && parent != "." && parent != "/"; parent = ppath.Parent(parent) {
			if parent == ModsDir || parent == UserLibsDir {
				break
			}
			folders[parent] = true
		}
	}
	for _, name := range recordedPackFiles(record) {
		add(name)
	}
	order := make([]string, 0, len(folders))
	for folder := range folders {
		order = append(order, folder)
	}
	sort.Slice(order, func(i, j int) bool {
		left, right := strings.Count(order[i], "/"), strings.Count(order[j], "/")
		if left != right {
			return left > right
		}
		return order[i] > order[j]
	})
	return order
}

// restoreVersionProxy puts back only the proxy this installer recorded parking.
func restoreVersionProxy(game string, record *Record, removed *[]string) error {
	if !loaderInstalled(record) || !record.Loader.ProxyParked {
		return nil
	}
	proxy := ppath.Join(game, VersionDLLName)
	backup := ppath.Join(game, ProxyBackupName)
	if !ppath.IsFile(backup) {
		return nil
	}
	if ppath.Exists(proxy) {
		return loaderFail("%s sits where %s was parked: decide which proxy the game should load "+
			"and remove the other before uninstalling", VersionDLLName, ProxyBackupName)
	}
	if err := os.Rename(backup, proxy); err != nil {
		return loaderFail("cannot restore %s from %s: %s", VersionDLLName, ProxyBackupName, err.Error())
	}
	*removed = append(*removed, ProxyBackupName)
	return nil
}

func nativePath(path string) string { return filepath.FromSlash(path) }
