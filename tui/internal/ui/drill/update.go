package drill

import (
	"fmt"
	"os"
	"os/exec"
	"strings"

	tea "github.com/charmbracelet/bubbletea"

	dbridge "github.com/jaz/learnbase/tui/internal/drill"
)

// ---------- messages ----------

type loadedMsg struct {
	drills []dbridge.Drill
	err    error
}

type reviewedMsg struct {
	drill *dbridge.Drill
	err   error
}

type capturedMsg struct {
	resp *dbridge.AddResponse
	err  error
}

type editorReturnedMsg struct {
	content string
	err     error
}

type captureFinishedMsg struct {
	req *dbridge.AddRequest
	err error
}

func loadDueCmd(b *dbridge.Bridge) tea.Cmd {
	return func() tea.Msg {
		drills, err := b.ListDue(0)
		return loadedMsg{drills: drills, err: err}
	}
}

func reviewCmd(b *dbridge.Bridge, filename string, passed bool, mode string, isFirst bool) tea.Cmd {
	return func() tea.Msg {
		d, err := b.Review(filename, passed, mode, isFirst)
		return reviewedMsg{drill: d, err: err}
	}
}

func captureCmd(b *dbridge.Bridge, req dbridge.AddRequest) tea.Cmd {
	return func() tea.Msg {
		resp, err := b.Add(req)
		return capturedMsg{resp: resp, err: err}
	}
}

// Update routes messages.
func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		// give the textinput a generous fraction of the terminal
		m.input.Width = max(20, msg.Width-10)
		return m, nil

	case loadedMsg:
		if msg.err != nil {
			m.err = msg.err.Error()
			return m, nil
		}
		m.queue = msg.drills
		m.queueIdx = 0
		m.passes, m.fails = 0, 0
		m.phase = PhaseSummary
		m.err = ""
		return m, nil

	case reviewedMsg:
		if msg.err != nil {
			m.err = msg.err.Error()
			return m, nil
		}
		// advance queue
		m.queueIdx++
		if m.queueIdx >= len(m.queue) {
			m.phase = PhaseFinished
			m.current = nil
			return m, nil
		}
		return m.startCard(), nil

	case editorReturnedMsg:
		if msg.err != nil {
			m.err = msg.err.Error()
			return m, nil
		}
		m.multilineAns = msg.content
		m.phase = PhaseRevealed
		return m, nil

	case captureFinishedMsg:
		m.phase = PhaseSummary
		if msg.err != nil {
			m.err = msg.err.Error()
			return m, nil
		}
		if msg.req == nil {
			m.status = "capture cancelled"
			return m, nil
		}
		return m, captureCmd(m.bridge, *msg.req)

	case capturedMsg:
		if msg.err != nil {
			m.err = msg.err.Error()
			return m, nil
		}
		if len(msg.resp.Similar) > 0 {
			titles := []string{}
			for _, s := range msg.resp.Similar {
				titles = append(titles, fmt.Sprintf("  - %s (%.2f)", s.Title, s.Similarity))
			}
			m.status = "Similar drills already exist (capture skipped):\n" + strings.Join(titles, "\n")
			return m, nil
		}
		m.status = fmt.Sprintf("✓ Captured: %s (variants: %s)", msg.resp.Created, msg.resp.VariantsStatus)
		return m, loadDueCmd(m.bridge)

	case tea.KeyMsg:
		return m.handleKey(msg)
	}
	return m, nil
}

func (m Model) handleKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	// global keys
	switch msg.Type {
	case tea.KeyCtrlC:
		return m, tea.Quit
	}
	if msg.Type == tea.KeyRunes && len(msg.Runes) == 1 && msg.Runes[0] == 'q' {
		// 'q' quits except inside the textinput while attempting (let user type 'q')
		if m.phase != PhaseAttempt {
			return m, tea.Quit
		}
	}

	switch m.phase {
	case PhaseLoading:
		return m, nil
	case PhaseSummary:
		return m.handleSummaryKey(msg)
	case PhaseAttempt:
		return m.handleAttemptKey(msg)
	case PhaseRevealed:
		return m.handleRevealedKey(msg)
	case PhaseFinished:
		return m.handleFinishedKey(msg)
	}
	return m, nil
}

