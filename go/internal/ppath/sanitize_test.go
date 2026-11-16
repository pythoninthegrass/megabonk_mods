package ppath

import "testing"

func TestSanitizeName(t *testing.T) {
	cases := map[string]string{
		"thps-warehouse.mblevel.json": "thps-warehouse.mblevel.json",
		"THPS Warehouse (v2)":         "thps-warehouse-v2",
		"../etc/passwd":               "etc-passwd",
		"..":                          "",
		"":                            "",
		"   ":                         "",
		".hidden":                     "hidden",
		"pack//name":                  "pack-name",
		"café":                        "caf",
	}
	for raw, want := range cases {
		if got := SanitizeName(raw); got != want {
			t.Errorf("SanitizeName(%q) = %q, want %q", raw, got, want)
		}
	}
}
