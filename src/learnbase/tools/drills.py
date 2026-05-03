"""MCP handlers for code drill cards."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from mcp.types import TextContent

from ..core.note_manager import NoteManager
from ..core.models import DrillNote
from ..core.llm_generator import generate_variants, LLMUnavailableError

logger = logging.getLogger(__name__)


def _format_similar_drills(matches: list[dict]) -> str:
    lines = ["⚠️ Similar drill cards already exist:\n"]
    for i, m in enumerate(matches, 1):
        sim = m.get("similarity") or 0.0
        lines.append(f"{i}. {m.get('filename')} — {m.get('title')} (similarity: {sim:.2f})")
    lines.append(
        "\nTo create anyway, call this tool again with `force: true`.\n"
        "To merge into an existing card, use edit_note instead."
    )
    return "\n".join(lines)


def handle_add_drill_card(note_manager: NoteManager, arguments: Any) -> list[TextContent]:
    """Capture a new drill card.

    Required: title, prompt, model_answer, language
    Optional: why_captured, tags, force (bypass similarity check), skip_variants
    """
    title = arguments.get("title")
    prompt = arguments.get("prompt")
    model_answer = arguments.get("model_answer")
    language = arguments.get("language")
    why_captured = arguments.get("why_captured", "")
    tags = arguments.get("tags") or []
    force = bool(arguments.get("force", False))
    skip_variants = bool(arguments.get("skip_variants", False))

    missing = [
        name for name, val in (
            ("title", title),
            ("prompt", prompt),
            ("model_answer", model_answer),
            ("language", language),
        ) if not val
    ]
    if missing:
        return [TextContent(
            type="text",
            text=f"Error: required fields missing: {', '.join(missing)}"
        )]

    # Similarity check — warn unless force=true.
    if not force:
        similar = note_manager.find_similar_drills(prompt=prompt, threshold=0.75, limit=3)
        if similar:
            return [TextContent(type="text", text=_format_similar_drills(similar))]

    # Variant generation (best-effort).
    buddy_variants: list[dict] = []
    reverse_variants: list[dict] = []
    variants_status = "pending"
    variants_note = ""

    if not skip_variants:
        try:
            result = generate_variants(
                prompt=prompt, model_answer=model_answer, language=language
            )
            buddy_variants = result["buddy"]
            reverse_variants = result["reverse"]
            variants_status = "ready"
        except LLMUnavailableError as e:
            logger.info(f"Variant generation skipped: {e}")
            variants_status = "failed"
            variants_note = (
                f"\n(Variants not generated: {e}. "
                "Drill mode works; Buddy/Reverse unavailable until you run regenerate_variants.)"
            )
        except ValueError as e:
            logger.warning(f"Variant generation produced invalid output: {e}")
            variants_status = "failed"
            variants_note = (
                f"\n(Variants failed validation: {e}. Run regenerate_variants to retry.)"
            )
        except Exception as e:
            logger.error(f"Unexpected variant generation error: {e}", exc_info=True)
            variants_status = "failed"
            variants_note = f"\n(Variants failed: {e}. Run regenerate_variants to retry.)"

    try:
        filename = note_manager.create_drill_note(
            title=title,
            prompt=prompt,
            model_answer=model_answer,
            language=language,
            why_captured=why_captured,
            tags=tags,
            buddy_variants=buddy_variants,
            reverse_variants=reverse_variants,
            variants_status=variants_status,
        )
    except ValueError as e:
        return [TextContent(type="text", text=f"Error: {e}")]
    except (IOError, OSError) as e:
        return [TextContent(type="text", text=f"Error: file write failed: {e}")]

    msg = (
        f"✓ Created drill card: {filename}\n"
        f"Title: {title}\n"
        f"Language: {language}\n"
        f"Variants: {variants_status}"
        f"{variants_note}"
    )
    return [TextContent(type="text", text=msg)]


def handle_review_drill(note_manager: NoteManager, arguments: Any) -> list[TextContent]:
    """Record a drill review (ladder SR advance / demote)."""
    filename = arguments.get("filename")
    passed = arguments.get("passed")
    mode = arguments.get("mode", "drill")
    is_first_mode = bool(arguments.get("is_first_mode", True))

    if not filename:
        return [TextContent(type="text", text="Error: filename is required")]
    if passed is None:
        return [TextContent(type="text", text="Error: passed (bool) is required")]
    if mode not in ("drill", "buddy", "reverse"):
        return [TextContent(
            type="text",
            text=f"Error: mode must be 'drill', 'buddy', or 'reverse' — got '{mode}'"
        )]

    try:
        updated = note_manager.update_drill_review(
            filename=filename, passed=bool(passed), is_first_mode=is_first_mode
        )
    except ValueError as e:
        return [TextContent(type="text", text=f"Error: {e}")]
    except (IOError, OSError) as e:
        return [TextContent(type="text", text=f"Error: file write failed: {e}")]

    verdict = "PASS" if passed else "FAIL"
    sr_note = "(first-mode attempt, SR updated)" if is_first_mode else "(free practice, SR unchanged)"
    rewrite_flag = " ⚠️ [needs rewrite]" if updated.needs_rewrite else ""
    next_review_str = updated.next_review.strftime("%Y-%m-%d")

    msg = (
        f"✓ {verdict} ({mode}) {sr_note}{rewrite_flag}\n"
        f"File: {filename}\n"
        f"Ladder step: {updated.ladder_step}\n"
        f"Next review: {next_review_str}\n"
        f"Fail streak: {updated.fail_streak}\n"
        f"Review count: {updated.review_count}"
    )
    return [TextContent(type="text", text=msg)]


def handle_list_due_drills(note_manager: NoteManager, arguments: Any) -> list[TextContent]:
    """List drill cards that are due today or earlier."""
    limit = arguments.get("limit")

    due = note_manager.get_due_drills(limit=limit)
    if not due:
        return [TextContent(type="text", text="No drill cards currently due.")]

    lines = [f"Found {len(due)} drill card(s) due for review:\n"]
    for d in due:
        days_until = d.days_until_review()
        if days_until < 0:
            status = f"overdue by {-days_until} days"
        elif days_until == 0:
            status = "due today"
        else:
            status = f"due in {days_until} days"
        rewrite_flag = " ⚠️ [needs rewrite]" if d.needs_rewrite else ""
        lines.append(
            f"- {d.filename}{rewrite_flag}\n"
            f"    Title: {d.title}\n"
            f"    Language: {d.language}\n"
            f"    Status: {status} (step {d.ladder_step}, reviews {d.review_count})\n"
            f"    Variants: {d.variants_status}"
        )
    return [TextContent(type="text", text="\n".join(lines))]


def handle_get_drill(note_manager: NoteManager, arguments: Any) -> list[TextContent]:
    """Fetch a drill card with prompt, model answer, and variants."""
    filename = arguments.get("filename")
    if not filename:
        return [TextContent(type="text", text="Error: filename is required")]

    note = note_manager.get_note(filename)
    if not note:
        return [TextContent(type="text", text=f"Error: drill '{filename}' not found")]
    if not isinstance(note, DrillNote):
        return [TextContent(type="text", text=f"Error: '{filename}' is not a drill card")]

    prompt, model_answer = note.parse_prompt_and_answer()
    last_reviewed_str = (
        note.last_reviewed.strftime("%Y-%m-%d") if note.last_reviewed else "Never"
    )

    result = (
        f"# {note.title}\n\n"
        f"**File**: {note.filename}\n"
        f"**Language**: {note.language}\n"
        f"**Tags**: {', '.join(note.tags) or '-'}\n"
        f"**Ladder step**: {note.ladder_step}\n"
        f"**Next review**: {note.next_review.strftime('%Y-%m-%d')}\n"
        f"**Last reviewed**: {last_reviewed_str}\n"
        f"**Reviews**: {note.review_count}  |  **Fail streak**: {note.fail_streak}\n"
        f"**Variants status**: {note.variants_status}\n"
        f"**Needs rewrite**: {note.needs_rewrite}\n\n"
        f"---\n\n"
        f"## Prompt\n{prompt}\n\n"
        f"## Model Answer\n```{note.language}\n{model_answer}\n```\n\n"
        f"## Why captured\n{note.why_captured or '-'}\n\n"
        f"## Buddy variants ({len(note.buddy_variants)})\n"
    )
    for i, v in enumerate(note.buddy_variants, 1):
        result += f"{i}. `{v.get('broken', '')}` — {v.get('bug', '')}\n"
    result += f"\n## Reverse variants ({len(note.reverse_variants)})\n"
    for i, v in enumerate(note.reverse_variants, 1):
        correct = v.get("correct", False)
        label = "correct" if correct else f"BUGGY — {v.get('issue', '')}"
        result += f"{i}. `{v.get('code', '')}` ({label})\n"

    return [TextContent(type="text", text=result)]


def handle_regenerate_variants(note_manager: NoteManager, arguments: Any) -> list[TextContent]:
    """Retry AI variant generation for a card (typically one with status=failed/pending)."""
    filename = arguments.get("filename")
    if not filename:
        return [TextContent(type="text", text="Error: filename is required")]

    note = note_manager.get_note(filename)
    if not note:
        return [TextContent(type="text", text=f"Error: drill '{filename}' not found")]
    if not isinstance(note, DrillNote):
        return [TextContent(type="text", text=f"Error: '{filename}' is not a drill card")]

    prompt, model_answer = note.parse_prompt_and_answer()
    if not prompt or not model_answer:
        return [TextContent(
            type="text",
            text=f"Error: could not parse prompt/model_answer from {filename}; check body format"
        )]

    try:
        result = generate_variants(
            prompt=prompt, model_answer=model_answer, language=note.language
        )
    except LLMUnavailableError as e:
        return [TextContent(type="text", text=f"LLM unavailable: {e}")]
    except ValueError as e:
        return [TextContent(type="text", text=f"LLM returned invalid output: {e}")]
    except Exception as e:
        logger.error(f"regenerate_variants failed: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Unexpected error: {e}")]

    note_manager.update_drill_variants(
        filename=filename,
        buddy_variants=result["buddy"],
        reverse_variants=result["reverse"],
        variants_status="ready",
    )

    return [TextContent(
        type="text",
        text=(
            f"✓ Regenerated variants for {filename}\n"
            f"Buddy: {len(result['buddy'])}\n"
            f"Reverse: {len(result['reverse'])}"
        )
    )]
