package ui

import (
	"fmt"
	"os"
	"os/exec"
	"time"

	tea "github.com/charmbracelet/bubbletea"

	"github.com/jaz/learnbase/tui/internal/notes"
	"github.com/jaz/learnbase/tui/internal/search"
)

type semReadyMsg struct{ err error }

type debounceMsg struct {
	seq   int
	query string
	mode  FilterMode
}

type searchResultMsg struct {
	seq     int
	results []search.Result
	err     error
}

type editorFinishedMsg struct{ err error }

func waitForSemantic(s *search.Semantic) tea.Cmd {
	return func() tea.Msg {
		if s == nil {
			return semReadyMsg{err: fmt.Errorf("semantic helper not started")}
		}
		return semReadyMsg{err: s.Ready()}
	}
}

func scheduleDebounce(seq int, query string, mode FilterMode) tea.Cmd {
	return tea.Tick(debounceInterval, func(time.Time) tea.Msg {
		return debounceMsg{seq: seq, query: query, mode: mode}
	})
}

// Update handles key events and async messages.
func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		m.resizePreview()
		m.refreshPreview()
		return m, nil

	case semReadyMsg:
		if msg.err != nil {
			m.semErr = msg.err.Error()
			return m, nil
		}
		m.semReady = true
		if m.query != "" && m.mode == FilterSemantic {
			m.searchSeq++
			return m, scheduleDebounce(m.searchSeq, m.query, m.mode)
		}
		return m, nil

	case debounceMsg:
		if msg.seq != m.searchSeq {
			return m, nil
		}
		if msg.query == "" {
			m.results = nil
			m.sel = 0
			m.inProgress = false
			return m, nil
		}
		m.inProgress = true
		return m, runSearch(m.sem, m.notes, msg)

	case searchResultMsg:
		if msg.seq != m.searchSeq {
			return m, nil
		}
		m.inProgress = false
		if msg.err != nil {
			m.searchErr = msg.err.Error()
			m.results = nil
		} else {
			m.searchErr = ""
			m.results = msg.results
			if m.sel >= len(m.results) {
				m.sel = 0
			}
		}
		m.refreshPreview()
		return m, nil

	case editorFinishedMsg:
		return m, nil

	case tea.KeyMsg:
		return m.handleKey(msg)
	}
	return m, nil
}

func (m Model) handleKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	// Preview scroll bindings — handled before the default key paths so typing
	// text never triggers scrolling and vice versa.
	if msg.Alt {
		switch msg.Type {
		case tea.KeyUp:
			m.preview.LineUp(1)
			return m, nil
		case tea.KeyDown:
			m.preview.LineDown(1)
			return m, nil
		}
	}
	switch msg.Type {
	case tea.KeyPgUp:
		m.preview.HalfViewUp()
		return m, nil
	case tea.KeyPgDown:
		m.preview.HalfViewDown()
		return m, nil
	case tea.KeyCtrlU:
		m.preview.HalfViewUp()
		return m, nil
	case tea.KeyCtrlD:
		m.preview.HalfViewDown()
		return m, nil
	}

	switch msg.Type {
	case tea.KeyCtrlC:
		return m, tea.Quit
	case tea.KeyTab:
		m.mode = m.mode.next()
		m.searchSeq++
		if m.query == "" {
			m.results = nil
			return m, nil
		}
		return m, scheduleDebounce(m.searchSeq, m.query, m.mode)
	case tea.KeyUp, tea.KeyCtrlP:
		if m.sel > 0 {
			m.sel--
			m.refreshPreview()
		}
		return m, nil
	case tea.KeyDown, tea.KeyCtrlN:
		if m.sel < len(m.results)-1 {
			m.sel++
			m.refreshPreview()
		}
		return m, nil
	case tea.KeyEsc:
		m.query = ""
		m.results = nil
		m.sel = 0
		m.searchErr = ""
		return m, nil
	case tea.KeyBackspace:
		if len(m.query) > 0 {
			m.query = m.query[:len(m.query)-1]
			m.searchSeq++
			return m, scheduleDebounce(m.searchSeq, m.query, m.mode)
		}
		return m, nil
	case tea.KeyEnter:
		return m.openEditor()
	case tea.KeyRunes, tea.KeySpace:
		runes := msg.Runes
		if msg.Type == tea.KeySpace {
			runes = []rune{' '}
		}
		if len(runes) == 1 {
			switch runes[0] {
			case 'q':
				if m.query == "" {
					return m, tea.Quit
				}
			case 'o':
				if m.query == "" {
					return m.openEditor()
				}
			}
		}
		m.query += string(runes)
		m.searchSeq++
		return m, scheduleDebounce(m.searchSeq, m.query, m.mode)
	}
	return m, nil
}

func (m Model) openEditor() (tea.Model, tea.Cmd) {
	if len(m.results) == 0 {
		return m, nil
	}
	r := m.results[m.sel]
	n := m.byName[r.Filename]
	if n == nil {
		return m, nil
	}
	editor := os.Getenv("EDITOR")
	if editor == "" {
		editor = "vi"
	}
	cmd := exec.Command(editor, n.Path)
	return m, tea.ExecProcess(cmd, func(err error) tea.Msg {
		return editorFinishedMsg{err: err}
	})
}

// resizePreview recomputes the viewport dimensions from the current window
// size. Called on every WindowSizeMsg and whenever the layout is recomputed.
func (m *Model) resizePreview() {
	w, h := m.previewDimensions()
	if w < 1 {
		w = 1
	}
	if h < 1 {
		h = 1
	}
	m.preview.Width = w
	m.preview.Height = h
	m.previewReady = true
	// Glamour wraps at a fixed column; rebuild it at the current viewport width
	// so its output matches and lipgloss never has to re-wrap (which would
	// silently grow the pane vertically).
	m.rebuildGlamour(w)
	// Drop the cache so the next refresh re-renders at the new width.
	m.previewCache = map[string]string{}
	m.currentPreview = ""
}

// refreshPreview loads the currently-selected note's rendered markdown into
// the viewport, resetting scroll to the top if the selection changed.
func (m *Model) refreshPreview() {
	if !m.previewReady || len(m.results) == 0 {
		m.preview.SetContent("")
		m.currentPreview = ""
		return
	}
	r := m.results[m.sel]
	if r.Filename == m.currentPreview {
		return
	}
	n := m.byName[r.Filename]
	if n == nil {
		m.preview.SetContent("")
		m.currentPreview = ""
		return
	}
	body := n.Body
	if cached, ok := m.previewCache[r.Filename]; ok {
		body = cached
	} else if m.glamour != nil {
		if out, err := m.glamour.Render(n.Body); err == nil {
			body = out
			m.previewCache[r.Filename] = out
		}
	}
	m.preview.SetContent(body)
	m.preview.GotoTop()
	m.currentPreview = r.Filename
}

func runSearch(sem *search.Semantic, all []*notes.Note, msg debounceMsg) tea.Cmd {
	return func() tea.Msg {
		switch msg.mode {
		case FilterKeyword:
			return searchResultMsg{
				seq:     msg.seq,
				results: search.Keyword(all, msg.query, resultLimit),
			}
		case FilterTag:
			return searchResultMsg{
				seq:     msg.seq,
				results: search.Tag(all, msg.query, resultLimit),
			}
		case FilterSemantic:
			if sem == nil {
				return searchResultMsg{seq: msg.seq, err: fmt.Errorf("semantic helper unavailable")}
			}
			res, err := sem.Query(msg.query, resultLimit)
			return searchResultMsg{seq: msg.seq, results: res, err: err}
		}
		return searchResultMsg{seq: msg.seq}
	}
}
