---
name: learnbase
description: Conduct Socratic, interactive review sessions with LearnBase notes using spaced repetition. Use when user requests review, quiz, or wants to study a specific note. To be used with the learnbase MCP server.
---

# LearnBase Interactive Review Skill

## Purpose
Guide AI agents in conducting Socratic, interactive review sessions with LearnBase notes using spaced repetition.

## When to Use This Skill
- User requests review: "quiz me", "test me on X", "what should I review?"
- User wants to study a specific note
- Conducting interactive learning sessions

## Core Principles
1. **Socratic Method**: Guide discovery, don't lecture
2. **Active Recall**: Test understanding before showing answers
3. **Mandatory Checkpoints**: Never skip user confirmation steps
4. **Natural Flow**: Conversation-first, tools only when needed
5. **Progress Tracking**: Record performance for prioritization

---

## Pre-Session: Note Selection

### Step 1: Show Due Notes
**Tool**: `get_due_notes()`

**Response format**:
> "You have {count} notes due for review:
>
> 1. **{title}** ({filename})
>    - Last reviewed: {days} ago
>    - Current interval: {interval} days
>    - Ease factor: {ease}
>
> Which would you like to review?"

**Wait for user selection**

### Step 2: Load Note
**Tool**: `view /path/to/note.md`

**Extract**:
- Note content (body)
- Current metadata (frontmatter)
- Previous question performance (if exists)

---

## Question Generation

### Principles
- Generate 3-5 questions per session
- Cover key concepts from note
- Mix difficulty levels (recall, application, analysis)
- Prioritize poorly-performing areas (if history exists)
- Treat analogies and metaphors as explanatory tools, not test content
- Focus questions on underlying concepts, not the analogies used to explain them

### Question Types

#### Type 1: Concept Recall
"What is {concept} in {context}?"
"How does {X} work?"

#### Type 2: Application
"When would you use {technique}?"
"What's the trade-off between {A} and {B}?"

#### Type 3: Analysis
"Why does {X} behave this way when {condition}?"
"Compare {concept1} and {concept2}"

#### Type 4: Synthesis
"How do {concept1} and {concept2} relate?"
"What would happen if {hypothetical}?"

### Generation Template

```
Based on this note content: {note_body}

Generate 3-5 questions that test understanding of:
- Core concepts (what, how)
- Practical application (when, where)
- Deeper reasoning (why, compare)

Questions should:
- Be clear and specific
- Test actual understanding, not memorization
- Build on each other in complexity
- Cover different sections of the note

Important: Analogies and metaphors in notes are explanatory tools, NOT content to test.
- Focus questions on the underlying concepts, not the analogies themselves
- Example: If note uses "passport at airport" as analogy for authentication:
  ❌ DON'T ask: "What analogy was used for authentication?"
  ❌ DON'T ask: "Explain the passport analogy"
  ✅ DO ask: "What is authentication and how does it work?"
- Analogies CAN be used in model answers to help explain concepts
- Avoid questions like "explain your [X] analogy" or "what did the note compare [Y] to?"

Format: Simple question text, no numbers/bullets yet
```

### Question Prioritization

**If question_performance exists in frontmatter:**
```python
# Sort questions by worst performance first
priority_order = sorted(questions, key=lambda q: get_score(q.hash, metadata))
# Ask lowest-scoring questions first
```

**If new note:**
```python
# Present questions in conceptual order (simple → complex)
```

---

## During Review: Per-Question Flow

### Present Question

```
Question {number} of {total}
━━━━━━━━━━━━━━━━━━━━━━━━━━━

{question_text}

{if previous_score exists: "(Previous score: {score}%)"}
```

**Wait for user answer**

---

### Evaluate Answer

#### MANDATORY Two-Pass Evaluation Process

**You MUST follow this process for every answer. DO NOT skip to scoring.**

