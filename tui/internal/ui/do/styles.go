package do

import "github.com/charmbracelet/lipgloss"

// Green retro palette — deliberately distinct from the orange notes TUI.
var (
	colorPrimary = lipgloss.Color("#33ff33")
	colorAccent  = lipgloss.Color("#aaff66")
	colorDim     = lipgloss.Color("#2d7a2d")
	colorDimmer  = lipgloss.Color("#1a4a1a")
	colorBG      = lipgloss.Color("#0a0a0a")
	colorWarn    = lipgloss.Color("#ffcc33")
	colorError   = lipgloss.Color("#ff4444")
)

type styles struct {
	app          lipgloss.Style
	leftPane     lipgloss.Style
	rightPane    lipgloss.Style
	chipActive   lipgloss.Style
	chipIdle     lipgloss.Style
	divider      lipgloss.Style
	rowIdle      lipgloss.Style
	rowSelected  lipgloss.Style
	rowDim       lipgloss.Style
	rowDone      lipgloss.Style
	rowOverdue   lipgloss.Style
	rowPinned    lipgloss.Style
	statusDim    lipgloss.Style
	statusAccent lipgloss.Style
	helpBar      lipgloss.Style
	helpKey      lipgloss.Style
	helpText     lipgloss.Style
	detailTitle  lipgloss.Style
	detailMeta   lipgloss.Style
	detailLabel  lipgloss.Style
	detailValue  lipgloss.Style
	errorText    lipgloss.Style
	formLabel    lipgloss.Style
	formInput    lipgloss.Style
	formActive   lipgloss.Style
	formFooter   lipgloss.Style
}

func newStyles() *styles {
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
		rowIdle: lipgloss.NewStyle().
			Foreground(colorPrimary).
			Background(colorBG),
		rowSelected: lipgloss.NewStyle().
			Foreground(colorBG).
			Background(colorPrimary).
			Bold(true),
		rowDim: lipgloss.NewStyle().
			Foreground(colorDim).
			Background(colorBG),
		rowDone: lipgloss.NewStyle().
			Foreground(colorDimmer).
			Background(colorBG).
			Strikethrough(true),
		rowOverdue: lipgloss.NewStyle().
			Foreground(colorWarn).
			Background(colorBG),
		rowPinned: lipgloss.NewStyle().
			Foreground(colorBG).
			Background(colorAccent).
			Bold(true),
		statusDim: lipgloss.NewStyle().
			Foreground(colorDim).
			Background(colorBG),
		statusAccent: lipgloss.NewStyle().
			Foreground(colorAccent).
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
		detailTitle: lipgloss.NewStyle().
			Foreground(colorAccent).
			Background(colorBG).
			Bold(true),
		detailMeta: lipgloss.NewStyle().
			Foreground(colorDim).
			Background(colorBG).
			Italic(true),
		detailLabel: lipgloss.NewStyle().
			Foreground(colorDim).
			Background(colorBG),
		detailValue: lipgloss.NewStyle().
			Foreground(colorPrimary).
			Background(colorBG),
		errorText: lipgloss.NewStyle().
			Foreground(colorError).
			Background(colorBG).
			Bold(true),
		formLabel: lipgloss.NewStyle().
			Foreground(colorDim).
			Background(colorBG),
		formInput: lipgloss.NewStyle().
			Foreground(colorPrimary).
			Background(colorBG),
		formActive: lipgloss.NewStyle().
			Foreground(colorAccent).
			Background(colorBG).
			Bold(true),
		formFooter: lipgloss.NewStyle().
			Foreground(colorDim).
			Background(colorBG).
			Italic(true),
	}
}
