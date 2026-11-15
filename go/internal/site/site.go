// Package site talks to the megabonkmod.party API: it turns what a player
// pastes into the level file, pictures and asset packs that level needs.
package site

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"
)

const (
	// DefaultBaseURL is the production API.
	DefaultBaseURL = "https://api.megabonkmod.party"
	// BaseURLEnv names the environment variable that overrides the API location.
	BaseURLEnv = "MEGABONK_API_URL"
	// SiteHost is the host a player's link is accepted from.
	SiteHost = "megabonkmod.party"

	// ExampleCode is a real share code, used wherever the installer shows the
	// player what an input looks like.
	ExampleCode = "7N1-MVB-WKF"

	// LevelDownloadSuffix is the counting route for a level file.
	LevelDownloadSuffix = "/api/l/%s/download"
	// PackDownloadSuffix is the route that zips one pack version.
	PackDownloadSuffix = "/api/p/%s/download"
	// FileSuffix is where PocketBase serves a record's uploaded file.
	FileSuffix = "/api/files/%s/%s/%s"
	// RecordsSuffix is the list endpoint the metadata lookup goes through.
	RecordsSuffix = "/api/collections/levels/records"

	collectionLevels    = "levels"
	packPlatform        = "windows"
	levelFileSuffix     = ".mblevel.json"
	userAgent           = "megabonk-installer"
	maxResponseBytes    = 32 << 20
	maxErrorBodyBytes   = 8 << 10
	maxErrorDetailRunes = 200
	notFoundMessage     = "level not found"
)

// shareCodePattern is the code pattern the levels collection enforces.
var shareCodePattern = regexp.MustCompile(`^[0-9A-HJKMNP-TV-Z]{3}-[0-9A-HJKMNP-TV-Z]{3}-[0-9A-HJKMNP-TV-Z]{3}$`)

var packIDPattern = regexp.MustCompile(`^[a-z0-9][a-z0-9_-]{0,63}$`)

var notAllowed = regexp.MustCompile(`[^a-zA-Z0-9.\-]`)

// Error is anything the player needs to read from the API.
type Error struct{ message string }

func (e *Error) Error() string { return e.message }

func fail(format string, args ...any) error {
	return &Error{message: fmt.Sprintf(format, args...)}
}

// NotFoundError means no level answers to that share code, hidden or never created.
type NotFoundError struct {
	Code    string
	Message string
}

func (e *NotFoundError) Error() string {
	message := notFoundMessage
	if e.Code != "" {
		message += ": " + e.Code
	}
	return withDetail(message, e.Message)
}

// PackNotHostedError means the site has no archive for that pack version.
type PackNotHostedError struct {
	PackID  string
	Version string
	Message string
}

func (e *PackNotHostedError) Error() string {
	message := "pack " + e.PackID + " is not hosted on " + SiteHost
	if e.Version != "" {
		message += " version " + e.Version
	}
	return withDetail(message, e.Message)
}

func withDetail(message, detail string) string {
	if detail == "" {
		return message
	}
	return message + ": " + detail
}

// PackNotHosted tells callers this is a missing pack, not an unreachable site.
func (e *PackNotHostedError) PackNotHosted() bool { return true }

// RateLimitedError means the API asked for fewer requests.
type RateLimitedError struct {
	Path    string
	Seconds int
}

func (e *RateLimitedError) Error() string {
	if e.Seconds > 0 {
		return "the " + SiteHost + " API is busy: too many requests for " + e.Path +
			". Wait " + strconv.Itoa(e.Seconds) + " second(s) and retry."
	}
	return "the " + SiteHost + " API is busy: too many requests for " + e.Path + ". Wait a moment and retry."
}

// RateLimited lets callers test for a rate limit without naming the type.
func (e *RateLimitedError) RateLimited() bool { return true }

// HTTPError is an API response that is neither a missing record nor a rate limit.
type HTTPError struct {
	Status  int
	Path    string
	Message string
}

func (e *HTTPError) Error() string {
	return withDetail("the "+SiteHost+" API answered "+strconv.Itoa(e.Status)+" for "+e.Path, e.Message)
}

// Level is one gallery level, with everything needed to install it.
type Level struct {
	ID        string
	Code      string
	Title     string
	LevelFile string
	Cover     string
	Biome     string
	Slug      string
	Packs     map[string]string

	client *Client
}

// Filename is the level's file on disk: the stored file name when the record
// has one, otherwise the slug of its title.
func (l *Level) Filename() string {
	if l.LevelFile != "" {
		return l.LevelFile
	}
	return l.Slug + levelFileSuffix
}

