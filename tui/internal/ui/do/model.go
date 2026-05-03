// Package do is the Bubble Tea TUI for task / priority / project CRUD.
package do

import (
	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"

	"github.com/jaz/learnbase/tui/internal/store"
)

// ViewMode is which of the three entity lists is active.
type ViewMode int

const (
	ViewTasks ViewMode = iota
	ViewProjects
)

func (v ViewMode) next() ViewMode { return (v + 1) % 2 }

func (v ViewMode) label() string {
	switch v {
	case ViewTasks:
		return "Tasks"
	case ViewProjects:
		return "Projects"
	}
	return "?"
}

// Model is the top-level TUI state.
type Model struct {
	width, height int
	styles        *styles
	db            *store.DB

	view ViewMode

	tasks    []*store.Task
	projects []*store.Project
	sel        int

	filter store.TaskFilter

	detail viewport.Model

	form *formState

	err    string
	status string
}

// NewModel constructs the initial model and triggers the first load.
func NewModel(db *store.DB) Model {
	vp := viewport.New(80, 20)
	vp.MouseWheelEnabled = true
	return Model{
		styles: newStyles(),
		db:     db,
		view:   ViewTasks,
		detail: vp,
	}
}

// Init triggers the initial data load.
func (m Model) Init() tea.Cmd {
	return tea.Batch(loadCmd(m.db), tea.EnterAltScreen)
}
