package drill

import "github.com/charmbracelet/lipgloss"

// Retro monochrome neon-yellow palette — single hue on black, brightness/weight only.
// Deliberately distinct from the do TUI's green and the notes TUI's orange.
var (
	colorPrimary = lipgloss.Color("#FFFF33") // neon yellow
	colorAccent  = lipgloss.Color("#FFFF99") // brighter highlight
	colorDim     = lipgloss.Color("#888833") // ~50% brightness, muted
	colorDimmer  = lipgloss.Color("#3a3a1a") // borders, dividers
	colorBG      = lipgloss.Color("#0a0a0a") // near-black background
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
	rowBold      lipgloss.Style
	statusDim    lipgloss.Style
	statusAccent lipgloss.Style
	helpBar      lipgloss.Style
	helpKey      lipgloss.Style
	helpText     lipgloss.Style
	cardTitle    lipgloss.Style
	cardMeta     lipgloss.Style
	cardLabel    lipgloss.Style
	cardValue    lipgloss.Style
	codeBlock    lipgloss.Style
	codeBlockDim lipgloss.Style
	prompt       lipgloss.Style
	answerInput  lipgloss.Style
	answerLocked lipgloss.Style
	verdictPass  lipgloss.Style
	verdictFail  lipgloss.Style
	flagWarn     lipgloss.Style
	formLabel    lipgloss.Style
	formInput    lipgloss.Style
	formActive   lipgloss.Style
	formFooter   lipgloss.Style
	errorText    lipgloss.Style
}

func newStyles() *styles {
	return &styles{
		app: lipgloss.NewStyle().Background(colorBG),
		leftPane: lipgloss.NewStyle().
			Foreground(colorPrimary).
			Background(colorBG).
			Border(lipgloss.NormalBorder(), false, true, false, false).
			BorderForeground(colorDimmer).
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
		rowBold: lipgloss.NewStyle().
			Foreground(colorAccent).
			Background(colorBG).
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
		cardTitle: lipgloss.NewStyle().
			Foreground(colorAccent).
			Background(colorBG).
			Bold(true),
		cardMeta: lipgloss.NewStyle().
			Foreground(colorDim).
			Background(colorBG).
			Italic(true),
		cardLabel: lipgloss.NewStyle().
			Foreground(colorDim).
			Background(colorBG),
		cardValue: lipgloss.NewStyle().
			Foreground(colorPrimary).
			Background(colorBG),
		codeBlock: lipgloss.NewStyle().
			Foreground(colorPrimary).
			Background(colorBG).
			Border(lipgloss.NormalBorder(), true).
			BorderForeground(colorDimmer).
			BorderBackground(colorBG).
			Padding(0, 1),
		codeBlockDim: lipgloss.NewStyle().
			Foreground(colorDim).
			Background(colorBG).
			Border(lipgloss.NormalBorder(), true).
			BorderForeground(colorDimmer).
			BorderBackground(colorBG).
			Padding(0, 1),
		prompt: lipgloss.NewStyle().
			Foreground(colorPrimary).
			Background(colorBG),
		answerInput: lipgloss.NewStyle().
			Foreground(colorAccent).
			Background(colorBG).
			Border(lipgloss.NormalBorder(), true).
			BorderForeground(colorPrimary).
			BorderBackground(colorBG).
			Padding(0, 1),
		answerLocked: lipgloss.NewStyle().
			Foreground(colorDim).
			Background(colorBG).
			Border(lipgloss.NormalBorder(), true).
			BorderForeground(colorDimmer).
			BorderBackground(colorBG).
			Padding(0, 1),
		verdictPass: lipgloss.NewStyle().
			Foreground(colorBG).
			Background(colorAccent).
			Bold(true).
			Padding(0, 1),
		verdictFail: lipgloss.NewStyle().
			Foreground(colorBG).
			Background(colorDim).
			Bold(true).
			Padding(0, 1),
		flagWarn: lipgloss.NewStyle().
			Foreground(colorAccent).
			Background(colorBG).
			Bold(true).
			Underline(true),
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
		errorText: lipgloss.NewStyle().
			Foreground(colorAccent).
			Background(colorBG).
			Bold(true).
			Underline(true),
	}
}
