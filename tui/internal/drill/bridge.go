// Package drill owns the long-lived Python helper subprocess that backs the
// drill TUI. Requests are JSON line-delimited; responses are read in lockstep.
package drill

import (
	"bufio"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"sync"
)

type Bridge struct {
	cmd    *exec.Cmd
	stdin  io.WriteCloser
	stdout *bufio.Reader

	mu      sync.Mutex
	ready   bool
	readyCh chan error
	closed  bool
}

// Drill mirrors the Python helper's _serialise_drill output.
type Drill struct {
	Filename        string                   `json:"filename"`
	Title           string                   `json:"title"`
	Language        string                   `json:"language"`
	Tags            []string                 `json:"tags"`
	WhyCaptured     string                   `json:"why_captured"`
	Prompt          string                   `json:"prompt"`
	ModelAnswer     string                   `json:"model_answer"`
	LadderStep      int                      `json:"ladder_step"`
	NextReview      string                   `json:"next_review"`
	LastReviewed    *string                  `json:"last_reviewed"`
	ReviewCount     int                      `json:"review_count"`
	FailStreak      int                      `json:"fail_streak"`
	NeedsRewrite    bool                     `json:"needs_rewrite"`
	VariantsStatus  string                   `json:"variants_status"`
	BuddyVariants   []map[string]interface{} `json:"buddy_variants"`
	ReverseVariants []map[string]interface{} `json:"reverse_variants"`
}

// SimilarMatch mirrors find_similar_drills output.
type SimilarMatch struct {
	Filename   string  `json:"filename"`
	Title      string  `json:"title"`
	Similarity float64 `json:"similarity"`
}

// AddRequest captures all fields needed for op=add.
type AddRequest struct {
	Title        string   `json:"title"`
	Prompt       string   `json:"prompt"`
	ModelAnswer  string   `json:"model_answer"`
	Language     string   `json:"language"`
	WhyCaptured  string   `json:"why_captured"`
	Tags         []string `json:"tags"`
	Force        bool     `json:"force"`
	SkipVariants bool     `json:"skip_variants"`
}

// AddResponse: either Created is set (success) or Similar is non-nil (dedup hit).
type AddResponse struct {
	Created        string         `json:"created"`
	VariantsStatus string         `json:"variants_status"`
	Similar        []SimilarMatch `json:"similar"`
}

type rawResponse struct {
	Ready          bool             `json:"ready"`
	Error          string           `json:"error"`
	Drills         []Drill          `json:"drills"`
	Drill          *Drill           `json:"drill"`
	Matches        []SimilarMatch   `json:"matches"`
	Created        string           `json:"created"`
	VariantsStatus string           `json:"variants_status"`
	Similar        []SimilarMatch   `json:"similar"`
}

// Start launches the Python helper.
func Start(repoRoot string) (*Bridge, error) {
	py, err := resolvePython(repoRoot)
	if err != nil {
		return nil, err
	}
	script := filepath.Join(repoRoot, "tui", "helper", "learnbase_drill.py")
	if _, err := os.Stat(script); err != nil {
		return nil, fmt.Errorf("drill helper missing at %s: %w", script, err)
	}

	cmd := exec.Command(py, script)
	cmd.Env = append(os.Environ(), "PYTHONUNBUFFERED=1")

	stdin, err := cmd.StdinPipe()
	if err != nil {
		return nil, err
	}
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return nil, err
	}
	stderr, err := cmd.StderrPipe()
	if err != nil {
		return nil, err
	}

	if err := cmd.Start(); err != nil {
		return nil, fmt.Errorf("start drill helper: %w", err)
	}

	b := &Bridge{
		cmd:     cmd,
		stdin:   stdin,
		stdout:  bufio.NewReader(stdout),
		readyCh: make(chan error, 1),
	}

	go b.waitReady()
	go drain(stderr)
	return b, nil
}

func (b *Bridge) waitReady() {
	line, err := b.stdout.ReadBytes('\n')
	if err != nil {
		b.readyCh <- fmt.Errorf("drill helper produced no output: %w", err)
		return
	}
	var resp rawResponse
	if err := json.Unmarshal(line, &resp); err != nil {
		b.readyCh <- fmt.Errorf("drill helper malformed init: %s", string(line))
		return
	}
	if resp.Error != "" {
		b.readyCh <- errors.New(resp.Error)
		return
	}
	if !resp.Ready {
		b.readyCh <- fmt.Errorf("drill helper unexpected init: %s", string(line))
		return
	}
	b.mu.Lock()
	b.ready = true
	b.mu.Unlock()
	b.readyCh <- nil
}

