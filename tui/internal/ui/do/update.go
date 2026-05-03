package do

import (
	"fmt"

	tea "github.com/charmbracelet/bubbletea"

	"github.com/jaz/learnbase/tui/internal/store"
)

// ---------- messages ----------

type loadedMsg struct {
	tasks    []*store.Task
	projects []*store.Project
	err      error
}

type savedMsg struct {
	status string
	err    error
}

func loadCmd(db *store.DB) tea.Cmd {
	return func() tea.Msg {
		t, err := db.ListTasks(store.TaskFilter{})
		if err != nil {
			return loadedMsg{err: err}
		}
		pr, err := db.ListProjects()
		if err != nil {
			return loadedMsg{err: err}
		}
		return loadedMsg{tasks: t, projects: pr}
	}
}

func reloadCmd(db *store.DB, f store.TaskFilter) tea.Cmd {
	return func() tea.Msg {
		t, errT := db.ListTasks(f)
		pr, errPr := db.ListProjects()
		if err := firstErr(errT, errPr); err != nil {
			return loadedMsg{err: err}
		}
		return loadedMsg{tasks: t, projects: pr}
	}
}

func firstErr(errs ...error) error {
	for _, e := range errs {
		if e != nil {
			return e
		}
	}
	return nil
}

// Update routes key/message events.
func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		m.resizeDetail()
		m.refreshDetail()
		return m, nil

	case loadedMsg:
		if msg.err != nil {
			m.err = msg.err.Error()
			return m, nil
		}
		if msg.tasks != nil {
			m.tasks = msg.tasks
		}
		if msg.projects != nil {
			m.projects = msg.projects
		}
		if m.sel >= m.listLen() {
			if m.listLen() > 0 {
				m.sel = m.listLen() - 1
			} else {
				m.sel = 0
			}
		}
		m.err = ""
		m.refreshDetail()
		return m, nil

	case savedMsg:
		if msg.err != nil {
			m.err = msg.err.Error()
			return m, nil
		}
		m.err = ""
		m.status = msg.status
		m.form = nil
		return m, reloadCmd(m.db, m.filter)

	case tea.KeyMsg:
		if m.form != nil {
			return m.updateForm(msg)
		}
		return m.updateList(msg)
	}
	return m, nil
}

// ---------- list-mode input ----------

func (m Model) updateList(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch msg.Type {
	case tea.KeyCtrlC:
		return m, tea.Quit
	case tea.KeyTab:
		m.view = m.view.next()
		m.sel = 0
		m.refreshDetail()
		return m, nil
	case tea.KeyUp, tea.KeyCtrlP:
		if m.sel > 0 {
			m.sel--
			m.refreshDetail()
		}
		return m, nil
	case tea.KeyDown, tea.KeyCtrlN:
		if m.sel < m.listLen()-1 {
			m.sel++
			m.refreshDetail()
		}
		return m, nil
	case tea.KeyShiftUp:
		return m.moveTaskInline(-1)
	case tea.KeyShiftDown:
		return m.moveTaskInline(+1)
	case tea.KeyEnter:
		return m.openEditForm()
	case tea.KeyEsc:
		m.err = ""
		m.status = ""
		return m, nil
	case tea.KeySpace:
		return m.toggleInline()
	case tea.KeyRunes:
		if len(msg.Runes) != 1 {
			return m, nil
		}
		switch msg.Runes[0] {
		case 'q':
			return m, tea.Quit
		case 'n':
			return m.openCreateForm(), nil
		case 'r':
			return m, loadCmd(m.db)
		case 'D':
			return m.archiveInline()
		case 'd':
			if m.view == ViewTasks {
				m.filter.Due = (m.filter.Due + 1) % 4
				return m, reloadCmd(m.db, m.filter)
			}
		case 'w':
			if m.view == ViewTasks {
				m.filter.Workspace = cycleWorkspace(m.filter.Workspace)
				return m, reloadCmd(m.db, m.filter)
			}
		case 's':
			if m.view == ViewTasks {
				m.filter.Status = cycleStatus(m.filter.Status)
				return m, reloadCmd(m.db, m.filter)
			}
		case 'x':
			return m.toggleInline()
		case 'i':
			return m.toggleInProgressInline()
		case 'p':
			return m.togglePinInline()
		}
	}
	return m, nil
}

// ---------- form-mode input ----------

func (m Model) updateForm(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch msg.Type {
	case tea.KeyEsc:
		m.form = nil
		m.err = ""
		return m, nil
	case tea.KeyTab, tea.KeyDown:
		m.form.focusIdx((m.form.focus + 1) % len(m.form.fields))
		return m, nil
	case tea.KeyShiftTab, tea.KeyUp:
		m.form.focusIdx((m.form.focus - 1 + len(m.form.fields)) % len(m.form.fields))
		return m, nil
	case tea.KeyCtrlS:
		return m, m.submitForm()
	case tea.KeyEnter:
		f := m.form.fields[m.form.focus]
		if f.multiSel {
			f.toggleCursor()
			return m, nil
		}
		if m.form.focus == len(m.form.fields)-1 {
			return m, m.submitForm()
		}
		m.form.focusIdx(m.form.focus + 1)
		return m, nil
	case tea.KeyLeft:
		f := m.form.fields[m.form.focus]
		if f.multiSel {
			f.cursorLeft()
			return m, nil
		}
		if f.isSelect() {
			f.cyclePrev()
			return m, nil
		}
	case tea.KeyRight:
		f := m.form.fields[m.form.focus]
		if f.multiSel {
			f.cursorRight()
			return m, nil
		}
		if f.isSelect() {
			f.cycleNext()
			return m, nil
		}
	}

	f := m.form.fields[m.form.focus]
	if f.isSelect() || f.multiSel {
		return m, nil
	}
	var cmd tea.Cmd
	f.input, cmd = f.input.Update(msg)
	return m, cmd
}

