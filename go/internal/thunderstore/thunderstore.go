// Package thunderstore resolves the level editor mod and the BepInEx pack it
// depends on from Thunderstore, and downloads the pack archive.
//
// Metadata comes from the experimental package endpoint, whose latest entry
// carries version_number, download_url and dependencies as
// Namespace-Name-Version strings. The pack archive itself comes from the CDN at
// gcdn.thunderstore.io, whose files sit under BepInExPack/. Every request
// carries an ordinary browser User-Agent: the default scripting client is
// refused by Cloudflare with error 1010 (docs/thunderstore.md).
//
// Nothing is written where the game can see it until the archive's SHA-256 has
// been checked against the caller's pinned digest, so a swapped or truncated
// download fails as an error rather than as a broken install.
package thunderstore

import (
	"archive/zip"
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ppath"
)

const (
	// ModNamespace is the team that publishes the level editor mod.
	ModNamespace = "pythoninthegrass"
	// ModName is the level editor mod's package name.
	ModName = "Megabonk_Level_Editor"
	// BepInExNamespace is the team that publishes the IL2CPP loader pack.
	BepInExNamespace = "BepInEx"
	// BepInExName is the loader pack's package name.
	BepInExName = "BepInExPack_IL2CPP"

	// DefaultAPIBaseURL is the site the metadata endpoint lives on.
	DefaultAPIBaseURL = "https://thunderstore.io"
	// DefaultCDNBaseURL is the CDN the package archives are served from.
	DefaultCDNBaseURL = "https://gcdn.thunderstore.io"

	// APIBaseURLEnv names the environment variable that overrides the metadata
	// location, which is how a test points the client at a local server.
	APIBaseURLEnv = "MEGABONK_THUNDERSTORE_API_URL"
	// CDNBaseURLEnv names the environment variable that overrides the CDN.
	CDNBaseURLEnv = "MEGABONK_THUNDERSTORE_CDN_URL"

	// UserAgent is an ordinary browser identity. Thunderstore's CDN answers a
	// default scripting client with Cloudflare error 1010.
	UserAgent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

	// ArchiveSuffix is the CDN path a package archive is served from.
	ArchiveSuffix = "/live/repository/packages/%s-%s-%s.zip"

	// PackRoot is the directory every member of the loader pack's archive sits
	// under, and the layout the installer extracts from.
	PackRoot = "BepInExPack"

	// MaxArchiveBytes is the largest pack archive the installer will hold.
	MaxArchiveBytes = 400 << 20
	// MaxMetadataBytes is the largest metadata document the endpoint should ever
	// answer with.
	MaxMetadataBytes = 1 << 20
	// MaxErrorBodyBytes is how much of an error page is kept for the message.
	MaxErrorBodyBytes = 8 << 10

	metadataSuffix = "/api/experimental/package/%s/%s/"

	packArchiveName = PackRoot + "/"
	tempSuffix      = ".part"
	maxErrorRunes   = 200
	requestTimeout  = 2 * time.Minute
	// referenceParts is the fewest hyphen-separated parts a reference can have:
	// a namespace, a name and a version, each without a hyphen of its own.
	referenceParts = 3
)

// bepinexPins holds the SHA-256 of every loader pack archive the installer is
// known to work with; 6.0.788 is the version thunderstore.toml depends on and
// the digest scripts/repair_bepinex.py pins.
var bepinexPins = map[string]string{
	"6.0.788": "ce25d925f9eaba817214f5d6b2083b8e135ed0592b5a61b9f75ea5d4c02f5300",
}

// dependencyField is a namespace or name: letters, digits, '_' and '.', with
// hyphens allowed only between two such characters, so no field starts or ends
// with a hyphen or carries two in a row.
var dependencyField = regexp.MustCompile(`^[A-Za-z0-9_.]+(?:-[A-Za-z0-9_.]+)*$`)

var (
	versionPattern = regexp.MustCompile(`^[0-9]+\.[0-9]+\.[0-9]+$`)
	hex64          = regexp.MustCompile(`^[0-9a-f]{64}$`)
	safeName       = regexp.MustCompile(`^[A-Za-z0-9_.-]+$`)
)