// Ready blocks until the helper is initialised (or errors).
func (b *Bridge) Ready() error { return <-b.readyCh }

// Close terminates the helper.
func (b *Bridge) Close() {
	b.mu.Lock()
	if b.closed {
		b.mu.Unlock()
		return
	}
	b.closed = true
	b.mu.Unlock()
	_ = b.stdin.Close()
	_ = b.cmd.Process.Kill()
	_ = b.cmd.Wait()
}

func (b *Bridge) call(req map[string]interface{}) (rawResponse, error) {
	b.mu.Lock()
	defer b.mu.Unlock()
	var resp rawResponse
	if b.closed {
		return resp, errors.New("drill helper closed")
	}
	if !b.ready {
		return resp, errors.New("drill helper not ready")
	}
	payload, err := json.Marshal(req)
	if err != nil {
		return resp, err
	}
	if _, err := b.stdin.Write(append(payload, '\n')); err != nil {
		return resp, fmt.Errorf("write request: %w", err)
	}
	line, err := b.stdout.ReadBytes('\n')
	if err != nil {
		return resp, fmt.Errorf("read response: %w", err)
	}
	if err := json.Unmarshal(line, &resp); err != nil {
		return resp, fmt.Errorf("parse response: %w: %s", err, string(line))
	}
	if resp.Error != "" {
		return resp, errors.New(resp.Error)
	}
	return resp, nil
}

func (b *Bridge) ListDue(limit int) ([]Drill, error) {
	req := map[string]interface{}{"op": "list_due"}
	if limit > 0 {
		req["limit"] = limit
	}
	resp, err := b.call(req)
	if err != nil {
		return nil, err
	}
	return resp.Drills, nil
}

func (b *Bridge) Get(filename string) (*Drill, error) {
	resp, err := b.call(map[string]interface{}{"op": "get", "filename": filename})
	if err != nil {
		return nil, err
	}
	return resp.Drill, nil
}

func (b *Bridge) Review(filename string, passed bool, mode string, isFirstMode bool) (*Drill, error) {
	resp, err := b.call(map[string]interface{}{
		"op":            "review",
		"filename":      filename,
		"passed":        passed,
		"mode":          mode,
		"is_first_mode": isFirstMode,
	})
	if err != nil {
		return nil, err
	}
	return resp.Drill, nil
}

func (b *Bridge) Add(req AddRequest) (*AddResponse, error) {
	body := map[string]interface{}{
		"op":            "add",
		"title":         req.Title,
		"prompt":        req.Prompt,
		"model_answer":  req.ModelAnswer,
		"language":      req.Language,
		"why_captured":  req.WhyCaptured,
		"tags":          req.Tags,
		"force":         req.Force,
		"skip_variants": req.SkipVariants,
	}
	resp, err := b.call(body)
	if err != nil {
		return nil, err
	}
	return &AddResponse{
		Created:        resp.Created,
		VariantsStatus: resp.VariantsStatus,
		Similar:        resp.Similar,
	}, nil
}

func (b *Bridge) Regenerate(filename string) (*Drill, error) {
	resp, err := b.call(map[string]interface{}{"op": "regenerate", "filename": filename})
	if err != nil {
		return nil, err
	}
	return resp.Drill, nil
}

func drain(r io.Reader) {
	_, _ = io.Copy(io.Discard, r)
}

func resolvePython(repoRoot string) (string, error) {
	if p := os.Getenv("LEARNBASE_PYTHON"); p != "" {
		if _, err := os.Stat(p); err == nil {
			return p, nil
		}
	}
	venv := filepath.Join(repoRoot, "venv", "bin", "python")
	if _, err := os.Stat(venv); err == nil {
		return venv, nil
	}
	if p, err := exec.LookPath("python3"); err == nil {
		return p, nil
	}
	return "", errors.New("no Python interpreter found (set LEARNBASE_PYTHON, create venv/, or install python3)")
}
