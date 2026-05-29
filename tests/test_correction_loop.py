"""
Unit tests for the Autonomous AI Self-Correction Loop.
"""

import pytest
from src.workflow.correction_loop import apply_deterministic_fixes, _route_issue_to_file


class TestCorrectionLoopRouting:

    def test_route_issue_by_record_id(self):
        """Routing should prioritize record_id prefix (case-insensitive)."""
        # Outcomes (O###)
        assert _route_issue_to_file("O066", "scenario", "scenario_mixing") == "outcome_extraction.json"
        assert _route_issue_to_file("o92", "any", "any") == "outcome_extraction.json"
        
        # Scenarios (S###)
        assert _route_issue_to_file("S01", "any", "scenario_mixing") == "scenario_extraction.json"
        assert _route_issue_to_file("s25", "any", "any") == "scenario_extraction.json"
        
        # Spaces (SP###)
        assert _route_issue_to_file("SP03", "any", "any") == "space_extraction.json"
        assert _route_issue_to_file("sp9", "any", "any") == "space_extraction.json"
        
        # Intervention Components (C###)
        assert _route_issue_to_file("C12", "any", "any") == "intervention_component_extraction.json"
        assert _route_issue_to_file("c01", "any", "any") == "intervention_component_extraction.json"
        
        # Meta Readiness
        assert _route_issue_to_file("META_A001", "any", "any") == "meta_readiness.json"

    def test_route_issue_by_record_type(self):
        """Routing should fall back to record_type when record_id does not have a clean prefix."""
        assert _route_issue_to_file("some_id", "outcome_record", "any") == "outcome_extraction.json"
        assert _route_issue_to_file("some_id", "Scenario", "any") == "scenario_extraction.json"
        assert _route_issue_to_file("some_id", "intervention_component", "any") == "intervention_component_extraction.json"
        assert _route_issue_to_file("some_id", "space_record", "any") == "space_extraction.json"
        assert _route_issue_to_file("some_id", "meta_readiness", "any") == "meta_readiness.json"


class TestCorrectionLoopDeterministicFixes:

    def test_contradictory_digitization_status_fix(self):
        """Rule contradictory_digitization_status should set usable_for_quantitative_synthesis=True."""
        original_data = {
            "extracted_outcomes": [
                {
                    "outcome_temp_id": "O001",
                    "needs_digitization": True,
                    "digitization_required_for_meta": True,
                    "usable_for_quantitative_synthesis": False
                },
                {
                    "outcome_temp_id": "O002",
                    "needs_digitization": True,
                    "digitization_required_for_meta": True,
                    "usable_for_quantitative_synthesis": True
                }
            ]
        }
        
        issues = [
            {
                "id": "iss_1",
                "record_id": "O001",
                "issue_type": "contradictory_digitization_status",
                "severity": "high",
                "description": "Contradictory digitization status",
                "required_action": "Fix"
            }
        ]
        
        fixed_data, resolved_ids = apply_deterministic_fixes(
            original_data, issues, "outcome_extraction.json", "A001"
        )
        
        assert "iss_1" in resolved_ids
        assert fixed_data["extracted_outcomes"][0]["usable_for_quantitative_synthesis"] is True
        assert fixed_data["extracted_outcomes"][1]["usable_for_quantitative_synthesis"] is True

    def test_duplicate_outcome_fix(self):
        """Rule duplicate_outcome should set human_review_required=True."""
        original_data = {
            "extracted_outcomes": [
                {
                    "outcome_temp_id": "O001",
                    "human_review_required": False
                }
            ]
        }
        
        issues = [
            {
                "id": "iss_2",
                "record_id": "O001",
                "issue_type": "duplicate_outcome",
                "severity": "medium",
                "description": "Duplicate outcome",
                "required_action": "Review"
            }
        ]
        
        fixed_data, resolved_ids = apply_deterministic_fixes(
            original_data, issues, "outcome_extraction.json", "A001"
        )
        
        assert "iss_2" in resolved_ids
        assert fixed_data["extracted_outcomes"][0]["human_review_required"] is True

    def test_missing_unit_when_value_null_dismissed(self):
        """Rule missing_unit should dismiss the issue when value is None."""
        original_data = {
            "extracted_outcomes": [
                {
                    "outcome_temp_id": "O001",
                    "value": None,
                    "unit": None
                },
                {
                    "outcome_temp_id": "O002",
                    "value": 10.5,
                    "unit": None
                }
            ]
        }
        
        issues = [
            {
                "id": "iss_3",
                "record_id": "O001",
                "issue_type": "missing_unit",
                "severity": "medium",
                "description": "Missing unit",
                "required_action": "Add unit"
            },
            {
                "id": "iss_4",
                "record_id": "O002",
                "issue_type": "missing_unit",
                "severity": "medium",
                "description": "Missing unit",
                "required_action": "Add unit"
            }
        ]
        
        fixed_data, resolved_ids = apply_deterministic_fixes(
            original_data, issues, "outcome_extraction.json", "A001"
        )
        
        assert "iss_3" in resolved_ids
        assert "iss_4" not in resolved_ids


class TestCorrectionLoopRegexExtraction:

    def test_regex_extract_individual_and_ranges(self):
        """Should extract individual outcome IDs and range expansions from text."""
        import re
        
        test_issues = [
            {
                "record_id": "outcome_extraction.json",
                "description": "For outcomes O003, O005, O011, O013, O021, O023, O031, O033, the occupant group...",
                "required_action": "Change occupant group from general to non_elderly."
            },
            {
                "record_id": "outcome_extraction.json",
                "description": "Due to the granularity mismatch, outcomes O003-O006 are not linked correctly.",
                "required_action": "Re-link outcomes O003 to O006."
            }
        ]
        
        affected_ids = set()
        for iss in test_issues:
            rid = str(iss.get("record_id") or "")
            desc = str(iss.get("description") or "")
            action = str(iss.get("required_action") or "")
            
            for text_to_search in (rid, desc, action):
                # 1. Individual matches
                matches = re.findall(r'[Oo](\d{3})', text_to_search)
                for m in matches:
                    affected_ids.add(f"O{m}")
                
                # 2. Range matches
                range_matches = re.findall(r'[Oo](\d{3})\s*[-–—to]+\s*[Oo]?(\d{3})', text_to_search)
                for start, end in range_matches:
                    try:
                        s_num = int(start)
                        e_num = int(end)
                        if s_num < e_num:
                            for num in range(s_num, e_num + 1):
                                affected_ids.add(f"O{num:03d}")
                    except Exception:
                        pass
                        
        # Individual IDs from first issue
        assert "O003" in affected_ids
        assert "O005" in affected_ids
        assert "O011" in affected_ids
        assert "O013" in affected_ids
        assert "O021" in affected_ids
        
        # Range IDs (O003-O006) from second issue should be fully expanded
        assert "O004" in affected_ids
        assert "O006" in affected_ids
        
        # Non-mentioned ID should not be present
        assert "O002" not in affected_ids
        assert "O012" not in affected_ids
