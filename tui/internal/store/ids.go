package store

import (
	"regexp"
	"strings"
	"time"
	"unicode"
)

// TaskID mirrors Python's Task.create_id (models.py:459):
//   - alphanumeric and whitespace preserved, everything else dropped
//   - lowercase, split by whitespace, joined with '-'
//   - truncated to 40 chars
//   - prefixed with YYYY-MM-DD-
func TaskID(title string, due time.Time) string {
	var b strings.Builder
	b.Grow(len(title))
	for _, r := range title {
		if unicode.IsLetter(r) || unicode.IsDigit(r) || unicode.IsSpace(r) {
			b.WriteRune(r)
		}
	}
	slug := strings.Join(strings.Fields(strings.ToLower(b.String())), "-")
	if len(slug) > 40 {
		slug = slug[:40]
	}
	return due.Format("2006-01-02") + "-" + slug
}

// PriorityID mirrors PlanningManager's slug + id composition:
//   - {scope}-{period}-{slug}
//   - slug: [^\w\s-] stripped, [-\s]+ → '-', trimmed, 40-char cap
//     (python's \w matches [A-Za-z0-9_]; we match that exactly).
func PriorityID(scope, period, description string) string {
	return scope + "-" + period + "-" + Slugify(description)
}

var slugStripRE = regexp.MustCompile(`[^\w\s-]`)
var slugCollapseRE = regexp.MustCompile(`[-\s]+`)

// Slugify follows Python's PlanningManager._slugify rules exactly.
func Slugify(text string) string {
	s := strings.ToLower(text)
	s = slugStripRE.ReplaceAllString(s, "")
	s = slugCollapseRE.ReplaceAllString(s, "-")
	s = strings.Trim(s, "-")
	if len(s) > 40 {
		s = s[:40]
	}
	return s
}

// NowString is the timestamp format both Python and the TUI write. Seconds
// precision is sufficient — Python writes microseconds but comparisons are
// lexicographic on ISO 8601 and both encodings sort identically.
func NowString() string {
	return time.Now().Format("2006-01-02T15:04:05.000000")
}
