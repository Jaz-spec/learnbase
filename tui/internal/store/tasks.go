package store

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"strings"
	"time"
)

// Task is the row shape the TUI consumes. JSON columns are already decoded.
type Task struct {
	ID           string
	Title        string
	Description  string
	Categories   []string
	Workspace    string // work|personal|contract
	Project      string // nullable
	Due          time.Time
	Status       string // pending|in_progress|completed
	Dependencies []string
	Created      time.Time
	Updated      time.Time
	Completed    *time.Time
	Confidence   map[string]float64
	Reasoning    string
	PriorityID   string
	Archived     bool
	Pinned       bool
	Position     *int // nullable; NULL sorts last
}

// TaskFilter captures the three user-visible toggles in the TUI.
type TaskFilter struct {
	Due       DueFilter
	Workspace string // "" = any, else work|personal|contract
	Status    string // "" = any, else pending|in_progress|completed
}

// DueFilter is a named set of inclusive date ranges.
type DueFilter int

const (
	DueAny DueFilter = iota
	DueToday
	DueThisWeek
	DueOverdue
)

// ListTasks returns active (non-archived) tasks matching the filter,
// ordered by position NULLS LAST then due ASC.
func (d *DB) ListTasks(f TaskFilter) ([]*Task, error) {
	q := `SELECT id, title, description, categories, workspace, project, due, status,
	              dependencies, created, updated, completed, confidence, reasoning,
	              priority_id, archived, pinned, position
	      FROM tasks WHERE archived = 0`
	var args []any

	if f.Workspace != "" {
		q += " AND workspace = ?"
		args = append(args, f.Workspace)
	}
	if f.Status != "" {
		q += " AND status = ?"
		args = append(args, f.Status)
	}
	// Due is compared against the ISO 8601 prefix of due (YYYY-MM-DD) so we
	// don't care about the HH:MM portion stored alongside the date.
	now := time.Now()
	switch f.Due {
	case DueToday:
		today := now.Format("2006-01-02")
		q += " AND substr(due,1,10) = ?"
		args = append(args, today)
	case DueThisWeek:
		// Monday of this week (ISO week start) through Sunday.
		weekday := int(now.Weekday())
		if weekday == 0 {
			weekday = 7 // Sunday → 7 so the Monday offset is correct
		}
		monday := now.AddDate(0, 0, -(weekday - 1))
		sunday := monday.AddDate(0, 0, 6)
		q += " AND substr(due,1,10) >= ? AND substr(due,1,10) <= ?"
		args = append(args, monday.Format("2006-01-02"), sunday.Format("2006-01-02"))
	case DueOverdue:
		today := now.Format("2006-01-02")
		q += " AND substr(due,1,10) < ? AND status != 'completed'"
		args = append(args, today)
	}

	q += " ORDER BY position IS NULL, position ASC, due ASC, id ASC"

	rows, err := d.conn.Query(q, args...)
	if err != nil {
		return nil, fmt.Errorf("list tasks: %w", err)
	}
	defer rows.Close()

	var out []*Task
	for rows.Next() {
		t, err := scanTask(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, t)
	}
	return out, rows.Err()
}

// GetTask returns a single task by ID (even if archived).
func (d *DB) GetTask(id string) (*Task, error) {
	row := d.conn.QueryRow(`SELECT id, title, description, categories, workspace, project, due, status,
	              dependencies, created, updated, completed, confidence, reasoning,
	              priority_id, archived, pinned, position
	      FROM tasks WHERE id = ?`, id)
	return scanTask(row)
}

// CreateTask writes a new task. It mirrors Python's column defaults so rows
// are indistinguishable from MCP-created ones.
func (d *DB) CreateTask(t *Task) error {
	if t.ID == "" {
		t.ID = TaskID(t.Title, t.Due)
	}
	now := time.Now()
	if t.Created.IsZero() {
		t.Created = now
	}
	t.Updated = now

	cats, _ := json.Marshal(coalesceStrings(t.Categories))
	deps, _ := json.Marshal(coalesceStrings(t.Dependencies))
	conf, _ := json.Marshal(coalesceConfidence(t.Confidence))

	_, err := d.conn.Exec(`
		INSERT INTO tasks (id, title, description, categories, workspace, project,
			due, status, dependencies, created, updated, completed, confidence,
			reasoning, priority_id, archived)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)`,
		t.ID, t.Title, t.Description, string(cats),
		t.Workspace, nullableStr(t.Project),
		t.Due.Format("2006-01-02T15:04:05"),
		orDefault(t.Status, "pending"),
		string(deps),
		formatTS(t.Created),
		formatTS(t.Updated),
		nullableTime(t.Completed),
		string(conf),
		nullableStr(t.Reasoning),
		nullableStr(t.PriorityID),
	)
	if err != nil {
		return fmt.Errorf("create task: %w", err)
	}
	return nil
}