func (m Model) handleSummaryKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch msg.Type {
	case tea.KeyEnter:
		if len(m.queue) == 0 {
			return m, nil
		}
		return m.startCard(), nil
	case tea.KeyEsc:
		m.err = ""
		m.status = ""
		return m, nil
	case tea.KeyRunes:
		if len(msg.Runes) == 1 {
			switch msg.Runes[0] {
			case 'c':
				return m, openCaptureEditorCmd()
			case 'r':
				return m, loadDueCmd(m.bridge)
			}
		}
	}
	return m, nil
}

func (m Model) handleAttemptKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch msg.Type {
	case tea.KeyTab:
		m.mode = m.mode.Next()
		m.input.Reset()
		m.multilineAns = ""
		// Re-pick variant on mode change so we surface a relevant one.
		m.variantIx = 0
		return m, nil
	case tea.KeyCtrlE:
		return m, openAnswerEditorCmd(m.current.Language, m.input.Value())
	case tea.KeyEnter:
		typed := strings.TrimSpace(m.input.Value())
		if typed == "" && m.multilineAns == "" {
			return m, nil // require at least something typed (type-first-lock)
		}
		m.phase = PhaseRevealed
		return m, nil
	case tea.KeyEsc:
		m.phase = PhaseSummary
		return m, nil
	}
	var cmd tea.Cmd
	m.input, cmd = m.input.Update(msg)
	return m, cmd
}

func (m Model) handleRevealedKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch msg.Type {
	case tea.KeyEsc:
		m.phase = PhaseAttempt
		return m, nil
	case tea.KeyTab:
		// allow cycling modes after reveal too — for free practice on the same card.
		// (SR has already been counted for the first mode if user submits.)
		m.mode = m.mode.Next()
		m.input.Reset()
		m.multilineAns = ""
		m.input.Focus()
		m.phase = PhaseAttempt
		return m, nil
	}
	if msg.Type == tea.KeyRunes && len(msg.Runes) == 1 {
		switch msg.Runes[0] {
		case 'p':
			return m.submitVerdict(true)
		case 'f':
			return m.submitVerdict(false)
		}
	}
	return m, nil
}

func (m Model) handleFinishedKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch msg.Type {
	case tea.KeyEnter:
		return m, loadDueCmd(m.bridge)
	}
	if msg.Type == tea.KeyRunes && len(msg.Runes) == 1 {
		if msg.Runes[0] == 'c' {
			return m, openCaptureEditorCmd()
		}
	}
	return m, nil
}

func (m Model) submitVerdict(passed bool) (tea.Model, tea.Cmd) {
	if m.current == nil {
		return m, nil
	}
	filename := m.current.Filename
	isFirst := !m.firstModeID[filename]
	m.firstModeID[filename] = true
	if passed {
		m.passes++
	} else {
		m.fails++
	}
	return m, reviewCmd(m.bridge, filename, passed, m.mode.Label(), isFirst)
}

func (m Model) startCard() Model {
	if m.queueIdx >= len(m.queue) {
		m.phase = PhaseFinished
		return m
	}
	d := m.queue[m.queueIdx]
	m.current = &d
	m.mode = ModeDrill
	m.input.Reset()
	m.input.Focus()
	m.multilineAns = ""
	m.variantIx = m.sessionRand.Intn(maxVariants(d, m.mode))
	m.phase = PhaseAttempt
	m.err = ""
	return m
}

func maxVariants(d dbridge.Drill, mode Mode) int {
	n := 0
	switch mode {
	case ModeBuddy:
		n = len(d.BuddyVariants)
	case ModeReverse:
		n = len(d.ReverseVariants)
	}
	if n == 0 {
		return 1
	}
	return n
}

// ---------- $EDITOR drop-out ----------

func openAnswerEditorCmd(language, current string) tea.Cmd {
	return tea.ExecProcess(buildEditorCmd(answerTemplate(language, current)), func(err error) tea.Msg {
		if err != nil {
			return editorReturnedMsg{err: err}
		}
		content, readErr := readEditorBuffer()
		return editorReturnedMsg{content: content, err: readErr}
	})
}

func answerTemplate(language, current string) string {
	if current == "" {
		return fmt.Sprintf("# Type your answer below (%s). Save and exit when done.\n# Lines starting with # are stripped.\n\n", language)
	}
	return fmt.Sprintf("# Type your answer below (%s). Save and exit when done.\n# Lines starting with # are stripped.\n\n%s", language, current)
}

var editorBufferPath string

