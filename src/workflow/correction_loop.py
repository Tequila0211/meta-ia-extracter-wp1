"""
Autonomous AI Self-Correction Loop.

Automatically reads semantic and schema issues logged by the Auditor (Step 10) in SQLite,
applies deterministic rule-based fixes first, then invokes Gemini 2.5 Flash as a text-only
refining agent to surgically correct JSON files (including structural scenario refactoring),
re-validates them against schemas, and re-imports corrected records into SQLite.
"""

import json
import re
from pathlib import Path
from typing import Any
from sqlalchemy import text

from src.ai.gemini_client import GeminiClient
from src.database.db import DatabaseManager
from src.database.repository import get_document_by_code
from src.utils.logging_config import get_logger

logger = get_logger("validation")


# ---------------------------------------------------------------------------
# Phase 1: Deterministic Rule-Based Fixes (no LLM needed)
# ---------------------------------------------------------------------------

def apply_deterministic_fixes(
    data: dict, issues: list[dict], target_file: str, document_code: str
) -> tuple[dict, list[str]]:
    """Apply rule-based fixes that don't require LLM reasoning.

    These are logical if/then rules derived from the patterns observed in the
    QA log.  They run instantly, cost zero tokens, and are 100 % deterministic.

    Returns:
        (modified_data, list_of_resolved_issue_ids)
    """
    resolved_ids: list[str] = []

    if target_file != "outcome_extraction.json":
        return data, resolved_ids

    outcomes = data.get("extracted_outcomes", [])
    outcomes_map = {o.get("outcome_temp_id", f"__{i}"): o for i, o in enumerate(outcomes)}

    for issue in issues:
        itype = str(issue.get("issue_type", "")).lower()
        rid = str(issue.get("record_id", ""))

        # ------------------------------------------------------------------
        # RULE 1: contradictory_digitization_status
        # Pattern: needs_digitization=true AND digitization_required_for_meta=true
        #          BUT usable_for_quantitative_synthesis=false
        # Fix: set usable_for_quantitative_synthesis = true
        # ------------------------------------------------------------------
        if itype == "contradictory_digitization_status" and rid in outcomes_map:
            outcome = outcomes_map[rid]
            if outcome.get("needs_digitization") and outcome.get("digitization_required_for_meta"):
                outcome["usable_for_quantitative_synthesis"] = True
                resolved_ids.append(issue["id"])
                logger.debug(f"[{document_code}] Deterministic fix: {rid} usable_for_quantitative_synthesis → true")

        # ------------------------------------------------------------------
        # RULE 2: duplicate_outcome
        # We cannot delete without human confirmation, but we CAN flag them
        # for human review so they appear in the review dashboard.
        # ------------------------------------------------------------------
        elif itype == "duplicate_outcome" and rid in outcomes_map:
            outcome = outcomes_map[rid]
            outcome["human_review_required"] = True
            resolved_ids.append(issue["id"])
            logger.debug(f"[{document_code}] Deterministic fix: {rid} flagged as human_review_required (duplicate)")

        # ------------------------------------------------------------------
        # RULE 3: missing_unit when value is null
        # If there is no numeric value, missing unit is expected/irrelevant.
        # ------------------------------------------------------------------
        elif itype == "missing_unit" and rid in outcomes_map:
            outcome = outcomes_map[rid]
            if outcome.get("value") is None:
                resolved_ids.append(issue["id"])
                logger.debug(f"[{document_code}] Deterministic fix: {rid} missing_unit dismissed (value is null)")

    # Rebuild the list preserving order
    data["extracted_outcomes"] = list(outcomes_map.values())

    if resolved_ids:
        logger.info(
            f"[{document_code}] Deterministic fixes applied: {len(resolved_ids)} issues resolved without LLM."
        )
    return data, resolved_ids


# ---------------------------------------------------------------------------
# Phase 2: Structural Scenario Refactoring (LLM-powered)
# ---------------------------------------------------------------------------

