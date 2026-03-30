"""Dark theme colors and style configuration."""

# Background layers (darkest → lightest)
BG_BASE = "#16162a"       # window background
BG_SURFACE = "#1e1e34"    # cards, panels
BG_HOVER = "#262642"      # row hover
BG_SELECTED = "#2a2a4a"   # row selected
BG_INPUT = "#222240"      # text entries

# Borders / dividers
BORDER = "#2c2c4a"
DIVIDER = "#2a2a44"

# Text
TEXT = "#d0d0dc"           # primary text
TEXT_MUTED = "#7a7a98"     # secondary / labels
TEXT_DIM = "#55556e"       # disabled / placeholder
TEXT_BRIGHT = "#f0f0f8"    # headings, emphasis

# Accents
ACCENT = "#6c6cff"        # primary accent (indigo)
ACCENT_GREEN = "#4ade80"  # success / selected indicator
ACCENT_RED = "#f87171"    # overdue / error
ACCENT_AMBER = "#fbbf24"  # in-progress / warning
ACCENT_TEAL = "#2dd4bf"   # workspace tag

# Status colors
STATUS_COLORS = {
    "pending": TEXT_MUTED,
    "in_progress": ACCENT_AMBER,
    "completed": ACCENT_GREEN,
}

# Workspace badge colors
WS_COLORS = {
    "work": "#818cf8",     # indigo
    "personal": "#a78bfa", # violet
    "contract": "#67e8f9", # cyan
}

# Font config
FONT_FAMILY = "SF Pro Text"  # falls back gracefully on macOS
FONT_TITLE = (FONT_FAMILY, 13)
FONT_BODY = (FONT_FAMILY, 12)
FONT_SMALL = (FONT_FAMILY, 11)
FONT_TINY = (FONT_FAMILY, 10)
FONT_GROUP = (FONT_FAMILY, 10, "bold")
FONT_HEADING = (FONT_FAMILY, 15, "bold")
