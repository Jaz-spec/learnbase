package drill

import (
	"math/rand"

	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"

	"github.com/jaz/learnbase/tui/internal/drill"
)

// Model is the top-level TUI state.
type Model struct {
	width, height int
	styles        *styles
	bridge        *drill.Bridge

	phase Phase

	// Queue
	queue       []drill.Drill
	queueIdx    int
	passes      int
	fails       int
	firstModeID map[string]bool // filename → already counted SR for this card this session

	// Current card / mode
	mode      Mode
	current   *drill.Drill
	variantIx int // which buddy/reverse variant we're showing

	// Attempt input
	input        textinput.Model
	multilineAns string // populated when user uses $EDITOR for multi-line

	// Capture state
	capturePending bool

	// Status
	err    string
	status string

	// Session meta
	sessionRand *rand.Rand
}

// NewModel constructs the TUI model. The bridge must already be Ready.
func NewModel(b *drill.Bridge) Model {
	in := textinput.New()
	in.Placeholder = "type your answer (Ctrl+E for $EDITOR, Enter to submit)"
	in.CharLimit = 0
	in.Width = 60

	return Model{
		styles:      newStyles(),
		bridge:      b,
		phase:       PhaseLoading,
		input:       in,
		firstModeID: make(map[string]bool),
		sessionRand: rand.New(rand.NewSource(1)), // deterministic per session
	}
}

// Init triggers loading the due-queue and entering alt screen.
func (m Model) Init() tea.Cmd {
	return tea.Batch(loadDueCmd(m.bridge), tea.EnterAltScreen)
}
