package drill

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"

	dbridge "github.com/jaz/learnbase/tui/internal/drill"
)

// View renders the current phase.
func (m Model) View() string {
	if m.width == 0 {
		return ""
	}

	header := m.renderHeader()
	body := m.renderBody()
	footer := m.renderFooter()

	full := lipgloss.JoinVertical(lipgloss.Left, header, body, footer)
	return m.styles.app.Render(full)
}

// ---------- header (mode chips + status) ----------

func (m Model) renderHeader() string {
	if m.phase == PhaseLoading {
		return m.styles.cardMeta.Render(" learnbase-drill ") + "\n" +
			m.styles.statusDim.Render(" loading...") + "\n"
	}

	chips := []string{}
	for _, mode := range []Mode{ModeDrill, ModeBuddy, ModeReverse} {
		label := mode.Label()
		if mode == m.mode {
			chips = append(chips, m.styles.chipActive.Render("●"+label))
		} else {
			chips = append(chips, m.styles.chipIdle.Render(" "+label))
		}
	}
	chipBar := strings.Join(chips, m.styles.divider.Render(" "))

	status := ""
	switch m.phase {
	case PhaseSummary:
		status = fmt.Sprintf("%d due  ·  press Enter to start, c to capture, q to quit", len(m.queue))
	case PhaseAttempt, PhaseRevealed:
		status = fmt.Sprintf("card %d/%d  ·  passes %d  ·  fails %d", m.queueIdx+1, len(m.queue), m.passes, m.fails)
	case PhaseFinished:
		status = fmt.Sprintf("session complete  ·  passes %d  ·  fails %d", m.passes, m.fails)
	}

	bar := lipgloss.JoinHorizontal(
		lipgloss.Bottom,
		chipBar,
		m.styles.divider.Render("   "),
		m.styles.statusDim.Render(status),
	)
	return bar + "\n" + m.renderRule()
}

func (m Model) renderRule() string {
	width := m.width
	if width <= 0 {
		width = 80
	}
	return m.styles.divider.Render(strings.Repeat("─", width))
}

// ---------- footer (help + errors + status) ----------

func (m Model) renderFooter() string {
	parts := []string{}
	if m.err != "" {
		parts = append(parts, m.styles.errorText.Render("error: "+m.err))
	}
	if m.status != "" {
		parts = append(parts, m.styles.statusAccent.Render(m.status))
	}
	parts = append(parts, m.helpLine())
	return strings.Join(parts, "\n")
}

func (m Model) helpLine() string {
	hints := [][2]string{}
	switch m.phase {
	case PhaseSummary:
		hints = append(hints,
			[2]string{"enter", "start"},
			[2]string{"c", "capture"},
			[2]string{"r", "reload"},
			[2]string{"q", "quit"},
		)
	case PhaseAttempt:
		hints = append(hints,
			[2]string{"tab", "switch mode"},
			[2]string{"ctrl+e", "$EDITOR"},
			[2]string{"enter", "submit"},
			[2]string{"esc", "back"},
		)
	case PhaseRevealed:
		hints = append(hints,
			[2]string{"p", "pass"},
			[2]string{"f", "fail"},
			[2]string{"tab", "try another mode"},
			[2]string{"esc", "back"},
		)
	case PhaseFinished:
		hints = append(hints,
			[2]string{"enter", "reload due"},
			[2]string{"c", "capture"},
			[2]string{"q", "quit"},
		)
	}
	chunks := []string{}
	for _, h := range hints {
		chunks = append(chunks,
			m.styles.helpKey.Render(h[0])+" "+m.styles.helpText.Render(h[1]))
	}
	return m.styles.helpBar.Render(strings.Join(chunks, "  "))
}

// ---------- body (per-phase) ----------

func (m Model) renderBody() string {
	switch m.phase {
	case PhaseLoading:
		return m.styles.statusDim.Render("\n  loading due drills...\n")
	case PhaseSummary:
		return m.renderSummary()
	case PhaseAttempt:
		return m.renderCard(false)
	case PhaseRevealed:
		return m.renderCard(true)
	case PhaseFinished:
		return m.renderFinished()
	}
	return ""
}