// CoverURL is where the cover picture is served, or "" when the level has none.
func (l *Level) CoverURL() string { return l.fileURL(l.Cover) }

// BiomeURL is where the biome picture is served, or "" when the level has none.
func (l *Level) BiomeURL() string { return l.fileURL(l.Biome) }

func (l *Level) fileURL(name string) string {
	if l.ID == "" || name == "" || l.client == nil {
		return ""
	}
	return l.client.baseURL + fmt.Sprintf(FileSuffix, collectionLevels, l.ID, notAllowed.ReplaceAllString(name, ""))
}

// DownloadURL is the counting route for the level file.
func (l *Level) DownloadURL() string {
	if l.client == nil {
		return ""
	}
	return l.client.baseURL + fmt.Sprintf(LevelDownloadSuffix, url.PathEscape(l.Code))
}

// Download fetches the level file through the counting route, never the raw file path.
func (l *Level) Download() ([]byte, error) {
	if l.Code == "" || l.client == nil {
		return nil, fail("cannot download a level without a share code")
	}
	return l.client.request(l.DownloadURL(), func(response *http.Response) error {
		if response.StatusCode == http.StatusNotFound {
			return &NotFoundError{Code: l.Code, Message: serverMessage(response.Body)}
		}
		return responseError(response)
	})
}

// DownloadLevel gets one level file by share code through the counting route.
func (c *Client) DownloadLevel(input string) ([]byte, error) {
	level, err := c.LookupLevel(input)
	if err != nil {
		return nil, err
	}
	return level.Download()
}

// Client talks to one API location.
type Client struct {
	baseURL    string
	httpClient *http.Client
}

// HTTPClient is the client the requests go through, so a caller can adjust the
// timeout or proxy.
func (c *Client) HTTPClient() *http.Client { return c.httpClient }

// NewClient builds a client for a base URL such as https://api.megabonkmod.party.
func NewClient(baseURL string) *Client {
	normalised, err := NormalizeBaseURL(baseURL)
	if err != nil {
		normalised = DefaultBaseURL
	}
	return &Client{baseURL: normalised, httpClient: newHTTPClient()}
}

// NewClientFromEnv builds a client for MEGABONK_API_URL, or the default.
func NewClientFromEnv() *Client { return NewClient(EnvBaseURL()) }

// BaseURL is the API location this client goes to.
func (c *Client) BaseURL() string { return c.baseURL }

// withClient attaches a client to a level built by hand, the way the tests do.
func (c *Client) withClient(level *Level) *Level {
	level.client = c
	return level
}

// EnvBaseURL is the API location named by the environment, or the default.
func EnvBaseURL() string {
	if text := strings.TrimSpace(os.Getenv(BaseURLEnv)); text != "" {
		return text
	}
	return DefaultBaseURL
}

// NormalizeBaseURL canonicalises an API location, refusing anything that is not a
// plain http or https origin.
func NormalizeBaseURL(raw string) (string, error) {
	text := strings.TrimSpace(raw)
	if text == "" {
		return DefaultBaseURL, nil
	}
	candidate := text
	if !strings.Contains(candidate, "://") {
		candidate = "https://" + candidate
	}
	parsed, err := url.Parse(candidate)
	if err != nil {
		return "", fail("%s is not a valid API URL: %s", strconv.Quote(text), err.Error())
	}
	if parsed.Scheme != "http" && parsed.Scheme != "https" {
		return "", fail("%s is not a valid API URL: expected http or https", strconv.Quote(text))
	}
	if parsed.Host == "" {
		return "", fail("%s is not a valid API URL: no host", strconv.Quote(text))
	}
	if parsed.Path != "" && parsed.Path != "/" {
		return "", fail("%s points at a path; %s wants the API's origin only", strconv.Quote(text), BaseURLEnv)
	}
	if parsed.RawQuery != "" || parsed.Fragment != "" {
		return "", fail("%s carries a query or fragment; %s wants the API's origin only", strconv.Quote(text), BaseURLEnv)
	}
	return parsed.Scheme + "://" + parsed.Host, nil
}

// NormalizeCode turns a code or a site level link into the canonical share code.
func NormalizeCode(input string) (string, error) {
	text := strings.TrimSpace(input)
	if text == "" {
		return "", fail("no share code given: pass a code such as " + ExampleCode + ", a " +
			SiteHost + "/l/<code> link, or a " + SiteHost + "/levels/view/?code=<code> link")
	}
	if looksLikeLink(text) {
		return codeFromURL(text)
	}
	if code := formatCode(text); code != "" {
		return code, nil
	}
	return "", fail("%s is not a level: pass a share code such as "+ExampleCode+", "+
		SiteHost+"/l/<code> link, or a "+SiteHost+"/levels/view/?code=<code> link", strconv.Quote(input))
}

