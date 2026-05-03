"""Variant generator for drill cards.

At capture time, calls an LLM to produce 'buddy' (broken-to-fix) and 'reverse'
(maybe-broken-to-judge) variants of a drill card's model answer. These variants
are stored on the card so that review (including Buddy and Reverse modes) can
run offline without further LLM calls.

Provider is pluggable via the LLM_PROVIDER env var (default: anthropic).
Gracefully degrades: if no API key or SDK is available, the caller can save
the card with variants_status='failed' and regenerate later.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class LLMUnavailableError(RuntimeError):
    """Raised when variant generation can't proceed (missing key or SDK)."""


DEFAULT_MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """You generate practice variants for code drill flashcards.

Given a code prompt, a reference solution, and its language, produce:
  - 2 "buddy" variants: plausibly broken versions of the solution, each with a one-line bug description.
  - 2 "reverse" variants: code snippets attempting the same goal. Include one correct and one buggy. For buggy ones, add a one-line issue description.

Rules:
  - Bugs must be realistic — wrong flag, off-by-one, inverted filter, wrong tool — not cartoonishly obvious.
  - Keep each variant as close to the reference shape as possible. One isolated mistake per broken variant.
  - Respect the provided language and its idioms.
  - Output ONLY a single JSON object matching the schema below. No prose, no code fences.

Schema:
{
  "buddy": [
    {"broken": "<code>", "bug": "<one-line description>"},
    {"broken": "<code>", "bug": "<one-line description>"}
  ],
  "reverse": [
    {"code": "<code>", "correct": true},
    {"code": "<code>", "correct": false, "issue": "<one-line description>"}
  ]
}
"""


def generate_variants(
    prompt: str,
    model_answer: str,
    language: str,
    model: str = DEFAULT_MODEL,
) -> Dict[str, List[Dict[str, Any]]]:
    """Generate buddy and reverse variants for a drill card.

    Args:
        prompt: The drill prompt / goal text.
        model_answer: The reference solution code.
        language: Code language (bash, python, sql, regex, etc.).
        model: Anthropic model ID. Defaults to Haiku 4.5 (cheap, fast).

    Returns:
        {"buddy": [{"broken": str, "bug": str}, ...],
         "reverse": [{"code": str, "correct": bool, "issue"?: str}, ...]}

    Raises:
        LLMUnavailableError: if anthropic SDK isn't installed or key is missing.
        ValueError: if the model returns unparseable output.
    """
    provider = os.environ.get("LLM_PROVIDER", "anthropic").lower()
    if provider != "anthropic":
        raise LLMUnavailableError(
            f"LLM provider '{provider}' not implemented. Only 'anthropic' is currently supported."
        )

    try:
        import anthropic
    except ImportError as e:
        raise LLMUnavailableError(
            "anthropic SDK not installed. Install with: pip install anthropic"
        ) from e

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise LLMUnavailableError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key)

    user_msg = (
        f"Language: {language}\n\n"
        f"Prompt:\n{prompt}\n\n"
        f"Reference solution:\n```{language}\n{model_answer}\n```"
    )

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        temperature=0.3,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_msg}],
    )

    raw = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    ).strip()

    logger.debug(f"LLM raw variant response: {raw[:500]}")
    return _parse_variants_response(raw)


def _parse_variants_response(raw: str) -> Dict[str, List[Dict[str, Any]]]:
    """Parse the LLM's JSON response. Tolerates stray code fences and prose."""
    # Strip accidental ```json ... ``` fences.
    fence = re.match(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", raw, re.DOTALL)
    if fence:
        raw = fence.group(1)

    # Extract the first JSON object if the model added stray prose.
    first_brace = raw.find("{")
    last_brace = raw.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        raw = raw[first_brace : last_brace + 1]

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned non-JSON response: {raw[:200]}") from e

    buddy = data.get("buddy", [])
    reverse = data.get("reverse", [])

    if not isinstance(buddy, list) or not isinstance(reverse, list):
        raise ValueError("LLM response missing buddy/reverse lists")

    # Basic shape validation — each buddy needs broken+bug, each reverse needs code+correct.
    for v in buddy:
        if not isinstance(v, dict) or "broken" not in v or "bug" not in v:
            raise ValueError(f"Malformed buddy variant: {v}")
    for v in reverse:
        if not isinstance(v, dict) or "code" not in v or "correct" not in v:
            raise ValueError(f"Malformed reverse variant: {v}")

    return {"buddy": buddy, "reverse": reverse}
