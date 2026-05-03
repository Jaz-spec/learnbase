// Command learnbase-drill is the TUI for code drill flashcards.
package main

import (
	"fmt"
	"os"
	"path/filepath"

	tea "github.com/charmbracelet/bubbletea"

	drillbridge "github.com/jaz/learnbase/tui/internal/drill"
	drillui "github.com/jaz/learnbase/tui/internal/ui/drill"
)

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, "learnbase-drill:", err)
		os.Exit(1)
	}
}

func run() error {
	repoRoot := findRepoRoot()
	bridge, err := drillbridge.Start(repoRoot)
	if err != nil {
		return fmt.Errorf("start drill helper: %w", err)
	}
	defer bridge.Close()

	if err := bridge.Ready(); err != nil {
		return fmt.Errorf("drill helper failed to initialise: %w", err)
	}

	m := drillui.NewModel(bridge)
	p := tea.NewProgram(m, tea.WithAltScreen())
	_, err = p.Run()
	return err
}

func findRepoRoot() string {
	candidates := []string{}
	if exe, err := os.Executable(); err == nil {
		if resolved, err := filepath.EvalSymlinks(exe); err == nil {
			candidates = append(candidates, filepath.Dir(resolved))
		}
	}
	if cwd, err := os.Getwd(); err == nil {
		candidates = append(candidates, cwd)
	}

	for _, start := range candidates {
		d := start
		for i := 0; i < 6; i++ {
			if _, err := os.Stat(filepath.Join(d, "pyproject.toml")); err == nil {
				return d
			}
			parent := filepath.Dir(d)
			if parent == d {
				break
			}
			d = parent
		}
	}

	cwd, _ := os.Getwd()
	return cwd
}
