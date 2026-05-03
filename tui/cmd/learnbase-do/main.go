// Command learnbase-do is a fast, keyboard-driven TUI for tasks, priorities,
// and projects. It writes directly to ~/.learnbase/tasks.db alongside the
// Python MCP server.
package main

import (
	"fmt"
	"os"

	tea "github.com/charmbracelet/bubbletea"

	"github.com/jaz/learnbase/tui/internal/store"
	"github.com/jaz/learnbase/tui/internal/ui/do"
)

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, "learnbase-do:", err)
		os.Exit(1)
	}
}

func run() error {
	db, err := store.Open()
	if err != nil {
		return err
	}
	defer db.Close()

	m := do.NewModel(db)
	p := tea.NewProgram(m, tea.WithAltScreen())
	_, err = p.Run()
	return err
}
