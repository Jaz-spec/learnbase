# Note Validation Skill

## Purpose
Research and validate the accuracy of LearnBase notes, find authoritative sources, and assign confidence scores.

## When to Use This Skill
- User requests: "validate this note", "verify [note name]", "find sources for X"
- User asks: "what needs verifying?", "show unverified notes"
- User says: "check if this is accurate", "is this right?"

## Core Principles
1. **Research-First**: Always verify claims against authoritative sources
2. **Source Quality**: Prefer official documentation, academic papers, and reputable technical resources
3. **Honest Assessment**: Give realistic confidence scores based on source quality and content accuracy
4. **Constructive Feedback**: Suggest specific amendments, don't just point out errors

---

## Workflow

### Step 1: Note Selection

**If user specifies a note:**
- Proceed directly to Step 2

**If user asks "what needs verifying?":**
```
Tool: list_notes(needs_verification=true)

Response:
"These notes need verification:

1. **{title}** ({filename})
   - Created: {date}
   - Review count: {count}

Which would you like me to validate?"
```

**Wait for user selection**

---

### Step 2: Load and Analyze Note

**Tool**: `get_note(filename)`

**Extract**:
- Title
- Body content
- Current sources (if any)
- Current confidence_score (if any)

**Analysis**:
Identify the main claims/concepts in the note:
- What technical concepts are explained?
- What examples or code snippets are provided?
- What relationships or comparisons are made?
- Are there any specific facts, statistics, or technical details?

**Present to user**:
```
📝 **{title}**

I've identified these key claims to verify:
1. {claim_1}
2. {claim_2}
3. {claim_3}

{if existing sources:}
Current sources: {count} source(s)
Current confidence: {score}

I'll research these claims and find authoritative sources. This will take a moment...
```

---

### Step 3: Research and Verification

**For each claim identified:**

1. **Search for sources** (Tool: `WebSearch`)
   - Query: "{technical_concept} official documentation 2026"
   - Query: "{technical_concept} {specific_framework/language}"
   - Prefer: Official docs, GitHub repos, RFCs, academic papers, reputable blogs

2. **Fetch and verify** (Tool: `WebFetch`)
   - Read source content
   - Check if claim is supported
   - Note any discrepancies

**Source Quality Hierarchy**:
- **Tier 1 (Best)**: Official documentation, RFCs, academic papers, source code
- **Tier 2 (Good)**: Well-known technical blogs (Mozilla, Google Developers, etc.)
- **Tier 3 (OK)**: Stack Overflow (high-voted answers), reputable tutorials
- **Tier 4 (Avoid)**: Random blogs, Medium posts without citations, forum posts

**Research Notes Template**:
```
Claim: {claim}
Source: {url}
Quality: Tier {1-4}
Verdict: ✓ Confirmed | ⚠️ Partially accurate | ✗ Incorrect
Notes: {specific findings}
```

---

### Step 4: Calculate Confidence Score

**Algorithm**:
```
Base score = 0.5

For each claim:
  If Tier 1 source confirms: +0.15
  If Tier 2 source confirms: +0.10
  If Tier 3 source confirms: +0.05
  If partially accurate: +0.03
  If incorrect: -0.20
  If no source found: -0.05

Adjustments:
  All major claims verified: +0.10
  Multiple high-quality sources agree: +0.10
  Code examples verified against docs: +0.10
  Contradictions found: -0.30

Final score: clamp(base_score + adjustments, 0.0, 1.0)
```

**Confidence Thresholds**:
- **0.8-1.0**: Excellent - well-sourced and accurate
- **0.6-0.79**: Good - mostly accurate, minor gaps
- **0.4-0.59**: Fair - significant verification needed
- **0.0-0.39**: Poor - major inaccuracies or no sources

---

### Step 5: Generate Amendments

**If confidence < 0.8, suggest specific amendments:**

**Amendment Types**:
1. **Corrections**: "Change X to Y because [source] shows..."
2. **Additions**: "Add information about Z from [source]"
3. **Clarifications**: "Reword this section to be more precise"
4. **Code fixes**: "Update code example to match [official docs]"

**Format**:
```
## Suggested Amendments

### 1. [Section/Claim]
**Issue**: {what's wrong or missing}
**Suggestion**: {specific change}
**Source**: {url that supports this}

### 2. [Section/Claim]
...
```

---

### Step 6: Present Results

```
✅ **Validation Complete: {title}**

## Research Summary
Found {n} authoritative sources across {m} claims.

## Confidence Score: {score} ({excellent|good|fair|poor})

### Sources Found:
1. **{source_title}** ({tier})
   {url}
   Verified: {claims covered}

2. **{source_title}** ({tier})
   {url}
   Verified: {claims covered}

{if amendments needed:}
## Suggested Amendments ({count})

### 1. {amendment_title}
**Issue**: {description}
**Suggestion**: {specific change}
**Source**: {url}

{if score >= 0.8:}
✨ This note is well-verified! Only minor improvements suggested.

{if score < 0.6:}
⚠️ This note needs significant revision. Would you like me to suggest a rewrite?
```

---

### Step 7: 🚨 MANDATORY - Get User Decision

