package do

import (
	"fmt"
	"strings"
	"time"

	"github.com/charmbracelet/lipgloss"

	"github.com/jaz/learnbase/tui/internal/store"
)

// View renders the TUI.
func (m Model) View() string {
	if m.width < 50 || m.height < 12 {
		return m.styles.errorText.Render("terminal too small — resize to at least 50×12")
	}

	leftW, rightW := m.paneWidths()
	bodyH := m.paneHeight()

	left := m.renderLeft(leftW, bodyH)
	right := m.renderRight(rightW, bodyH)

	body := lipgloss.JoinHorizontal(lipgloss.Top, left, right)
	help := m.renderHelp(m.width)
	return lipgloss.JoinVertical(lipgloss.Left, body, help)
}

func (m Model) paneWidths() (int, int) {
	leftW := m.width * 2 / 5
	if leftW < 34 {
		leftW = 34
	}
	if leftW > 55 {
		leftW = 55
	}
	rightW := m.width - leftW
	return leftW, rightW
}

func (m Model) paneHeight() int {
	h := m.height - 1
	if h < 1 {
		h = 1
	}
	return h
}

// ---------- left pane ----------

func (m Model) renderLeft(w, h int) string {
	innerW := w - 5 // padding (2+2) + right border (1)

	var b strings.Builder
	b.WriteString(m.renderViewChips())
	b.WriteString("\n")

	filterLines := m.renderFilters()
	for _, line := range filterLines {
		b.WriteString(line + "\n")
	}

	b.WriteString(m.styles.divider.Render(strings.Repeat("─", innerW)))
	b.WriteString("\n")

	// Remaining rows for the list.
	listRows := h - 2 /*padding*/ - 1 /*chips*/ - len(filterLines) - 1 /*divider*/ - 1 /*footer*/
	if listRows < 3 {
		listRows = 3
	}
	b.WriteString(m.renderList(innerW, listRows))
	b.WriteString("\n")
	b.WriteString(m.styles.statusDim.Render(m.footerLine()))

	return m.styles.leftPane.Width(w).Height(h).MaxWidth(w).MaxHeight(h).Render(b.String())
}

func (m Model) renderViewChips() string {
	chip := func(v ViewMode) string {
		label := v.label()
		if v == m.view {
			return m.styles.chipActive.Render("●" + label)
		}
		return m.styles.chipIdle.Render(" " + label)
	}
	return chip(ViewTasks) + chip(ViewProjects)
}

func (m Model) renderFilters() []string {
	if m.view != ViewTasks {
		return nil
	}
	label := m.styles.detailLabel
	chip := func(active bool, text string) string {
		if active {
			return m.styles.chipActive.Render(text)
		}
		return m.styles.chipIdle.Render(text)
	}
	dueLine := label.Render("due  ") +
		chip(m.filter.Due == store.DueAny, "all") +
		chip(m.filter.Due == store.DueToday, "today") +
		chip(m.filter.Due == store.DueThisWeek, "week") +
		chip(m.filter.Due == store.DueOverdue, "overdue")
	wsLine := label.Render("ws   ") +
		chip(m.filter.Workspace == "", "all") +
		chip(m.filter.Workspace == "work", "work") +
		chip(m.filter.Workspace == "personal", "personal") +
		chip(m.filter.Workspace == "contract", "contract")
	stLine := label.Render("stat ") +
		chip(m.filter.Status == "", "all") +
		chip(m.filter.Status == "pending", "pending") +
		chip(m.filter.Status == "in_progress", "doing") +
		chip(m.filter.Status == "completed", "done")
	return []string{dueLine, wsLine, stLine}
}

func (m Model) renderList(width, maxLines int) string {
	rows := m.listRows()
	if len(rows) == 0 {
		empty := m.styles.statusDim.Render("no items — press `n` to create")
		return empty + strings.Repeat("\n", max(0, maxLines-1))
	}

	// Scroll the visible window so the selected row is in range.
	start := 0
	if m.sel >= maxLines {
		start = m.sel - maxLines + 1
	}
	end := start + maxLines
	if end > len(rows) {
		end = len(rows)
	}

	var lines []string
	for i := start; i < end; i++ {
		lines = append(lines, m.renderRow(rows[i], width, i == m.sel))
	}
	for len(lines) < maxLines {
		lines = append(lines, "")
	}
	return strings.Join(lines, "\n")
}

// row is a view-agnostic shape used by the left list.
type row struct {
	marker string // like "[ ]" or "[x]" for tasks, "◉" for priorities, etc.
	label  string
	trail  string // short trailing metadata (e.g. "work", "stale")
	style  lipgloss.Style
	pinned bool
}