// looksLikeLink reports whether the input names a site rather than a bare code.
func looksLikeLink(text string) bool {
	if strings.Contains(text, "://") {
		return true
	}
	first := strings.SplitN(text, "/", 2)[0]
	return strings.Contains(first, ".") || strings.HasPrefix(text, "/")
}

func codeFromURL(text string) (string, error) {
	candidate := text
	if !strings.Contains(candidate, "://") {
		candidate = "https://" + candidate
	}
	parsed, err := url.Parse(candidate)
	if err != nil {
		return "", fail("%s is not a valid link: %s", strconv.Quote(text), err.Error())
	}
	host := strings.ToLower(parsed.Hostname())
	if host != SiteHost && host != "www."+SiteHost {
		return "", fail("%s is not a %s level link: it points at %s, so there is no share code to read. "+
			"Pass a code such as "+ExampleCode+" or a https://%s/l/<code> link.",
			strconv.Quote(text), SiteHost, orNone(host), SiteHost)
	}
	path := strings.TrimSuffix(parsed.EscapedPath(), "/")
	if strings.HasPrefix(path, "/l/") {
		code := formatCode(strings.TrimPrefix(path, "/l/"))
		if code == "" {
			return "", fail("%s is not a level link: %s is not a share code",
				strconv.Quote(text), strconv.Quote(strings.TrimPrefix(path, "/l/")))
		}
		return code, nil
	}
	if path != "/levels/view" {
		return "", fail("%s is not a level link on %s: expected /l/<share code> or /levels/view/?code=<share code>",
			strconv.Quote(text), SiteHost)
	}
	code := formatCode(parsed.Query().Get("code"))
	if code == "" {
		return "", fail("%s has no share code in its ?code= parameter", strconv.Quote(text))
	}
	return code, nil
}

func orNone(text string) string {
	if text == "" {
		return "another host"
	}
	return text
}

// formatCode canonicalises a code, or "" when it is not one.
func formatCode(raw string) string {
	compact := strings.ReplaceAll(strings.ToUpper(strings.TrimSpace(raw)), "-", "")
	if len(compact) != 9 {
		return ""
	}
	canonical := compact[:3] + "-" + compact[3:6] + "-" + compact[6:]
	if !shareCodePattern.MatchString(canonical) {
		return ""
	}
	return canonical
}

// Slug is the level's file name stem: the same slug the site stores its level
// file under (slugify in pocketbase/pb_hooks/level_lib.js).
func Slug(title string) string {
	slug := strings.Map(keepSlugRune, strings.ToLower(title))
	for strings.Contains(slug, "--") {
		slug = strings.ReplaceAll(slug, "--", "-")
	}
	slug = strings.Trim(slug, "-")
	if slug == "" {
		return "level"
	}
	return slug
}

// keepSlugRune keeps what JS [^a-z0-9]+ survives; everything else becomes a hyphen.
func keepSlugRune(r rune) rune {
	if (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') {
		return r
	}
	return '-'
}

// LookupLevel fetches a level's metadata by share code.
func (c *Client) LookupLevel(input string) (*Level, error) {
	code, err := NormalizeCode(input)
	if err != nil {
		return nil, err
	}
	path := RecordsSuffix + "?filter=" + url.QueryEscape("(code='"+code+"')")
	body, err := c.request(c.baseURL+path, func(response *http.Response) error {
		if response.StatusCode == http.StatusNotFound || response.StatusCode == http.StatusForbidden {
			return &NotFoundError{Code: code, Message: serverMessage(response.Body)}
		}
		return responseError(response)
	})
	if err != nil {
		return nil, err
	}
	level, err := levelFromDocument(body, code)
	if err != nil {
		return nil, err
	}
	level.client = c
	return level, nil
}

// DownloadPack fetches one pack version as the zip that unpacks into UserData/LevelPacks/.
func (c *Client) DownloadPack(packID, version string) ([]byte, error) {
	if !packIDPattern.MatchString(packID) {
		return nil, fail("%s is not a pack id: use 1 to 64 characters of lowercase letters, digits, '_', or '-'",
			strconv.Quote(packID))
	}
	origin := c.baseURL + fmt.Sprintf(PackDownloadSuffix, url.PathEscape(packID))
	requestURL := origin + "?platform=" + packPlatform
	if version != "" {
		requestURL += "&version=" + url.QueryEscape(version)
	}
	return c.request(requestURL, func(response *http.Response) error {
		if response.StatusCode == http.StatusNotFound {
			return &PackNotHostedError{PackID: packID, Version: version, Message: serverMessage(response.Body)}
		}
		return responseError(response)
	})
}