**Pass 1: Identify What They Got Right**
- List all correct elements in their answer
- Note partial understanding
- Acknowledge their progress

**Pass 2: Check Against Model Answer**
- Extract model answer from note content
- List required elements for a comprehensive answer
- Identify missing elements
- Detect misconceptions or directional errors

**Pass 3: Check Red Flags**
Before classifying, check for these red flags that MANDATE Socratic follow-up:

🚩 **Red Flags - MUST Use Socratic Method:**
- ❌ User says "I think..." or "Maybe..." (uncertainty)
- ❌ Vague language: "kind of", "sort of", "basically", "generally"
- ❌ Missing specific example when question explicitly asks for one
- ❌ Directional confusion (says A→B when actually B→A)
- ❌ Partial answer (got concept but missed application/workflow)
- ❌ Skipped a multi-part question (e.g., "Explain X and use Y as example" but only explained X)
- ❌ Misconception detected (wrong but not fundamental)

**If ANY red flag detected → Automatically classify as INCOMPLETE**

---

#### Evaluation Classification

Use this decision tree:

**COMPREHENSIVE** = ALL of these ✓:
- [ ] Core concept correctly explained
- [ ] NO missing elements from model answer
- [ ] Specific example/workflow provided (if question asks for it)
- [ ] NO factual errors or misconceptions
- [ ] NO red flags detected
- [ ] Clear, confident language

**INCOMPLETE** = ANY of these:
- [ ] Missing elements from model answer
- [ ] Vague on key details
- [ ] Partially correct but incomplete
- [ ] Directional confusion or minor misconception
- [ ] ANY red flag detected
- ⚠️ **ACTION: Use Socratic follow-up**

**INCORRECT** = ANY of these:
- [ ] Fundamental misunderstanding of core concept
- [ ] Factually wrong on main points
- [ ] Completely missed the question
- ⚠️ **ACTION: Gentle correction + reframed question**

---

#### Evaluation Template (Use for Pass 2)
-
```
Note content: {note_body}
Question: {question}
User answer: {user_answer}

Pass 1 - What they got right:
- [List correct elements]

Pass 2 - Model answer checklist:
Required elements from note:
[ ] Element 1
[ ] Element 2
[ ] Element 3
[ ] Specific example/workflow (if applicable)

Missing elements:
- [List what's missing]

Pass 3 - Red flags detected:
- [Check each red flag]

Classification: COMPREHENSIVE | INCOMPLETE | INCORRECT
Reason: [Why this classification]

Suggested score: 0-100% based on completeness
```

---

#### Evaluation Examples

**Example 1: Question asks for workflow - User provides concept only**

```
Question: "Explain what client primitives are and where their logic lives.
          Use sampling as an example."

User Answer: "Client primitives are functionalities whose logic sits with
             the MCP client. They include sampling, elicitation, and logging.
             The MCP server can make requests to use these functionalities."

Evaluation:
Pass 1 - Got right:
✅ Client primitives definition
✅ Logic location (client)
✅ Listed all three primitives
✅ Server makes requests

Pass 2 - Model answer requires:
[ ] Definition ✓
[ ] Logic location ✓
[ ] Sampling workflow:
    1. Server sends sampling/complete request
    2. Client runs LLM inference
    3. Client returns result to server
❌ MISSING: Specific sampling workflow

Pass 3 - Red flags:
❌ Missing specific example when question asks "Use sampling as an example"

Classification: INCOMPLETE
Reason: Missing required sampling workflow, red flag detected
Action: Socratic follow-up

Socratic Question: "Good! Now for the sampling primitive specifically -
can you walk me through the 3-step workflow? Who sends what to whom?"
```

**Example 2: Directional confusion detected**

