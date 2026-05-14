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