// ---------- inline mutations (sync DB + reload) ----------

func (m Model) toggleInline() (tea.Model, tea.Cmd) {
	if m.view != ViewTasks || m.sel >= len(m.tasks) {
		return m, nil
	}
	if err := m.db.ToggleTaskStatus(m.tasks[m.sel].ID); err != nil {
		m.err = err.Error()
		return m, nil
	}
	m.status = "toggled"
	return m, reloadCmd(m.db, m.filter)
}

func (m Model) togglePinInline() (tea.Model, tea.Cmd) {
	if m.view != ViewTasks || m.sel >= len(m.tasks) {
		return m, nil
	}
	if err := m.db.TogglePinned(m.tasks[m.sel].ID); err != nil {
		m.err = err.Error()
		return m, nil
	}
	return m, reloadCmd(m.db, m.filter)
}

func (m Model) toggleInProgressInline() (tea.Model, tea.Cmd) {
	if m.view != ViewTasks || m.sel >= len(m.tasks) {
		return m, nil
	}
	if err := m.db.ToggleTaskInProgress(m.tasks[m.sel].ID); err != nil {
		m.err = err.Error()
		return m, nil
	}
	m.status = "in_progress →"
	return m, reloadCmd(m.db, m.filter)
}

func (m Model) archiveInline() (tea.Model, tea.Cmd) {
	switch m.view {
	case ViewTasks:
		if m.sel >= len(m.tasks) {
			return m, nil
		}
		if err := m.db.ArchiveTask(m.tasks[m.sel].ID); err != nil {
			m.err = err.Error()
			return m, nil
		}
		m.status = "archived"
	case ViewProjects:
		if m.sel >= len(m.projects) {
			return m, nil
		}
		if err := m.db.ArchiveProject(m.projects[m.sel].ID); err != nil {
			m.err = err.Error()
			return m, nil
		}
		m.status = "archived"
	}
	return m, reloadCmd(m.db, m.filter)
}

func (m Model) moveTaskInline(delta int) (tea.Model, tea.Cmd) {
	if m.view != ViewTasks || len(m.tasks) == 0 {
		return m, nil
	}
	if (delta < 0 && m.sel == 0) || (delta > 0 && m.sel == len(m.tasks)-1) {
		return m, nil
	}
	ids := make([]string, len(m.tasks))
	for i, t := range m.tasks {
		ids[i] = t.ID
	}
	id := m.tasks[m.sel].ID
	if err := m.db.MovePosition(ids, id, delta); err != nil {
		m.err = err.Error()
		return m, nil
	}
	m.sel += delta
	return m, reloadCmd(m.db, m.filter)
}

// ---------- form open helpers ----------

func (m Model) openCreateForm() Model {
	switch m.view {
	case ViewTasks:
		m.form = buildTaskForm(nil, m.projects)
	case ViewProjects:
		m.form = buildProjectForm(nil)
	}
	return m
}

func (m Model) openEditForm() (tea.Model, tea.Cmd) {
	switch m.view {
	case ViewTasks:
		if m.sel >= len(m.tasks) {
			return m, nil
		}
		m.form = buildTaskForm(m.tasks[m.sel], m.projects)
	case ViewProjects:
		if m.sel >= len(m.projects) {
			return m, nil
		}
		m.form = buildProjectForm(m.projects[m.sel])
	}
	return m, nil
}

func (m Model) submitForm() tea.Cmd {
	db := m.db
	form := m.form
	return func() tea.Msg {
		var err error
		switch form.target {
		case formTask:
			err = form.submitTask(db)
		case formProject:
			err = form.submitProject(db)
		}
		if err != nil {
			return savedMsg{err: fmt.Errorf("save: %w", err)}
		}
		return savedMsg{status: "saved"}
	}
}

// ---------- small helpers ----------

func (m Model) listLen() int {
	switch m.view {
	case ViewTasks:
		return len(m.tasks)
	case ViewProjects:
		return len(m.projects)
	}
	return 0
}

func cycleWorkspace(cur string) string {
	switch cur {
	case "":
		return "work"
	case "work":
		return "personal"
	case "personal":
		return "contract"
	default:
		return ""
	}
}

func cycleStatus(cur string) string {
	switch cur {
	case "":
		return "pending"
	case "pending":
		return "in_progress"
	case "in_progress":
		return "completed"
	default:
		return ""
	}
}

func (m *Model) resizeDetail() {
	_, innerW, innerH := m.detailDims()
	if innerW < 1 {
		innerW = 1
	}
	if innerH < 1 {
		innerH = 1
	}
	m.detail.Width = innerW
	m.detail.Height = innerH
}

func (m *Model) refreshDetail() {
	m.detail.SetContent(m.detailBody())
	m.detail.GotoTop()
}
