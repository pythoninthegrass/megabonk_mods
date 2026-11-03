// Package jsonx decodes JSON for the checks the installer makes before it
// copies anything: what type a field is, whether it is present, whether it is
// a non-blank string. Values are decoded with json.Number so an int in the
// document stays distinguishable from a float.
package jsonx

import (
	"bytes"
	"encoding/json"
	"strings"
)

// Decode parses JSON text into map[string]any, []any, json.Number, string,
// bool and nil.
func Decode(text string) (any, error) {
	decoder := json.NewDecoder(bytes.NewReader([]byte(text)))
	decoder.UseNumber()
	var value any
	if err := decoder.Decode(&value); err != nil {
		return nil, err
	}
	var extra any
	if err := decoder.Decode(&extra); err == nil {
		return nil, errExtraData
	}
	return value, nil
}

type extraDataError struct{}

func (extraDataError) Error() string { return "extra data after the JSON document" }

var errExtraData = extraDataError{}

// AsMap returns the value as an object, or false for any other JSON type.
func AsMap(value any) (map[string]any, bool) {
	typed, ok := value.(map[string]any)
	return typed, ok
}

// AsList returns the value as an array, or false for any other JSON type.
func AsList(value any) ([]any, bool) {
	typed, ok := value.([]any)
	return typed, ok
}

// Text renders a decoded scalar the way a message wants it: numbers keep their
// document spelling, null reads as None, and containers fall back to their
// encoded form.
func Text(value any) string {
	switch typed := value.(type) {
	case nil:
		return "None"
	case bool:
		if typed {
			return "True"
		}
		return "False"
	case string:
		return typed
	case json.Number:
		return typed.String()
	default:
		encoded, err := json.Marshal(typed)
		if err != nil {
			return "None"
		}
		return string(encoded)
	}
}

// Truthy is Python's truth test on a decoded value: null, false, zero, and an
// empty string, array, or object are all false.
func Truthy(value any) bool {
	switch typed := value.(type) {
	case nil:
		return false
	case bool:
		return typed
	case string:
		return typed != ""
	case json.Number:
		if whole, err := typed.Int64(); err == nil {
			return whole != 0
		}
		real, err := typed.Float64()
		return err == nil && real != 0
	case map[string]any:
		return len(typed) > 0
	case []any:
		return len(typed) > 0
	default:
		return true
	}
}

// IsInt reports whether the value is a JSON integer (Python counts a bool as
// an int, and this contract follows it).
func IsInt(value any) bool {
	switch typed := value.(type) {
	case bool:
		return true
	case json.Number:
		// A float literal is spelled with a fraction or an exponent.
		text := typed.String()
		return !strings.ContainsAny(text, ".eE")
	}
	return false
}

// IsString reports whether the value is a JSON string.
func IsString(value any) bool {
	_, ok := value.(string)
	return ok
}

// IsNonBlankString reports whether the value is a string with content, which is
// what a pack manifest's required fields have to be.
func IsNonBlankString(value any) bool {
	text, ok := value.(string)
	return ok && strings.TrimSpace(text) != ""
}

// IsStringList reports whether the value is an array of strings.
func IsStringList(value any) bool {
	items, ok := value.([]any)
	if !ok {
		return false
	}
	for _, item := range items {
		if _, ok := item.(string); !ok {
			return false
		}
	}
	return true
}

// Length is len() over the decoded types a record can hold.
func Length(value any) int {
	switch typed := value.(type) {
	case nil:
		return 0
	case string:
		return len([]rune(typed))
	case []any:
		return len(typed)
	case map[string]any:
		return len(typed)
	default:
		return 0
	}
}