// UpdateTask updates only the fields that change from the TUI's forms.
// Unspecified fields aren't touched. `updated` is always bumped.
func (d *DB) UpdateTask(id string, patch TaskPatch) error {
	sets := []string{"updated = ?"}
	args := []any{formatTS(time.Now())}

	if patch.Title != nil {
		sets = append(sets, "title = ?")
		args = append(args, *patch.Title)
	}
	if patch.Description != nil {
		sets = append(sets, "description = ?")
		args = append(args, *patch.Description)
	}
	if patch.Workspace != nil {
		sets = append(sets, "workspace = ?")
		args = append(args, *patch.Workspace)
	}
	if patch.Project != nil {
		sets = append(sets, "project = ?")
		args = append(args, nullableStr(*patch.Project))
	}
	if patch.Due != nil {
		sets = append(sets, "due = ?")
		args = append(args, patch.Due.Format("2006-01-02T15:04:05"))
	}
	if patch.Status != nil {
		sets = append(sets, "status = ?")
		args = append(args, *patch.Status)
		if *patch.Status == "completed" {
			sets = append(sets, "completed = ?")
			args = append(args, formatTS(time.Now()))
		} else {
			sets = append(sets, "completed = NULL")
		}
	}
	if patch.PriorityID != nil {
		sets = append(sets, "priority_id = ?")
		args = append(args, nullableStr(*patch.PriorityID))
	}
	if patch.Categories != nil {
		b, _ := json.Marshal(coalesceStrings(*patch.Categories))
		sets = append(sets, "categories = ?")
		args = append(args, string(b))
	}
	if patch.Pinned != nil {
		sets = append(sets, "pinned = ?")
		if *patch.Pinned {
			args = append(args, 1)
		} else {
			args = append(args, 0)
		}
	}

	args = append(args, id)
	q := "UPDATE tasks SET " + strings.Join(sets, ", ") + " WHERE id = ?"
	if _, err := d.conn.Exec(q, args...); err != nil {
		return fmt.Errorf("update task: %w", err)
	}
	return nil
}

// TaskPatch is a sparse update container — nil means "don't touch".
type TaskPatch struct {
	Title       *string
	Description *string
	Workspace   *string
	Project     *string
	Due         *time.Time
	Status      *string
	PriorityID  *string
	Categories  *[]string
	Pinned      *bool
}

// ToggleTaskStatus flips pending ↔ completed. in_progress → completed.
func (d *DB) ToggleTaskStatus(id string) error {
	t, err := d.GetTask(id)
	if err != nil {
		return err
	}
	next := "completed"
	if t.Status == "completed" {
		next = "pending"
	}
	return d.UpdateTask(id, TaskPatch{Status: &next})
}

// ToggleTaskInProgress flips in_progress ↔ pending. Completed tasks go to
// in_progress (i.e. resume). Lets the user declare what they're actively
// working on without pressing Edit.
func (d *DB) ToggleTaskInProgress(id string) error {
	t, err := d.GetTask(id)
	if err != nil {
		return err
	}
	next := "in_progress"
	if t.Status == "in_progress" {
		next = "pending"
	}
	return d.UpdateTask(id, TaskPatch{Status: &next})
}

// TogglePinned pins or unpins a task. Pinning is blocked when 3 tasks are
// already pinned.
func (d *DB) TogglePinned(id string) error {
	t, err := d.GetTask(id)
	if err != nil {
		return err
	}
	if !t.Pinned {
		var count int
		if err := d.conn.QueryRow(
			`SELECT COUNT(*) FROM tasks WHERE pinned = 1 AND archived = 0`,
		).Scan(&count); err != nil {
			return err
		}
		if count >= 3 {
			return fmt.Errorf("3 pinned tasks max — unpin one first")
		}
	}
	pinned := !t.Pinned
	return d.UpdateTask(id, TaskPatch{Pinned: &pinned})
}

