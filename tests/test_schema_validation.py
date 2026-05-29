"""
Tests for JSON schema validation.

Tests (PRD §25.1):
- Valid JSON passes.
- JSON with missing required field fails.
- JSON with invalid status fails.
- JSON with invalid source_type fails.
"""

import json

import pytest

from src.validation.schema_validator import validate_against_schema


# ── Classification Schema Tests ──────────────────────────────────────

class TestClassificationSchema:

    def _valid_classification(self) -> dict:
        return {
            "document_id": "A001",
            "study_type": "simulation",
            "is_extractable": True,
            "has_simulation": True,
            "has_numeric_outcomes": True,
            "has_tables": True,
            "has_figures": True,
            "has_multiple_scenarios": False,
            "reason": "Article contains simulation data.",
            "status": "ready_for_mapping",
            "human_review_required": False,
            "title": "A Mock Study on Building Performance",
            "authors": "Jane Doe et al.",
            "year": "2020",
            "journal": "Journal of Building Science",
        }

    def test_valid_classification_passes(self):
        data = self._valid_classification()
        result = validate_against_schema(data, "classification.schema.json")
        assert result.valid

    def test_missing_required_field_fails(self):
        data = self._valid_classification()
        del data["study_type"]
        result = validate_against_schema(data, "classification.schema.json")
        assert not result.valid
        assert any("study_type" in e for e in result.errors)

    def test_invalid_status_fails(self):
        data = self._valid_classification()
        data["status"] = "invalid_status"
        result = validate_against_schema(data, "classification.schema.json")
        assert not result.valid

    def test_invalid_study_type_fails(self):
        data = self._valid_classification()
        data["study_type"] = "invalid_type"
        result = validate_against_schema(data, "classification.schema.json")
        assert not result.valid

    def test_null_values_accepted(self):
        data = self._valid_classification()
        data["is_extractable"] = None
        data["reason"] = None
        result = validate_against_schema(data, "classification.schema.json")
        assert result.valid


# ── Outcome Schema Tests ─────────────────────────────────────────────

class TestOutcomeSchema:

    def _valid_outcome(self) -> dict:
        return {
            "document_id": "A001",
            "extracted_outcomes": [
                {
                    "outcome_temp_id": "O001",
                    "scenario_temp_id": "S001",
                    "outcome_name": "cooling_demand",
                    "metric_group": "energy_demand",
                    "value": 85.3,
                    "unit": "kWh/m2.year",
                    "room_or_space": None,
                    "occupant_group": None,
                    "comparison_baseline_scenario_id": "S000",
                    "comparison_baseline_value": 120.5,
                    "reported_effect_value": -29.2,
                    "reported_effect_unit": "%",
                    "effect_direction": "reduction",
                    "extraction_method": "table",
                    "confidence": "high",
                    "source_type": "table",
                    "page": 12,
                    "table_or_figure": "Table 3",
                    "row_label": "Case A",
                    "column_label": "Retrofitted",
                    "evidence_text": "Cooling demand reduced from 120.5 to 85.3 kWh/m2.year",
                    "needs_digitization": False,
                    "status": "extracted",
                    "human_review_required": True,
                }
            ],
        }

    def test_valid_outcome_passes(self):
        data = self._valid_outcome()
        result = validate_against_schema(data, "outcome_extraction.schema.json")
        assert result.valid

    def test_invalid_effect_direction_fails(self):
        data = self._valid_outcome()
        data["extracted_outcomes"][0]["effect_direction"] = "invalid"
        result = validate_against_schema(data, "outcome_extraction.schema.json")
        assert not result.valid

    def test_invalid_source_type_fails(self):
        data = self._valid_outcome()
        data["extracted_outcomes"][0]["source_type"] = "invalid_source"
        result = validate_against_schema(data, "outcome_extraction.schema.json")
        assert not result.valid

    def test_missing_outcome_name_fails(self):
        data = self._valid_outcome()
        del data["extracted_outcomes"][0]["outcome_name"]
        result = validate_against_schema(data, "outcome_extraction.schema.json")
        assert not result.valid


# ── Audit Schema Tests ────────────────────────────────────────────────

class TestAuditSchema:

    def test_valid_audit_passes(self):
        data = {
            "document_id": "A001",
            "audit_status": "minor_issues",
            "issues": [
                {
                    "severity": "medium",
                    "issue_type": "missing_unit",
                    "affected_record": "O001",
                    "description": "Outcome O001 has no unit.",
                    "required_action": "Add unit from Table 3.",
                }
            ],
            "fields_to_block": ["O001"],
            "records_ready_for_review": ["O002"],
        }
        result = validate_against_schema(data, "audit.schema.json")
        assert result.valid

    def test_invalid_audit_status_fails(self):
        data = {
            "document_id": "A001",
            "audit_status": "invalid",
            "issues": [],
            "fields_to_block": [],
            "records_ready_for_review": [],
        }
        result = validate_against_schema(data, "audit.schema.json")
        assert not result.valid


# ── Building Case Schema Tests ────────────────────────────────────────

