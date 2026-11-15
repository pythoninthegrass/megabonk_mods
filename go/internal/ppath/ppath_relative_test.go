package ppath

import "testing"

func TestSafeRelative(t *testing.T) {
	for _, tc := range []struct {
		name string
		want bool
	}{
		{name: "BepInEx/plugins/MegabonkLevels/MegabonkLevels.Mod.dll", want: true},
		{name: "a/b/c.json", want: true},
		{name: "", want: false},
		{name: "/etc/passwd", want: false},
		{name: `a\b\c.dll`, want: false},
		{name: "C:/Windows/system.dll", want: false},
		{name: "a/b\x00c", want: false},
		{name: "../escape", want: false},
		{name: "a/../../escape", want: false},
		{name: "./a", want: false},
		{name: "a//b", want: false},
	} {
		if got := SafeRelative(tc.name); got != tc.want {
			t.Errorf("SafeRelative(%q) = %v, want %v", tc.name, got, tc.want)
		}
	}
}
