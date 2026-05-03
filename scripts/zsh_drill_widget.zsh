# LearnBase drill capture — zsh widget.
#
# Binds Ctrl+X Ctrl+D to capture the current command line (or the most recent
# history entry if the line is empty) as a drill flashcard.
#
# Install:
#   1. Source this file from your ~/.zshrc:
#         source /Users/jaz/Documents/learnBase/scripts/zsh_drill_widget.zsh
#   2. Reload zsh.
#
# To use a different binding, change the bindkey line at the bottom.
#
# Environment:
#   LEARNBASE_REPO   — repo path (auto-detected if this file is sourced)
#   LEARNBASE_PYTHON — Python interpreter for the helper (default: <repo>/venv/bin/python)
#   EDITOR           — editor for the capture template (default: vim)

# Resolve repo root from this file's location.
if [[ -z "$LEARNBASE_REPO" ]]; then
  if [[ -n "${(%):-%N}" ]]; then
    _learnbase_dir="${${(%):-%N}:A:h}"
    LEARNBASE_REPO="${_learnbase_dir:h}"
  fi
fi

learnbase-drill-capture-widget() {
  local repo="${LEARNBASE_REPO:-$HOME/Documents/learnBase}"
  local script="$repo/scripts/capture_drill.py"
  local py="${LEARNBASE_PYTHON:-$repo/venv/bin/python}"

  if [[ ! -f "$script" ]]; then
    zle -M "drill capture: $script not found"
    return 1
  fi
  if [[ ! -x "$py" ]] && ! command -v "$py" >/dev/null 2>&1; then
    py="python3"
  fi

  # Pull the line we want to capture: prefer the editing buffer, fall back to
  # the most recent history entry so this works after the user has just hit
  # Enter on a command they want to retain.
  local prefill="$BUFFER"
  if [[ -z "$prefill" ]]; then
    prefill="${history[$#history]}"
  fi

  # Save the current buffer so we can restore it after the editor closes.
  local saved_buffer="$BUFFER"
  local saved_cursor="$CURSOR"

  BUFFER=""
  zle -I  # invalidate display so the editor takes the screen cleanly

  "$py" "$script" --language bash --prefill-answer "$prefill"
  local rc=$?

  BUFFER="$saved_buffer"
  CURSOR="$saved_cursor"
  zle reset-prompt

  if (( rc == 0 )); then
    zle -M "✓ drill captured"
  elif (( rc == 3 )); then
    zle -M "⚠ similar drill exists — re-run script with --force to override"
  else
    zle -M "drill capture aborted (exit $rc)"
  fi
}

zle -N learnbase-drill-capture-widget
bindkey '^X^D' learnbase-drill-capture-widget