func (m Model) renderSummary() string {
	if len(m.queue) == 0 {
		return "\n" + m.styles.cardMeta.Render("  No drill cards due. Press c to capture one, or q to quit.") + "\n"
	}
	lines := []string{
		"",
		"  " + m.styles.cardTitle.Render(fmt.Sprintf("Up next (%d cards)", len(m.queue))),
		"",
	}
	for i, d := range m.queue {
		marker := " "
		if i == 0 {
			marker = "▶"
		}
		flag := ""
		if d.NeedsRewrite {
			flag = " " + m.styles.flagWarn.Render("[needs rewrite]")
		}
		row := fmt.Sprintf("  %s  %s  %s%s",
			m.styles.statusAccent.Render(marker),
			m.styles.cardLabel.Render(fmt.Sprintf("[%s]", d.Language)),
			m.styles.cardValue.Render(d.Title),
			flag,
		)
		meta := m.styles.cardMeta.Render(fmt.Sprintf(
			"      step %d · reviews %d · variants %s",
			d.LadderStep, d.ReviewCount, d.VariantsStatus,
		))
		lines = append(lines, row, meta, "")
	}
	return strings.Join(lines, "\n")
}

func (m Model) renderCard(revealed bool) string {
	if m.current == nil {
		return ""
	}
	d := *m.current

	left := m.renderCardLeft(d)
	right := m.renderCardRight(d, revealed)

	leftWidth := (m.width / 2) - 2
	if leftWidth < 30 {
		leftWidth = 30
	}
	rightWidth := m.width - leftWidth - 4
	if rightWidth < 30 {
		rightWidth = 30
	}
	leftRendered := m.styles.leftPane.Width(leftWidth).Render(left)
	rightRendered := m.styles.rightPane.Width(rightWidth).Render(right)
	return lipgloss.JoinHorizontal(lipgloss.Top, leftRendered, rightRendered)
}

func (m Model) renderCardLeft(d dbridge.Drill) string {
	header := m.styles.cardTitle.Render(d.Title)
	meta := m.styles.cardMeta.Render(fmt.Sprintf(
		"%s · step %d · reviews %d",
		d.Language, d.LadderStep, d.ReviewCount,
	))

	parts := []string{header, meta, "", m.styles.cardLabel.Render("PROMPT"), m.styles.prompt.Render(d.Prompt)}

	switch m.mode {
	case ModeBuddy:
		parts = append(parts, "", m.styles.cardLabel.Render("BROKEN VARIANT — find and fix the bug:"))
		broken := pickBuddyVariant(d, m.variantIx)
		parts = append(parts, m.styles.codeBlock.Render(fenced(d.Language, broken)))
	case ModeReverse:
		parts = append(parts, "", m.styles.cardLabel.Render("CANDIDATE — is it correct? if not, why?"))
		code := pickReverseVariant(d, m.variantIx)
		parts = append(parts, m.styles.codeBlockDim.Render(fenced(d.Language, code)))
	}

	if (m.mode == ModeBuddy && d.VariantsStatus != "ready") ||
		(m.mode == ModeReverse && d.VariantsStatus != "ready") {
		parts = append(parts, "",
			m.styles.flagWarn.Render(
				"⚠ Variants status: "+d.VariantsStatus+
					"  (run regenerate_variants when ANTHROPIC_API_KEY is set)"),
		)
	}

	return strings.Join(parts, "\n")
}