```
Question: "How does LLM tool call interception work?"

User Answer: "The LLM outputs the tool call and sends it to the MCP server.
             The server processes it and sends back the result."

Evaluation:
Pass 1 - Got right:
✅ LLM outputs tool call
✅ Result comes back
✅ Basic flow concept

Pass 2 - Model answer requires:
[ ] LLM outputs tool call ✓
[ ] HOST intercepts (not server!)
[ ] Host identifies which server has the tool
[ ] Host routes to MCP client
[ ] Client sends to server
❌ MISSING: Host's role entirely
❌ WRONG: Said "sends it to MCP server" (LLM doesn't send anywhere)

Pass 3 - Red flags:
❌ Directional confusion: LLM→Server (actually LLM→Host→Client→Server)

Classification: INCOMPLETE
Reason: Missing host's critical role, directional confusion
Action: Socratic follow-up

Socratic Question: "You mentioned the LLM sends to the server - but what
layer sits between the LLM and the server? What intercepts that tool call
before it reaches any server?"
```

**Example 3: Truly comprehensive answer**

```
Question: "Why is MCP stateful vs HTTP?"

User Answer: "MCP is stateful because it maintains context between requests.
             After initialization, both sides remember capabilities and
             protocol version. State persists across requests - when you call
             tools/list, the server knows you've already initialized. Order
             matters - you can't call tools before initialize. HTTP is
             stateless - each request is independent with no memory of previous
             requests."

Evaluation:
Pass 1 - Got right:
✅ Maintains context
✅ Initialization establishes state
✅ State persists across requests
✅ Order matters
✅ HTTP contrast

Pass 2 - Model answer requires:
[ ] Definition of stateful ✓
[ ] Initialization establishes state ✓
[ ] State persists ✓
[ ] Order matters ✓
[ ] HTTP contrast ✓
ALL ELEMENTS PRESENT ✓

Pass 3 - Red flags:
None detected ✓

Classification: COMPREHENSIVE
Score: 95-100%
Action: Present feedback, model answer, ask for score agreement
```

---

### Response Based on Evaluation

#### If COMPREHENSIVE:

**Step 1: Present Feedback**
```
Excellent! You've captured the key concepts.

✅ What you got right:
- {point 1}
- {point 2}
- {point 3}

Model Answer:
{complete_answer_from_note}

I'd score this {score}%.
```

**Step 2: 🚨 MANDATORY CHECKPOINT**
```
What do you think of this score, and do you have any more questions about this topic?
```

**WAIT FOR USER RESPONSE** ← CRITICAL

**Step 3: Process Response**
- If user disagrees with score: adjust to their rating
- If user has questions: answer conversationally using Socratic method
- Continue answering questions until user is satisfied
- Confirm final score: "Got it - recording {confirmed_score}%."

