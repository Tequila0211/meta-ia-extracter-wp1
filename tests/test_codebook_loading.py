"""
Tests for codebook loading and validation.

Tests (PRD §25.3):
- codebook.yaml loads correctly.
- Duplicate field_name fails.
- Critical field without evidence_required fails.
"""

import copy

import pytest
import yaml

from src.utils.paths import get_codebook_path
from src.validation.codebook_validator import (
    get_codebook_fields,
    load_codebook,
    validate_codebook_integrity,
)


class TestCodebookLoading:

    def test_codebook_loads(self):
        """Codebook YAML loads successfully."""
        codebook = load_codebook()
        assert codebook is not None
        assert "codebook" in codebook
        assert "fields" in codebook

    def test_codebook_has_fields(self):
        """Codebook has the expected number of fields."""
        codebook = load_codebook()
        fields = codebook.get("fields", [])
        assert len(fields) >= 18  # PRD defines 18+ fields

    def test_codebook_has_version(self):
        """Codebook has a version string."""
        codebook = load_codebook()
        version = codebook.get("codebook", {}).get("version")
        assert version is not None

    def test_codebook_fields_indexed(self):
        """get_codebook_fields returns a dict indexed by field_name."""
        fields = get_codebook_fields()
        assert isinstance(fields, dict)
        assert "cooling_demand" in fields
        assert "study_type" in fields

    def test_codebook_integrity_passes(self):
        """The project codebook passes integrity validation."""
        result = validate_codebook_integrity()
        assert result.valid, f"Errors: {result.errors}"


class TestCodebookValidation:

    def test_duplicate_field_name_fails(self):
        """Codebook with duplicate field_name should fail."""
        codebook = load_codebook()
        codebook_copy = copy.deepcopy(codebook)
        # Add a duplicate
        codebook_copy["fields"].append(codebook_copy["fields"][0])
        result = validate_codebook_integrity(codebook_copy)
        assert not result.valid
        assert any("Duplicate" in e for e in result.errors)

    def test_critical_without_evidence_fails(self):
        """Critical field without evidence_required should fail."""
        codebook = {
            "codebook": {"version": "test"},
            "fields": [
                {
                    "field_name": "test_field",
                    "entity_level": "outcome",
                    "data_type": "numeric",
                    "critical": True,
                    "evidence_required": False,  # This should fail
                    "required": True,
                }
            ],
        }
        result = validate_codebook_integrity(codebook)
        assert not result.valid
        assert any("evidence_required" in e for e in result.errors)

    def test_field_without_entity_level_fails(self):
        """Field without entity_level should fail."""
        codebook = {
            "codebook": {"version": "test"},
            "fields": [
                {
                    "field_name": "test_field",
                    "data_type": "string",
                    # Missing entity_level
                }
            ],
        }
        result = validate_codebook_integrity(codebook)
        assert not result.valid
        assert any("entity_level" in e for e in result.errors)
