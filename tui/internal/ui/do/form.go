package do

import (
	"fmt"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/textinput"

	"github.com/jaz/learnbase/tui/internal/store"
)

// formTarget describes what entity the form is editing.
type formTarget int

const (
	formTask formTarget = iota
	formProject
)

// formField is one row in the form modal.
type formField struct {
	key   string
	label string
	hint  string
	input textinput.Model // used only when options == nil

	// Single-select: cycle with ←/→ when focused.
	options []string
	optIdx  int

	// Multi-select: ←/→ moves cursor, Enter toggles.
	multiSel bool
	selected map[string]bool
	cursor   int
}

func (f *formField) isSelect() bool { return f.options != nil && !f.multiSel }

func (f *formField) value() string {
	if f.multiSel {
		var sel []string
		for _, o := range f.options {
			if f.selected[o] {
				sel = append(sel, o)
			}
		}
		return strings.Join(sel, ",")
	}
	if f.options != nil {
		if len(f.options) == 0 {
			return ""
		}
		return f.options[f.optIdx]
	}
	return strings.TrimSpace(f.input.Value())
}

func (f *formField) cycleNext() {
	if len(f.options) > 0 {
		f.optIdx = (f.optIdx + 1) % len(f.options)
	}
}

func (f *formField) cyclePrev() {
	if len(f.options) > 0 {
		f.optIdx = (f.optIdx - 1 + len(f.options)) % len(f.options)
	}
}

func (f *formField) cursorRight() {
	if f.cursor < len(f.options)-1 {
		f.cursor++
	}
}

func (f *formField) cursorLeft() {
	if f.cursor > 0 {
		f.cursor--
	}
}

func (f *formField) toggleCursor() {
	if !f.multiSel || len(f.options) == 0 {
		return
	}
	opt := f.options[f.cursor]
	if f.selected[opt] {
		delete(f.selected, opt)
	} else {
		f.selected[opt] = true
	}
}

// formState is the modal overlay shown during create/edit.
type formState struct {
	target     formTarget
	existingID string
	fields     []*formField
	focus      int
	err        string
}

// buildTaskForm populates fields for a task.
func buildTaskForm(t *store.Task, projects []*store.Project) *formState {
	projectOpts := make([]string, 0, len(projects)+1)
	projectOpts = append(projectOpts, "")
	for _, p := range projects {
		projectOpts = append(projectOpts, p.ID)
	}

	var (
		titleVal = ""
		dueVal   = ""
		descVal  = ""
		wsVal    = "personal"
		projVal  = ""
		statVal  = "pending"
		catVals  []string
	)
	var existingID string

	if t != nil {
		existingID = t.ID
		titleVal = t.Title
		dueVal = t.Due.Format("02.01.06 15:04")
		descVal = t.Description
		wsVal = t.Workspace
		projVal = t.Project
		statVal = t.Status
		catVals = t.Categories
	}

	fields := []*formField{
		newTextField("title", "Title", titleVal, "short summary"),
		newTextField("due", "Due", dueVal, "DD.MM.YY or DD.MM.YY HH:MM"),
		newSelectField("workspace", "Workspace", []string{"personal", "work", "contract"}, wsVal, "← → to change"),
		newSelectField("project", "Project", projectOpts, projVal, "← → to change (empty = none)"),
		newSelectField("status", "Status", []string{"pending", "in_progress", "completed"}, statVal, "← → to change"),
		newMultiSelectField("categories", "Categories", []string{"people", "idea", "project", "admin"}, catVals),
		newTextField("description", "Description", descVal, "markdown body (optional)"),
	}

	s := &formState{target: formTask, existingID: existingID, fields: fields}
	s.focusIdx(0)
	return s
}


func buildProjectForm(p *store.Project) *formState {
	fields := []*formField{
		newTextField("id", "ID", "", "unique slug: lowercase-hyphens"),
		newTextField("name", "Name", "", "human-readable project name"),
		newTextField("workspace", "Workspace", "work", "work|personal|contract"),
		newTextField("description", "Description", "", "one or two lines"),
		newTextField("status", "Status", "active", "active|inactive"),
	}
	s := &formState{target: formProject, fields: fields}
	if p != nil {
		s.existingID = p.ID
		fields[0].hint = "(id cannot change)"
		setField(fields, "id", p.ID)
		setField(fields, "name", p.Name)
		setField(fields, "workspace", p.Workspace)
		setField(fields, "description", p.Description)
		setField(fields, "status", p.Status)
	}
	s.focusIdx(0)
	return s
}

func newTextField(key, label, initial, hint string) *formField {
	in := textinput.New()
	in.Prompt = ""
	in.CharLimit = 512
	in.SetValue(initial)
	return &formField{key: key, label: label, hint: hint, input: in}
}

func newSelectField(key, label string, options []string, startVal, hint string) *formField {
	in := textinput.New()
	in.Prompt = ""
	idx := 0
	for i, o := range options {
		if o == startVal {
			idx = i
			break
		}
	}
	return &formField{key: key, label: label, hint: hint, input: in, options: options, optIdx: idx}
}