def refine_scenarios_structural(
    client: GeminiClient,
    scenarios_data: dict,
    outcomes_data: dict,
    scenario_schema: dict,
    issues: list[dict],
    document_code: str,
) -> tuple[dict | None, dict | None]:
    """Structural refinement that can split/create/merge scenarios AND reassign outcomes.

    This mode receives BOTH the scenarios file and the outcomes file so the LLM
    can create new scenarios, split existing ones, and reassign outcome
    ``scenario_temp_id`` references in a single atomic operation.

    Returns:
        (refined_scenarios_data, refined_outcomes_data) or (None, None) on failure.
    """
    from src.utils.json_utils import parse_json_safe
    from google.genai import types

    system_prompt = (
        "You are an expert structural data engineer for a systematic review meta-analysis project.\n"
        "Your task is to resolve SCENARIO_MIXING and EXTRACTION_OMISSION issues by restructuring\n"
        "the scenarios and reassigning outcomes to the correct scenarios.\n\n"
        "You CAN and SHOULD:\n"
        "1. SPLIT scenarios that mix spatial granularities (e.g., room-level outcomes mixed with\n"
        "   building-level outcomes in the same scenario). Create separate scenarios for each\n"
        "   granularity level.\n"
        "2. CREATE new scenarios where the audit says outcomes are missing a proper scenario home\n"
        "   (e.g., 'Baseline, 2020, Building-level').\n"
        "3. REASSIGN outcomes to the correct scenario by updating their scenario_temp_id.\n"
        "4. UPDATE the 'reported_outcomes' list of each scenario to accurately reflect which\n"
        "   outcomes belong to it.\n\n"
        "You MUST NOT:\n"
        "- Delete any existing outcomes or change their numeric values.\n"
        "- Modify fields unrelated to the scenario assignment.\n\n"
        "Return a JSON object with exactly two keys:\n"
        "1. 'scenarios': The COMPLETE corrected scenarios array (with new/split scenarios included).\n"
        "   New scenario_temp_ids must follow the existing pattern (S01, S02, ..., Snn).\n"
        "2. 'outcome_reassignments': Array of objects with {\"outcome_temp_id\": \"Oxx\",\n"
        "   \"new_scenario_temp_id\": \"Syy\"} for every outcome whose scenario_temp_id changes.\n\n"
        "Return ONLY the valid JSON object. Do not include markdown formatting like ```json."
    )

    issues_str = ""
    for i, issue in enumerate(issues, 1):
        issues_str += (
            f"--- Issue {i} ---\n"
            f"Record ID: {issue['record_id']}\n"
            f"Issue Type: {issue['issue_type']}\n"
            f"Severity: {issue['severity']}\n"
            f"Description: {issue['description']}\n"
            f"Required Action: {issue['required_action']}\n\n"
        )

    # Build a compact summary of outcomes (just id + scenario_temp_id + outcome_name + room_or_space)
    # to avoid exceeding token limits
    outcomes_summary = []
    for o in outcomes_data.get("extracted_outcomes", []):
        outcomes_summary.append({
            "outcome_temp_id": o.get("outcome_temp_id"),
            "scenario_temp_id": o.get("scenario_temp_id"),
            "outcome_name": o.get("outcome_name"),
            "room_or_space": o.get("room_or_space"),
            "occupant_group": o.get("occupant_group"),
            "value": o.get("value"),
        })

    user_prompt = (
        f"Document: {document_code}\n\n"
        f"AUDITOR'S FINDINGS / REQUIRED ACTIONS:\n"
        f"{issues_str}\n"
        f"CURRENT SCENARIOS:\n"
        f"{json.dumps(scenarios_data, indent=2)}\n\n"
        f"CURRENT OUTCOME ASSIGNMENTS (summary):\n"
        f"{json.dumps(outcomes_summary, indent=2)}\n\n"
        f"SCENARIO SCHEMA:\n"
        f"{json.dumps(scenario_schema, indent=2)}\n\n"
        f"Please return a JSON object with 'scenarios' and 'outcome_reassignments'."
    )

    current_client = client.client_free if client.client_free else client.client
    last_error = None

    for attempt in range(1, 3):
        if not current_client:
            logger.error(f"[{document_code}] No Gemini client for structural refinement.")
            return None, None
        try:
            response = current_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[user_prompt],
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )
            raw_text = response.text
            if not raw_text:
                return None, None

            result = parse_json_safe(raw_text)
            if not result:
                return None, None

            # Build refined scenarios data
            new_scenarios = result.get("scenarios", [])
            if not new_scenarios:
                logger.warning(f"[{document_code}] Structural refinement returned empty scenarios.")
                return None, None

            refined_scenarios = {
                "document_id": scenarios_data.get("document_id", document_code),
                "scenarios": new_scenarios,
            }

            # Apply outcome reassignments
            reassignments = result.get("outcome_reassignments", [])
            reassign_map = {r["outcome_temp_id"]: r["new_scenario_temp_id"] for r in reassignments if "outcome_temp_id" in r}

            if reassign_map:
                refined_outcomes = json.loads(json.dumps(outcomes_data))  # deep copy
                for outcome in refined_outcomes.get("extracted_outcomes", []):
                    tid = outcome.get("outcome_temp_id")
                    if tid in reassign_map:
                        old_sid = outcome.get("scenario_temp_id")
                        new_sid = reassign_map[tid]
                        outcome["scenario_temp_id"] = new_sid
                        logger.debug(f"[{document_code}] Reassigned {tid}: {old_sid} → {new_sid}")
            else:
                refined_outcomes = outcomes_data

            logger.info(
                f"[{document_code}] Structural refinement: "
                f"{len(new_scenarios)} scenarios, {len(reassign_map)} outcome reassignments."
            )
            return refined_scenarios, refined_outcomes

        except Exception as e:
            last_error = str(e)
            logger.warning(
                f"[{document_code}] Structural refinement error attempt {attempt}: {e}"
            )
            if current_client == getattr(client, 'client_free', None) and getattr(client, 'client_paid', None):
                logger.info(f"[{document_code}] Switching to Paid Key for structural retry...")
                current_client = client.client_paid
            else:
                break

    logger.error(f"[{document_code}] Structural refinement failed: {last_error}")
    return None, None