func (m Model) listRows() []row {
	switch m.view {
	case ViewTasks:
		out := make([]row, 0, len(m.tasks))
		today := time.Now().Format("2006-01-02")
		for _, t := range m.tasks {
			marker := "[ ]"
			if t.Status == "in_progress" {
				marker = "[~]"
			}
			if t.Pinned {
				marker = "[★]"
			}
			if t.Status == "completed" {
				marker = "[x]"
			}

			st := m.styles.rowIdle
			switch {
			case t.Status == "completed":
				st = m.styles.rowDone
			case t.Due.Format("2006-01-02") < today:
				st = m.styles.rowOverdue
			case t.Pinned:
				st = m.styles.rowPinned
			}
			label := t.Due.Format("15:04") + " " + t.Title
			trail := t.Workspace
			if t.Project != "" {
				trail = t.Workspace + "/" + t.Project
			}
			out = append(out, row{marker: marker, label: label, trail: trail, style: st, pinned: t.Pinned && t.Status != "completed"})
		}
		return out
	case ViewProjects:
		out := make([]row, 0, len(m.projects))
		for _, p := range m.projects {
			marker := "◆"
			st := m.styles.rowIdle
			trail := p.Workspace
			switch p.Staleness {
			case store.StalenessStale:
				trail = p.Workspace + " · stale"
				st = m.styles.rowOverdue
			case store.StalenessInactive:
				trail = p.Workspace + " · inactive"
				st = m.styles.rowDone
			}
			out = append(out, row{marker: marker, label: p.Name, trail: trail, style: st})
		}
		return out
	}
	return nil
}


func (m Model) renderRow(r row, width int, selected bool) string {
	prefix := "  "
	if selected {
		prefix = "> "
	}
	marker := r.marker + " "
	trail := r.trail
	gap := 1
	if trail == "" {
		gap = 0
	}
	// Work out available label width.
	maxLabel := width - lipgloss.Width(prefix) - lipgloss.Width(marker) - lipgloss.Width(trail) - gap
	if maxLabel < 4 {
		maxLabel = 4
	}
	label := truncate(r.label, maxLabel)
	labelW := lipgloss.Width(label)
	fill := width - lipgloss.Width(prefix) - lipgloss.Width(marker) - labelW - lipgloss.Width(trail)
	if fill < 0 {
		fill = 0
	}
	rowStr := prefix + marker + label + strings.Repeat(" ", fill) + trail
	if selected {
		return m.styles.rowSelected.Render(rowStr)
	}
	if r.pinned {
		return m.styles.rowPinned.Render(rowStr)
	}
	return r.style.Render(rowStr)
}

func (m Model) footerLine() string {
	total := m.listLen()
	if total == 0 {
		return fmt.Sprintf("0 %s", m.view.label())
	}
	if m.err != "" {
		return m.styles.errorText.Render("! " + m.err)
	}
	status := ""
	if m.status != "" {
		status = " · " + m.status
	}
	return fmt.Sprintf("%d/%d · %s%s", m.sel+1, total, m.view.label(), status)
}

// ---------- right pane ----------

// detailDims returns (pane width, inner viewport width, inner viewport height).
func (m Model) detailDims() (int, int, int) {
	_, rightW := m.paneWidths()
	paneH := m.paneHeight()
	innerW := rightW - 4 // padding (2+2)
	innerH := paneH - 2  // padding rows
	innerH -= 3          // title + meta + blank
	if innerH < 1 {
		innerH = 1
	}
	return rightW, innerW, innerH
}

func (m Model) renderRight(w, h int) string {
	pane := m.styles.rightPane.Width(w).Height(h).MaxWidth(w).MaxHeight(h)

	if m.form != nil {
		return pane.Render(m.renderForm(w - 4))
	}

	if m.listLen() == 0 {
		return pane.Render(m.styles.statusDim.Render("no items — press `n` to create"))
	}

	title, meta := m.detailHeader()
	body := clampLines(m.detail.View(), w-4, m.detail.Height)
	content := m.styles.detailTitle.Render(title) + "\n" +
		m.styles.detailMeta.Render(meta) + "\n\n" +
		body
	return pane.Render(content)
}

func (m Model) detailHeader() (string, string) {
	switch m.view {
	case ViewTasks:
		if m.sel >= len(m.tasks) {
			return "", ""
		}
		t := m.tasks[m.sel]
		return t.Title, t.ID
	case ViewProjects:
		if m.sel >= len(m.projects) {
			return "", ""
		}
		p := m.projects[m.sel]
		return p.Name, p.ID
	}
	return "", ""
}

