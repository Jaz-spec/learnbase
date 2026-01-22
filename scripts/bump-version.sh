#!/bin/bash
# Bump version number across all files

set -e

CURRENT_VERSION=$(cat VERSION)
BUMP_TYPE="${1:-patch}"  # major, minor, or patch

# Parse current version
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"

# Bump version based on type
case "$BUMP_TYPE" in
  major)
    MAJOR=$((MAJOR + 1))
    MINOR=0
    PATCH=0
    ;;
  minor)
    MINOR=$((MINOR + 1))
    PATCH=0
    ;;
  patch)
    PATCH=$((PATCH + 1))
    ;;
  *)
    echo "Usage: $0 {major|minor|patch}"
    exit 1
    ;;
esac

NEW_VERSION="$MAJOR.$MINOR.$PATCH"

echo "Bumping version: $CURRENT_VERSION → $NEW_VERSION"

# Update VERSION file
echo "$NEW_VERSION" > VERSION

# Update __version__.py
cat > src/learnbase/__version__.py <<EOF
"""Version information for LearnBase."""

__version__ = "$NEW_VERSION"
EOF

# Update pyproject.toml
sed -i '' "s/version = \".*\"/version = \"$NEW_VERSION\"/" pyproject.toml

echo "✓ Version bumped to $NEW_VERSION"
echo ""
echo "Next steps:"
echo "  1. Update CHANGELOG.md"
echo "  2. git add VERSION src/learnbase/__version__.py pyproject.toml CHANGELOG.md"
echo "  3. git commit -m 'chore: bump version to $NEW_VERSION'"
echo "  4. git tag -a v$NEW_VERSION -m 'Release v$NEW_VERSION'"