// Error means Thunderstore could not be asked, answered something the installer
// cannot use, or delivered bytes that are not what was pinned.
type Error struct{ Message string }

func (e *Error) Error() string { return e.Message }

func fail(format string, args ...any) error {
	return &Error{Message: fmt.Sprintf(format, args...)}
}

// Dependency is one package reference in the form Thunderstore spells it,
// Namespace-Name-Version.
type Dependency struct {
	Namespace string
	Name      string
	Version   string
}

// FullName is the reference as the site writes it.
func (d Dependency) FullName() string {
	return d.Namespace + "-" + d.Name + "-" + d.Version
}

// ParseDependency reads a Namespace-Name-Version reference the way the site's
// own PackageReference.parse does: the version is taken from the right first,
// then the name, so the namespace may keep hyphens and a name may keep
// underscores.
func ParseDependency(reference string) (Dependency, error) {
	notADependency := fail("%s is not a Thunderstore dependency: expected Namespace-Name-Version with a three-part version",
		strconv.Quote(reference))
	// A dotted version is one hyphen-separated part, so the tail is the version,
	// the part before it the name, and everything left over the namespace.
	parts := strings.Split(reference, "-")
	version := parts[len(parts)-1]
	if !versionPattern.MatchString(version) || len(parts) < referenceParts {
		return Dependency{}, notADependency
	}
	name := parts[len(parts)-2]
	namespace := strings.Join(parts[:len(parts)-2], "-")
	if !dependencyField.MatchString(name) || !dependencyField.MatchString(namespace) {
		return Dependency{}, notADependency
	}
	return Dependency{Namespace: namespace, Name: name, Version: version}, nil
}

// Latest is the latest object in the package endpoint's document. The site also
// answers icon, downloads, date_created, website_url and is_active, which the
// installer has no use for.
type Latest struct {
	Namespace    string
	Name         string
	Version      string
	FullName     string
	Dependencies []string
	DownloadURL  string
}

// DependsOn finds the version of one dependency, reporting false when the
// package does not declare it. A reference the site wrote badly is an error
// rather than a miss, because the installer cannot tell which version to install.
func (l Latest) DependsOn(namespace, name string) (string, bool, error) {
	for _, reference := range l.Dependencies {
		dependency, err := ParseDependency(reference)
		if err != nil {
			return "", false, fail("the %s package lists a malformed dependency: %s",
				ModName, err.Error())
		}
		if dependency.Namespace == namespace && dependency.Name == name {
			return dependency.Version, true, nil
		}
	}
	return "", false, nil
}

// Resolution is what the installer needs before it downloads anything: the
// mod's current version and where to get it, and the loader pack version that
// mod depends on with its CDN archive URL.
type Resolution struct {
	Version           string
	FullName          string
	DownloadURL       string
	Dependencies      []Dependency
	BepInExVersion    string
	BepInExArchiveURL string
	BepInExPinnedSHA  string
}

// Client talks to one Thunderstore deployment: the metadata site and the CDN.
type Client struct {
	apiBase    string
	cdnBase    string
	httpClient *http.Client
}

// NewClient builds a client for a metadata site and a CDN. A blank or unusable
// location falls back to the public one, so a mistyped
// MEGABONK_THUNDERSTORE_*_URL cannot stop an install.
func NewClient(apiBase, cdnBase string) *Client {
	return &Client{
		apiBase:    resolveBase(apiBase, DefaultAPIBaseURL),
		cdnBase:    resolveBase(cdnBase, DefaultCDNBaseURL),
		httpClient: newHTTPClient(),
	}
}

// NewClientFromEnv builds a client for the locations named by the environment,
// or the public ones when the variables are unset or blank.
func NewClientFromEnv() *Client {
	return NewClient(os.Getenv(APIBaseURLEnv), os.Getenv(CDNBaseURLEnv))
}

// HTTPClient is the client the requests go through, so a caller can adjust the
// timeout or proxy.
func (c *Client) HTTPClient() *http.Client { return c.httpClient }