func buildEditorCmd(template string) *exec.Cmd {
	editor := os.Getenv("EDITOR")
	if editor == "" {
		editor = "vim"
	}
	tmp, err := os.CreateTemp("", "learnbase-drill-*.txt")
	if err != nil {
		// surface as error path — caller should handle the read failing
		return exec.Command("false")
	}
	editorBufferPath = tmp.Name()
	_, _ = tmp.WriteString(template)
	tmp.Close()
	return exec.Command(editor, editorBufferPath)
}

func readEditorBuffer() (string, error) {
	if editorBufferPath == "" {
		return "", fmt.Errorf("no editor buffer")
	}
	data, err := os.ReadFile(editorBufferPath)
	_ = os.Remove(editorBufferPath)
	editorBufferPath = ""
	if err != nil {
		return "", err
	}
	// Strip lines beginning with '#'.
	lines := []string{}
	for _, line := range strings.Split(string(data), "\n") {
		if strings.HasPrefix(strings.TrimSpace(line), "#") {
			continue
		}
		lines = append(lines, line)
	}
	return strings.TrimSpace(strings.Join(lines, "\n")), nil
}

// openCaptureEditorCmd builds a single-template capture flow.
// User fills in fields between markers, saves, and the result is parsed.
func openCaptureEditorCmd() tea.Cmd {
	template := captureTemplate()
	return tea.ExecProcess(buildEditorCmd(template), func(err error) tea.Msg {
		if err != nil {
			return captureFinishedMsg{err: err}
		}
		raw, readErr := readEditorBufferRaw()
		if readErr != nil {
			return captureFinishedMsg{err: readErr}
		}
		req, parseErr := parseCaptureTemplate(raw)
		if parseErr != nil {
			return captureFinishedMsg{err: parseErr}
		}
		if req == nil {
			return captureFinishedMsg{} // cancelled (empty)
		}
		return captureFinishedMsg{req: req}
	})
}

func captureTemplate() string {
	return `# Drill capture template — fill the fields below the [TAGS] markers.
# Lines starting with '#' are comments and stripped on save.
# Required: TITLE, PROMPT, ANSWER, LANGUAGE.

[TITLE]


[LANGUAGE]
bash

[PROMPT]


[ANSWER]


[WHY]


[TAGS]

`
}

// readEditorBufferRaw is like readEditorBuffer but preserves '#' lines so
// section markers like [TITLE] survive parsing.
func readEditorBufferRaw() (string, error) {
	if editorBufferPath == "" {
		return "", fmt.Errorf("no editor buffer")
	}
	data, err := os.ReadFile(editorBufferPath)
	_ = os.Remove(editorBufferPath)
	editorBufferPath = ""
	if err != nil {
		return "", err
	}
	return string(data), nil
}

func parseCaptureTemplate(raw string) (*dbridge.AddRequest, error) {
	sections := map[string]string{}
	current := ""
	var buf []string
	flush := func() {
		if current != "" {
			sections[current] = strings.TrimSpace(strings.Join(buf, "\n"))
		}
		buf = nil
	}
	for _, line := range strings.Split(raw, "\n") {
		t := strings.TrimSpace(line)
		if strings.HasPrefix(t, "#") {
			continue
		}
		if strings.HasPrefix(t, "[") && strings.HasSuffix(t, "]") {
			flush()
			current = strings.Trim(t, "[]")
			continue
		}
		if current != "" {
			buf = append(buf, line)
		}
	}
	flush()

	if sections["TITLE"] == "" && sections["PROMPT"] == "" && sections["ANSWER"] == "" {
		return nil, nil // treat as cancellation
	}
	missing := []string{}
	for _, key := range []string{"TITLE", "LANGUAGE", "PROMPT", "ANSWER"} {
		if sections[key] == "" {
			missing = append(missing, key)
		}
	}
	if len(missing) > 0 {
		return nil, fmt.Errorf("capture missing required fields: %s", strings.Join(missing, ", "))
	}

	tags := []string{}
	if sections["TAGS"] != "" {
		for _, t := range strings.Split(sections["TAGS"], ",") {
			t = strings.TrimSpace(t)
			if t != "" {
				tags = append(tags, t)
			}
		}
	}

	return &dbridge.AddRequest{
		Title:       sections["TITLE"],
		Language:    sections["LANGUAGE"],
		Prompt:      sections["PROMPT"],
		ModelAnswer: sections["ANSWER"],
		WhyCaptured: sections["WHY"],
		Tags:        tags,
	}, nil
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