// responseError turns a failed response into the error the player should see.
func responseError(response *http.Response) error {
	if response.StatusCode == http.StatusTooManyRequests {
		return &RateLimitedError{
			Path:    response.Request.URL.Path,
			Seconds: retryAfterSeconds(response),
		}
	}
	return &HTTPError{
		Status:  response.StatusCode,
		Path:    response.Request.URL.Path,
		Message: serverMessage(response.Body),
	}
}

// retryAfterSeconds reads the seconds from a Retry-After header, ignoring an
// HTTP-date form the player cannot act on more precisely than "a moment".
func retryAfterSeconds(response *http.Response) int {
	text := strings.TrimSpace(response.Header.Get("Retry-After"))
	seconds, err := strconv.Atoi(text)
	if err != nil || seconds < 0 {
		return 0
	}
	return seconds
}

// serverMessage returns the message a PocketBase handler sent with its body.
func serverMessage(body io.Reader) string {
	limited, err := io.ReadAll(io.LimitReader(body, maxErrorBodyBytes))
	if err != nil || len(limited) == 0 {
		return ""
	}
	var document map[string]any
	if err := json.Unmarshal(limited, &document); err != nil {
		return clipText(string(limited))
	}
	if message := textField(document, "message"); message != "" {
		return clipText(message)
	}
	for _, value := range document {
		if field, ok := value.(map[string]any); ok {
			if message := textField(field, "message"); message != "" {
				return clipText(message)
			}
		}
	}
	return ""
}

func clipText(text string) string {
	text = strings.Join(strings.Fields(text), " ")
	if len(text) <= maxErrorDetailRunes {
		return text
	}
	return text[:maxErrorDetailRunes] + "..."
}

func newHTTPClient() *http.Client {
	return &http.Client{
		Timeout: 2 * time.Minute,
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
			return fail("refused a redirect off the API host to %s", request.URL.Host)
		},
	}
}

// request gets a body, checking the status before the body is read.
func (c *Client) request(requestURL string, classify func(response *http.Response) error) ([]byte, error) {
	request, err := http.NewRequest(http.MethodGet, requestURL, nil)
	if err != nil {
		return nil, err
	}
	request.Header.Set("Accept", "application/json, application/zip, */*")
	request.Header.Set("User-Agent", userAgent)
	response, err := c.httpClient.Do(request)
	if err != nil {
		return nil, fail("cannot reach the %s API at %s: %s", SiteHost, c.baseURL, err.Error())
	}
	defer response.Body.Close()
	path := request.URL.Path
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		return nil, classify(response)
	}
	body, err := io.ReadAll(io.LimitReader(response.Body, maxResponseBytes+1))
	if err != nil {
		return nil, fail("the %s API closed the connection while downloading %s: %s", SiteHost, path, err.Error())
	}
	if len(body) > maxResponseBytes {
		return nil, fail("%s is larger than the %d MB the installer will hold in memory", path, maxResponseBytes>>20)
	}
	return body, nil
}

type transportFunc func(request *http.Request) (*http.Response, error)

func (f transportFunc) RoundTrip(request *http.Request) (*http.Response, error) { return f(request) }

// levelFromDocument reads the record out of PocketBase's list envelope.
func levelFromDocument(body []byte, code string) (*Level, error) {
	document, err := decodeObject(body)
	if err != nil {
		return nil, fail("the %s API did not return a JSON object for %s: %s", SiteHost, code, err.Error())
	}
	items, ok := arrayField(document, "items")
	if !ok {
		return nil, fail("the %s API returned no 'items' list for %s", SiteHost, code)
	}
	if len(items) == 0 {
		return nil, &NotFoundError{Code: code}
	}
	record, ok := objectField(items[0])
	if !ok {
		return nil, fail("the " + SiteHost + " API returned a level that is not a JSON object")
	}
	level := &Level{
		ID:        textField(record, "id"),
		Code:      code,
		Title:     textField(record, "title"),
		LevelFile: textField(record, "level"),
		Cover:     textField(record, "cover"),
		Biome:     textField(record, "biome"),
	}
	// A lookup by file name asks for the code in the same request, so the caller
	// can still take the counting download route rather than the raw file path.
	if level.Code == "" {
		level.Code = textField(record, "code")
	}
	level.Slug = Slug(level.Title)
	if level.ID == "" || level.LevelFile == "" {
		return nil, fail("the level record for %s is missing its id or level file", code)
	}
	level.Packs = packsField(record)
	return level, nil
}