# ---------------------------------------------------------------------------
# Phase 3: Standard LLM Refinement (existing, preserved)
# ---------------------------------------------------------------------------

def refine_json_with_gemini(
    client: GeminiClient,
    original_data: dict,
    schema_data: dict,
    issues: list[dict],
    document_code: str
) -> dict | None:
    """Invokes Gemini 2.5 Flash as a text-only refining agent to surgically correct a JSON file."""
    from src.utils.json_utils import parse_json_safe
    from google.genai import types

    is_outcomes_file = "extracted_outcomes" in original_data

    if is_outcomes_file:
        # Outcomes are massive and exceed LLM output token limits. Let's do surgical editing.
        refine_system_prompt = (
            "You are an expert AI data engineering agent specializing in surgical data correction.\n"
            "Instead of returning the entire massive JSON file, you will output ONLY the modifications "
            "and new records needed to resolve the auditor's findings.\n\n"
            "Return a JSON object with exactly two keys:\n"
            "1. 'modified_outcomes': Array of existing outcomes to correct. You MUST include outcome_temp_id "
            "and only the fields being modified/corrected.\n"
            "2. 'new_outcomes': Array of brand new outcomes that are currently omitted. Fully populated matching the schema.\n\n"
            "Return ONLY the valid JSON object. Do not include markdown formatting like ```json."
        )
        
        # We define a specialized surgical schema to constrain the output size
        outcome_item_schema = schema_data["properties"]["extracted_outcomes"]["items"]
        surgical_schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["modified_outcomes", "new_outcomes"],
            "properties": {
                "modified_outcomes": {
                    "type": "array",
                    "description": "Outcomes from the original file that need modification. Provide only the updated fields, but MUST include outcome_temp_id.",
                    "items": outcome_item_schema
                },
                "new_outcomes": {
                    "type": "array",
                    "description": "Brand new outcomes to be added to resolve omissions. Must match the schema fully.",
                    "items": outcome_item_schema
                }
            }
        }
        schema_to_send = surgical_schema
    else:
        refine_system_prompt = (
            "You are an expert AI data engineering agent specializing in structural and semantic data refinement.\n"
            "Your task is to take an existing JSON extraction file, analyze a list of semantic and schema issues logged by an Auditor, "
            "and surgically edit the JSON to resolve all of those issues.\n\n"
            "Mandatory rules:\n"
            "1. Fix ONLY the targeted issues mentioned in the audit log.\n"
            "2. Do NOT add, remove, or modify any other correct data or structural keys unless required to solve the issue.\n"
            "3. Strictly adhere to the provided JSON Schema.\n"
            "4. Return ONLY a valid JSON object matching the schema. Do not include markdown formatting like ```json."
        )
        schema_to_send = schema_data

    issues_str = ""
    for i, issue in enumerate(issues, 1):
        issues_str += (
            f"--- Issue {i} ---\n"
            f"Record Type: {issue['record_type']}\n"
            f"Record ID: {issue['record_id']}\n"
            f"Issue Type: {issue['issue_type']}\n"
            f"Severity: {issue['severity']}\n"
            f"Description: {issue['description']}\n"
            f"Required Action: {issue['required_action']}\n\n"
        )

    if is_outcomes_file:
        # Collect all outcome IDs mentioned in the issues to optimize prompt size
        affected_ids = set()
        for iss in issues:
            rid = str(iss.get("record_id") or "")
            desc = str(iss.get("description") or "")
            action = str(iss.get("required_action") or "")
            
            # Search for IDs and ranges in all three text fields
            for text_to_search in (rid, desc, action):
                # 1. Individual matches (e.g. O001)
                matches = re.findall(r'[Oo](\d{3})', text_to_search)
                for m in matches:
                    affected_ids.add(f"O{m}")
                
                # 2. Range matches (e.g. O003-O010 or O003 to O010)
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
        
        all_outcomes = original_data.get("extracted_outcomes", [])
        filtered_outcomes = [o for o in all_outcomes if o.get("outcome_temp_id") in affected_ids]
        
        # If filtered_outcomes is empty (e.g. no specific record IDs, or it's a general issue), send everything
        if filtered_outcomes:
            # We also send a couple of reference ones for context so the LLM has examples of correct ones
            reference_count = 0
            for o in all_outcomes:
                if o.get("outcome_temp_id") not in affected_ids and reference_count < 2:
                    filtered_outcomes.append(o)
                    reference_count += 1
            
            # Sort the filtered list by temporary ID
            def get_id_num(item):
                match = re.search(r'\d+', item.get("outcome_temp_id", ""))
                return int(match.group()) if match else 9999
            filtered_outcomes = sorted(filtered_outcomes, key=get_id_num)
            
            prompt_data = {
                "document_id": original_data.get("document_id"),
                "extracted_outcomes": filtered_outcomes
            }
            logger.info(f"[{document_code}] Optimized outcomes prompt: sent {len(filtered_outcomes)} of {len(all_outcomes)} outcomes.")
        else:
            prompt_data = original_data
            logger.info(f"[{document_code}] Sending all {len(all_outcomes)} outcomes (no specific record_id matches).")

        user_prompt = (
            f"Document: {document_code}\n\n"
            f"AUDITOR'S FINDINGS / REQUIRED ACTIONS:\n"
            f"{issues_str}\n"
            f"ORIGINAL OUTCOMES (to modify or base additions on):\n"
            f"{json.dumps(prompt_data, indent=2)}\n\n"
            f"REQUIRED OUTPUT JSON SCHEMA:\n"
            f"{json.dumps(schema_to_send, indent=2)}\n\n"
            f"Please return a JSON object with 'modified_outcomes' and 'new_outcomes' to resolve all findings."
        )
    else:
        user_prompt = (
            f"Document: {document_code}\n\n"
            f"AUDITOR'S FINDINGS / REQUIRED ACTIONS:\n"
            f"{issues_str}\n"
            f"ORIGINAL JSON CONTENT:\n"
            f"{json.dumps(original_data, indent=2)}\n\n"
            f"REQUIRED JSON SCHEMA:\n"
            f"{json.dumps(schema_to_send, indent=2)}\n\n"
            f"Please return the complete, corrected JSON file matching the schema and resolving all findings."
        )

    # Use the free client first to save cost, with dynamic conmutation to paid client upon failure
    current_client = client.client_free if client.client_free else client.client
    
    last_error = None
    for attempt in range(1, 3):
        if not current_client:
            logger.error(f"[{document_code}] No Gemini client initialized for refinement.")
            return None
        try:
            response = current_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[user_prompt],
                config=types.GenerateContentConfig(
                    system_instruction=refine_system_prompt,
                    temperature=0.1,
                    response_mime_type="application/json",
                )
            )
            raw_text = response.text
            if not raw_text:
                return None
            
            refined_res = parse_json_safe(raw_text)
            if not refined_res:
                return None

            if is_outcomes_file:
                # Merge surgical modifications and additions back into original outcomes list
                outcomes_list = original_data.get("extracted_outcomes", [])
                outcomes_map = {o["outcome_temp_id"]: o for o in outcomes_list}
                
                # Merge modifications
                for mod in refined_res.get("modified_outcomes", []):
                    tid = mod.get("outcome_temp_id")
                    if tid in outcomes_map:
                        outcomes_map[tid].update(mod)
                
                # Append new outcomes
                new_list = refined_res.get("new_outcomes", [])
                for new_out in new_list:
                    tid = new_out.get("outcome_temp_id")
                    if tid:
                        outcomes_map[tid] = new_out
                
                # Re-sort outcomes by temporary ID to keep O001, O002, etc. ordered
                def get_id_num(item):
                    match = re.search(r'\d+', item.get("outcome_temp_id", ""))
                    return int(match.group()) if match else 9999
                    
                sorted_outcomes = sorted(outcomes_map.values(), key=get_id_num)
                
                # Construct final merged data
                merged_data = {
                    "document_id": original_data.get("document_id", document_code),
                    "extracted_outcomes": sorted_outcomes
                }
                return merged_data
            else:
                return refined_res

        except Exception as e:
            last_error = str(e)
            logger.warning(
                f"[{document_code}] Refinement error on attempt {attempt} with "
                f"{'Free' if current_client == client.client_free else 'Paid'} Key: {e}"
            )
            # Switch to paid client if we hit rate limits or resource exhaustion on free client
            if current_client == client.client_free and client.client_paid:
                logger.info(f"[{document_code}] Switching dynamically to Paid Key for refinement retry...")
                current_client = client.client_paid
            else:
                break
    
    logger.error(f"[{document_code}] Gemini refinement call failed after retry: {last_error}")
    return None


