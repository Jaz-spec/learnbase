package ui

import "github.com/charmbracelet/lipgloss"

// Retro monochrome-orange palette.
var (
	colorPrimary = lipgloss.Color("#ff8c00")
	colorAccent  = lipgloss.Color("#ffcc33")
	colorDim     = lipgloss.Color("#8b4a00")
	colorDimmer  = lipgloss.Color("#5a2f00")
	colorBG      = lipgloss.Color("#0a0a0a")
)

type styles struct {
	app         lipgloss.Style
	leftPane    lipgloss.Style
	rightPane   lipgloss.Style
	input       lipgloss.Style
	inputCursor lipgloss.Style
	chipActive  lipgloss.Style
	chipIdle    lipgloss.Style
	divider     lipgloss.Style
	resultIdle  lipgloss.Style
	resultSel   lipgloss.Style
	resultScore lipgloss.Style
	status      lipgloss.Style
	statusDim   lipgloss.Style
	helpBar     lipgloss.Style
	helpKey     lipgloss.Style
	helpText    lipgloss.Style
	previewTitle lipgloss.Style
	previewMeta lipgloss.Style
	loading     lipgloss.Style
	errorText   lipgloss.Style
}

func newStyles() *styles {
	base := lipgloss.NewStyle().Foreground(colorPrimary).Background(colorBG)

	return &styles{
		app: lipgloss.NewStyle().Background(colorBG),
		leftPane: lipgloss.NewStyle().
			Foreground(colorPrimary).
			Background(colorBG).
			Border(lipgloss.NormalBorder(), false, true, false, false).
			BorderForeground(colorDim).
			BorderBackground(colorBG).
			Padding(1, 2),
		rightPane: lipgloss.NewStyle().
			Foreground(colorPrimary).
			Background(colorBG).
			Padding(1, 2),
		input: base.
			Foreground(colorAccent).
			Bold(true),
		inputCursor: lipgloss.NewStyle().
			Foreground(colorBG).
			Background(colorAccent),
		chipActive: lipgloss.NewStyle().
			Foreground(colorBG).
			Background(colorPrimary).
			Bold(true).
			Padding(0, 1),
		chipIdle: lipgloss.NewStyle().
			Foreground(colorDim).
			Background(colorBG).
			Padding(0, 1),
		divider: lipgloss.NewStyle().
			Foreground(colorDimmer).
			Background(colorBG),
		resultIdle: base,
		resultSel: lipgloss.NewStyle().
			Foreground(colorBG).
			Background(colorPrimary).
			Bold(true),
		resultScore: lipgloss.NewStyle().
			Foreground(colorDim).
			Background(colorBG),
		status: base,
		statusDim: lipgloss.NewStyle().
			Foreground(colorDim).
			Background(colorBG),
		helpBar: lipgloss.NewStyle().
			Background(colorBG).
			Foreground(colorDim).
			Padding(0, 1),
		helpKey: lipgloss.NewStyle().
			Foreground(colorAccent).
			Background(colorBG).
			Bold(true),
		helpText: lipgloss.NewStyle().
			Foreground(colorDim).
			Background(colorBG),
		previewTitle: lipgloss.NewStyle().
			Foreground(colorAccent).
			Background(colorBG).
			Bold(true),
		previewMeta: lipgloss.NewStyle().
			Foreground(colorDim).
			Background(colorBG).
			Italic(true),
		loading: lipgloss.NewStyle().
			Foreground(colorAccent).
			Background(colorBG).
			Italic(true),
		errorText: lipgloss.NewStyle().
			Foreground(lipgloss.Color("#ff4444")).
			Background(colorBG).
			Bold(true),
	}
}
