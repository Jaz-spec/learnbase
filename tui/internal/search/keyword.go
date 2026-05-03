package search

import (
	"sort"
	"strings"

	"github.com/jaz/learnbase/tui/internal/notes"
)

// Keyword does a case-insensitive substring search across title and body.
// Ranking: title matches outweigh body matches, multiple hits raise the score.
func Keyword(all []*notes.Note, query string, limit int) []Result {
	q := strings.ToLower(strings.TrimSpace(query))
	if q == "" {
		return nil
	}

	type scored struct {
		note  *notes.Note
		score float64
	}

	var hits []scored
	for _, n := range all {
		titleCount := strings.Count(n.LowerTitle, q)
		bodyCount := strings.Count(n.LowerBody, q)
		if titleCount == 0 && bodyCount == 0 {
			continue
		}
		score := float64(titleCount)*3 + float64(bodyCount)
		hits = append(hits, scored{note: n, score: score})
	}

	sort.SliceStable(hits, func(i, j int) bool {
		if hits[i].score != hits[j].score {
			return hits[i].score > hits[j].score
		}
		return hits[i].note.Filename < hits[j].note.Filename
	})

	if limit > 0 && len(hits) > limit {
		hits = hits[:limit]
	}

	maxScore := 0.0
	for _, h := range hits {
		if h.score > maxScore {
			maxScore = h.score
		}
	}

	out := make([]Result, 0, len(hits))
	for _, h := range hits {
		normalized := 0.0
		if maxScore > 0 {
			normalized = h.score / maxScore
		}
		out = append(out, Result{
			Filename:   h.note.Filename,
			Title:      h.note.Title,
			Score:      normalized,
			ScoreKnown: true,
		})
	}
	return out
}