func (m Model) detailBody() string {
	label := m.styles.detailLabel
	value := m.styles.detailValue

	line := func(k, v string) string {
		if v == "" {
			v = "—"
		}
		return label.Render(fmt.Sprintf("%-11s", k)) + value.Render(v)
	}

	switch m.view {
	case ViewTasks:
		if m.sel >= len(m.tasks) {
			return ""
		}
		t := m.tasks[m.sel]
		cats := strings.Join(t.Categories, ", ")
		pinStr := "no"
		if t.Pinned {
			pinStr = "★ yes"
		}
		lines := []string{
			line("due:", t.Due.Format("02.01.06 15:04")),
			line("workspace:", t.Workspace),
			line("project:", t.Project),
			line("status:", t.Status),
			line("pinned:", pinStr),
			line("categories:", cats),
		}
		if t.Description != "" {
			lines = append(lines, "", value.Render(t.Description))
		}
		if t.Reasoning != "" {
			lines = append(lines, "", label.Render("reasoning:"), value.Render(t.Reasoning))
		}
		return strings.Join(lines, "\n")
	case ViewProjects:
		if m.sel >= len(m.projects) {
			return ""
		}
		p := m.projects[m.sel]
		lines := []string{
			line("workspace:", p.Workspace),
			line("status:", p.Status),
			line("staleness:", string(p.Staleness)),
			line("updated:", p.UpdatedAt.Format("02.01.06")),
		}
		if p.Description != "" {
			lines = append(lines, "", value.Render(p.Description))
		}
		return strings.Join(lines, "\n")
	}
	return ""
}

// ---------- form rendering ----------

func (m Model) renderForm(innerW int) string {
	title := "New " + formTargetName(m.form.target)
	if m.form.existingID != "" {
		title = "Edit " + formTargetName(m.form.target) + ": " + m.form.existingID
	}

	var lines []string
	lines = append(lines, m.styles.detailTitle.Render(title))
	lines = append(lines, "")

	for i, f := range m.form.fields {
		focused := i == m.form.focus
		labelStyle := m.styles.formLabel
		if focused {
			labelStyle = m.styles.formActive
		}

		var inputStr string
		switch {
		case f.multiSel:
			var parts []string
			for j, opt := range f.options {
				isCur := focused && j == f.cursor
				isSel := f.selected[opt]
				prefix := " "
				if isSel {
					prefix = "●"
				}
				if isCur {
					parts = append(parts, m.styles.chipActive.Render("["+prefix+opt+"]"))
				} else if isSel {
					parts = append(parts, m.styles.chipActive.Render(prefix+opt))
				} else {
					parts = append(parts, m.styles.chipIdle.Render(prefix+opt))
				}
			}
			inputStr = strings.Join(parts, "")
		case f.isSelect():
			val := f.value()
			if val == "" {
				val = "—"
			}
			if focused {
				inputStr = "← " + val + " →"
			} else {
				inputStr = val
			}
		default:
			inputStr = f.input.View()
		}

		lines = append(lines,
			labelStyle.Render(f.label+":"),
			"  "+inputStr,
			"  "+m.styles.formFooter.Render(f.hint),
			"",
		)
	}

	if m.form.err != "" {
		lines = append(lines, m.styles.errorText.Render("! "+m.form.err))
	}
	if m.err != "" {
		lines = append(lines, m.styles.errorText.Render("! "+m.err))
	}
	lines = append(lines,
		m.styles.formFooter.Render("Tab/↑↓ field · ←/→ select · ↵ toggle · Ctrl+S save · Esc cancel"),
	)
	return strings.Join(lines, "\n")
}

func formTargetName(t formTarget) string {
	switch t {
	case formTask:
		return "task"
	case formProject:
		return "project"
	}
	return "?"
}

// ---------- help bar + small utils ----------

func (m Model) renderHelp(w int) string {
	k := m.styles.helpKey
	t := m.styles.helpText

	parts := []string{
		k.Render("Tab") + t.Render(" view"),
		k.Render("↑↓") + t.Render(" nav"),
	}
	if m.view == ViewTasks {
		parts = append(parts,
			k.Render("dws") + t.Render(" filter"),
			k.Render("⇧↑↓") + t.Render(" move"),
			k.Render("x") + t.Render(" done"),
			k.Render("i") + t.Render(" doing"),
			k.Render("p") + t.Render(" pin"),
		)
	}
	parts = append(parts,
		k.Render("n") + t.Render(" new"),
		k.Render("⏎") + t.Render(" edit"),
		k.Render("D") + t.Render(" archive"),
		k.Render("q") + t.Render(" quit"),
	)
	line := strings.Join(parts, t.Render(" · "))
	return m.styles.helpBar.Width(w).Render(line)
}

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

func truncate(s string, maxW int) string {
	if maxW <= 0 {
		return ""
	}
	if lipgloss.Width(s) <= maxW {
		return s
	}
	if maxW <= 1 {
		return "…"
	}
	runes := []rune(s)
	if len(runes) <= maxW-1 {
		return s
	}
	return string(runes[:maxW-1]) + "…"
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
