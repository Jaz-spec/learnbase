package ui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

// View renders the split layout.
func (m Model) View() string {
	if m.width < 40 || m.height < 10 {
		return m.styles.errorText.Render("terminal too small — resize to at least 40×10")
	}

	leftW, rightW := m.paneWidths()
	bodyH := m.paneHeight()

	left := m.renderLeft(leftW, bodyH)
	right := m.renderRight(rightW, bodyH)
	body := lipgloss.JoinHorizontal(lipgloss.Top, left, right)

	help := m.renderHelp(m.width)

	return lipgloss.JoinVertical(lipgloss.Left, body, help)
}

func (m Model) renderLeft(w, h int) string {
	var b strings.Builder

	// Search line.
	prompt := m.styles.input.Render("> ")
	cursor := m.styles.inputCursor.Render(" ")
	b.WriteString(prompt + m.styles.input.Render(m.query) + cursor)
	b.WriteString("\n")

	// Filter chips.
	b.WriteString(m.renderChips())
	b.WriteString("\n")

	// Status / divider.
	b.WriteString(m.styles.divider.Render(strings.Repeat("─", w-5)))
	b.WriteString("\n")

	// Results or loading/empty message.
	resultLines := h - 6 // budget: input(1) + chips(1) + divider(1) + trailing stat(1) + padding
	if resultLines < 3 {
		resultLines = 3
	}

	if m.mode == FilterSemantic && !m.semReady {
		b.WriteString(m.styles.loading.Render("[loading embeddings…]"))
		b.WriteString(strings.Repeat("\n", resultLines-1))
	} else if m.semErr != "" && m.mode == FilterSemantic {
		b.WriteString(m.styles.errorText.Render("semantic unavailable"))
		b.WriteString("\n")
		b.WriteString(m.styles.statusDim.Render(truncate(m.semErr, w-5)))
		b.WriteString(strings.Repeat("\n", max(0, resultLines-2)))
	} else if len(m.results) == 0 {
		if m.query == "" {
			b.WriteString(m.styles.statusDim.Render("type to search"))
		} else if m.inProgress {
			b.WriteString(m.styles.loading.Render("searching…"))
		} else if m.searchErr != "" {
			b.WriteString(m.styles.errorText.Render(truncate(m.searchErr, w-5)))
		} else {
			b.WriteString(m.styles.statusDim.Render("no matches"))
		}
		b.WriteString(strings.Repeat("\n", resultLines-1))
	} else {
		lines := m.renderResults(w-5, resultLines)
		b.WriteString(lines)
	}

	// Footer status.
	b.WriteString("\n")
	b.WriteString(m.styles.statusDim.Render(m.statusLine()))

	return m.styles.leftPane.Width(w).Height(h).MaxWidth(w).MaxHeight(h).Render(b.String())
}

func (m Model) renderChips() string {
	chip := func(mode FilterMode) string {
		label := mode.label()
		if mode == FilterSemantic && !m.semReady {
			label = label + "…"
		}
		if mode == m.mode {
			return m.styles.chipActive.Render("●" + label)
		}
		return m.styles.chipIdle.Render(" " + label)
	}
	return chip(FilterSemantic) + chip(FilterKeyword) + chip(FilterTag)
}

func (m Model) renderResults(width, maxLines int) string {
	start := 0
	if m.sel >= maxLines {
		start = m.sel - maxLines + 1
	}
	end := start + maxLines
	if end > len(m.results) {
		end = len(m.results)
	}

	const prefixW = 2 // "> " or "  "
	var lines []string
	for i := start; i < end; i++ {
		r := m.results[i]
		label := r.Filename
		if r.Title != "" {
			label = r.Title
		}

		scoreStr := ""
		scoreW := 0
		if r.ScoreKnown {
			scoreStr = fmt.Sprintf("%3d", int(r.Score*100))
			scoreW = 3
		}

		// Reserve 1 space between label and score when a score is shown.
		gap := 0
		if scoreW > 0 {
			gap = 1
		}

		maxLabel := width - prefixW - gap - scoreW
		if maxLabel < 1 {
			maxLabel = 1
		}
		labelTrunc := truncate(label, maxLabel)
		labelW := lipgloss.Width(labelTrunc)

		spaces := width - prefixW - labelW - scoreW
		if spaces < 0 {
			spaces = 0
		}

		prefix := "  "
		if i == m.sel {
			prefix = "> "
		}
		row := prefix + labelTrunc + strings.Repeat(" ", spaces)

		if i == m.sel {
			lines = append(lines,
				m.styles.resultSel.Render(row)+
					m.styles.resultSel.Render(scoreStr))
		} else {
			lines = append(lines,
				m.styles.resultIdle.Render(row)+
					m.styles.resultScore.Render(scoreStr))
		}
	}

	// Pad to maxLines.
	for len(lines) < maxLines {
		lines = append(lines, "")
	}
	return strings.Join(lines, "\n")
}

