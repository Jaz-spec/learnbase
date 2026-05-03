// Package drill is the Bubble Tea TUI for code drill flashcards.
package drill

// Mode is which of the three review modes the user is in.
type Mode int

const (
	ModeDrill Mode = iota
	ModeBuddy
	ModeReverse
)

func (m Mode) Label() string {
	switch m {
	case ModeDrill:
		return "Drill"
	case ModeBuddy:
		return "Buddy"
	case ModeReverse:
		return "Reverse"
	}
	return "?"
}

func (m Mode) Next() Mode { return (m + 1) % 3 }

func (m Mode) Description() string {
	switch m {
	case ModeDrill:
		return "Produce — write the answer from a blank prompt"
	case ModeBuddy:
		return "Repair — given a broken version, produce the fix"
	case ModeReverse:
		return "Review — judge whether the candidate is correct"
	}
	return ""
}

// Phase is the current high-level UI state.
type Phase int

const (
	PhaseLoading Phase = iota
	PhaseSummary
	PhaseAttempt
	PhaseRevealed
	PhaseFinished
	PhaseCaptureWait // running $EDITOR for capture
)
