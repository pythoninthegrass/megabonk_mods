//go:build windows

package steam

// identity falls back to the resolved path: discovery runs on Linux, and without
// a POSIX dev/inode pair the path itself is the best dedupe key.
func identity(path string) string {
	return resolve(path)
}
