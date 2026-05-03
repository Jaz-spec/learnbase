#!/bin/bash
set -e
trap 'echo "[Version] Bump failed. Check the error above."' ERR

# Only run on main
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [[ "$CURRENT_BRANCH" != "main" ]]; then
  echo "[Version] Not on main branch (currently on $CURRENT_BRANCH). Aborting."
  exit 1
fi

# Get last tag, default to v0.0.0 if none exists
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")

# Get commit messages since last tag
COMMITS=$(git log "$LAST_TAG"..HEAD --pretty=format:"%s")

if [[ -z "$COMMITS" ]]; then
  echo "[Version] No commits since $LAST_TAG. Nothing to bump."
  exit 0
fi

# Infer bump type from conventional commits
BUMP="patch"
if echo "$COMMITS" | grep -qE "BREAKING CHANGE|^(feat|fix|docs|style|refactor|test|chore|build|ci|perf|revert)(\(.+\))?!:"; then
  BUMP="major"
elif echo "$COMMITS" | grep -qE "^feat(\(.+\))?:"; then
  BUMP="minor"
fi

# Parse current version from pyproject.toml
CURRENT_VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
MAJOR=$(echo "$CURRENT_VERSION" | cut -d. -f1)
MINOR=$(echo "$CURRENT_VERSION" | cut -d. -f2)
PATCH=$(echo "$CURRENT_VERSION" | cut -d. -f3)

# Calculate new version
if [[ "$BUMP" == "major" ]]; then
  MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0
elif [[ "$BUMP" == "minor" ]]; then
  MINOR=$((MINOR + 1)); PATCH=0
else
  PATCH=$((PATCH + 1))
fi

NEW_VERSION="$MAJOR.$MINOR.$PATCH"

echo "[Version] $LAST_TAG → v$NEW_VERSION ($BUMP bump)"
echo "[Version] Commits since $LAST_TAG:"
echo "$COMMITS" | head -10 | sed 's/^/  - /'

# Update pyproject.toml
sed -i '' "s/^version = \"$CURRENT_VERSION\"/version = \"$NEW_VERSION\"/" pyproject.toml

# Commit, tag, push
git add pyproject.toml
git commit -m "chore: bump version to $NEW_VERSION"
git tag "v$NEW_VERSION"
git push origin main --tags

echo "[Version] Done. Tagged and pushed v$NEW_VERSION."