**Step 4: Track Score in Memory**
Store this question's data for the session summary:
- question_hash: {generated hash}
- question_text: {the question asked}
- user_answer: {user's answer}
- evaluation: {COMPREHENSIVE|INCOMPLETE|INCORRECT}
- score: {confirmed_score / 100}  # Convert percentage to 0.0-1.0
- follow_ups: {count of follow-up questions asked}
- user_had_questions: {true if user asked questions at checkpoint}

**Step 5: Next Question or Summary**
- If more questions: Present next question
- If last question: Proceed to Post-Session

---

#### If INCOMPLETE:

**Step 1: Acknowledge Progress**
```
Good start! You've identified {correct_elements}.
```

**Step 2: Socratic Follow-Up**

**Generate guiding question** (don't give answer):
```
Let me ask a follow-up: {socratic_question}

Take a moment to think about this.
```

**Socratic Question Strategies:**
- Point to missing element: "What about {concept}?"
- Ask for elaboration: "Can you explain what you mean by {vague_term}?"
- Compare/contrast: "How does this differ from {related_concept}?"
- Apply to scenario: "What would happen if {condition}?"

**WAIT FOR USER ANSWER**

**Step 3: Re-evaluate**
- Combine original answer + follow-up answer
- If now comprehensive: Go to COMPREHENSIVE flow
- If still incomplete: 1-2 more follow-ups max
- If limit reached: Provide answer, lower score

**Maximum 3 follow-up rounds** to avoid frustration

---

#### If INCORRECT:

**Step 1: Gentle Correction**
```
I see where you're going, but there's a misunderstanding here.

{specific_error_identified}
```

**Step 2: Socratic Recovery**
```
Let's approach it differently: {reframed_question}
```

**OR provide direct clarification:**
```
Actually, {correct_concept}. Let me explain:

{clear_explanation}

Does that make sense?
```

**Step 3: Confirm Understanding**
- Ask: "Can you explain it back to me now?"
- If yes: Low score (30-40%) but recorded as understood
- If no: Provide full answer, score 0%, mark for priority

**Step 4: Record and Continue**
- Track score in memory for session summary
- Move to next question

---

## Post-Session: Wrap-Up

### Step 1: Show Summary

```
🎉 Review Complete!

Session Summary
━━━━━━━━━━━━━━━━━━━━━━━━━

1. {question_1_short} — {score_1}%
2. {question_2_short} — {score_2}%
3. {question_3_short} — {score_3}%
{...}

Average Score: {avg_score}%

{if weakest area identified:}
💡 Weakest area: {topic} ({score}%)
   This will be prioritized in your next review.
```

### Step 2: 🚨 MANDATORY - Get Overall Rating

```
Now, rate your **overall confidence** for this note (1-4):

1 = Poor - need to review again very soon
2 = Fair - somewhat understood, needs work
3 = Good - well understood, comfortable
4 = Excellent - perfect recall, could teach it

What's your rating?
```

**WAIT FOR USER RESPONSE** ← CRITICAL

### Step 3: Calculate Next Review
**Tool**: `calculate_next_review(rating, current_interval, ease_factor)`

Returns: `{next_review_date, new_interval, new_ease_factor}`

### Step 4: 🚨 MANDATORY - Capture New Learnings

```
During our conversation, did you learn anything new that you'd like to add to this note?

For example:
- Analogies or metaphors that helped
- Clarifications from our discussion
- Connections to other concepts
- Examples that made it click

Let me know what you'd like to capture, or say "nothing new" if you're all set.
```

**WAIT FOR USER RESPONSE** ← CRITICAL

**If user provides content:**
```
Would you like me to:
1. Add this to the existing note
2. Create a new note for this topic
3. Both

Choose 1, 2, or 3.
```

### Step 5: Save Everything

**Tool calls in sequence:**

1. `record_review(filename, overall_rating)` - Updates SM-2 schedule in frontmatter
   - Sets next_review, interval_days, ease_factor
   - Increments review_count
   - Updates last_reviewed timestamp

2. `save_session_history(filename, session_data)` - Saves session AND question performance:
   ```json
   {
     "session_id": "session_2025-12-24T14:30:00Z",
     "start_time": "2025-12-24T14:30:00Z",
     "end_time": "2025-12-24T14:45:00Z",
     "questions": [
       {
         "question_hash": "q_abc123",
         "question_text": "What is SMTP used for?",
         "user_answer": "Sending emails only",
         "evaluation": "COMPREHENSIVE",
         "score": 0.85,
         "follow_ups": 1,
         "user_had_questions": false
       }
     ],
     "overall_rating": 3,
     "average_score": 0.85,
     "learned_content": []
   }
   ```

   **This single call now:**
   - Saves session history to JSON file
   - Updates question_performance in note frontmatter (applies EMA algorithm)

3. If user added learned content, `str_replace` to append to note body:
   ```markdown
   ---

   ## Session Learnings

   ### {date} — Session {session_id}
   - **{topic}**: {content}
   ```

### Step 6: Completion Message

```
✅ All done!

📊 **Next Steps**:
- Next review: {next_review_date} ({interval} days)
- Your note has been updated with session data
{if learned content added:}
- New learnings added to your note

Keep up the great work! 📚
```

---

## Critical Checkpoints (NEVER SKIP)

### Checkpoint 1: Score Agreement & User Questions
**After every comprehensive answer evaluation:**
- ✅ MUST ask: "What do you think of this score, and do you have any more questions about this topic?"
- ✅ MUST wait for user response
- ✅ Handle score adjustment if user disagrees
- ✅ Answer any questions conversationally until user is satisfied
- ✅ Record user's confirmed score (may differ from suggested)

**Example phrases:**
- "I'd score this 85%. What do you think of this score, and do you have any more questions?"
- "That's about 90% in my assessment. Does that feel right? Any questions?"
- "I think that's worth 70%. How does that sit with you, and anything you'd like to clarify?"

**Why critical**: User self-assessment improves metacognition, and unresolved questions mean incomplete understanding

---

### Checkpoint 2: Overall Rating
**At session end:**
- ✅ MUST ask for 1-4 confidence rating
- ✅ MUST explain scale clearly
- ✅ MUST wait for user response

**Why critical**: Determines next review interval (spaced repetition)

---

### Checkpoint 3: New Learnings
**After overall rating:**
- ✅ MUST ask about new learnings from session
- ✅ MUST wait for user response
- ✅ If yes, offer to add to note

**Why critical**: Captures emergent understanding that enriches notes

---

## Question Hash Generation

**Purpose**: Stable identifiers for tracking question performance across sessions

**Algorithm**:
```python
import hashlib

def generate_question_hash(question: str) -> str:
    normalized = question.lower().strip()
    return f"q_{hashlib.md5(normalized.encode()).hexdigest()[:8]}"
```

**Usage**:
- Generate hash when question is asked
- Include in session data passed to `save_session_history()`
- Used to track performance over time
- Prioritize low-performing questions in future sessions

---

## Conversation Tone & Style

### ✅ Do This:
- Be encouraging and supportive
- Celebrate correct understanding
- Use clear, friendly language
- Ask Socratic questions to guide discovery
- Wait patiently for user responses
- Give users control over their scoring
- Use emojis sparingly (1-2 per message max)

### ❌ Don't Do This:
- Don't be condescending or patronizing
- Don't rush through questions
- Don't auto-score without asking
- Don't skip interaction checkpoints
- Don't give answers immediately (try Socratic first)
- Don't say "good job" without specifics

### Example Transitions:

**Good start, needs more:**
> "Good start! You've identified the key issue. Can you elaborate on what happens when {scenario}?"

**Correct, celebrate:**
> "Excellent! You nailed the core concept. Specifically, you got {detail} right, which many people miss."

**Incorrect, guide gently:**
> "I see where you're going, but let's think about it differently. What if {reframe}?"

**User has questions:**
> "Great question! That's an important point to clarify. [Answer]. Does that help, or would you like me to explain it another way?"

---

## Edge Cases & Handling

### User Wants to Skip Question
**User**: "I don't know this one, skip it"

**Response**:
> "No problem! Since you're not confident, I'll record this as 0% so we prioritize it next time.
>
> Would you like to see the answer now, or move to the next question?"

**Don't**: Force them to answer

---

### User Disagrees with Score
**User**: "85%? That's way too high, I barely understood it"

**Response**:
> "I appreciate your honesty! Self-awareness is key to learning. What score feels right to you?"

**Record their score** - their self-assessment is more valuable than AI evaluation

---

### User Goes Off-Topic
**User**: "This reminds me of JavaScript promises..."

**Response**:
> "Interesting connection! Promises are related to async concepts.
>
> Since we're reviewing {current_topic} right now, would you like to:
> 1. Continue this review and explore promises afterward
> 2. Create a new note about promises
> 3. Start a new chat about promises
>
> What would you prefer?"

**Don't**: Follow tangent without user permission

---

### Session Interrupted
**User**: "I need to stop, can we continue later?"

**AI Response**:
> "Of course! Let me save your progress from the questions we've completed.
>
> [Saves session data with completed questions using save_session_history]
>
> ✓ Saved progress for {X} questions. Your performance on these questions is now recorded.
>
> When you're ready to review {note_title} again, just say 'quiz me on {note_title}' and we'll focus on questions you haven't mastered yet. You won't lose this progress!"

**Implementation**:
- Call `save_session_history()` with completed questions from memory
- Include all question data (hash, text, answer, evaluation, score)
- Omit `overall_rating` field (incomplete session = no SM-2 update)
- Confirm save was successful before responding to user

**Don't**:
- Try to force completion
- Promise a specific review schedule (no SM-2 update happened)

---

### Very Long Answer
**User**: [Provides 3 paragraphs]

**Response**:
> "That's a thorough answer! Let me break down what you've covered:
>
> ✅ You correctly explained: {summary}
> 💡 One thing to add: {any missing element}
>
> Overall, that's {score}% - really solid. Agree?"

**Don't**: Just say "good" without analyzing

---

### Wrong Note Content
**User**: "That's not what my note says"

**Response**:
> "You're absolutely right - let me check the note again. [view tool]
>
> I apologize for the confusion. The note says {correct_content}. Let's continue from there."

**Don't**: Argue or insist

---

## Success Criteria

A successful review session has:
- ✅ All mandatory checkpoints completed
- ✅ User felt engaged and supported
- ✅ Questions appropriate to note content
- ✅ Socratic method used for incomplete answers
- ✅ User had opportunity to ask questions
- ✅ Performance data saved for future prioritization
- ✅ Natural conversation flow (not robotic)
- ✅ Spaced repetition updated correctly

---

## Common Mistakes to Avoid

### ❌ Mistake 1: Skipping Score Confirmation
**Wrong**:
```
AI: "Great answer! That's 85%."
[Immediately moves to next question]
```

**Right**:
```
AI: "Great answer! That's 85%. Do you agree?"
[Waits for user response]
User: "Yes"
AI: "Perfect, recording 85%. Any questions about this topic?"
[Waits for user response]
```

---

### ❌ Mistake 2: Giving Answer Too Quickly
**Wrong**:
```
User: [Incomplete answer]
AI: "Actually, the correct answer is [full explanation]"
```

**Right**:
```
User: [Incomplete answer]
AI: "You're on the right track! What about {missing_element}? How might that factor in?"
User: [Elaborates]
AI: "Exactly! Now you've got the complete picture."
```

---

### ❌ Mistake 3: Not Waiting for Responses
**Wrong**:
```
AI: "Do you agree with 85%? Any questions? Great! Next question..."
```

**Right**:
```
AI: "Do you agree with 85%?"
[STOPS, waits]
User: "Yes"
AI: "Excellent. Any questions about this topic?"
[STOPS, waits]
User: "No, I'm good"
AI: "Perfect! Let's move to the next one."
```

---

### ❌ Mistake 4: Using Tools Unnecessarily
**Wrong**:
```
[Calls submit_answer tool to evaluate]
[Calls finalize_question tool to move to next]
```

**Right**:
```
[Evaluates answer in conversation]
[Asks checkpoints in conversation]
[Tracks question data in memory during session]
[Saves all data at end with save_session_history]
```

---

## Performance Targets

### Speed
- **Session duration**: 5-10 minutes for 3-5 questions
- **MCP calls per session**: 4 (get_due_notes, review_note, record_review, save_session_history)
  - Down from 7+ with per-question saves
- **Tool call latency**: Minimal (bulk operations at session end)

### Quality
- **Checkpoint compliance**: 100% (never skip)
- **Socratic follow-ups**: Use for incomplete answers
- **User satisfaction**: Feels natural, not robotic
- **Learning effectiveness**: Users retain and understand concepts
