package proton

import (
	"go/ast"
	"go/parser"
	"go/token"
	"os"
	"path/filepath"
	"testing"
)

// The distributable ships no MelonLoader vendor archive and no separate .NET 6
// runtime: the BepInEx pack carries both. These helpers must not come back.
func TestRuntimeAndMelonLoaderHelpersAreGone(t *testing.T) {
	banned := []string{
		"RuntimeTarget",
		"RuntimeInstalled",
		"ExtractRuntime",
		"RemoveRuntime",
		"LaunchOption",
		"WindowsPath",
		"ProtonRoots",
		"PickProton",
		"ProtonWineBin",
		"RuntimeMarkerName",
		"RuntimeHost",
		"DLLName",
		"DLLValue",
	}
	declared := map[string]bool{}
	fset := token.NewFileSet()
	entries, err := os.ReadDir(".")
	if err != nil {
		t.Fatal(err)
	}
	for _, entry := range entries {
		name := entry.Name()
		if entry.IsDir() || filepath.Ext(name) != ".go" {
			continue
		}
		file, parseErr := parser.ParseFile(fset, name, nil, 0)
		if parseErr != nil {
			t.Fatal(parseErr)
		}
		for _, decl := range file.Decls {
			switch spec := decl.(type) {
			case *ast.FuncDecl:
				declared[spec.Name.Name] = true
			case *ast.GenDecl:
				for _, inner := range spec.Specs {
					switch value := inner.(type) {
					case *ast.TypeSpec:
						declared[value.Name.Name] = true
					case *ast.ValueSpec:
						for _, ident := range value.Names {
							declared[ident.Name] = true
						}
					}
				}
			}
		}
	}
	for _, name := range banned {
		if declared[name] {
			t.Errorf("%s is still declared in package proton", name)
		}
	}
}