// APIBase is the metadata location this client goes to.
func (c *Client) APIBase() string { return c.apiBase }

// CDNBase is the CDN this client downloads archives from.
func (c *Client) CDNBase() string { return c.cdnBase }

// MetadataURL is the package endpoint the mod's metadata is read from.
func (c *Client) MetadataURL() string {
	return c.apiBase + fmt.Sprintf(metadataSuffix, ModNamespace, ModName)
}

// ArchiveURL is the CDN location of one package version's archive.
func (c *Client) ArchiveURL(namespace, name, version string) string {
	return CDNPackageURL(c.cdnBase, namespace, name, version)
}

// CDNPackageURL is the CDN location of one package version's archive.
func CDNPackageURL(cdnBase, namespace, name, version string) string {
	return resolveBase(cdnBase, DefaultCDNBaseURL) + fmt.Sprintf(ArchiveSuffix, namespace, name, version)
}

// Resolve reads the mod's latest version, its download URL, and the loader pack
// version it depends on.
func (c *Client) Resolve() (*Resolution, error) {
	body, err := c.get(c.MetadataURL(), MaxMetadataBytes, func(response *http.Response) error {
		return &Error{Message: fmt.Sprintf("Thunderstore answered %d for %s: %s",
			response.StatusCode, ModNamespace+"/"+ModName, errorBody(response.Body))}
	})
	if err != nil {
		return nil, err
	}
	latest, err := decodeLatest(body)
	if err != nil {
		return nil, err
	}
	bepinexVersion, found, err := latest.DependsOn(BepInExNamespace, BepInExName)
	if err != nil {
		return nil, err
	}
	if !found {
		return nil, fail("%s %s does not depend on %s-%s, so the loader pack version cannot be resolved",
			ModNamespace+"/"+ModName, latest.Version, BepInExNamespace, BepInExName)
	}
	resolution := &Resolution{
		Version:           latest.Version,
		FullName:          latest.FullName,
		DownloadURL:       latest.DownloadURL,
		BepInExVersion:    bepinexVersion,
		BepInExArchiveURL: c.ArchiveURL(BepInExNamespace, BepInExName, bepinexVersion),
	}
	if digest, pinned := PinnedBepInExDigest(bepinexVersion); pinned {
		resolution.BepInExPinnedSHA = digest
	}
	for _, reference := range latest.Dependencies {
		dependency, depErr := ParseDependency(reference)
		if depErr != nil {
			return nil, depErr
		}
		resolution.Dependencies = append(resolution.Dependencies, dependency)
	}
	return resolution, nil
}

// Downloaded is one archive sitting on disk, verified against the digest it was
// fetched for.
type Downloaded struct {
	Path      string
	URL       string
	Version   string
	SHA256    string
	Size      int64
	FromCache bool
}

// DownloadBepInEx puts the loader pack archive for one version at target,
// fetching it from the CDN when it is not already there intact. The digest is
// mandatory: an archive that does not match it is discarded before anything is
// installed, and so is one whose members do not sit under BepInExPack/.
func (c *Client) DownloadBepInEx(version, expectedSHA256, target string) (*Downloaded, error) {
	if !versionPattern.MatchString(version) {
		return nil, fail("%s is not a loader pack version: expected a three-part version", strconv.Quote(version))
	}
	digest := strings.ToLower(strings.TrimSpace(expectedSHA256))
	if !hex64.MatchString(digest) {
		return nil, fail("no SHA-256 is pinned for %s-%s %s, so its archive cannot be verified",
			BepInExNamespace, BepInExName, version)
	}
	if err := checkTargetPath(target); err != nil {
		return nil, err
	}
	archiveURL := c.ArchiveURL(BepInExNamespace, BepInExName, version)
	if existing, err := verifiedFile(target, digest); err == nil {
		return existing, nil
	}
	if err := os.MkdirAll(ppath.Parent(target), 0o755); err != nil {
		return nil, fail("cannot create the folder for %s: %s", target, err.Error())
	}
	body, err := c.get(archiveURL, MaxArchiveBytes, func(response *http.Response) error {
		return &Error{Message: fmt.Sprintf("Thunderstore answered %d for the %s %s archive: %s",
			response.StatusCode, BepInExName, version, errorBody(response.Body))}
	})
	if err != nil {
		return nil, err
	}
	if err := CheckDigest(body, digest); err != nil {
		return nil, err
	}
	if err := checkPackLayout(body, BepInExName+" "+version); err != nil {
		return nil, err
	}
	if err := writeVerified(target, body); err != nil {
		return nil, err
	}
	return &Downloaded{Path: target, URL: archiveURL, Version: version, SHA256: digest, Size: int64(len(body))}, nil
}

