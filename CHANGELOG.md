# Changelog

All notable changes to LearnBase will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Explicit priority requests for review sessions
- In-memory priority tracking in review skill
- Priority data persistence in session history
- Priority request tracking at topic level with automatic deactivation after 2 sessions
- Extended MCP save_session_history schema with priority fields
- Comprehensive test suite for priority logic (13 tests passing)

## [0.2.0] - 2026-01-22

### Added
- Auto-approval hooks for safe tool calls
- Git post-push hook for automatic PR generation
- Semantic versioning system with VERSION file and bump script
- CHANGELOG.md following Keep a Changelog format
- CI/CD workflow improvements

## [0.1.0] - 2026-01-22

### Added
- Initial implementation of LearnBase MCP server
- Spaced repetition using SM-2 algorithm
- Markdown notes with YAML frontmatter
- Question performance tracking
- Review session skill
- Session history logging

### Core Features
- Note management tools (add, edit, delete, list)
- Review workflow tools (get_due_notes, review_note, record_review)
- Statistics and analytics
- Scheduled and spaced repetition modes

[Unreleased]: https://github.com/yourusername/learnbase/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/yourusername/learnbase/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/yourusername/learnbase/releases/tag/v0.1.0
