package search

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

// Semantic owns a long-lived Python subprocess that answers semantic queries
// via the existing RAGManager. Queries are serialised; a response is read
// before the next request is sent.
type Semantic struct {
	cmd    *exec.Cmd
	stdin  io.WriteCloser
	stdout *bufio.Reader
	stderr io.ReadCloser

	mu      sync.Mutex
	ready   bool
	readyCh chan error
	closed  bool
}

type helperRequest struct {
	Query string `json:"query"`
	Limit int    `json:"limit"`
}

type helperResponse struct {
	Ready   bool             `json:"ready,omitempty"`
	Error   string           `json:"error,omitempty"`
	Results []helperResultIn `json:"results,omitempty"`
}

type helperResultIn struct {
	Filename   string   `json:"filename"`
	Title      string   `json:"title"`
	Similarity *float64 `json:"similarity"`
	NoteType   string   `json:"note_type"`
}

// StartSemantic launches the Python helper and waits (asynchronously) for the
// readiness signal. Ready() / Query() block until init completes or fails.
// repoRoot is the learnbase repo root (used to find the helper script and
// resolve the Python interpreter).
func StartSemantic(repoRoot string) (*Semantic, error) {
	py, err := resolvePython(repoRoot)
	if err != nil {
		return nil, err
	}
	script := filepath.Join(repoRoot, "tui", "helper", "learnbase_search.py")
	if _, err := os.Stat(script); err != nil {
		return nil, fmt.Errorf("helper script missing at %s: %w", script, err)
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
		return nil, fmt.Errorf("start helper: %w", err)
	}

	s := &Semantic{
		cmd:     cmd,
		stdin:   stdin,
		stdout:  bufio.NewReader(stdout),
		stderr:  stderr,
		readyCh: make(chan error, 1),
	}

	go s.waitReady()
	go drain(stderr)
	return s, nil
}

func (s *Semantic) waitReady() {
	line, err := s.stdout.ReadBytes('\n')
	if err != nil {
		s.readyCh <- fmt.Errorf("helper produced no output: %w", err)
		return
	}
	var resp helperResponse
	if err := json.Unmarshal(line, &resp); err != nil {
		s.readyCh <- fmt.Errorf("helper sent malformed init: %s", string(line))
		return
	}
	if resp.Error != "" {
		s.readyCh <- errors.New(resp.Error)
		return
	}
	if !resp.Ready {
		s.readyCh <- fmt.Errorf("helper sent unexpected init: %s", string(line))
		return
	}
	s.mu.Lock()
	s.ready = true
	s.mu.Unlock()
	s.readyCh <- nil
}

// Ready blocks until the helper has finished loading (or failed).
func (s *Semantic) Ready() error {
	return <-s.readyCh
}

// Query sends a request and returns results.
func (s *Semantic) Query(query string, limit int) ([]Result, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.closed {
		return nil, errors.New("semantic helper closed")
	}
	if !s.ready {
		return nil, errors.New("semantic helper not ready")
	}

	req := helperRequest{Query: query, Limit: limit}
	payload, err := json.Marshal(req)
	if err != nil {
		return nil, err
	}
	if _, err := s.stdin.Write(append(payload, '\n')); err != nil {
		return nil, fmt.Errorf("write query: %w", err)
	}

	line, err := s.stdout.ReadBytes('\n')
	if err != nil {
		return nil, fmt.Errorf("read response: %w", err)
	}
	var resp helperResponse
	if err := json.Unmarshal(line, &resp); err != nil {
		return nil, fmt.Errorf("parse response: %w: %s", err, string(line))
	}
	if resp.Error != "" {
		return nil, errors.New(resp.Error)
	}

	out := make([]Result, 0, len(resp.Results))
	for _, r := range resp.Results {
		score := 0.0
		known := false
		if r.Similarity != nil {
			score = *r.Similarity
			known = true
		}
		out = append(out, Result{
			Filename:   r.Filename,
			Title:      r.Title,
			Score:      score,
			ScoreKnown: known,
		})
	}
	return out, nil
}

// Close stops the helper subprocess.
func (s *Semantic) Close() {
	s.mu.Lock()
	if s.closed {
		s.mu.Unlock()
		return
	}
	s.closed = true
	s.mu.Unlock()
	_ = s.stdin.Close()
	_ = s.cmd.Process.Kill()
	_ = s.cmd.Wait()
}

func drain(r io.Reader) {
	// Discard stderr so the pipe never blocks. Helper errors are surfaced via
	// the JSON protocol on stdout.
	_, _ = io.Copy(io.Discard, r)
}

// resolvePython picks the Python interpreter for the helper, in priority order:
//  1. $LEARNBASE_PYTHON
//  2. <repoRoot>/venv/bin/python
//  3. python3 on PATH
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