// checkTargetPath accepts only a plain file path: every component names a real
// file or folder, so no ".." can climb out of the folder the caller meant and
// "." cannot stand in for the file name itself.
func checkTargetPath(target string) error {
	if strings.TrimSpace(target) == "" {
		return fail("no target path was given for the %s archive", PackRoot)
	}
	if strings.ContainsRune(target, 0) || strings.ContainsAny(target, "\\:") {
		return fail("%s is not a usable archive path", strconv.Quote(target))
	}
	// Clean would collapse "a/../b" to "b" and hide the climb, so the raw path
	// is what gets inspected. An absolute path's leading slash shows up as an
	// empty first part and is not a name.
	for index, part := range strings.Split(filepath.ToSlash(target), "/") {
		if index == 0 && part == "" {
			continue
		}
		if part == "." || part == ".." {
			return fail("%s is not a usable archive path: it must name a file inside one folder",
				strconv.Quote(target))
		}
		if part == "" || !safeName.MatchString(part) {
			return fail("%s is not a usable archive path: %s is not a valid file or folder name",
				strconv.Quote(target), strconv.Quote(part))
		}
	}
	return nil
}

// PinnedBepInExDigest is the known-good SHA-256 of one loader pack version.
func PinnedBepInExDigest(version string) (string, bool) {
	digest, ok := bepinexPins[strings.TrimSpace(version)]
	return digest, ok
}

// CheckDigest reports whether bytes carry the digest they were downloaded for.
func CheckDigest(body []byte, expectedSHA256 string) error {
	want := strings.ToLower(strings.TrimSpace(expectedSHA256))
	if !hex64.MatchString(want) {
		return fail("the expected SHA-256 %s is not 64 hex characters", strconv.Quote(expectedSHA256))
	}
	sum := sha256.Sum256(body)
	got := hex.EncodeToString(sum[:])
	if got != want {
		return fail("checksum mismatch: the %s-%s archive has SHA-256 %s, expected %s; nothing was installed",
			BepInExNamespace, BepInExName, got, want)
	}
	return nil
}

// decodeLatest reads the latest object out of the package document. The status
// has already been checked, so anything that is not the expected JSON object
// reads as a broken response rather than as a missing package.
func decodeLatest(body []byte) (*Latest, error) {
	var document struct {
		Namespace string `json:"namespace"`
		Name      string `json:"name"`
		Latest    *struct {
			Namespace    string   `json:"namespace"`
			Name         string   `json:"name"`
			Version      string   `json:"version_number"`
			FullName     string   `json:"full_name"`
			Dependencies []string `json:"dependencies"`
			DownloadURL  string   `json:"download_url"`
		} `json:"latest"`
	}
	if err := json.Unmarshal(body, &document); err != nil {
		return nil, fail("Thunderstore did not answer with a JSON object for %s/%s: %s",
			ModNamespace, ModName, clip(err.Error()))
	}
	if document.Latest == nil {
		return nil, fail("the Thunderstore document for %s/%s has no latest version", ModNamespace, ModName)
	}
	latest := document.Latest
	if !versionPattern.MatchString(latest.Version) {
		return nil, fail("the latest version of %s/%s is %s, which is not a three-part version",
			ModNamespace, ModName, strconv.Quote(latest.Version))
	}
	if strings.TrimSpace(latest.DownloadURL) == "" {
		return nil, fail("the latest version of %s/%s has no download_url", ModNamespace, ModName)
	}
	if _, err := url.ParseRequestURI(latest.DownloadURL); err != nil {
		return nil, fail("the download_url of %s/%s %s is not a URL: %s",
			ModNamespace, ModName, latest.Version, clip(err.Error()))
	}
	if len(latest.Dependencies) == 0 {
		return nil, fail("the latest version of %s/%s lists no dependencies", ModNamespace, ModName)
	}
	name := latest.Name
	if name == "" {
		name = document.Name
	}
	namespace := latest.Namespace
	if namespace == "" {
		namespace = document.Namespace
	}
	fullName := latest.FullName
	if fullName == "" {
		fullName = namespace + "-" + name + "-" + latest.Version
	}
	return &Latest{
		Namespace:    namespace,
		Name:         name,
		Version:      latest.Version,
		FullName:     fullName,
		Dependencies: latest.Dependencies,
		DownloadURL:  latest.DownloadURL,
	}, nil
}