class TestBuildingCaseSchema:

    def _valid_building_case(self) -> dict:
        return {
            "document_id": "A001",
            "building_cases": [
                {
                    "building_case_temp_id": "BC01",
                    "building_case_label": "Case A",
                    "building_typology": "residential",
                    "construction_period": "1990-2000",
                    "new_or_existing": "existing",
                    "conditioned_floor_area_m2": 150.0,
                    "number_of_floors": 2.0,
                    "envelope_description": "Concrete block walls",
                    "hvac_description": "Split units",
                    "passive_features_existing": "None",
                    "location": "Madrid",
                    "climate_zone": "Csa",
                    "evidence": {
                        "page": 4,
                        "source_type": "text",
                        "evidence_text": "The residential case study building..."
                    },
                    "status": "extracted"
                }
            ]
        }

    def test_valid_building_case_passes(self):
        data = self._valid_building_case()
        result = validate_against_schema(data, "building_case_extraction.schema.json")
        assert result.valid

    def test_invalid_new_or_existing_enum_fails(self):
        data = self._valid_building_case()
        data["building_cases"][0]["new_or_existing"] = "invalid_enum"
        result = validate_against_schema(data, "building_case_extraction.schema.json")
        assert not result.valid

    def test_missing_required_case_field_fails(self):
        data = self._valid_building_case()
        del data["building_cases"][0]["building_typology"]
        result = validate_against_schema(data, "building_case_extraction.schema.json")
        assert not result.valid


# ── Space Schema Tests ────────────────────────────────────────────────

class TestSpaceSchema:

    def _valid_space(self) -> dict:
        return {
            "document_id": "A001",
            "spaces": [
                {
                    "space_temp_id": "SP01",
                    "building_case_temp_id": "BC01",
                    "scenario_temp_id": "S01",
                    "space_name_original": "Master Bedroom",
                    "space_type_standardized": "bedroom",
                    "evaluated_area_m2": 24.5,
                    "evaluated_height_m": 2.8,
                    "evaluated_volume_m3": 68.6,
                    "floor_level": "First Floor",
                    "orientation": "South",
                    "window_to_wall_ratio": 0.3,
                    "opening_area_m2": 2.4,
                    "occupancy_density": "2 persons",
                    "evidence_page": 5,
                    "evidence_text": "We monitored the bedroom space.",
                    "status": "extracted"
                }
            ]
        }

    def test_valid_space_passes(self):
        data = self._valid_space()
        result = validate_against_schema(data, "space_extraction.schema.json")
        assert result.valid

    def test_invalid_space_type_fails(self):
        data = self._valid_space()
        data["spaces"][0]["space_type_standardized"] = "invalid_space_type"
        result = validate_against_schema(data, "space_extraction.schema.json")
        assert not result.valid


# ── Intervention Component Schema Tests ───────────────────────────────

class TestInterventionComponentSchema:

    def _valid_component(self) -> dict:
        return {
            "document_id": "A001",
            "components": [
                {
                    "scenario_temp_id": "S01",
                    "component_id": "A001_S01_C01",
                    "component_family": "cool_surface",
                    "component_type": "cool_roof",
                    "component_description_original": "Reflective paint applied to roof surface",
                    "is_passive": True,
                    "is_active_support": False,
                    "is_existing_feature": False,
                    "operation_schedule": "24h",
                    "parameter_value": 0.85,
                    "parameter_unit": "albedo",
                    "evidence_page": 7,
                    "evidence_text": "Roof coating with high solar reflectance.",
                    "confidence": "high",
                    "status": "extracted"
                }
            ]
        }

    def test_valid_component_passes(self):
        data = self._valid_component()
        result = validate_against_schema(data, "intervention_component_extraction.schema.json")
        assert result.valid

    def test_invalid_component_family_fails(self):
        data = self._valid_component()
        data["components"][0]["component_family"] = "invalid_family"
        result = validate_against_schema(data, "intervention_component_extraction.schema.json")
        assert not result.valid


# ── Baseline Matching Schema Tests ────────────────────────────────────

class TestBaselineMatchingSchema:

    def _valid_matching(self) -> dict:
        return {
            "document_id": "A001",
            "matches": [
                {
                    "intervention_scenario_temp_id": "S01",
                    "baseline_scenario_temp_id": "S00",
                    "comparison_logic": "same_building_no_intervention",
                    "match_confidence": "high",
                    "evidence_page": 8,
                    "evidence_text": "Scenario 1 is compared to the baseline case S00.",
                    "reason": "Direct comparison between control and retrofit.",
                    "status": "matched"
                }
            ]
        }

    def test_valid_matching_passes(self):
        data = self._valid_matching()
        result = validate_against_schema(data, "baseline_matching.schema.json")
        assert result.valid

    def test_invalid_comparison_logic_fails(self):
        data = self._valid_matching()
        data["matches"][0]["comparison_logic"] = "invalid_logic"
        result = validate_against_schema(data, "baseline_matching.schema.json")
        assert not result.valid


# ── Meta Readiness Schema Tests ───────────────────────────────────────

class TestMetaReadinessSchema:

    def _valid_readiness(self) -> dict:
        return {
            "document_id": "A001",
            "readiness_records": [
                {
                    "record_id": "O001",
                    "has_valid_scenario": True,
                    "has_valid_baseline": True,
                    "has_numeric_value": True,
                    "has_unit": True,
                    "has_page": True,
                    "has_evidence": True,
                    "source_quality": "table",
                    "human_validated": True,
                    "eligible_for_primary_meta_analysis": True,
                    "eligible_for_sensitivity_analysis": True,
                    "classification": "eligible_primary_meta_analysis",
                    "blocking_reason": None
                }
            ]
        }

    def test_valid_readiness_passes(self):
        data = self._valid_readiness()
        result = validate_against_schema(data, "meta_readiness.schema.json")
        assert result.valid

    def test_invalid_classification_fails(self):
        data = self._valid_readiness()
        data["readiness_records"][0]["classification"] = "invalid_classification"
        result = validate_against_schema(data, "meta_readiness.schema.json")
        assert not result.valid