// ArchiveTask soft-deletes by setting archived = 1.
func (d *DB) ArchiveTask(id string) error {
	_, err := d.conn.Exec(`UPDATE tasks SET archived = 1, updated = ? WHERE id = ?`,
		formatTS(time.Now()), id)
	return err
}

// MovePosition swaps the selected task's position with its neighbour in the
// currently-filtered list. Callers pass the filtered IDs (in display order)
// so we can look up the neighbour without re-running the query.
func (d *DB) MovePosition(orderedIDs []string, id string, delta int) error {
	idx := -1
	for i, tid := range orderedIDs {
		if tid == id {
			idx = i
			break
		}
	}
	if idx < 0 {
		return fmt.Errorf("task %s not in current view", id)
	}
	j := idx + delta
	if j < 0 || j >= len(orderedIDs) {
		return nil // at edge, no-op
	}

	tx, err := d.conn.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()

	// Ensure every row in the view has a position. Assign sequential
	// positions based on the visible order so we have a stable frame of
	// reference, then swap the two cells.
	for i, tid := range orderedIDs {
		if _, err := tx.Exec(`UPDATE tasks SET position = ? WHERE id = ?`, i, tid); err != nil {
			return err
		}
	}
	if _, err := tx.Exec(`UPDATE tasks SET position = ? WHERE id = ?`, j, orderedIDs[idx]); err != nil {
		return err
	}
	if _, err := tx.Exec(`UPDATE tasks SET position = ? WHERE id = ?`, idx, orderedIDs[j]); err != nil {
		return err
	}
	return tx.Commit()
}

// ---------- scanning helpers ----------

type rowScanner interface {
	Scan(...any) error
}

func scanTask(r rowScanner) (*Task, error) {
	var (
		t           Task
		catsRaw     string
		depsRaw     string
		confRaw     string
		project     sql.NullString
		completed   sql.NullString
		reasoning   sql.NullString
		priorityID  sql.NullString
		archivedInt int
		pinnedInt   int
		dueRaw      string
		createdRaw  string
		updatedRaw  string
		position    sql.NullInt64
	)
	err := r.Scan(
		&t.ID, &t.Title, &t.Description, &catsRaw, &t.Workspace, &project,
		&dueRaw, &t.Status, &depsRaw, &createdRaw, &updatedRaw, &completed,
		&confRaw, &reasoning, &priorityID, &archivedInt, &pinnedInt, &position,
	)
	if err != nil {
		return nil, err
	}

	_ = json.Unmarshal([]byte(catsRaw), &t.Categories)
	_ = json.Unmarshal([]byte(depsRaw), &t.Dependencies)
	_ = json.Unmarshal([]byte(confRaw), &t.Confidence)

	t.Project = project.String
	t.Reasoning = reasoning.String
	t.PriorityID = priorityID.String
	t.Archived = archivedInt != 0
	t.Pinned = pinnedInt != 0

	t.Due = parseTS(dueRaw)
	t.Created = parseTS(createdRaw)
	t.Updated = parseTS(updatedRaw)
	if completed.Valid {
		ts := parseTS(completed.String)
		t.Completed = &ts
	}
	if position.Valid {
		p := int(position.Int64)
		t.Position = &p
	}
	return &t, nil
}

// ---------- small helpers ----------

func coalesceStrings(s []string) []string {
	if s == nil {
		return []string{}
	}
	return s
}

func coalesceConfidence(m map[string]float64) map[string]float64 {
	if m == nil {
		return map[string]float64{}
	}
	return m
}

func nullableStr(s string) any {
	if s == "" {
		return nil
	}
	return s
}

func nullableTime(t *time.Time) any {
	if t == nil {
		return nil
	}
	return formatTS(*t)
}

func orDefault(s, d string) string {
	if s == "" {
		return d
	}
	return s
}

func formatTS(t time.Time) string {
	// Microseconds to match Python's datetime.isoformat() default.
	return t.Format("2006-01-02T15:04:05.000000")
}

// parseTS tolerates both microsecond-precision and second-precision ISO
// timestamps (the two formats produced by Python across its history).
func parseTS(s string) time.Time {
	if s == "" {
		return time.Time{}
	}
	layouts := []string{
		"2006-01-02T15:04:05.000000",
		"2006-01-02T15:04:05",
		time.RFC3339,
	}
	for _, l := range layouts {
		if t, err := time.ParseInLocation(l, s, time.Local); err == nil {
			return t
		}
	}
	return time.Time{}
}