// checkPackLayout makes sure the archive is a loader pack rather than something
// else served at that URL: every member sits under BepInExPack/ and no name
// climbs out of it.
func checkPackLayout(body []byte, what string) error {
	reader, err := zip.NewReader(bytes.NewReader(body), int64(len(body)))
	if err != nil {
		return fail("the %s archive is not a readable zip: %s", what, clip(err.Error()))
	}
	seen := 0
	for _, member := range reader.File {
		name := filepath.ToSlash(member.Name)
		if !strings.HasPrefix(name, packArchiveName) {
			return fail("the %s archive puts %s outside %s/", what, strconv.Quote(member.Name), PackRoot)
		}
		relative := strings.TrimPrefix(name, packArchiveName)
		if relative == "" || strings.HasPrefix(relative, "/") || strings.Contains(relative, "\\") ||
			strings.Contains(relative, ":") || climbsOut(relative) {
			return fail("the %s archive carries an unsafe member name: %s", what, strconv.Quote(member.Name))
		}
		seen++
	}
	if seen == 0 {
		return fail("the %s archive has no files under %s/", what, PackRoot)
	}
	return nil
}

// climbsOut reports whether a member name walks up out of the pack folder.
func climbsOut(relative string) bool {
	for _, part := range strings.Split(relative, "/") {
		if part == ".." {
			return true
		}
	}
	return false
}

// verifiedFile is the archive already at path when it carries the digest, so a
// second run does not refetch it.
func verifiedFile(path, digest string) (*Downloaded, error) {
	body, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	if err := CheckDigest(body, digest); err != nil {
		return nil, err
	}
	if err := checkPackLayout(body, "cached "+BepInExName); err != nil {
		return nil, err
	}
	return &Downloaded{Path: path, Version: "", SHA256: digest, Size: int64(len(body)), FromCache: true}, nil
}

// writeVerified puts the verified bytes at path through a temporary file, so a
// failed write never leaves a half archive where the installer would use it.
func writeVerified(path string, body []byte) error {
	temporary := path + tempSuffix
	if err := writeTemporary(temporary, body); err != nil {
		return err
	}
	if err := os.Rename(temporary, path); err != nil {
		discard(temporary)
		return fail("cannot put %s in place: %s", path, err.Error())
	}
	return nil
}

// writeTemporary writes the whole body to a fresh file at path, which is left
// behind only when the bytes landed there intact.
func writeTemporary(path string, body []byte) error {
	handle, err := os.OpenFile(path, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, 0o644)
	if err != nil {
		return fail("cannot write %s: %s", path, err.Error())
	}
	written, writeErr := handle.Write(body)
	closeErr := handle.Close()
	if writeErr != nil {
		discard(path)
		return fail("cannot write %s: %s", path, writeErr.Error())
	}
	if closeErr != nil {
		discard(path)
		return fail("cannot finish writing %s: %s", path, closeErr.Error())
	}
	if written != len(body) {
		discard(path)
		return fail("%s was written short: %d of %d bytes", path, written, len(body))
	}
	return nil
}

