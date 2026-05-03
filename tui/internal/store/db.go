// Package store is the Go-side data layer for tasks / priorities / projects
// stored in ~/.learnbase/tasks.db. The Python MCP server owns the same DB;
// both sides rely on WAL mode for concurrent read/write safety.
package store

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"

	_ "modernc.org/sqlite"
)

// DB wraps the connection and manager factories.
type DB struct {
	conn *sql.DB
}

// Open connects to ~/.learnbase/tasks.db, sets WAL + busy_timeout to match
// the Python side, and runs the one idempotent migration the TUI needs
// (ADD COLUMN position).
func Open() (*DB, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return nil, err
	}
	path := filepath.Join(home, ".learnbase", "tasks.db")
	if _, err := os.Stat(path); err != nil {
		return nil, fmt.Errorf("tasks.db not found at %s (is the MCP server set up?): %w", path, err)
	}

	conn, err := sql.Open("sqlite", path+"?_pragma=journal_mode(WAL)&_pragma=busy_timeout(5000)")
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}
	// One writer at a time is a SQLite-wide rule; SetMaxOpenConns(1) avoids
	// lock thrashing when the TUI runs concurrent reads + writes.
	conn.SetMaxOpenConns(1)

	d := &DB{conn: conn}
	if err := d.migrate(); err != nil {
		_ = conn.Close()
		return nil, err
	}
	return d, nil
}

func (d *DB) Close() error { return d.conn.Close() }

// migrate runs idempotent schema bumps the TUI depends on.
func (d *DB) migrate() error {
	// Manual ordering column on tasks — NULL for existing rows so they fall
	// through to the due-date sort. Python is forward-compatible (SELECTs
	// name explicit columns; INSERTs omit this).
	if !d.hasColumn("tasks", "position") {
		if _, err := d.conn.Exec(`ALTER TABLE tasks ADD COLUMN position INTEGER`); err != nil {
			return fmt.Errorf("add tasks.position column: %w", err)
		}
	}
	if !d.hasColumn("tasks", "pinned") {
		if _, err := d.conn.Exec(`ALTER TABLE tasks ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0`); err != nil {
			return fmt.Errorf("add tasks.pinned column: %w", err)
		}
	}
	return nil
}

func (d *DB) hasColumn(table, col string) bool {
	rows, err := d.conn.Query(fmt.Sprintf("PRAGMA table_info(%s)", table))
	if err != nil {
		return false
	}
	defer rows.Close()
	for rows.Next() {
		var cid int
		var name, ctype string
		var notnull, pk int
		var dflt sql.NullString
		if err := rows.Scan(&cid, &name, &ctype, &notnull, &dflt, &pk); err != nil {
			return false
		}
		if name == col {
			return true
		}
	}
	return false
}