// packsField reads the pack id to version map, ignoring entries that are not strings.
func packsField(record map[string]any) map[string]string {
	packs, ok := objectField(record["packs"])
	if !ok {
		return map[string]string{}
	}
	versions := make(map[string]string, len(packs))
	for id, raw := range packs {
		if version, ok := raw.(string); ok && version != "" {
			versions[id] = version
		}
	}
	return versions
}

// PackIDs lists the required pack ids in sorted order.
func (l *Level) PackIDs() []string {
	ids := make([]string, 0, len(l.Packs))
	for id := range l.Packs {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	return ids
}

func decodeObject(body []byte) (map[string]any, error) {
	var document any
	if err := json.Unmarshal(body, &document); err != nil {
		return nil, err
	}
	object, ok := document.(map[string]any)
	if !ok {
		return nil, fail("the document is not a JSON object")
	}
	return object, nil
}

func objectField(value any) (map[string]any, bool) {
	object, ok := value.(map[string]any)
	return object, ok
}

func arrayField(object map[string]any, key string) ([]any, bool) {
	items, ok := object[key].([]any)
	return items, ok
}

func textField(object map[string]any, key string) string {
	text, _ := object[key].(string)
	return text
}

// levelFileName is the shape a stored level file name keeps to be worth asking
// the server about.
var levelFileName = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._ -]{0,120}$`)

// safeLevelFileName accepts one file name, with no path in it, that is worth
// asking the server about.
func safeLevelFileName(filename string) (string, error) {
	name := strings.TrimSpace(filename)
	if !levelFileName.MatchString(name) || strings.ContainsAny(name, "/\\") ||
		strings.Contains(name, "..") {
		return "", fail("%s is not a level file name: expected a file name such as my-level.mblevel.json",
			strconv.Quote(filename))
	}
	return name, nil
}

// LookupLevelByFilename finds the hosted record whose stored level file carries
// the name a player's local file has, so its packs can be installed too.
func (c *Client) LookupLevelByFilename(filename string) (*Level, error) {
	name, err := safeLevelFileName(filename)
	if err != nil {
		return nil, err
	}
	requestURL := c.baseURL + RecordsSuffix + "?filter=" + url.QueryEscape("(level='"+name+"')")
	body, err := c.request(requestURL, func(response *http.Response) error {
		if response.StatusCode == http.StatusNotFound || response.StatusCode == http.StatusForbidden {
			return &NotFoundError{Message: serverMessage(response.Body)}
		}
		return responseError(response)
	})
	if err != nil {
		return nil, err
	}
	level, err := levelFromDocument(body, "")
	if err != nil {
		return nil, err
	}
	return c.withClient(level), nil
}

// DownloadFile gets one file the API serves, such as a level's cover picture. The
// URL has to be on this client's API host.
func (c *Client) DownloadFile(fileURL string) ([]byte, error) {
	parsed, err := url.Parse(strings.TrimSpace(fileURL))
	if err != nil || parsed.Scheme != "https" && parsed.Scheme != "http" || parsed.Host == "" {
		return nil, fail("%s is not a file URL the %s API serves", strconv.Quote(fileURL), SiteHost)
	}
	if !sameAPIHost(parsed.Host, c.baseURL) {
		return nil, fail("%s is not served by the %s API at %s", strconv.Quote(fileURL), SiteHost, c.baseURL)
	}
	return c.request(parsed.String(), responseError)
}

// sameAPIHost reports whether a host is the one the client's API lives on.
func sameAPIHost(host, baseURL string) bool {
	origin, err := NormalizeBaseURL(baseURL)
	if err != nil {
		return false
	}
	return strings.EqualFold(host, strings.TrimPrefix(strings.TrimPrefix(origin, "https://"), "http://"))
}

// PackDownloadURL is where one pack version's archive is served.
func (c *Client) PackDownloadURL(packID, version string) string {
	origin := c.baseURL + fmt.Sprintf(PackDownloadSuffix, url.PathEscape(packID))
	requestURL := origin + "?platform=" + packPlatform
	if version != "" {
		requestURL += "&version=" + url.QueryEscape(version)
	}
	return requestURL
}

// IsNotFound reports a level the player cannot see, whether it never existed or
// is hidden.
func IsNotFound(err error) bool {
	var notFound *NotFoundError
	return errors.As(err, &notFound)
}

// IsPackNotHosted reports a pack the site does not offer, as distinct from the
// site being unreachable.
func IsPackNotHosted(err error) bool {
	var notHosted *PackNotHostedError
	return errors.As(err, &notHosted)
}