// discard removes a temporary file, whose absence is the outcome either way.
func discard(path string) { _ = os.Remove(path) }

// get fetches a body, checking the status before it is read so a 404 or a
// Cloudflare error page reads as what it is rather than as corrupt data.
func (c *Client) get(requestURL string, limit int64, classify func(response *http.Response) error) ([]byte, error) {
	request, err := http.NewRequest(http.MethodGet, requestURL, nil)
	if err != nil {
		return nil, err
	}
	request.Header.Set("User-Agent", UserAgent)
	request.Header.Set("Accept", "application/json, application/zip, */*")
	response, err := c.httpClient.Do(request)
	if err != nil {
		return nil, fail("cannot reach %s: %s", requestURL, clip(err.Error()))
	}
	defer response.Body.Close()
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		return nil, classify(response)
	}
	body, err := io.ReadAll(io.LimitReader(response.Body, limit+1))
	if err != nil {
		return nil, fail("%s closed the connection while downloading: %s", requestURL, clip(err.Error()))
	}
	if int64(len(body)) > limit {
		return nil, fail("%s is larger than the %d MB the installer will hold in memory",
			requestURL, limit>>20)
	}
	return body, nil
}

// errorBody keeps a short piece of an error response for the message.
func errorBody(body io.Reader) string {
	limited, err := io.ReadAll(io.LimitReader(body, MaxErrorBodyBytes))
	if err != nil || len(limited) == 0 {
		return "no explanation"
	}
	return clip(strings.Join(strings.Fields(string(limited)), " "))
}

func clip(text string) string {
	if len(text) <= maxErrorRunes {
		return text
	}
	return text[:maxErrorRunes] + "..."
}

// normalizeBase canonicalises a location: a missing scheme gets https, a
// trailing slash is dropped, and anything that is not a plain http or https
// origin is refused so a bad setting cannot point the installer at a file.
func normalizeBase(raw string) (string, error) {
	candidate := strings.TrimSpace(raw)
	if candidate == "" {
		return "", fail("no Thunderstore location was given")
	}
	if !strings.Contains(candidate, "://") {
		candidate = "https://" + candidate
	}
	parsed, err := url.Parse(candidate)
	if err != nil {
		return "", fail("%s is not a valid Thunderstore location: %s", strconv.Quote(raw), clip(err.Error()))
	}
	if parsed.Scheme != "http" && parsed.Scheme != "https" {
		return "", fail("%s is not an http or https Thunderstore location", strconv.Quote(raw))
	}
	if parsed.Host == "" {
		return "", fail("%s has no Thunderstore host", strconv.Quote(raw))
	}
	if parsed.User != nil || parsed.RawQuery != "" || parsed.Fragment != "" {
		return "", fail("%s must be a plain Thunderstore origin", strconv.Quote(raw))
	}
	return strings.TrimRight(parsed.String(), "/"), nil
}

// resolveBase is the location to use, which is the public one when the
// configured value is blank or not a usable origin.
func resolveBase(raw, fallback string) string {
	normalized, err := normalizeBase(raw)
	if err != nil || normalized == "" {
		return fallback
	}
	return normalized
}

func newHTTPClient() *http.Client {
	return &http.Client{
		Timeout: requestTimeout,
		// Resolved when the request goes out, so a test can substitute
		// http.DefaultTransport and prove nothing reaches the network.
		Transport: transportFunc(func(request *http.Request) (*http.Response, error) {
			return http.DefaultTransport.RoundTrip(request)
		}),
		CheckRedirect: func(request *http.Request, via []*http.Request) error {
			if len(via) >= 10 {
				return fail("too many redirects")
			}
			if len(via) > 0 && strings.EqualFold(via[0].URL.Host, request.URL.Host) {
				return nil
			}
			return fail("refused a redirect off the Thunderstore host to %s", request.URL.Host)
		},
	}
}

type transportFunc func(request *http.Request) (*http.Response, error)

func (f transportFunc) RoundTrip(request *http.Request) (*http.Response, error) { return f(request) }
