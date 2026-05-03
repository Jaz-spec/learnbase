package store

import (
	"fmt"
	"strings"
	"time"
)

// StalenessThresholdDays mirrors ContextManager.STALENESS_THRESHOLD_DAYS.
const StalenessThresholdDays = 14

// Staleness is the UI-facing health indicator computed at read time.
type Staleness string

const (
	StalenessFresh    Staleness = "fresh"
	StalenessStale    Staleness = "stale"
	StalenessInactive Staleness = "inactive"
)

// Project is a row from projects + computed staleness.
type Project struct {
	ID          string
	Name        string
	Workspace   string // work|personal|contract
	Description string
	Status      string // active|inactive
	UpdatedAt   time.Time
	Staleness   Staleness
}

// ListProjects returns all projects with freshly-computed staleness. Ordered
// by status ASC (active first), then most-recently-updated.
func (d *DB) ListProjects() ([]*Project, error) {
	rows, err := d.conn.Query(`
		SELECT id, name, workspace, description, status, updated_at
		FROM projects
		ORDER BY status ASC, updated_at DESC`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	now := time.Now()
	var out []*Project
	for rows.Next() {
		var (
			p           Project
			updatedRaw  string
		)
		if err := rows.Scan(&p.ID, &p.Name, &p.Workspace, &p.Description, &p.Status, &updatedRaw); err != nil {
			return nil, err
		}
		p.UpdatedAt = parseTS(updatedRaw)
		p.Staleness = computeStaleness(p.Status, p.UpdatedAt, now)
		out = append(out, &p)
	}
	return out, rows.Err()
}

// GetProject fetches by ID.
func (d *DB) GetProject(id string) (*Project, error) {
	row := d.conn.QueryRow(`
		SELECT id, name, workspace, description, status, updated_at
		FROM projects WHERE id = ?`, id)
	var (
		p          Project
		updatedRaw string
	)
	if err := row.Scan(&p.ID, &p.Name, &p.Workspace, &p.Description, &p.Status, &updatedRaw); err != nil {
		return nil, err
	}
	p.UpdatedAt = parseTS(updatedRaw)
	p.Staleness = computeStaleness(p.Status, p.UpdatedAt, time.Now())
	return &p, nil
}

// CreateProject inserts a new project row. ID is user-provided and must match
// the [a-z0-9-]+ shape (enforced upstream in the form layer).
func (d *DB) CreateProject(p *Project) error {
	if p.Status == "" {
		p.Status = "active"
	}
	p.UpdatedAt = time.Now()
	_, err := d.conn.Exec(`
		INSERT INTO projects (id, name, workspace, description, status, updated_at)
		VALUES (?, ?, ?, ?, ?, ?)`,
		p.ID, p.Name, p.Workspace, p.Description, p.Status, formatTS(p.UpdatedAt),
	)
	if err != nil {
		return fmt.Errorf("create project: %w", err)
	}
	return nil
}

// UpdateProject bumps updated_at on any change.
func (d *DB) UpdateProject(id string, patch ProjectPatch) error {
	sets := []string{"updated_at = ?"}
	args := []any{formatTS(time.Now())}

	if patch.Name != nil {
		sets = append(sets, "name = ?")
		args = append(args, *patch.Name)
	}
	if patch.Workspace != nil {
		sets = append(sets, "workspace = ?")
		args = append(args, *patch.Workspace)
	}
	if patch.Description != nil {
		sets = append(sets, "description = ?")
		args = append(args, *patch.Description)
	}
	if patch.Status != nil {
		sets = append(sets, "status = ?")
		args = append(args, *patch.Status)
	}
	args = append(args, id)
	q := "UPDATE projects SET " + strings.Join(sets, ", ") + " WHERE id = ?"
	_, err := d.conn.Exec(q, args...)
	return err
}

// ArchiveProject sets status to inactive (mirrors Python's archive_project).
func (d *DB) ArchiveProject(id string) error {
	inactive := "inactive"
	return d.UpdateProject(id, ProjectPatch{Status: &inactive})
}

// ProjectPatch is a sparse update.
type ProjectPatch struct {
	Name        *string
	Workspace   *string
	Description *string
	Status      *string
}

// computeStaleness mirrors ContextManager._annotate_staleness: inactive status
// short-circuits; otherwise 14-day threshold separates fresh from stale.
func computeStaleness(status string, updated time.Time, now time.Time) Staleness {
	if status == "inactive" {
		return StalenessInactive
	}
	if updated.IsZero() {
		return StalenessStale
	}
	if now.Sub(updated) > time.Duration(StalenessThresholdDays)*24*time.Hour {
		return StalenessStale
	}
	return StalenessFresh
}
