"""
Codebook validation.

Validates extracted data against codebook definitions:
- outcome_name exists in codebook
- entity_level consistency
- data_type consistency
- unit requirements
- allowed_source_types
"""

from typing import Any

import yaml

from src.utils.logging_config import get_logger
from src.utils.paths import get_codebook_path

logger = get_logger("validation")


class CodebookValidationResult:
    """Result of codebook validation."""

    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, msg: str):
        self.errors.append(msg)
        logger.warning(f"Codebook error: {msg}")

    def add_warning(self, msg: str):
        self.warnings.append(msg)
        logger.info(f"Codebook warning: {msg}")

    def __bool__(self):
        return self.valid


def load_codebook() -> dict:
    """Load and return the codebook YAML.

    Returns:
        Parsed codebook dict.

    Raises:
        FileNotFoundError: If codebook file doesn't exist.
    """
    codebook_path = get_codebook_path()
    with open(codebook_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_codebook_fields(codebook: dict | None = None) -> dict[str, dict]:
    """Get codebook fields indexed by field_name.

    Args:
        codebook: Optional pre-loaded codebook dict.

    Returns:
        Dict mapping field_name to field definition.
    """
    if codebook is None:
        codebook = load_codebook()

    fields = codebook.get("fields", [])
    return {f["field_name"]: f for f in fields}


def validate_codebook_integrity(codebook: dict | None = None) -> CodebookValidationResult:
    """Validate the codebook itself for consistency.

    Checks:
    - No duplicate field_names
    - Critical fields have evidence_required=True
    - Required metadata present

    Args:
        codebook: Optional pre-loaded codebook dict.

    Returns:
        CodebookValidationResult.
    """
    if codebook is None:
        codebook = load_codebook()

    result = CodebookValidationResult()
    fields = codebook.get("fields", [])

    if not fields:
        result.add_error("Codebook has no fields defined")
        return result

    # Check for duplicate field_names
    seen_names = set()
    for field in fields:
        name = field.get("field_name")
        if not name:
            result.add_error("Field missing 'field_name'")
            continue
        if name in seen_names:
            result.add_error(f"Duplicate field_name: {name}")
        seen_names.add(name)

        # Critical fields must have evidence_required
        if field.get("critical") and not field.get("evidence_required"):
            result.add_error(
                f"Critical field '{name}' must have evidence_required=true"
            )

        # Required metadata checks
        if "entity_level" not in field:
            result.add_error(f"Field '{name}' missing 'entity_level'")
        if "data_type" not in field:
            result.add_error(f"Field '{name}' missing 'data_type'")

    logger.info(
        f"Codebook validation: {len(fields)} fields, "
        f"{len(result.errors)} errors, {len(result.warnings)} warnings"
    )
    return result


def validate_outcome_against_codebook(
    outcome_name: str,
    outcome_data: dict[str, Any],
    codebook: dict | None = None,
) -> CodebookValidationResult:
    """Validate a single outcome against the codebook.

    Args:
        outcome_name: Name of the outcome field.
        outcome_data: Outcome data dict.
        codebook: Optional pre-loaded codebook dict.

    Returns:
        CodebookValidationResult.
    """
    result = CodebookValidationResult()
    fields = get_codebook_fields(codebook)

    # Check field exists in codebook
    if outcome_name not in fields:
        result.add_error(f"Unknown codebook field: {outcome_name}")
        return result

    field_def = fields[outcome_name]

    # Check entity_level consistency
    expected_level = field_def.get("entity_level")
    if expected_level == "outcome":
        # Numeric fields need units
        if field_def.get("original_unit_required"):
            unit = outcome_data.get("unit")
            if not unit and outcome_data.get("value") is not None:
                result.add_error(
                    f"Field '{outcome_name}' requires units for numeric values"
                )

    # Check allowed_values for categorical fields
    if field_def.get("data_type") == "categorical":
        allowed = field_def.get("allowed_values", [])
        value = outcome_data.get(outcome_name)
        if value and allowed and value not in allowed:
            result.add_error(
                f"Value '{value}' not in allowed values for '{outcome_name}': {allowed}"
            )

    # Check source_type restrictions
    allowed_sources = field_def.get("allowed_source_types")
    if allowed_sources:
        source_type = outcome_data.get("source_type")
        if source_type and source_type not in allowed_sources:
            result.add_warning(
                f"Source type '{source_type}' not in allowed sources for '{outcome_name}': {allowed_sources}"
            )

    return result