# ---------------------------------------------------------------------------
# Re-import helpers
# ---------------------------------------------------------------------------

def reimport_corrected_records(session, doc_id: str, document_code: str, target_file: str, data: dict):
    """Clears SQLite records for a specific table and document, and re-imports the corrected JSON records."""
    from src.database.repository import (
        insert_scenario,
        insert_intervention_component,
        insert_space,
        insert_outcome,
        insert_meta_readiness
    )

    if target_file == "scenario_extraction.json":
        # Clear existing scenarios and re-insert
        session.execute(text("DELETE FROM scenarios WHERE document_id = :doc_id"), {"doc_id": doc_id})
        scenarios = data.get("scenarios", [])
        for i, scenario_data in enumerate(scenarios, 1):
            scenario_code = f"{document_code}_S{i:02d}"
            insert_scenario(session, doc_id, scenario_code, scenario_data)
        logger.info(f"[{document_code}] Re-imported {len(scenarios)} corrected scenarios to SQLite.")

    elif target_file == "intervention_component_extraction.json":
        # Clear existing components and re-insert
        session.execute(text("DELETE FROM intervention_components WHERE document_id = :doc_id"), {"doc_id": doc_id})
        components = data.get("components", [])
        
        # Build scenario lookup to resolve scenario_id
        from src.database.repository import get_scenarios_for_document
        db_scenarios = get_scenarios_for_document(session, doc_id)
        scenario_lookup = {s.scenario_temp_id: s.id for s in db_scenarios}
        
        for i, comp_data in enumerate(components, 1):
            component_code = f"{document_code}_C{i:02d}"
            scenario_temp_id = comp_data.get("scenario_temp_id")
            scenario_id = scenario_lookup.get(scenario_temp_id)
            if not scenario_id and scenario_temp_id:
                clean_id = scenario_temp_id.split("_")[-1]
                scenario_id = scenario_lookup.get(clean_id)
                if not scenario_id and clean_id.startswith('S') and clean_id[1:].isdigit():
                    scenario_id = scenario_lookup.get(f"S{int(clean_id[1:])}")
                    if not scenario_id:
                        scenario_id = scenario_lookup.get(f"S{int(clean_id[1:]):02d}")
            insert_intervention_component(session, doc_id, component_code, comp_data, scenario_id=scenario_id)
        logger.info(f"[{document_code}] Re-imported {len(components)} corrected intervention components.")

    elif target_file == "space_extraction.json":
        # Clear existing spaces and re-insert
        session.execute(text("DELETE FROM spaces WHERE document_id = :doc_id"), {"doc_id": doc_id})
        spaces = data.get("spaces", [])
        for i, space_data in enumerate(spaces, 1):
            space_code = f"{document_code}_SP{i:02d}"
            insert_space(session, doc_id, space_code, space_data)
        logger.info(f"[{document_code}] Re-imported {len(spaces)} corrected spaces.")

    elif target_file == "outcome_extraction.json":
        # Clear existing outcomes and re-insert
        session.execute(text("DELETE FROM outcomes WHERE document_id = :doc_id"), {"doc_id": doc_id})
        outcomes = data.get("extracted_outcomes", [])
        
        # Build scenario lookup to resolve scenario_id
        from src.database.repository import get_scenarios_for_document
        db_scenarios = get_scenarios_for_document(session, doc_id)
        scenario_lookup = {s.scenario_temp_id: s.id for s in db_scenarios}
        
        for i, out_data in enumerate(outcomes, 1):
            outcome_code = f"{document_code}_O{i:03d}"
            
            # Link to scenario if possible
            scenario_temp_id = out_data.get("scenario_temp_id")
            scenario_id = scenario_lookup.get(scenario_temp_id)
            
            # Fallback if AI prepended document ID or formatted it differently
            if not scenario_id and scenario_temp_id:
                clean_id = scenario_temp_id.split("_")[-1] # Gets 'S01' from 'A001_S01'
                scenario_id = scenario_lookup.get(clean_id)
                # Try removing zero padding if that fails ('S1' vs 'S01')
                if not scenario_id and clean_id.startswith('S') and clean_id[1:].isdigit():
                    scenario_id = scenario_lookup.get(f"S{int(clean_id[1:])}")
                    if not scenario_id:
                        scenario_id = scenario_lookup.get(f"S{int(clean_id[1:]):02d}")
            
            insert_outcome(session, doc_id, scenario_id, outcome_code, out_data)
        logger.info(f"[{document_code}] Re-imported {len(outcomes)} corrected outcomes.")

    elif target_file == "meta_readiness.json":
        # Clear existing meta-readiness records and re-insert
        session.execute(text("DELETE FROM meta_readiness WHERE document_id = :doc_id"), {"doc_id": doc_id})
        records = data.get("readiness_records", [])
        for rec_data in records:
            insert_meta_readiness(session, doc_id, rec_data)
        logger.info(f"[{document_code}] Re-imported {len(records)} corrected meta-readiness records.")