func (m Model) renderCardRight(d dbridge.Drill, revealed bool) string {
	parts := []string{}

	if !revealed {
		parts = append(parts,
			m.styles.cardLabel.Render(strings.ToUpper(m.mode.Label())+" — "+m.mode.Description()),
			"",
			m.styles.cardLabel.Render("YOUR ANSWER"),
			m.styles.answerInput.Render(m.input.View()),
		)
		if m.multilineAns != "" {
			parts = append(parts, "",
				m.styles.cardLabel.Render("(multi-line buffer from $EDITOR):"),
				m.styles.codeBlock.Render(m.multilineAns),
			)
		}
		return strings.Join(parts, "\n")
	}

	// revealed phase
	user := m.input.Value()
	if m.multilineAns != "" {
		user = m.multilineAns
	}
	parts = append(parts,
		m.styles.cardLabel.Render("YOUR ANSWER"),
		m.styles.answerLocked.Render(user),
		"",
		m.styles.cardLabel.Render("MODEL ANSWER"),
		m.styles.codeBlock.Render(fenced(d.Language, d.ModelAnswer)),
	)

	switch m.mode {
	case ModeBuddy:
		bug := pickBuddyBug(d, m.variantIx)
		if bug != "" {
			parts = append(parts, "", m.styles.cardLabel.Render("BUG IN BROKEN VARIANT"), m.styles.cardValue.Render(bug))
		}
	case ModeReverse:
		correct := pickReverseCorrectness(d, m.variantIx)
		issue := pickReverseIssue(d, m.variantIx)
		verdict := m.styles.verdictPass.Render("CANDIDATE WAS CORRECT")
		if !correct {
			verdict = m.styles.verdictFail.Render("CANDIDATE WAS BUGGY")
		}
		parts = append(parts, "", verdict)
		if !correct && issue != "" {
			parts = append(parts, m.styles.cardValue.Render("Issue: "+issue))
		}
	}

	if d.WhyCaptured != "" {
		parts = append(parts, "",
			m.styles.cardLabel.Render("WHY CAPTURED"),
			m.styles.cardMeta.Render(d.WhyCaptured),
		)
	}

	parts = append(parts, "",
		m.styles.cardLabel.Render("Self-assess: "+
			m.styles.helpKey.Render("p")+m.styles.cardLabel.Render(" pass  ·  ")+
			m.styles.helpKey.Render("f")+m.styles.cardLabel.Render(" fail")),
	)

	return strings.Join(parts, "\n")
}

func (m Model) renderFinished() string {
	total := m.passes + m.fails
	rate := 0.0
	if total > 0 {
		rate = float64(m.passes) / float64(total) * 100
	}
	return strings.Join([]string{
		"",
		"  " + m.styles.cardTitle.Render("Session complete"),
		"",
		fmt.Sprintf("  %s  %d", m.styles.cardLabel.Render("passes:"), m.passes),
		fmt.Sprintf("  %s  %d", m.styles.cardLabel.Render("fails:"), m.fails),
		fmt.Sprintf("  %s  %.0f%%", m.styles.cardLabel.Render("rate:"), rate),
		"",
		"  " + m.styles.cardMeta.Render("Press Enter to reload due, c to capture, q to quit."),
		"",
	}, "\n")
}

// ---------- variant helpers ----------

func fenced(language, code string) string {
	return code
}

func pickBuddyVariant(d dbridge.Drill, ix int) string {
	if len(d.BuddyVariants) == 0 {
		return "(no variants — try Drill mode, or run regenerate_variants)"
	}
	v := d.BuddyVariants[ix%len(d.BuddyVariants)]
	if s, ok := v["broken"].(string); ok {
		return s
	}
	return ""
}

func pickBuddyBug(d dbridge.Drill, ix int) string {
	if len(d.BuddyVariants) == 0 {
		return ""
	}
	v := d.BuddyVariants[ix%len(d.BuddyVariants)]
	if s, ok := v["bug"].(string); ok {
		return s
	}
	return ""
}

func pickReverseVariant(d dbridge.Drill, ix int) string {
	if len(d.ReverseVariants) == 0 {
		return "(no variants — try Drill mode, or run regenerate_variants)"
	}
	v := d.ReverseVariants[ix%len(d.ReverseVariants)]
	if s, ok := v["code"].(string); ok {
		return s
	}
	return ""
}

func pickReverseCorrectness(d dbridge.Drill, ix int) bool {
	if len(d.ReverseVariants) == 0 {
		return true
	}
	v := d.ReverseVariants[ix%len(d.ReverseVariants)]
	if b, ok := v["correct"].(bool); ok {
		return b
	}
	return true
}

func pickReverseIssue(d dbridge.Drill, ix int) string {
	if len(d.ReverseVariants) == 0 {
		return ""
	}
	v := d.ReverseVariants[ix%len(d.ReverseVariants)]
	if s, ok := v["issue"].(string); ok {
		return s
	}
	return ""
}
