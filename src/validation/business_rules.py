"""
Methodological business rules and blocking conditions.

Implements all blocking rules from config/extraction_rules.yaml:
- No numeric value without unit
- No critical value without evidence
- No extracted value without page
- Figure values must be marked for digitization
- No package splitting without explicit evidence
- No unknown codebook fields
- 10 new robust validation rules (generic_passive_design_forbidden, misting_not_ventilation, etc.)
"""

import json
from typing import Any

import yaml

from src.utils.logging_config import get_logger
from src.utils.paths import get_extraction_rules_path
from src.validation.codebook_validator import get_codebook_fields

logger = get_logger("validation")


class BusinessRuleResult:
    """Result of a single business rule check."""

    def __init__(self, rule_name: str, passed: bool, action: str | None = None, message: str | None = None):
        self.rule_name = rule_name
        self.passed = passed
        self.action = action  # 'block', 'set_needs_digitization', 'reject', 'unclear', 'flag', 'human_review_required'
        self.message = message


class BusinessRulesValidationResult:
    """Aggregate result of all business rule checks."""

    def __init__(self):
        self.results: list[BusinessRuleResult] = []

    @property
    def valid(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def blocked(self) -> bool:
        return any(r.action == "block" for r in self.results if not r.passed)

    @property
    def failures(self) -> list[BusinessRuleResult]:
        return [r for r in self.results if not r.passed]

    def add(self, result: BusinessRuleResult):
        self.results.append(result)
        if not result.passed:
            logger.warning(f"Business rule failed: {result.rule_name} → {result.action}: {result.message}")

    def __bool__(self):
        return self.valid


def load_extraction_rules() -> dict:
    """Load extraction rules from YAML."""
    rules_path = get_extraction_rules_path()
    with open(rules_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def check_outcome_rules(outcome_data: dict[str, Any]) -> BusinessRulesValidationResult:
    """Check all business rules for an outcome record.

    Args:
        outcome_data: Outcome data dict.

    Returns:
        BusinessRulesValidationResult.
    """
    result = BusinessRulesValidationResult()
    status = outcome_data.get("status")

    # Rule: missing_page
    if status in ("extracted", "extracted_approximate") and outcome_data.get("page") is None:
        result.add(BusinessRuleResult(
            rule_name="missing_page",
            passed=False,
            action="block",
            message="Extracted outcome has no page number",
        ))
    else:
        result.add(BusinessRuleResult(rule_name="missing_page", passed=True))

    # Rule: missing_evidence
    codebook_fields = get_codebook_fields()
    outcome_name = outcome_data.get("outcome_name", "")
    field_def = codebook_fields.get(outcome_name, {})
    is_critical = field_def.get("critical", False)

    if is_critical:
        evidence_text = outcome_data.get("evidence_text")
        crop_path = outcome_data.get("crop_path")
        if not evidence_text and not crop_path:
            result.add(BusinessRuleResult(
                rule_name="missing_evidence",
                passed=False,
                action="block",
                message=f"Critical field '{outcome_name}' has no evidence",
            ))
        else:
            result.add(BusinessRuleResult(rule_name="missing_evidence", passed=True))
    else:
        result.add(BusinessRuleResult(rule_name="missing_evidence", passed=True))

    # Rule: missing_numeric_unit
    has_numeric = (
        outcome_data.get("value") is not None
        or outcome_data.get("reported_effect_value") is not None
    )
    has_unit = bool(
        outcome_data.get("unit")
        or outcome_data.get("reported_effect_unit")
    )
    if has_numeric and not has_unit:
        result.add(BusinessRuleResult(
            rule_name="missing_numeric_unit",
            passed=False,
            action="block",
            message="Numeric outcome has no unit",
        ))
    else:
        result.add(BusinessRuleResult(rule_name="missing_numeric_unit", passed=True))

    # Rule: figure_without_digitization
    source_type = outcome_data.get("source_type")
    extraction_method = outcome_data.get("extraction_method")
    needs_digit = outcome_data.get("needs_digitization", False)
    if source_type == "figure" and extraction_method == "not_extracted" and not needs_digit:
        result.add(BusinessRuleResult(
            rule_name="figure_without_digitization",
            passed=False,
            action="set_needs_digitization",
            message="Figure source not marked for digitization",
        ))
    else:
        result.add(BusinessRuleResult(rule_name="figure_without_digitization", passed=True))

    # Rule: orphan_outcome
    if not outcome_data.get("scenario_temp_id"):
        result.add(BusinessRuleResult(
            rule_name="orphan_outcome",
            passed=False,
            action="block",
            message="Outcome is missing a link to a scenario (scenario_temp_id)",
        ))
    else:
        result.add(BusinessRuleResult(rule_name="orphan_outcome", passed=True))

    # Rule: unknown_codebook_field
    if outcome_name and outcome_name not in codebook_fields:
        result.add(BusinessRuleResult(
            rule_name="unknown_codebook_field",
            passed=False,
            action="reject",
            message=f"Unknown field: {outcome_name}",
        ))
    else:
        result.add(BusinessRuleResult(rule_name="unknown_codebook_field", passed=True))

    # Rule: intervention_requires_baseline_for_effect (NEW)
    calc_effect = outcome_data.get("calculated_effect_value")
    comp_baseline = outcome_data.get("comparison_baseline_scenario_id")
    baseline_val = outcome_data.get("baseline_value")
    if calc_effect is not None and not comp_baseline and not baseline_val:
        result.add(BusinessRuleResult(
            rule_name="intervention_requires_baseline_for_effect",
            passed=False,
            action="flag",
            message="Calculated effect is present but no baseline scenario or value is linked",
        ))
    else:
        result.add(BusinessRuleResult(rule_name="intervention_requires_baseline_for_effect", passed=True))

    # Rule: visual_figure_not_primary_meta (NEW)
    usable_meta = outcome_data.get("usable_for_quantitative_synthesis")
    if extraction_method in ("figure_visual_approximate", "figure_visual_confident") and usable_meta is True:
        result.add(BusinessRuleResult(
            rule_name="visual_figure_not_primary_meta",
            passed=False,
            action="flag",
            message="Figure visual values cannot be used in primary quantitative synthesis",
        ))
    else:
        result.add(BusinessRuleResult(rule_name="visual_figure_not_primary_meta", passed=True))

    # Rule: space_specific_outcomes_require_space_id (NEW)
    room_space = outcome_data.get("room_or_space")
    space_id = outcome_data.get("space_id")
    if room_space and not space_id:
        result.add(BusinessRuleResult(
            rule_name="space_specific_outcomes_require_space_id",
            passed=False,
            action="flag",
            message="Space-specific outcome is missing space_id link",
        ))
    else:
        result.add(BusinessRuleResult(rule_name="space_specific_outcomes_require_space_id", passed=True))

    # Rule: profile_outcome_not_single_value (NEW)
    if ("profile" in outcome_name.lower() or "curve" in outcome_name.lower()) and outcome_data.get("value") is not None:
        result.add(BusinessRuleResult(
            rule_name="profile_outcome_not_single_value",
            passed=False,
            action="flag",
            message="Temporal curves/profiles should not be extracted as scalar outcomes",
        ))
    else:
        result.add(BusinessRuleResult(rule_name="profile_outcome_not_single_value", passed=True))

    return result


def check_scenario_rules(scenario_data: dict[str, Any]) -> BusinessRulesValidationResult:
    """Check business rules for a scenario record.

    Args:
        scenario_data: Scenario data dict.

    Returns:
        BusinessRulesValidationResult.
    """
    result = BusinessRulesValidationResult()

    # Rule: baseline_intervention_pair
    baseline = scenario_data.get("baseline_description")
    intervention = scenario_data.get("intervention_description")
    if intervention and not baseline:
        result.add(BusinessRuleResult(
            rule_name="baseline_intervention_pair",
            passed=False,
            action="unclear",
            message="Intervention present but no baseline description",
        ))
    else:
        result.add(BusinessRuleResult(rule_name="baseline_intervention_pair", passed=True))

    # Rule: package_split
    is_package = scenario_data.get("is_package")
    components = scenario_data.get("package_components", [])
    if isinstance(components, str):
        try:
            components = json.loads(components)
        except Exception:
            components = []

    if is_package is False and len(components) > 1:
        result.add(BusinessRuleResult(
            rule_name="package_split",
            passed=False,
            action="block",
            message="Multiple components listed but is_package=false",
        ))
    else:
        result.add(BusinessRuleResult(rule_name="package_split", passed=True))

    # Rule: generic_passive_design_forbidden (NEW)
    inter_type = scenario_data.get("intervention_type")
    if inter_type == "passive_design":
        result.add(BusinessRuleResult(
            rule_name="generic_passive_design_forbidden",
            passed=False,
            action="human_review_required",
            message="Intervention type 'passive_design' is too generic and is forbidden",
        ))
    else:
        result.add(BusinessRuleResult(rule_name="generic_passive_design_forbidden", passed=True))

    # Rule: misting_not_ventilation (NEW)
    desc = (scenario_data.get("intervention_description") or "").lower()
    label = (scenario_data.get("scenario_label") or "").lower()
    has_misting_words = any(w in desc or w in label for w in ("misting", "fogging", "spray"))
    is_ventilation = inter_type in ("natural_ventilation", "night_ventilation", "stack_ventilation", "ventilation")
    if has_misting_words and is_ventilation:
        result.add(BusinessRuleResult(
            rule_name="misting_not_ventilation",
            passed=False,
            action="human_review_required",
            message="Scenario description mentions misting/fogging but is classified as ventilation",
        ))
    else:
        result.add(BusinessRuleResult(rule_name="misting_not_ventilation", passed=True))

    # Rule: package_requires_components (NEW)
    if is_package and len(components) < 2:
        result.add(BusinessRuleResult(
            rule_name="package_requires_components",
            passed=False,
            action="flag",
            message="Scenario is marked as a package but has fewer than 2 components",
        ))
    else:
        result.add(BusinessRuleResult(rule_name="package_requires_components", passed=True))

    # Rule: ssp_current_forbidden_unless_reported (NEW)
    ssp = scenario_data.get("ssp")
    if ssp == "current":
        result.add(BusinessRuleResult(
            rule_name="ssp_current_forbidden_unless_reported",
            passed=False,
            action="flag",
            message="SSP must NEVER be 'current'. Use climate_period_type='current' instead.",
        ))
    else:
        result.add(BusinessRuleResult(rule_name="ssp_current_forbidden_unless_reported", passed=True))

    # Rule: active_system_contamination_flag (NEW)
    desc_lower = desc
    label_lower = label
    has_active = any(w in desc_lower or w in label_lower for w in ("hvac", "air conditioning", "ac", "fan", "mechanical ventilation", "chiller", "heat pump"))
    if has_active and inter_type not in ("active_system_change", "mixed_passive_active_package", "controls"):
        result.add(BusinessRuleResult(
            rule_name="active_system_contamination_flag",
            passed=False,
            action="flag",
            message="Scenario contains active system elements but is classified as passive",
        ))
    else:
        result.add(BusinessRuleResult(rule_name="active_system_contamination_flag", passed=True))

    return result


def check_component_rules(component_data: dict[str, Any]) -> BusinessRulesValidationResult:
    """Check business rules for an intervention component.

    Args:
        component_data: Component data dict.

    Returns:
        BusinessRulesValidationResult.
    """
    result = BusinessRulesValidationResult()

    # Rule: components_require_evidence (NEW)
    ev_page = component_data.get("evidence_page")
    ev_text = component_data.get("evidence_text")
    if not ev_page or not ev_text:
        result.add(BusinessRuleResult(
            rule_name="components_require_evidence",
            passed=False,
            action="flag",
            message=f"Intervention component {component_data.get('component_id')} is missing evidence",
        ))
    else:
        result.add(BusinessRuleResult(rule_name="components_require_evidence", passed=True))

    return result
