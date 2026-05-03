package search

import (
	"sort"
	"strings"

	"github.com/jaz/learnbase/tui/internal/notes"
)

// Tag matches notes whose extracted hashtags contain the query as a substring.
// Exact tag matches rank above partial matches.
func Tag(all []*notes.Note, query string, limit int) []Result {
	q := strings.ToLower(strings.TrimSpace(strings.TrimPrefix(query, "#")))
	if q == "" {
		return nil
	}

	type scored struct {
		note  *notes.Note
		score int
	}

	var hits []scored
	for _, n := range all {
		best := 0
		for tag := range n.TagSet {
			switch {
			case tag == q:
				if 3 > best {
					best = 3
				}
			case strings.HasPrefix(tag, q):
				if 2 > best {
					best = 2
				}
			case strings.Contains(tag, q):
				if 1 > best {
					best = 1
				}
			}
		}
		if best == 0 {
			continue
		}
		hits = append(hits, scored{note: n, score: best})
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

	out := make([]Result, 0, len(hits))
	for _, h := range hits {
		out = append(out, Result{
			Filename: h.note.Filename,
			Title:    h.note.Title,
		})
	}
	return out
}
