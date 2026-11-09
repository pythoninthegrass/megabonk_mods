// Package vdf reads Valve's KeyValues (.vdf) format, enough to inspect
// Steam's own files. The installer never writes them: Steam rewrites
// localconfig.vdf while it runs.
package vdf

import (
	"fmt"
	"os"
	"strconv"
	"strings"
	"unicode/utf8"
)

type entry struct {
	key   string
	value any
}

// Dict is an insertion-ordered KeyValues object; find_all walks values in
// file order, so the order Python's dict keeps is part of the contract.
type Dict struct {
	entries []entry
	index   map[string]int
}

func newDict() *Dict {
	return &Dict{index: map[string]int{}}
}

func (d *Dict) Set(key string, value any) {
	if at, ok := d.index[key]; ok {
		d.entries[at].value = value
		return
	}
	d.index[key] = len(d.entries)
	d.entries = append(d.entries, entry{key: key, value: value})
}

func (d *Dict) Get(key string) (any, bool) {
	if at, ok := d.index[key]; ok {
		return d.entries[at].value, true
	}
	return nil, false
}

func (d *Dict) Keys() []string {
	keys := make([]string, 0, len(d.entries))
	for _, e := range d.entries {
		keys = append(keys, e.key)
	}
	return keys
}

func (d *Dict) Values() []any {
	values := make([]any, 0, len(d.entries))
	for _, e := range d.entries {
		values = append(values, e.value)
	}
	return values
}

func tokenize(text string) ([]string, error) {
	var tokens []string
	index := 0
	length := len(text)
	for index < length {
		char := text[index]
		if char == ' ' || char == '\t' || char == '\r' || char == '\n' {
			index++
			continue
		}
		if char == '{' || char == '}' {
			tokens = append(tokens, string(char))
			index++
			continue
		}
		if char == '"' {
			end := strings.IndexByte(text[index+1:], '"')
			if end != -1 {
				end += index + 1
			}
			for end != -1 && text[end-1] == '\\' {
				next := strings.IndexByte(text[end+1:], '"')
				if next == -1 {
					end = -1
					break
				}
				end += next + 1
			}
			if end == -1 {
				return nil, fmt.Errorf("unterminated quoted string")
			}
			tokens = append(tokens, strings.ReplaceAll(text[index+1:end], `\"`, `"`))
			index = end + 1
			continue
		}
		if char == '/' && strings.HasPrefix(text[index:], "//") {
			end := strings.IndexByte(text[index:], '\n')
			if end == -1 {
				index = length
			} else {
				index += end + 1
			}
			continue
		}
		end := index
		for end < length && !strings.ContainsRune(" \t\r\n{}\"", rune(text[end])) {
			end++
		}
		word := text[index:end]
		if strings.HasPrefix(word, "//") || strings.HasPrefix(word, ";") {
			break
		}
		tokens = append(tokens, word)
		index = end
	}
	return tokens, nil
}

func parseTokens(tokens []string, position int, depth int) (*Dict, int, error) {
	result := newDict()
	for position < len(tokens) {
		token := tokens[position]
		if token == "}" {
			if depth == 0 {
				return nil, 0, fmt.Errorf("unexpected '}'")
			}
			return result, position + 1, nil
		}
		if token == "{" {
			return nil, 0, fmt.Errorf("'{' without a key")
		}
		key := token
		position++
		if position >= len(tokens) {
			return nil, 0, fmt.Errorf("key %s has no value", strconv.Quote(key))
		}
		value := tokens[position]
		if value == "{" {
			child, next, err := parseTokens(tokens, position+1, depth+1)
			if err != nil {
				return nil, 0, err
			}
			result.Set(key, child)
			position = next
			continue
		}
		if value == "}" {
			return nil, 0, fmt.Errorf("key %s has no value", strconv.Quote(key))
		}
		result.Set(key, value)
		position++
	}
	if depth > 0 {
		return nil, 0, fmt.Errorf("unexpected end of file: missing '}'")
	}
	return result, position, nil
}

// Parse turns KeyValues text into nested dicts; scalar values stay strings.
func Parse(text string) (*Dict, error) {
	tokens, err := tokenize(text)
	if err != nil {
		return nil, err
	}
	parsed, _, err := parseTokens(tokens, 0, 0)
	return parsed, err
}

// Load reads a .vdf file, replacing bytes that are not valid UTF-8 the way
// Python's errors="replace" does, one U+FFFD per bad byte.
func Load(path string) (*Dict, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	return Parse(ToValidUTF8(string(raw)))
}

// ToValidUTF8 replaces each invalid UTF-8 byte with U+FFFD, so a Steam file
// with stray bytes still parses.
func ToValidUTF8(s string) string {
	if utf8.ValidString(s) {
		return s
	}
	var b strings.Builder
	for i := 0; i < len(s); {
		r, size := utf8.DecodeRuneInString(s[i:])
		if r == utf8.RuneError && size <= 1 {
			b.WriteRune(utf8.RuneError)
			i++
			continue
		}
		b.WriteString(s[i : i+size])
		i += size
	}
	return b.String()
}

// FindAll returns every value under a key path; "*" matches any single key.
func FindAll(data *Dict, path []string) []any {
	current := []any{any(data)}
	for _, key := range path {
		var next []any
		for _, node := range current {
			dict, ok := node.(*Dict)
			if !ok {
				continue
			}
			if key == "*" {
				next = append(next, dict.Values()...)
				continue
			}
			if value, ok := dict.Get(key); ok {
				next = append(next, value)
			}
		}
		current = next
	}
	var hits []any
	for _, value := range current {
		if _, isDict := value.(*Dict); isDict {
			continue
		}
		hits = append(hits, value)
	}
	return hits
}

// Find returns the first value under a key path, or nil.
func Find(data *Dict, path []string) any {
	hits := FindAll(data, path)
	if len(hits) == 0 {
		return nil
	}
	return hits[0]
}

func appSection(data *Dict, appID string) *Dict {
	for _, prefix := range [][]string{{"Steam", "apps"}, {"apps"}, {}} {
		var node any = data
		ok := true
		for _, key := range append(append([]string{}, prefix...), appID) {
			dict, isDict := node.(*Dict)
			if !isDict {
				ok = false
				break
			}
			value, found := dict.Get(key)
			if !found {
				ok = false
				break
			}
			node = value
		}
		if ok {
			if dict, isDict := node.(*Dict); isDict {
				return dict
			}
		}
	}
	return nil
}

func appField(data *Dict, appID, field string) (string, bool) {
	section := appSection(data, appID)
	if section == nil {
		return "", false
	}
	value, ok := section.Get(field)
	if !ok {
		return "", false
	}
	text, isString := value.(string)
	if !isString || strings.TrimSpace(text) == "" {
		return "", false
	}
	return text, true
}

// LaunchOptions returns the launch options Steam has for an app.
func LaunchOptions(data *Dict, appID string) (string, bool) {
	return appField(data, appID, "LaunchOptions")
}

// CompatForceTool returns the Proton tool forced for an app in Steam's settings.
func CompatForceTool(data *Dict, appID string) (string, bool) {
	return appField(data, appID, "CompatForceTool")
}

// LibraryFolderPaths returns every library path from libraryfolders.vdf, in file order.
func LibraryFolderPaths(data *Dict) []string {
	var paths []string
	for _, value := range FindAll(data, []string{"libraryfolders", "*", "path"}) {
		if text, ok := value.(string); ok {
			paths = append(paths, text)
		} else {
			paths = append(paths, fmt.Sprint(value))
		}
	}
	return paths
}
