// Package ui is the Bubble Tea TUI: split pane with search on the left and
// a markdown preview on the right.
package ui

import (
	"time"

	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/glamour"

	"github.com/jaz/learnbase/tui/internal/notes"
	"github.com/jaz/learnbase/tui/internal/search"
)

// FilterMode is which backend handles the current query.
type FilterMode int

const (
	FilterSemantic FilterMode = iota
	FilterKeyword
	FilterTag
)

func (f FilterMode) next() FilterMode { return (f + 1) % 3 }

func (f FilterMode) label() string {
	switch f {
	case FilterSemantic:
		return "Semantic"
	case FilterKeyword:
		return "Keyword"
	case FilterTag:
		return "Tag"
	}
	return "?"
}

const (
	debounceInterval = 150 * time.Millisecond
	resultLimit      = 30
)

// Model is the Bubble Tea model.
type Model struct {
	width  int
	height int

	styles *styles

	notes   []*notes.Note
	byName  map[string]*notes.Note
	glamour *glamour.TermRenderer

	sem         *search.Semantic
	semReady    bool
	semErr      string

	query   string
	mode    FilterMode
	results []search.Result
	sel     int

	searchErr  string
	searchSeq  int // increments per search to detect stale results
	inProgress bool

	preview        viewport.Model
	previewReady   bool
	previewCache   map[string]string
	currentPreview string // filename currently loaded into the viewport
}

// NewModel builds an initial model.
func NewModel(notesList []*notes.Note, sem *search.Semantic) Model {
	byName := make(map[string]*notes.Note, len(notesList))
	for _, n := range notesList {
		byName[n.Filename] = n
	}

	vp := viewport.New(80, 20)
	vp.MouseWheelEnabled = true

	return Model{
		styles:       newStyles(),
		notes:        notesList,
		byName:       byName,
		sem:          sem,
		mode:         FilterSemantic,
		preview:      vp,
		previewCache: map[string]string{},
	}
}

// rebuildGlamour (re)creates the markdown renderer word-wrapped to the current
// preview width. Called on resize so rendered lines never exceed the viewport
// width — otherwise lipgloss re-wraps them and grows the pane vertically.
func (m *Model) rebuildGlamour(width int) {
	if width < 1 {
		width = 1
	}
	r, err := glamour.NewTermRenderer(
		glamour.WithStandardStyle("dark"),
		glamour.WithWordWrap(width),
	)
	if err != nil {
		return
	}
	m.glamour = r
}

// Init schedules initial work: waiting for semantic helper readiness.
func (m Model) Init() tea.Cmd {
	return tea.Batch(
		waitForSemantic(m.sem),
		tea.EnterAltScreen,
	)
}
