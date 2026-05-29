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


def sanitize_json_data(data: Any, schema_name: str) -> tuple[Any, bool]:
    """Proactively sanitizes common LLM output mismatches with the schemas to make the pipeline resilient."""
    if not isinstance(data, dict):
        return data, False

    modified = False

    # 1. scenario_extraction.schema.json
    if schema_name == "scenario_extraction.schema.json":
        scenarios = data.get("scenarios")
        if isinstance(scenarios, list):
            for scen in scenarios:
                if isinstance(scen, dict):
                    # Ensure required status and human_review_required are present
                    if "status" not in scen or scen["status"] is None:
                        scen["status"] = "extracted"
                        modified = True
                    if "human_review_required" not in scen or scen["human_review_required"] is None:
                        scen["human_review_required"] = False
                        modified = True
                    
                    # Fill other potentially missing schema-required keys with defaults
                    required_keys = [
                        ("building_typology", "other"),
                        ("climate_location", None),
                        ("climate_zone", None),
                        ("climate_zone_source", None),
                        ("weather_file", None),
                        ("simulation_software", None),
                        ("year", None),
                        ("ssp", None),
                        ("climate_period_type", "current"),
                        ("operational_mode", "normal_operation"),
                        ("baseline_description", None),
                        ("intervention_description", None),
                        ("intervention_type", "not_applicable"),
                        ("is_package", False),
                        ("package_components", []),
                        ("reported_outcomes", []),
                        ("page", None),
                        ("source_type", "text"),
                        ("evidence_text", None)
                    ]
                    for key, default in required_keys:
                        if key not in scen:
                            scen[key] = default
                            modified = True

    # 2. intervention_component_extraction.schema.json
    elif schema_name == "intervention_component_extraction.schema.json":
        components = data.get("components")
        if isinstance(components, list):
            allowed_families = {
                "solar_shading", "natural_ventilation", "evaporative_cooling",
                "thermal_mass", "cool_surface", "green_infrastructure",
                "envelope", "earth_coupling", "active_system", "controls", "other"
            }
            for comp in components:
                if isinstance(comp, dict):
                    # Check component_family
                    fam = comp.get("component_family")
                    if fam not in allowed_families and fam is not None:
                        fam_str = str(fam).lower()
                        # Advanced classifier
                        if "courtyard" in fam_str:
                            comp["component_family"] = "envelope"
                        elif any(s in fam_str for s in ["shade", "shading", "canvas", "awning"]):
                            comp["component_family"] = "solar_shading"
                        elif any(s in fam_str for s in ["vent", "ventilation"]):
                            comp["component_family"] = "natural_ventilation"
                        elif any(s in fam_str for s in ["cool", "evap", "mist", "spray", "water"]):
                            comp["component_family"] = "evaporative_cooling"
                        elif any(s in fam_str for s in ["mass", "concrete", "brick"]):
                            comp["component_family"] = "thermal_mass"
                        elif any(s in fam_str for s in ["roof", "wall", "envelope", "insulation", "glazing", "window"]):
                            comp["component_family"] = "envelope"
                        elif any(s in fam_str for s in ["green", "plant", "roof_green", "garden"]):
                            comp["component_family"] = "green_infrastructure"
                        elif any(s in fam_str for s in ["control", "schedule", "adaptable"]):
                            comp["component_family"] = "controls"
                        elif any(s in fam_str for s in ["active", "pump", "fan", "hvac", "ac"]):
                            comp["component_family"] = "active_system"
                        else:
                            comp["component_family"] = "other"
                        modified = True

                    # Ensure status and is_passive are present
                    if "status" not in comp or comp["status"] is None:
                        comp["status"] = "extracted"
                        modified = True
                    if "is_passive" not in comp or comp["is_passive"] is None:
                        comp["is_passive"] = True
                        modified = True

                    # Ensure operation_schedule matches allowed enums
                    allowed_schedules = {"daytime", "nighttime", "24h", "seasonal", "other", None}
                    op_sched = comp.get("operation_schedule")
                    if op_sched not in allowed_schedules:
                        if op_sched == "hvac_off":
                            comp["operation_schedule"] = "other"
                        else:
                            comp["operation_schedule"] = "other"
                        modified = True

    # 3. meta_readiness.schema.json
    elif schema_name == "meta_readiness.schema.json":
        records = data.get("readiness_records")
        if isinstance(records, list):
            allowed_qualities = {"text", "table", "figure_digitized", "figure_visual", None}
            for rec in records:
                if isinstance(rec, dict):
                    q = rec.get("source_quality")
                    if q not in allowed_qualities and q is not None:
                        q_str = str(q).lower()
                        if "table" in q_str:
                            rec["source_quality"] = "table"
                        elif "figure_digitized" in q_str or "digitized" in q_str:
                            rec["source_quality"] = "figure_digitized"
                        elif "figure_visual" in q_str or "visual" in q_str:
                            rec["source_quality"] = "figure_visual"
                        elif "text" in q_str:
                            rec["source_quality"] = "text"
                        else:
                            rec["source_quality"] = None
                        modified = True

    # 4. outcome_extraction.schema.json
    elif schema_name == "outcome_extraction.schema.json":
        outcomes = data.get("extracted_outcomes")
        if isinstance(outcomes, list):
            allowed_aggregations = {"mean", "max", "min", "median", "cumulative", "hours_above_threshold", "other", None}
            allowed_periods = {"annual", "summer", "winter", "heatwave", "daytime", "nighttime", "other", None}
            for out in outcomes:
                if isinstance(out, dict):
                    # aggregation_method sanitization
                    agg = out.get("aggregation_method")
                    if agg not in allowed_aggregations:
                        if agg == "percentage_above_threshold":
                            out["aggregation_method"] = "hours_above_threshold"
                        else:
                            out["aggregation_method"] = "other"
                        modified = True
                    
                    # time_period sanitization
                    period = out.get("time_period")
                    if period not in allowed_periods:
                        if period in ("power_outage_heatwave", "heatwave_power_outage", "power_outage"):
                            out["time_period"] = "heatwave"
                        else:
                            out["time_period"] = "other"
                        modified = True

    return data, modified


def validate_json_file(
    json_path: str | Path,
    schema_name: str,
) -> SchemaValidationResult:
    """Validate a JSON file against a schema, applying proactive sanitisation of common LLM mismatches first.

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
        from src.utils.json_utils import load_ai_json
        data = load_ai_json(json_path)
    except json.JSONDecodeError as e:
        return SchemaValidationResult(
            valid=False, errors=[f"Invalid JSON in {json_path.name}: {e}"]
        )

    # Sanitize and save back if needed
    data, modified = sanitize_json_data(data, schema_name)
    if modified:
        logger.info(f"[{json_path.name}] Applying schema compliance sanitisation for {schema_name}...")
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save sanitized JSON to {json_path}: {e}")

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
