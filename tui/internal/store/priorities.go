package store

import (
	"database/sql"
	"fmt"
	"strings"
	"time"
)

// Priority is a row from the priorities table.
type Priority struct {
	ID          string
	ProjectID   string // nullable
	Description string
	Scope       string // monthly|weekly
	Period      string // 2026-04 or 2026-W16
	Status      string // pending|in_progress|completed|rolled_over
	CreatedAt   time.Time
	CompletedAt *time.Time
}

// priorityStatusCycle defines the progression used by Space in the TUI.
var priorityStatusCycle = []string{"pending", "in_progress", "completed", "rolled_over"}

// ListPriorities returns all priorities, monthly first, newest period first.
func (d *DB) ListPriorities() ([]*Priority, error) {
	rows, err := d.conn.Query(`
		SELECT id, project_id, description, scope, period, status, created_at, completed_at
		FROM priorities
		ORDER BY scope DESC, period DESC, created_at DESC`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var out []*Priority
	for rows.Next() {
		p, err := scanPriority(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, p)
	}
	return out, rows.Err()
}

// GetPriority fetches one by ID.
func (d *DB) GetPriority(id string) (*Priority, error) {
	row := d.conn.QueryRow(`
		SELECT id, project_id, description, scope, period, status, created_at, completed_at
		FROM priorities WHERE id = ?`, id)
	return scanPriority(row)
}

// CreatePriority mirrors PlanningManager.create_priority.
func (d *DB) CreatePriority(p *Priority) error {
	if p.ID == "" {
		p.ID = PriorityID(p.Scope, p.Period, p.Description)
	}
	if p.CreatedAt.IsZero() {
		p.CreatedAt = time.Now()
	}
	if p.Status == "" {
		p.Status = "pending"
	}
	_, err := d.conn.Exec(`
		INSERT INTO priorities (id, project_id, description, scope, period, status, created_at, completed_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
		p.ID, nullableStr(p.ProjectID), p.Description, p.Scope, p.Period, p.Status,
		formatTS(p.CreatedAt), nullableTime(p.CompletedAt),
	)
	if err != nil {
		return fmt.Errorf("create priority: %w", err)
	}
	return nil
}

// UpdatePriority supports sparse patches.
func (d *DB) UpdatePriority(id string, patch PriorityPatch) error {
	sets := []string{}
	args := []any{}

	if patch.Description != nil {
		sets = append(sets, "description = ?")
		args = append(args, *patch.Description)
	}
	if patch.ProjectID != nil {
		sets = append(sets, "project_id = ?")
		args = append(args, nullableStr(*patch.ProjectID))
	}
	if patch.Scope != nil {
		sets = append(sets, "scope = ?")
		args = append(args, *patch.Scope)
	}
	if patch.Period != nil {
		sets = append(sets, "period = ?")
		args = append(args, *patch.Period)
	}
	if patch.Status != nil {
		sets = append(sets, "status = ?")
		args = append(args, *patch.Status)
		if *patch.Status == "completed" {
			sets = append(sets, "completed_at = ?")
			args = append(args, formatTS(time.Now()))
		} else {
			sets = append(sets, "completed_at = NULL")
		}
	}
	if len(sets) == 0 {
		return nil
	}
	args = append(args, id)
	q := "UPDATE priorities SET " + strings.Join(sets, ", ") + " WHERE id = ?"
	_, err := d.conn.Exec(q, args...)
	return err
}

// CyclePriorityStatus bumps status → next in cycle.
func (d *DB) CyclePriorityStatus(id string) error {
	p, err := d.GetPriority(id)
	if err != nil {
		return err
	}
	next := priorityStatusCycle[0]
	for i, s := range priorityStatusCycle {
		if s == p.Status {
			next = priorityStatusCycle[(i+1)%len(priorityStatusCycle)]
			break
		}
	}
	return d.UpdatePriority(id, PriorityPatch{Status: &next})
}

// DeletePriority removes the row (no archived flag on priorities).
func (d *DB) DeletePriority(id string) error {
	_, err := d.conn.Exec(`DELETE FROM priorities WHERE id = ?`, id)
	return err
}

// PriorityPatch is a sparse update.
type PriorityPatch struct {
	Description *string
	ProjectID   *string
	Scope       *string
	Period      *string
	Status      *string
}

func scanPriority(r rowScanner) (*Priority, error) {
	var (
		p           Priority
		projectID   sql.NullString
		createdAt   string
		completedAt sql.NullString
	)
	err := r.Scan(&p.ID, &projectID, &p.Description, &p.Scope, &p.Period,
		&p.Status, &createdAt, &completedAt)
	if err != nil {
		return nil, err
	}
	p.ProjectID = projectID.String
	p.CreatedAt = parseTS(createdAt)
	if completedAt.Valid {
		ts := parseTS(completedAt.String)
		p.CompletedAt = &ts
	}
	return &p, nil
}
