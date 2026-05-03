// Package search provides the three search backends (keyword, tag, semantic).
package search

// Result is a single search hit surfaced to the UI.
type Result struct {
	Filename   string
	Title      string
	Score      float64 // 0..1 for display; higher is better
	ScoreKnown bool    // false → UI renders no score (e.g. tag matches)
}