# ---------------------------------------------------------------------------
# Routing helper
# ---------------------------------------------------------------------------

def _route_issue_to_file(record_id: str, record_type: str, issue_type: str) -> str:
    """Determine which JSON file an issue belongs to.

    IMPORTANT: record_id (e.g., 'O066', 'S01') takes absolute priority over
    issue_type keywords.  This fixes the previous bug where scenario_mixing
    issues referencing outcomes (O##) were mis-routed to scenario_extraction.json.
    """
    rid = record_id.lower()
    rtype = record_type.lower()
    itype = issue_type.lower()

    # ── Priority 1: record_id prefix ──────────────────────────────────────
    # Check outcome first because 'o' would also match in some scenario IDs
    if re.match(r'^o\d', rid):
        return "outcome_extraction.json"
    if rid.startswith("sp"):
        return "space_extraction.json"
    if re.match(r'^s\d', rid):
        return "scenario_extraction.json"
    if re.match(r'^c\d', rid):
        return "intervention_component_extraction.json"
    if rid.startswith("meta"):
        return "meta_readiness.json"

    # ── Priority 2: record_type keyword ───────────────────────────────────
    if "outcome" in rtype:
        return "outcome_extraction.json"
    if "scenario" in rtype:
        return "scenario_extraction.json"
    if "component" in rtype:
        return "intervention_component_extraction.json"
    if "space" in rtype:
        return "space_extraction.json"
    if "readiness" in rtype or "meta" in rtype:
        return "meta_readiness.json"

    # ── Priority 3: issue_type keyword (fallback) ─────────────────────────
    if "component" in itype or "active_system" in itype:
        return "intervention_component_extraction.json"
    # Note: scenario_mixing can affect BOTH files; the routing by record_id
    # above already handles this correctly.  This fallback is for edge cases
    # where the record_id is not a clean ID (e.g., 'mapping.json scenarios S01-S57').
    if "scenario" in itype and "scenario" in rid:
        return "scenario_extraction.json"
    if "omission" in itype or "mixing" in itype:
        return "outcome_extraction.json"

    # ── Default ───────────────────────────────────────────────────────────
    return "outcome_extraction.json"


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def run_self_correction_loop(document_code: str) -> bool:
    """Query qa_log for unresolved issues, apply deterministic fixes, invoke structural
    refactoring or standard LLM refinement, and re-import corrected records."""
    from src.utils.paths import get_document_ai_output_dir, get_schemas_dir
    from src.validation.schema_validator import validate_against_schema, sanitize_json_data
    from src.utils.json_utils import load_ai_json

    db = DatabaseManager()
    client = GeminiClient()

    with db.get_session() as session:
        doc = get_document_by_code(session, document_code)
        if not doc:
            logger.error(f"[{document_code}] Document not found for self-correction.")
            return False

        doc_id = doc.id

        # Query all unresolved high/medium/low severity issues from qa_log
        from src.database.models import QALog
        qa_issues = session.query(QALog).filter(
            QALog.document_id == doc_id,
            QALog.severity.in_(["high", "medium", "low"]),
            QALog.resolved == 0
        ).all()

        if not qa_issues:
            logger.info(f"[{document_code}] No unresolved issues in qa_log. Skipping self-correction.")
            return False

        logger.info(f"[{document_code}] Found {len(qa_issues)} unresolved issues. Starting self-correction...")

        # ── Step 1: Route issues to target files (FIXED routing) ──────────
        issues_by_file: dict[str, list[dict]] = {}
        for issue in qa_issues:
            target_file = _route_issue_to_file(
                record_id=str(issue.record_id or ""),
                record_type=str(issue.record_type or ""),
                issue_type=str(issue.issue_type or ""),
            )
            issues_by_file.setdefault(target_file, []).append({
                "id": issue.id,
                "record_id": issue.record_id,
                "record_type": issue.record_type,
                "issue_type": issue.issue_type,
                "severity": issue.severity,
                "description": issue.description,
                "required_action": issue.required_action
            })

        logger.info(
            f"[{document_code}] Routed issues: "
            + ", ".join(f"{f}: {len(v)}" for f, v in issues_by_file.items())
        )

        output_dir = get_document_ai_output_dir(document_code)
        schemas_dir = get_schemas_dir()
        corrected_any = False

        # ── Step 2: Deterministic fixes (Phase 1) ─────────────────────────
        # Apply to outcome_extraction.json if it has issues
        if "outcome_extraction.json" in issues_by_file:
            outcome_path = output_dir / "outcome_extraction.json"
            if outcome_path.exists():
                try:
                    outcome_data = load_ai_json(outcome_path)
                    outcome_data, det_resolved = apply_deterministic_fixes(
                        outcome_data,
                        issues_by_file["outcome_extraction.json"],
                        "outcome_extraction.json",
                        document_code,
                    )
                    if det_resolved:
                        # Write fixed outcomes to disk
                        with open(outcome_path, "w", encoding="utf-8") as f:
                            json.dump(outcome_data, f, indent=2)
                        # Re-import to SQLite
                        reimport_corrected_records(session, doc_id, document_code, "outcome_extraction.json", outcome_data)
                        # Mark resolved
                        for rid in det_resolved:
                            session.execute(
                                text("UPDATE qa_log SET resolved = 1 WHERE id = :id"),
                                {"id": rid},
                            )
                        corrected_any = True

                        # Remove deterministically-resolved issues from the LLM queue
                        det_set = set(det_resolved)
                        issues_by_file["outcome_extraction.json"] = [
                            iss for iss in issues_by_file["outcome_extraction.json"]
                            if iss["id"] not in det_set
                        ]
                        if not issues_by_file["outcome_extraction.json"]:
                            del issues_by_file["outcome_extraction.json"]

                except Exception as e:
                    logger.error(f"[{document_code}] Deterministic fix error: {e}")

        # ── Step 3: Structural scenario refactoring (Phase 2) ─────────────
        # Collect scenario_mixing / extraction_omission issues that target scenarios
        scenario_structural_issues = [
            iss for iss in issues_by_file.get("scenario_extraction.json", [])
            if iss["issue_type"] in ("scenario_mixing", "extraction_omission")
        ]

        if scenario_structural_issues:
            logger.info(
                f"[{document_code}] Launching structural refactoring for "
                f"{len(scenario_structural_issues)} scenario issues..."
            )
            scenario_path = output_dir / "scenario_extraction.json"
            outcome_path = output_dir / "outcome_extraction.json"
            scenario_schema_path = schemas_dir / "scenario_extraction.schema.json"
            outcome_schema_path = schemas_dir / "outcome_extraction.schema.json"

            if scenario_path.exists() and scenario_schema_path.exists():
                try:
                    scenarios_data = load_ai_json(scenario_path)
                    outcomes_data = load_ai_json(outcome_path) if outcome_path.exists() else {"extracted_outcomes": []}
                    with open(scenario_schema_path, "r", encoding="utf-8") as f:
                        scenario_schema = json.load(f)

                    refined_scenarios, refined_outcomes = refine_scenarios_structural(
                        client, scenarios_data, outcomes_data, scenario_schema,
                        scenario_structural_issues, document_code,
                    )

                    if refined_scenarios:
                        # Sanitize scenarios before validation
                        refined_scenarios, _ = sanitize_json_data(refined_scenarios, "scenario_extraction.schema.json")
                        
                        # Validate scenarios
                        val_s = validate_against_schema(refined_scenarios, "scenario_extraction.schema.json")
                        if val_s.valid:
                            # Write scenarios
                            with open(scenario_path, "w", encoding="utf-8") as f:
                                json.dump(refined_scenarios, f, indent=2)
                            reimport_corrected_records(session, doc_id, document_code, "scenario_extraction.json", refined_scenarios)

                            # Write outcomes if reassigned
                            if refined_outcomes and refined_outcomes is not outcomes_data:
                                # Sanitize outcomes before validation
                                refined_outcomes, _ = sanitize_json_data(refined_outcomes, "outcome_extraction.schema.json")
                                val_o = validate_against_schema(refined_outcomes, "outcome_extraction.schema.json")
                                if val_o.valid:
                                    with open(outcome_path, "w", encoding="utf-8") as f:
                                        json.dump(refined_outcomes, f, indent=2)
                                    reimport_corrected_records(session, doc_id, document_code, "outcome_extraction.json", refined_outcomes)
                                else:
                                    logger.warning(f"[{document_code}] Reassigned outcomes failed schema validation: {val_o.errors}")

                            # Mark structural issues as resolved
                            for iss in scenario_structural_issues:
                                session.execute(
                                    text("UPDATE qa_log SET resolved = 1 WHERE id = :id"),
                                    {"id": iss["id"]},
                                )
                            corrected_any = True

                            # Remove from pending
                            struct_ids = {iss["id"] for iss in scenario_structural_issues}
                            if "scenario_extraction.json" in issues_by_file:
                                issues_by_file["scenario_extraction.json"] = [
                                    iss for iss in issues_by_file["scenario_extraction.json"]
                                    if iss["id"] not in struct_ids
                                ]
                                if not issues_by_file["scenario_extraction.json"]:
                                    del issues_by_file["scenario_extraction.json"]
                        else:
                            logger.warning(f"[{document_code}] Structural scenarios failed schema validation: {val_s.errors}")

                except Exception as e:
                    logger.error(f"[{document_code}] Structural refactoring error: {e}")

        # ── Step 4: Standard LLM refinement for remaining issues (Phase 3) ─
        for target_file, file_issues in issues_by_file.items():
            if not file_issues:
                continue

            json_path = output_dir / target_file
            if not json_path.exists():
                logger.warning(f"[{document_code}] Expected JSON file {target_file} not found. Skipping.")
                continue

            # Load original JSON and schema
            try:
                original_data = load_ai_json(json_path)
            except Exception as e:
                logger.error(f"[{document_code}] Failed to load original JSON {target_file}: {e}")
                continue

            schema_name = target_file.replace(".json", ".schema.json")
            if target_file == "meta_readiness.json":
                schema_name = "meta_readiness.schema.json"
            
            schema_path = schemas_dir / schema_name
            if not schema_path.exists():
                logger.warning(f"[{document_code}] Schema {schema_name} not found. Skipping.")
                continue
            
            try:
                with open(schema_path, "r", encoding="utf-8") as f:
                    schema_data = json.load(f)
            except Exception as e:
                logger.error(f"[{document_code}] Failed to load schema {schema_name}: {e}")
                continue

            # Invoke Gemini refinement call
            logger.info(f"[{document_code}] Refining {target_file} with {len(file_issues)} remaining audit corrections...")
            refined_data = refine_json_with_gemini(client, original_data, schema_data, file_issues, document_code)
            
            if refined_data:
                # Sanitize refined JSON before validation
                refined_data, _ = sanitize_json_data(refined_data, schema_name)
                
                # Re-validate refined JSON
                val_res = validate_against_schema(refined_data, schema_name)
                if val_res.valid:
                    logger.info(f"[{document_code}] Refined JSON {target_file} passed schema validation!")
                    # Overwrite JSON on disk
                    try:
                        with open(json_path, "w", encoding="utf-8") as f:
                            json.dump(refined_data, f, indent=2)
                    except Exception as e:
                        logger.error(f"[{document_code}] Failed to write refined JSON to disk: {e}")
                        continue
                    
                    # Re-import to SQLite
                    try:
                        reimport_corrected_records(session, doc_id, document_code, target_file, refined_data)
                        corrected_any = True
                        
                        # Mark issues as resolved
                        issue_ids = [issue["id"] for issue in file_issues]
                        for issue_id in issue_ids:
                            session.execute(
                                text("UPDATE qa_log SET resolved = 1 WHERE id = :id"),
                                {"id": issue_id}
                            )
                    except Exception as e:
                        logger.error(f"[{document_code}] Failed to reimport corrected records to DB: {e}")
                        session.rollback()
                        continue
                else:
                    logger.warning(f"[{document_code}] Refined JSON {target_file} failed schema validation: {val_res.errors}")
            else:
                logger.warning(f"[{document_code}] Refinement call failed for {target_file}")
        
        if corrected_any:
            session.commit()
            logger.info(f"[{document_code}] Autonomous Self-Correction Loop completed successfully.")
            return True
        
        return False
