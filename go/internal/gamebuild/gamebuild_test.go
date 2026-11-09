package gamebuild

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func writeFile(t *testing.T, dir, name, content string) {
	t.Helper()
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, name), []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}

func windowsTree(t *testing.T) string {
	dir := filepath.Join(t.TempDir(), "Megabonk")
	writeFile(t, dir, WindowsExe, "MZ")
	writeFile(t, dir, GameAssembly, "MZ")
	writeFile(t, filepath.Join(dir, DataDir), "data_app.ini", "x")
	return dir
}

func TestClassifyRecognisesTheWindowsBuild(t *testing.T) {
	build := Classify(windowsTree(t))
	if build.Kind != Windows || !build.Supported() {
		t.Fatalf("kind = %q supported = %v", build.Kind, build.Supported())
	}
	if !build.HasWindowsExe || build.HasNativeExe || !build.HasDataDir {
		t.Errorf("flags = %+v", build)
	}
}

func TestClassifyRefusesTheNativeLinuxBuild(t *testing.T) {
	dir := filepath.Join(t.TempDir(), "Megabonk")
	writeFile(t, dir, NativeExe, "ELF")
	writeFile(t, filepath.Join(dir, DataDir), "data_app.ini", "x")
	build := Classify(dir)
	if build.Kind != NativeLinux || build.Supported() {
		t.Fatalf("kind = %q supported = %v", build.Kind, build.Supported())
	}
}

func TestClassifyCallsADirectoryWithBothExecutablesMixed(t *testing.T) {
	dir := windowsTree(t)
	writeFile(t, dir, NativeExe, "ELF")
	build := Classify(dir)
	if build.Kind != Mixed || !build.Supported() {
		t.Fatalf("kind = %q", build.Kind)
	}
}

func TestClassifyCallsAnEmptyDirectoryUnknown(t *testing.T) {
	build := Classify(t.TempDir())
	if build.Kind != Unknown || build.Supported() {
		t.Fatalf("kind = %q", build.Kind)
	}
}

func TestLaunchBinaryNamesTheRightExecutable(t *testing.T) {
	if LaunchBinary(NativeLinux) != NativeExe || LaunchBinary(Windows) != WindowsExe {
		t.Error("wrong launch binary names")
	}
}

func TestNativeBuildMessageNamesTheNativeExeAndSteamPlay(t *testing.T) {
	message := NativeBuildMessage("0.7.3", "/games/Megabonk")
	for _, want := range []string{"Megabonk.x86_64", "Steam Play", "/games/Megabonk", "MelonLoader 0.7.3"} {
		if !strings.Contains(message, want) {
			t.Errorf("message missing %q:\n%s", want, message)
		}
	}
	if lines := strings.Count(message, "\n") + 1; lines != 11 {
		t.Errorf("message line count = %d:\n%s", lines, message)
	}
}

func TestUnknownBuildMessageNamesWhatIsMissing(t *testing.T) {
	message := UnknownBuildMessage("/games/Nope")
	for _, want := range []string{"/games/Nope", WindowsExe, DataDir, "start it once"} {
		if !strings.Contains(message, want) {
			t.Errorf("message missing %q:\n%s", want, message)
		}
	}
}

func TestUnsupportedBuildMessagePicksByKind(t *testing.T) {
	if !strings.Contains(UnsupportedBuildMessage("/g/Megabonk", NativeLinux, "0.7.3"), "Linux native build") {
		t.Error("native kind should read as the native refusal")
	}
	if !strings.Contains(UnsupportedBuildMessage("/g/Megabonk", Unknown, "0.7.3"), "does not look like a Megabonk install") {
		t.Error("unknown kind should read as the unknown refusal")
	}
}
