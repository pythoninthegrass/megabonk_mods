//go:build !windows

package steam

import (
	"fmt"
	"os"
	"syscall"
)

// identity is how the reference dedupes candidates: the device and inode behind
// the resolved path, so a symlinked Steam directory matches the real one.
func identity(path string) string {
	resolved := resolve(path)
	info, err := os.Stat(resolved)
	if err != nil {
		return resolved
	}
	stat, ok := info.Sys().(*syscall.Stat_t)
	if !ok {
		return resolved
	}
	return fmt.Sprintf("%d:%d", stat.Dev, stat.Ino)
}
