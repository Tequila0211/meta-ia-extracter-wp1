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
            "scenario_temp_id": "S01",
            "outcome_name": "cooling_demand",
            "value": 120.5,
            "unit": None,
            "reported_effect_value": None,
            "reported_effect_unit": None,
            "page": 5,
            "evidence_text": "Some evidence",
            "source_type": "table",
            "extraction_method": "table",
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
            "scenario_temp_id": "S01",
            "outcome_name": "cooling_demand",
            "value": 120.5,
            "unit": "kWh/m2.year",
            "reported_effect_value": None,
            "reported_effect_unit": None,
            "page": None,
            "evidence_text": "Some evidence",
            "source_type": "table",
            "extraction_method": "table",
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
            "scenario_temp_id": "S01",
            "outcome_name": "cooling_demand",
            "value": 120.5,
            "unit": "kWh/m2.year",
            "reported_effect_value": None,
            "reported_effect_unit": None,
            "page": 5,
            "evidence_text": None,
            "crop_path": None,
            "source_type": "table",
            "extraction_method": "table",
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
            "scenario_temp_id": "S01",
            "outcome_name": "cooling_demand",
            "value": 120.5,
            "unit": "kWh/m2.year",
            "reported_effect_value": None,
            "reported_effect_unit": None,
            "page": 5,
            "evidence_text": "From figure",
            "source_type": "figure",
            "extraction_method": "not_extracted",
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
            "scenario_temp_id": "S01",
            "outcome_name": "cooling_demand",
            "value": 120.5,
            "unit": "kWh/m2.year",
            "reported_effect_value": None,
            "reported_effect_unit": None,
            "page": 12,
            "evidence_text": "Table 3 shows cooling demand.",
            "source_type": "table",
            "extraction_method": "table",
            "status": "extracted",
            "needs_digitization": False,
        }
        result = check_outcome_rules(data)
        assert result.valid

    def test_intervention_requires_baseline_for_effect(self):
        """Calculated effect without baseline scenario or value should be flagged."""
        data = {
            "scenario_temp_id": "S01",
            "outcome_name": "cooling_demand",
            "value": 85.3,
            "unit": "kWh/m2.year",
            "calculated_effect_value": -35.2,
            "comparison_baseline_scenario_id": None,
            "baseline_value": None,
            "page": 12,
            "evidence_text": "Reduced cooling demand",
            "status": "extracted",
        }
        result = check_outcome_rules(data)
        failures = [r for r in result.failures if r.rule_name == "intervention_requires_baseline_for_effect"]
        assert len(failures) > 0
        assert failures[0].action == "flag"

    def test_visual_figure_not_primary_meta(self):
        """Figure visual values cannot be used in primary quantitative synthesis."""
        data = {
            "scenario_temp_id": "S01",
            "outcome_name": "cooling_demand",
            "value": 85.3,
            "unit": "kWh/m2.year",
            "extraction_method": "figure_visual_approximate",
            "usable_for_quantitative_synthesis": True,
            "page": 12,
            "evidence_text": "Estimated from figure",
            "status": "extracted",
        }
        result = check_outcome_rules(data)
        failures = [r for r in result.failures if r.rule_name == "visual_figure_not_primary_meta"]
        assert len(failures) > 0
        assert failures[0].action == "flag"

    def test_space_specific_outcomes_require_space_id(self):
        """Space-specific outcome missing space_id should be flagged."""
        data = {
            "scenario_temp_id": "S01",
            "outcome_name": "cooling_demand",
            "value": 85.3,
            "unit": "kWh/m2.year",
            "room_or_space": "Living Room",
            "space_id": None,
            "page": 12,
            "evidence_text": "Room specific value",
            "status": "extracted",
        }
        result = check_outcome_rules(data)
        failures = [r for r in result.failures if r.rule_name == "space_specific_outcomes_require_space_id"]
        assert len(failures) > 0
        assert failures[0].action == "flag"

    def test_profile_outcome_not_single_value(self):
        """Temporal curves/profiles extracted as scalars should be flagged."""
        data = {
            "scenario_temp_id": "S01",
            "outcome_name": "cooling_demand_profile",
            "value": 85.3,
            "unit": "kWh/m2.year",
            "page": 12,
            "evidence_text": "Curve value",
            "status": "extracted",
        }
        result = check_outcome_rules(data)
        failures = [r for r in result.failures if r.rule_name == "profile_outcome_not_single_value"]
        assert len(failures) > 0
        assert failures[0].action == "flag"

    def test_generic_passive_design_forbidden(self):
        """Intervention type 'passive_design' is too generic and is forbidden."""
        from src.validation.business_rules import check_scenario_rules
        data = {
            "intervention_type": "passive_design",
            "intervention_description": "Generic passive strategy",
            "scenario_label": "Case A",
        }
        result = check_scenario_rules(data)
        failures = [r for r in result.failures if r.rule_name == "generic_passive_design_forbidden"]
        assert len(failures) > 0
        assert failures[0].action == "human_review_required"

    def test_misting_not_ventilation(self):
        """Scenario mentions misting/fogging but is classified as ventilation should be flagged."""
        from src.validation.business_rules import check_scenario_rules
        data = {
            "intervention_type": "natural_ventilation",
            "intervention_description": "High pressure misting system active",
            "scenario_label": "Case A",
        }
        result = check_scenario_rules(data)
        failures = [r for r in result.failures if r.rule_name == "misting_not_ventilation"]
        assert len(failures) > 0
        assert failures[0].action == "human_review_required"

    def test_package_requires_components(self):
        """Scenario marked as package but has fewer than 2 components should be flagged."""
        from src.validation.business_rules import check_scenario_rules
        data = {
            "is_package": True,
            "package_components": '["cool_roof"]',
            "intervention_type": "passive_package",
        }
        result = check_scenario_rules(data)
        failures = [r for r in result.failures if r.rule_name == "package_requires_components"]
        assert len(failures) > 0
        assert failures[0].action == "flag"

    def test_ssp_current_forbidden(self):
        """Scenario using 'current' as SSP should be flagged."""
        from src.validation.business_rules import check_scenario_rules
        data = {
            "ssp": "current",
            "intervention_type": "solar_shading",
        }
        result = check_scenario_rules(data)
        failures = [r for r in result.failures if r.rule_name == "ssp_current_forbidden_unless_reported"]
        assert len(failures) > 0
        assert failures[0].action == "flag"

    def test_active_system_contamination_flag(self):
        """Scenario containing active system elements but classified as passive should be flagged."""
        from src.validation.business_rules import check_scenario_rules
        data = {
            "intervention_type": "solar_shading",
            "intervention_description": "Retrofitting external shading with mechanical HVAC support",
            "scenario_label": "Retrofit Case",
        }
        result = check_scenario_rules(data)
        failures = [r for r in result.failures if r.rule_name == "active_system_contamination_flag"]
        assert len(failures) > 0
        assert failures[0].action == "flag"

    def test_components_require_evidence(self):
        """Intervention component missing evidence should be flagged."""
        from src.validation.business_rules import check_component_rules
        data = {
            "component_id": "C01",
            "evidence_page": None,
            "evidence_text": "Missing page",
        }
        result = check_component_rules(data)
        failures = [r for r in result.failures if r.rule_name == "components_require_evidence"]
        assert len(failures) > 0
        assert failures[0].action == "flag"

