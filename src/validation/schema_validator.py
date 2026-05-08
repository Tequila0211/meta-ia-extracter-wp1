"""
JSON Schema validation for AI outputs.

Loads schemas from schemas/ and validates AI output JSON against them.
"""

import json
from pathlib import Path
from typing import Any

import jsonschema

from src.utils.logging_config import get_logger
from src.utils.paths import get_schemas_dir

logger = get_logger("validation")


class SchemaValidationResult:
    """Result of a schema validation."""

    def __init__(self, valid: bool, errors: list[str] | None = None):
        self.valid = valid
        self.errors = errors or []

    def __bool__(self):
        return self.valid

    def __repr__(self):
        if self.valid:
            return "SchemaValidationResult(valid=True)"
        return f"SchemaValidationResult(valid=False, errors={self.errors})"


def load_schema(schema_name: str) -> dict:
    """Load a JSON schema from the schemas directory.

    Args:
        schema_name: Schema filename (e.g., 'classification.schema.json').

    Returns:
        Parsed JSON schema dict.

    Raises:
        FileNotFoundError: If schema file doesn't exist.
    """
    schema_path = get_schemas_dir() / schema_name
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_against_schema(
    data: dict[str, Any],
    schema_name: str,
) -> SchemaValidationResult:
    """Validate data against a JSON schema.

    Args:
        data: Data dictionary to validate.
        schema_name: Schema filename to validate against.

    Returns:
        SchemaValidationResult with valid flag and error details.
    """
    try:
        schema = load_schema(schema_name)
        jsonschema.validate(instance=data, schema=schema)
        logger.info(f"Schema validation passed: {schema_name}")
        return SchemaValidationResult(valid=True)
    except jsonschema.ValidationError as e:
        error_msg = f"Schema validation failed: {e.message}"
        error_path = " → ".join(str(p) for p in e.absolute_path) if e.absolute_path else "root"
        full_error = f"{error_msg} (at {error_path})"
        logger.warning(f"Schema validation failed for {schema_name}: {full_error}")
        return SchemaValidationResult(valid=False, errors=[full_error])
    except jsonschema.SchemaError as e:
        error_msg = f"Invalid schema {schema_name}: {e.message}"
        logger.error(error_msg)
        return SchemaValidationResult(valid=False, errors=[error_msg])


def validate_json_file(
    json_path: str | Path,
    schema_name: str,
) -> SchemaValidationResult:
    """Validate a JSON file against a schema.

    Args:
        json_path: Path to JSON file.
        schema_name: Schema filename to validate against.

    Returns:
        SchemaValidationResult.
    """
    json_path = Path(json_path)
    if not json_path.exists():
        return SchemaValidationResult(
            valid=False, errors=[f"JSON file not found: {json_path}"]
        )

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return SchemaValidationResult(
            valid=False, errors=[f"Invalid JSON in {json_path.name}: {e}"]
        )

    return validate_against_schema(data, schema_name)


# Schema mapping for task types
TASK_SCHEMA_MAP = {
    "classification": "classification.schema.json",
    "mapping": "mapping.schema.json",
    "scenario_extraction": "scenario_extraction.schema.json",
    "outcome_extraction": "outcome_extraction.schema.json",
    "audit": "audit.schema.json",
}


def validate_task_output(
    data: dict[str, Any],
    task_type: str,
) -> SchemaValidationResult:
    """Validate AI output for a specific task type.

    Args:
        data: AI output data.
        task_type: Task type name.

    Returns:
        SchemaValidationResult.
    """
    schema_name = TASK_SCHEMA_MAP.get(task_type)
    if not schema_name:
        return SchemaValidationResult(
            valid=False, errors=[f"Unknown task type: {task_type}"]
        )
    return validate_against_schema(data, schema_name)