func (m Model) statusLine() string {
	if len(m.results) == 0 {
		return fmt.Sprintf("%d notes indexed · mode: %s", len(m.notes), m.mode.label())
	}
	return fmt.Sprintf("%d/%d · mode: %s", m.sel+1, len(m.results), m.mode.label())
}

// previewDimensions returns the inner viewport size (width, height) based on
// the current window size. Used by both the update (resize viewport) and the
// view (layout the pane) to keep sizing in a single place.
func (m Model) previewDimensions() (int, int) {
	_, rightW := m.paneWidths()
	bodyH := m.paneHeight()
	// rightPane padding (1, 2) → 2 rows + 4 cols consumed by the frame.
	innerW := rightW - 4
	innerH := bodyH - 2
	// Title + meta + blank line above the viewport.
	innerH -= 3
	return innerW, innerH
}

func (m Model) paneWidths() (int, int) {
	leftW := m.width / 3
	if leftW < 30 {
		leftW = 30
	}
	if leftW > 50 {
		leftW = 50
	}
	rightW := m.width - leftW
	return leftW, rightW
}

func (m Model) paneHeight() int {
	h := m.height - 1 // help bar
	if h < 1 {
		h = 1
	}
	return h
}

func (m Model) renderRight(w, h int) string {
	pane := m.styles.rightPane.Width(w).Height(h).MaxWidth(w).MaxHeight(h)

	if len(m.results) == 0 {
		return pane.Render(m.styles.statusDim.Render("select a note to preview"))
	}
	r := m.results[m.sel]
	n := m.byName[r.Filename]
	if n == nil {
		return pane.Render(m.styles.errorText.Render("note not found on disk: " + r.Filename))
	}

	innerW := w - 4 // rightPane padding (1, 2)
	titleText := truncate(n.Title, innerW)
	title := m.styles.previewTitle.Render(titleText)
	metaText := truncate(fmt.Sprintf("%s · %s", n.Filename, n.Type), innerW)
	metaStyled := m.styles.previewMeta.Render(metaText)

	// Each viewport line is capped to innerW so a stray long line from glamour
	// (tables, code blocks, URLs) can never widen the pane and force a wrap.
	body := clampLines(m.preview.View(), innerW, m.preview.Height)

	content := title + "\n" + metaStyled + "\n\n" + body
	return pane.Render(content)
}

// clampLines truncates each line of s to maxW display cells and returns
// exactly maxLines lines (padding with blanks or trimming as needed).
func clampLines(s string, maxW, maxLines int) string {
	if maxW < 1 {
		maxW = 1
	}
	if maxLines < 1 {
		maxLines = 1
	}
	lines := strings.Split(s, "\n")
	for i, l := range lines {
		if lipgloss.Width(l) > maxW {
			lines[i] = lipgloss.NewStyle().MaxWidth(maxW).Render(l)
		}
	}
	if len(lines) > maxLines {
		lines = lines[:maxLines]
	}
	for len(lines) < maxLines {
		lines = append(lines, "")
	}
	return strings.Join(lines, "\n")
}

func (m Model) renderHelp(w int) string {
	k := m.styles.helpKey
	t := m.styles.helpText
	parts := []string{
		k.Render("Tab") + t.Render(" filter"),
		k.Render("↑↓") + t.Render(" nav"),
		k.Render("⌥↑↓") + t.Render(" scroll"),
		k.Render("o") + t.Render(" editor"),
		k.Render("Esc") + t.Render(" clear"),
		k.Render("q") + t.Render(" quit"),
	}
	line := strings.Join(parts, t.Render(" · "))
	return m.styles.helpBar.Width(w).Render(line)
}

func truncate(s string, max int) string {
	if max <= 0 {
		return ""
	}
	if lipgloss.Width(s) <= max {
		return s
	}
	if max <= 1 {
		return "…"
	}
	// Crude rune-based truncate; fine for ASCII/common markdown.
	runes := []rune(s)
	if len(runes) <= max-1 {
		return s
	}
	return string(runes[:max-1]) + "…"
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
