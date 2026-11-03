//go:build windows

package ui

import "os"

// ttyFlags has no non-blocking or no-ctty variant on Windows; the probe simply
// fails there and the run stays headless.
const ttyFlags = os.O_RDONLY
