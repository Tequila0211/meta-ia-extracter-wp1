"""
Methodological business rules and blocking conditions.

Implements all blocking rules from config/extraction_rules.yaml:
- No numeric value without unit
- No critical value without evidence
- No extracted value without page
- Figure values must be marked for digitization
- No package splitting without explicit evidence
- No unknown codebook fields
"""

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
        self.action = action  # 'block', 'set_needs_digitization', 'reject', 'unclear'
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
    rules = load_extraction_rules()

    status = outcome_data.get("status")

    # Rule: missing_page
    if status == "extracted" and outcome_data.get("page") is None:
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
        outcome_data.get("baseline_value") is not None
        or outcome_data.get("intervention_value") is not None
        or outcome_data.get("reported_effect_value") is not None
    )
    has_unit = bool(
        outcome_data.get("baseline_unit")
        or outcome_data.get("intervention_unit")
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
    needs_digit = outcome_data.get("needs_digitization", False)
    if source_type == "figure" and not needs_digit:
        result.add(BusinessRuleResult(
            rule_name="figure_without_digitization",
            passed=False,
            action="set_needs_digitization",
            message="Figure source not marked for digitization",
        ))
    else:
        result.add(BusinessRuleResult(rule_name="figure_without_digitization", passed=True))

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
    if is_package is False and len(components) > 1:
        result.add(BusinessRuleResult(
            rule_name="package_split",
            passed=False,
            action="block",
            message="Multiple components listed but is_package=false",
        ))
    else:
        result.add(BusinessRuleResult(rule_name="package_split", passed=True))

    return result