func newMultiSelectField(key, label string, options []string, startVals []string) *formField {
	in := textinput.New()
	in.Prompt = ""
	sel := make(map[string]bool)
	for _, v := range startVals {
		if v != "" {
			sel[v] = true
		}
	}
	return &formField{
		key:      key,
		label:    label,
		hint:     "← → navigate · ↵ toggle · Tab next field",
		input:    in,
		options:  options,
		multiSel: true,
		selected: sel,
	}
}

func setField(fields []*formField, key, val string) {
	for _, f := range fields {
		if f.key == key {
			f.input.SetValue(val)
			return
		}
	}
}

func (s *formState) focusIdx(i int) {
	if i < 0 || i >= len(s.fields) {
		return
	}
	for j, f := range s.fields {
		if f.isSelect() || f.multiSel {
			continue
		}
		if j == i {
			f.input.Focus()
		} else {
			f.input.Blur()
		}
	}
	s.focus = i
}

func (s *formState) field(key string) string {
	for _, f := range s.fields {
		if f.key == key {
			return f.value()
		}
	}
	return ""
}

// ---------- submission paths ----------

func (s *formState) submitTask(db *store.DB) error {
	title := s.field("title")
	if title == "" {
		return fmt.Errorf("title is required")
	}
	due, err := parseDueDate(s.field("due"))
	if err != nil {
		return err
	}
	workspace := s.field("workspace")
	if !oneOf(workspace, "work", "personal", "contract") {
		return fmt.Errorf("workspace must be work, personal, or contract")
	}
	status := s.field("status")
	if status == "" {
		status = "pending"
	}
	if !oneOf(status, "pending", "in_progress", "completed") {
		return fmt.Errorf("status must be pending, in_progress, or completed")
	}

	catStr := s.field("categories")
	var cats []string
	for _, c := range strings.Split(catStr, ",") {
		c = strings.TrimSpace(c)
		if c != "" {
			cats = append(cats, c)
		}
	}

	if s.existingID == "" {
		task := &store.Task{
			Title:       title,
			Description: s.field("description"),
			Workspace:   workspace,
			Project:     s.field("project"),
			Due:         due,
			Status:      status,
			Categories:  cats,
		}
		return db.CreateTask(task)
	}

	descr := s.field("description")
	project := s.field("project")
	return db.UpdateTask(s.existingID, store.TaskPatch{
		Title:       &title,
		Description: &descr,
		Workspace:   &workspace,
		Project:     &project,
		Due:         &due,
		Status:      &status,
		Categories:  &cats,
	})
}


func (s *formState) submitProject(db *store.DB) error {
	id := s.field("id")
	name := s.field("name")
	workspace := s.field("workspace")
	if !oneOf(workspace, "work", "personal", "contract") {
		return fmt.Errorf("workspace must be work, personal, or contract")
	}
	status := s.field("status")
	if !oneOf(status, "active", "inactive") {
		return fmt.Errorf("status must be active or inactive")
	}
	descr := s.field("description")

	if s.existingID == "" {
		if id == "" || name == "" {
			return fmt.Errorf("id and name are required")
		}
		if !isSlug(id) {
			return fmt.Errorf("id must be lowercase letters, digits, hyphens")
		}
		return db.CreateProject(&store.Project{
			ID:          id,
			Name:        name,
			Workspace:   workspace,
			Description: descr,
			Status:      status,
		})
	}
	return db.UpdateProject(s.existingID, store.ProjectPatch{
		Name:        &name,
		Workspace:   &workspace,
		Description: &descr,
		Status:      &status,
	})
}

// ---------- helpers ----------

func oneOf(v string, allowed ...string) bool {
	for _, a := range allowed {
		if v == a {
			return true
		}
	}
	return false
}

func isSlug(s string) bool {
	if s == "" {
		return false
	}
	for _, r := range s {
		ok := (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') || r == '-'
		if !ok {
			return false
		}
	}
	return true
}

// parseDueDate accepts DD.MM.YY or DD.MM.YY HH:MM (preferred), plus legacy
// ISO formats. Date-only defaults to 09:00.
func parseDueDate(s string) (time.Time, error) {
	s = strings.TrimSpace(s)
	if s == "" {
		return time.Time{}, fmt.Errorf("due date is required (DD.MM.YY or DD.MM.YY HH:MM)")
	}
	layouts := []string{
		"02.01.06 15:04",
		"02.01.06",
		"2006-01-02 15:04",
		"2006-01-02T15:04",
		"2006-01-02",
	}
	for _, l := range layouts {
		if t, err := time.ParseInLocation(l, s, time.Local); err == nil {
			if l == "02.01.06" || l == "2006-01-02" {
				t = t.Add(9 * time.Hour)
			}
			return t, nil
		}
	}
	return time.Time{}, fmt.Errorf("unrecognised date format: %q (expected DD.MM.YY)", s)
}

// defaultPeriod returns sensible current-period string for a given scope.
func defaultPeriod(scope string) string {
	now := time.Now()
	if scope == "monthly" {
		return now.Format("2006-01")
	}
	year, week := now.ISOWeek()
	return fmt.Sprintf("%d-W%02d", year, week)
}
