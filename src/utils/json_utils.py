"""
Utility functions for parsing AI-generated JSON output.

Handles responses that may contain markdown code fences
(e.g., ```json ... ```) when response_mime_type is not set.
"""

import json
from pathlib import Path
from typing import Any


def strip_markdown_fences(text: str) -> str:
    """Strip markdown code fences from a string.

    When Gemini responds without response_mime_type='application/json'
    (e.g., when google_search grounding is active), it may wrap JSON
    output in markdown code fences like ```json ... ```.

    Args:
        text: Raw text that may contain markdown fences.

    Returns:
        Text with markdown fences removed.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Remove opening fence (```json or ```)
        try:
            first_newline = cleaned.index("\n")
            cleaned = cleaned[first_newline + 1:]
        except ValueError:
            return cleaned
        # Remove closing fence
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[:-3].rstrip()
    return cleaned


def parse_json_safe(text: str) -> Any:
    """Parse JSON from text, stripping markdown fences if present.

    Args:
        text: Raw text containing JSON, possibly wrapped in markdown fences.

    Returns:
        Parsed JSON data.

    Raises:
        json.JSONDecodeError: If the text is not valid JSON after cleanup.
    """
    return json.loads(strip_markdown_fences(text))


def load_ai_json(path: Path) -> Any:
    """Load and parse a JSON file saved from AI output.

    Handles markdown code fences that may be present in files saved
    from grounding-enabled API calls.

    Args:
        path: Path to the JSON file.

    Returns:
        Parsed JSON data.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the content is not valid JSON.
    """
    raw_text = path.read_text(encoding="utf-8")
    return parse_json_safe(raw_text)
