"""
Tests for methodological business rules.

Tests (PRD §25.2):
- Numeric outcome without unit → blocked.
- Outcome without page → blocked.
- Critical outcome without evidence → blocked.
- Figure without digitization → marked as needs_digitization.
"""

import pytest

from src.validation.business_rules import check_outcome_rules


class TestBusinessRules:

    def test_numeric_without_unit_blocked(self):
        """Outcome with numeric value but no unit should be blocked."""
        data = {
            "outcome_name": "cooling_demand",
            "baseline_value": 120.5,
            "baseline_unit": None,
            "intervention_value": None,
            "intervention_unit": None,
            "reported_effect_value": None,
            "reported_effect_unit": None,
            "page": 5,
            "evidence_text": "Some evidence",
            "source_type": "table",
            "status": "extracted",
            "needs_digitization": False,
        }
        result = check_outcome_rules(data)
        failures = [r for r in result.failures if r.rule_name == "missing_numeric_unit"]
        assert len(failures) > 0
        assert failures[0].action == "block"

    def test_outcome_without_page_blocked(self):
        """Extracted outcome without page number should be blocked."""
        data = {
            "outcome_name": "cooling_demand",
            "baseline_value": 120.5,
            "baseline_unit": "kWh/m2.year",
            "intervention_value": None,
            "intervention_unit": None,
            "reported_effect_value": None,
            "reported_effect_unit": None,
            "page": None,
            "evidence_text": "Some evidence",
            "source_type": "table",
            "status": "extracted",
            "needs_digitization": False,
        }
        result = check_outcome_rules(data)
        failures = [r for r in result.failures if r.rule_name == "missing_page"]
        assert len(failures) > 0
        assert failures[0].action == "block"

    def test_critical_without_evidence_blocked(self):
        """Critical outcome without evidence should be blocked."""
        data = {
            "outcome_name": "cooling_demand",
            "baseline_value": 120.5,
            "baseline_unit": "kWh/m2.year",
            "intervention_value": None,
            "intervention_unit": None,
            "reported_effect_value": None,
            "reported_effect_unit": None,
            "page": 5,
            "evidence_text": None,
            "crop_path": None,
            "source_type": "table",
            "status": "extracted",
            "needs_digitization": False,
        }
        result = check_outcome_rules(data)
        failures = [r for r in result.failures if r.rule_name == "missing_evidence"]
        assert len(failures) > 0
        assert failures[0].action == "block"

    def test_figure_without_digitization_flagged(self):
        """Figure source not marked for digitization should be flagged."""
        data = {
            "outcome_name": "cooling_demand",
            "baseline_value": 120.5,
            "baseline_unit": "kWh/m2.year",
            "intervention_value": None,
            "intervention_unit": None,
            "reported_effect_value": None,
            "reported_effect_unit": None,
            "page": 5,
            "evidence_text": "From figure",
            "source_type": "figure",
            "status": "extracted",
            "needs_digitization": False,
        }
        result = check_outcome_rules(data)
        failures = [r for r in result.failures if r.rule_name == "figure_without_digitization"]
        assert len(failures) > 0
        assert failures[0].action == "set_needs_digitization"

    def test_valid_outcome_passes(self):
        """A fully valid outcome should pass all rules."""
        data = {
            "outcome_name": "cooling_demand",
            "baseline_value": 120.5,
            "baseline_unit": "kWh/m2.year",
            "intervention_value": 85.0,
            "intervention_unit": "kWh/m2.year",
            "reported_effect_value": None,
            "reported_effect_unit": None,
            "page": 12,
            "evidence_text": "Table 3 shows cooling demand.",
            "source_type": "table",
            "status": "extracted",
            "needs_digitization": False,
        }
        result = check_outcome_rules(data)
        assert result.valid
