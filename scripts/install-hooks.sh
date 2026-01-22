#!/bin/bash
# Install git hooks for the project

HOOKS_DIR=".git/hooks"
SCRIPTS_DIR="$(dirname "$0")"

echo "Installing git hooks..."

# Copy post-push hook
cp "$SCRIPTS_DIR/hooks/post-push" "$HOOKS_DIR/post-push"
chmod +x "$HOOKS_DIR/post-push"

echo "✓ post-push hook installed"

echo ""
echo "Git hooks installed successfully!"
echo "The following hooks are now active:"
echo "  - post-push: Auto-generate PR after pushing a branch"
