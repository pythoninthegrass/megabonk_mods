//go:build !windows

package ui

import (
	"os"
	"syscall"
)

// ttyFlags opens the controlling terminal without blocking or claiming it.
const ttyFlags = os.O_RDONLY | syscall.O_NONBLOCK | syscall.O_NOCTTY
