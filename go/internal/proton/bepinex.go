package proton

const (
	// WinHTTPDLLName is the DLL the BepInEx pack ships as a proxy beside the
	// executable. Wine only loads it when the registry says it is native.
	WinHTTPDLLName = "winhttp"
	// WinHTTPValue is the DllOverrides value that makes Wine load that proxy.
	WinHTTPValue = "native,builtin"
	// WinHTTPLaunchOption is what a Proton player pastes into Steam's Launch Options.
	WinHTTPLaunchOption = `WINEDLLOVERRIDES="winhttp=n,b" %command%`
)

// SetWinHTTPOverride points Wine at the game folder's winhttp.dll proxy and says
// how it was done: "wine" or "registry".
func SetWinHTTPOverride(prefix, wineBin string, runner Runner) string {
	return SetDllOverride(prefix, WinHTTPDLLName, WinHTTPValue, "", wineBin, runner)
}

// ClearWinHTTPOverride removes the override the installer added to a prefix.
func ClearWinHTTPOverride(prefix, wineBin string, runner Runner) string {
	return ClearDllOverride(prefix, WinHTTPDLLName, "", wineBin, runner)
}

// WinHTTPOverrideApplied reports whether a prefix already loads the proxy.
func WinHTTPOverrideApplied(prefix string) bool {
	value, found := ReadDllOverride(prefix, WinHTTPDLLName, "")
	return found && value == WinHTTPValue
}
