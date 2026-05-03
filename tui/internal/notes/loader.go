// Package notes loads markdown notes from ~/.learnbase/notes/.
package notes

import (
	"bytes"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"

	"gopkg.in/yaml.v3"
)

// Note is a markdown note on disk with its frontmatter, body, and extracted tags.
type Note struct {
	Filename string
	Path     string
	Title    string
	Type     string
	Body     string
	Tags     []string
	TagSet   map[string]struct{}

	LowerTitle string
	LowerBody  string
}

type frontmatter struct {
	Title string `yaml:"title"`
	Type  string `yaml:"type"`
}

var (
	frontmatterSep = []byte("---")
	tagPattern     = regexp.MustCompile(`#([A-Za-z][A-Za-z0-9_-]*)`)
)

// LoadAll walks dir for *.md files, parses each, and returns the notes sorted by filename.
func LoadAll(dir string) ([]*Note, error) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil, fmt.Errorf("read notes dir: %w", err)
	}

	var out []*Note
	for _, e := range entries {
		if e.IsDir() || !strings.HasSuffix(strings.ToLower(e.Name()), ".md") {
			continue
		}
		if e.Name() == "README.md" {
			continue
		}
		p := filepath.Join(dir, e.Name())
		n, err := load(p)
		if err != nil {
			// Skip unreadable files rather than abort the whole load.
			continue
		}
		out = append(out, n)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Filename < out[j].Filename })
	return out, nil
}

func load(path string) (*Note, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	title := ""
	typ := ""
	body := raw

	if bytes.HasPrefix(raw, frontmatterSep) {
		rest := raw[len(frontmatterSep):]
		// Allow leading newline after opening ---.
		rest = bytes.TrimLeft(rest, "\r\n")
		if end := bytes.Index(rest, append([]byte("\n"), frontmatterSep...)); end >= 0 {
			fmRaw := rest[:end]
			var fm frontmatter
			if err := yaml.Unmarshal(fmRaw, &fm); err == nil {
				title = fm.Title
				typ = fm.Type
			}
			// Skip past the closing --- and any trailing newline.
			afterFM := rest[end+1+len(frontmatterSep):]
			afterFM = bytes.TrimLeft(afterFM, "\r\n")
			body = afterFM
		}
	}

	filename := filepath.Base(path)
	if title == "" {
		title = strings.TrimSuffix(filename, filepath.Ext(filename))
	}

	bodyStr := string(body)
	tags, set := extractTags(bodyStr)

	return &Note{
		Filename:   filename,
		Path:       path,
		Title:      title,
		Type:       typ,
		Body:       bodyStr,
		Tags:       tags,
		TagSet:     set,
		LowerTitle: strings.ToLower(title),
		LowerBody:  strings.ToLower(bodyStr),
	}, nil
}

func extractTags(body string) ([]string, map[string]struct{}) {
	set := map[string]struct{}{}
	var out []string
	for _, m := range tagPattern.FindAllStringSubmatch(body, -1) {
		tag := strings.ToLower(m[1])
		if _, ok := set[tag]; ok {
			continue
		}
		set[tag] = struct{}{}
		out = append(out, tag)
	}
	sort.Strings(out)
	return out, set
}