```
Would you like me to:
1. Update the note with sources and confidence score only
2. Update sources + apply suggested amendments
3. Show me a draft with amendments before updating
4. Don't update the note

Choose 1, 2, 3, or 4.
```

**WAIT FOR USER RESPONSE** ← CRITICAL

---

### Step 8: Update Note

**Based on user choice:**

**Option 1**: Update frontmatter only
```
Tool: edit_note(filename, title, body)
- Keep body unchanged
- Add/update sources list
- Set confidence_score
```

**Option 2**: Update frontmatter + apply amendments
```
Tool: edit_note(filename, title, body)
- Apply suggested changes to body
- Add/update sources list
- Set confidence_score
- Add "## Sources" section at end of note with full citations
```

**Option 3**: Show draft
```
Present full updated note content
Wait for approval
If approved → proceed with Option 2
```

**Option 4**: Do nothing
```
"Got it - no changes made. The research findings are here if you want to reference them later."
```

---

### Step 9: Confirmation

```
✅ Updated: {filename}

Changes made:
- Added {n} sources
- Set confidence score: {score}
{if amendments applied:}
- Applied {m} amendments

You can review this note anytime or continue researching other notes.
```

---

## Source Metadata Format

**Structure for sources list in frontmatter**:
```yaml
sources:
  - url: "https://docs.python.org/3/library/asyncio.html"
    title: "asyncio — Asynchronous I/O"
    accessed_date: "2026-01-24"
    note: "Official Python documentation - verified async/await behavior"
  - url: "https://peps.python.org/pep-0492/"
    title: "PEP 492 – Coroutines with async and await syntax"
    accessed_date: "2026-01-24"
    note: "Original proposal - verified syntax and semantics"
```

**When adding sources**:
- `url`: Required - full URL
- `title`: Optional but recommended - page title or document name
- `accessed_date`: Optional - today's date in YYYY-MM-DD format
- `note`: Optional - brief note about what this source verified

---

## Edge Cases

### No Sources Found
**User**: "Validate this note"
**Scenario**: Can't find authoritative sources

**Response**:
```
⚠️ **Limited Sources Found**

I searched for authoritative sources but couldn't find strong verification for these claims:
- {claim_1}
- {claim_2}

Confidence score: 0.3 (poor)

This might mean:
1. The information is too specific or niche
2. The topic is emerging/new
3. The claims may be inaccurate

Would you like me to:
1. Search with broader terms
2. Mark this note for manual verification
3. Flag it as low-confidence for now
```

### Contradicting Sources
**Scenario**: Multiple sources disagree

**Response**:
```
⚠️ **Conflicting Information Found**

Source A says: {claim_a}
Source B says: {claim_b}

This is often because:
- Different versions/implementations
- Context-dependent behavior
- One source is outdated

I've set confidence to 0.5 (fair). Recommend adding context about when each is true.
```

### User Disagrees with Assessment
**User**: "That confidence score is too low"

**Response**:
```
I understand - let me explain my reasoning:

{explain specific concerns that lowered score}

If you believe the note is accurate based on your expertise, I can:
1. Adjust the confidence score to what you think is appropriate
2. Add a note that this is based on domain expertise
3. Keep searching for better sources

What would you prefer?
```

---

## Research Quality Guidelines

### Good Research Practices
- ✅ Verify code examples actually run/compile
- ✅ Check publication dates (prefer recent for fast-moving tech)
- ✅ Cross-reference multiple sources
- ✅ Prefer primary sources (docs) over secondary (blogs)
- ✅ Note version-specific behavior

### Avoid
- ❌ Trusting single sources without verification
- ❌ Using outdated documentation
- ❌ Copying sources without verifying content
- ❌ Giving high scores without strong evidence
- ❌ Being vague in amendments ("fix this section")

---

## Success Criteria

A successful validation has:
- ✅ Researched all major claims in the note
- ✅ Found 2+ authoritative sources (when possible)
- ✅ Assigned honest, evidence-based confidence score
- ✅ Provided specific, actionable amendments
- ✅ Updated note with sources and score (if user approved)
- ✅ Clear explanation of confidence reasoning

---

## Common Validation Patterns

### Pattern 1: Code Snippet Verification
```
1. Identify the language/framework
2. Search: "{language} {concept} official documentation 2026"
3. Fetch official docs
4. Compare note's code with documented examples
5. Check for deprecated patterns
6. Verify output/behavior claims
```

### Pattern 2: Concept Definition Verification
```
1. Identify the technical term
2. Search: "{term} definition {field} 2026"
3. Find RFC/spec/official definition
4. Compare note's definition
5. Check for missing nuances
6. Verify examples are accurate
```

### Pattern 3: Comparison Verification
```
1. Identify items being compared (e.g., "X vs Y")
2. Search official docs for each
3. Verify comparison points are accurate
4. Check for missing important differences
5. Ensure fairness (not biased toward one option)
```

---

## Tips for Effective Validation

1. **Start broad, then narrow**: Search general topic first, then specific claims
2. **Use the year**: Add "2026" to searches to get current info
3. **Check multiple sources**: Don't stop at first result
4. **Be skeptical**: Question claims that seem surprising
5. **Document reasoning**: Explain why you gave a particular score
6. **Preserve user's voice**: When amending, keep their writing style
7. **Be constructive**: Frame amendments as improvements, not criticism
