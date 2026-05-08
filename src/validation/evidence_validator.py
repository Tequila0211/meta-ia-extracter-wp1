"""
Evidence validation.

Validates evidence records for completeness and consistency:
- Page number exists
- Source type is valid
- Either evidence_text or crop_path is present
"""

from typing import Any

import yaml

from src.utils.logging_config import get_logger
from src.utils.paths import get_controlled_vocabularies_path

logger = get_logger("validation")


class EvidenceValidationResult:
    """Result of evidence validation."""

    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, msg: str):
        self.errors.append(msg)
        logger.warning(f"Evidence error: {msg}")

    def add_warning(self, msg: str):
        self.warnings.append(msg)

    def __bool__(self):
        return self.valid


def load_valid_source_types() -> list[str]:
    """Load valid source types from controlled vocabularies."""
    vocab_path = get_controlled_vocabularies_path()
    with open(vocab_path, "r", encoding="utf-8") as f:
        vocab = yaml.safe_load(f)
    return vocab.get("source_type", [])


def validate_evidence(
    evidence_data: dict[str, Any],
    total_pages: int | None = None,
) -> EvidenceValidationResult:
    """Validate an evidence record.

    Args:
        evidence_data: Evidence data dict.
        total_pages: Total number of pages in the document (for page validation).

    Returns:
        EvidenceValidationResult.
    """
    result = EvidenceValidationResult()

    # Check page number
    page = evidence_data.get("page_number") or evidence_data.get("page")
    if page is None:
        result.add_error("Evidence has no page number")
    elif total_pages and page > total_pages:
        result.add_error(f"Page {page} exceeds document length ({total_pages} pages)")

    # Check source type
    source_type = evidence_data.get("source_type")
    if source_type:
        valid_types = load_valid_source_types()
        if source_type not in valid_types:
            result.add_error(f"Invalid source type: '{source_type}'. Valid: {valid_types}")
    else:
        result.add_warning("No source type specified")

    # Check evidence content
    evidence_text = evidence_data.get("evidence_text")
    crop_path = evidence_data.get("crop_path")
    if not evidence_text and not crop_path:
        result.add_error("Evidence has neither evidence_text nor crop_path — insufficient evidence")

    # Check table_or_figure if present
    table_or_figure = evidence_data.get("table_or_figure_label") or evidence_data.get("table_or_figure")
    if table_or_figure and not isinstance(table_or_figure, str):
        result.add_error("table_or_figure must be a string")

    return result
