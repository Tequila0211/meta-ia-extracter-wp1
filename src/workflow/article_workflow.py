"""
Article processing workflow.

Implements the full 10-step processing pipeline for a single article (PRD §15 & Robustecimiento).
"""

from pathlib import Path

from rich.console import Console

from src.ai.run_audit import run_audit
from src.ai.run_building_case_extraction import run_building_case_extraction
from src.ai.run_classification import run_classification
from src.ai.run_intervention_component_extraction import run_intervention_component_extraction
from src.ai.run_mapping import run_mapping
from src.ai.run_meta_readiness import run_meta_readiness
from src.ai.run_outcome_extraction import run_outcome_extraction
from src.ai.run_scenario_extraction import run_scenario_extraction
from src.ai.run_space_extraction import run_space_extraction
from src.ai.run_baseline_matching import run_baseline_matching
from src.database.db import DatabaseManager
from src.database.repository import (
    get_document_by_code,
    update_document_status,
)
from src.ingestion.preprocessing import preprocess_document
from src.utils.logging_config import get_logger
from src.utils.paths import get_document_ai_output_dir
from src.validation.schema_validator import validate_json_file

logger = get_logger("workflow")
console = Console()


def process_article(document_code: str) -> dict:
    """Process a single article through the full extraction pipeline.

    Steps:
    1-2. Verify PDF exists and document is registered
    3. Preprocess if needed
    4. Classification
    5. Mapping
    6. Building case extraction
    7. Scenario extraction
    8. Space extraction
    9. Intervention component coding
    10. Outcome extraction
    11. Baseline matching
    12. Audit
    13. Meta-readiness audit

    Args:
        document_code: Document code (e.g., 'A001').

    Returns:
        Dict with processing results and status.
    """
    result = {
        "document_code": document_code,
        "steps_completed": [],
        "errors": [],
        "final_status": None,
    }

    try:
        with DatabaseManager() as session:
            # Step 1-2: Verify document
            doc = get_document_by_code(session, document_code)
            if not doc:
                result["errors"].append(f"Document {document_code} not registered")
                result["final_status"] = "failed"
                return result

            pdf_path = Path(doc.file_path)
            if not pdf_path.exists():
                result["errors"].append(f"PDF not found: {pdf_path}")
                result["final_status"] = "failed"
                update_document_status(session, doc.id, "failed", "verification")
                return result

            result["steps_completed"].append("verification")

        # Step 3: Preprocess
        if _needs_step(document_code, "preprocessed"):
            console.print(f"\n[blue]Step 1/11: Preprocessing {document_code}...[/blue]")
            try:
                preprocess_document(document_code)
                result["steps_completed"].append("preprocessing")
            except Exception as e:
                result["errors"].append(f"Preprocessing failed: {e}")
                _set_failed(document_code)
                result["final_status"] = "failed"
                return result
        else:
            result["steps_completed"].append("preprocessing (cached)")

        # Step 4: Classification
        if _needs_step(document_code, "classified"):
            console.print(f"\n[blue]Step 2/11: Classifying {document_code}...[/blue]")
            try:
                cls_result = run_classification(document_code)
                if not cls_result["success"]:
                    result["errors"].append(f"Classification failed: {cls_result['error']}")
                    _set_failed(document_code)
                    result["final_status"] = "failed"
                    return result

                # Validate schema
                cls_path = get_document_ai_output_dir(document_code) / "classification.json"
                val = validate_json_file(cls_path, "classification.schema.json")
                if not val:
                    result["errors"].extend(val.errors)
                    logger.warning(f"Classification schema validation issues: {val.errors}")
                    log_schema_errors_to_qa_log(document_code, "classification.json", "classification", val.errors)

                result["steps_completed"].append("classification")

                # Check extractability
                cls_data = cls_result["data"]
                if cls_data and cls_data.get("is_extractable") is False:
                    console.print(f"[yellow]Article {document_code} is not extractable: {cls_data.get('reason')}[/yellow]")
                    with DatabaseManager() as session:
                        doc = get_document_by_code(session, document_code)
                        update_document_status(session, doc.id, "not_extractable", "classification")
                    result["final_status"] = "not_extractable"
                    return result

            except Exception as e:
                result["errors"].append(f"Classification error: {e}")
                _set_failed(document_code)
                result["final_status"] = "failed"
                return result
        else:
            result["steps_completed"].append("classification (cached)")
            cls_path = get_document_ai_output_dir(document_code) / "classification.json"
            cls_val = validate_json_file(cls_path, "classification.schema.json")
            if not cls_val:
                log_schema_errors_to_qa_log(document_code, "classification.json", "classification", cls_val.errors)

        # Step 5: Mapping
        if _needs_step(document_code, "mapped"):
            console.print(f"\n[blue]Step 3/11: Mapping {document_code}...[/blue]")
            try:
                map_result = run_mapping(document_code)
                if not map_result["success"]:
                    result["errors"].append(f"Mapping failed: {map_result['error']}")
                result["steps_completed"].append("mapping")
            except Exception as e:
                result["errors"].append(f"Mapping error: {e}")
                logger.error(f"Mapping error for {document_code}: {e}")
        else:
            result["steps_completed"].append("mapping (cached)")

        # Step 6: Building Case Extraction
        if _needs_step(document_code, "building_cases_extracted"):
            console.print(f"\n[blue]Step 4/11: Extracting building cases for {document_code}...[/blue]")
            try:
                bc_result = run_building_case_extraction(document_code)
                if not bc_result["success"]:
                    result["errors"].append(f"Building case extraction failed: {bc_result['error']}")
                
                # Validate schema
                bc_path = get_document_ai_output_dir(document_code) / "building_case_extraction.json"
                val = validate_json_file(bc_path, "building_case_extraction.schema.json")
                if not val:
                    result["errors"].extend(val.errors)
                    logger.warning(f"Building case extraction schema validation issues: {val.errors}")
                    log_schema_errors_to_qa_log(document_code, "building_case_extraction.json", "building_case", val.errors)

                result["steps_completed"].append("building_case_extraction")
            except Exception as e:
                result["errors"].append(f"Building case extraction error: {e}")
                logger.error(f"Building case extraction error for {document_code}: {e}")
        else:
            result["steps_completed"].append("building_case_extraction (cached)")
            bc_path = get_document_ai_output_dir(document_code) / "building_case_extraction.json"
            bc_val = validate_json_file(bc_path, "building_case_extraction.schema.json")
            if not bc_val:
                log_schema_errors_to_qa_log(document_code, "building_case_extraction.json", "building_case", bc_val.errors)

        # Step 7: Scenario extraction
        if _needs_step(document_code, "scenarios_extracted"):
            console.print(f"\n[blue]Step 5/11: Extracting scenarios for {document_code}...[/blue]")
            try:
                scen_result = run_scenario_extraction(document_code)
                if not scen_result["success"]:
                    result["errors"].append(f"Scenario extraction failed: {scen_result['error']}")
                
                # Validate schema
                scen_path = get_document_ai_output_dir(document_code) / "scenario_extraction.json"
                val = validate_json_file(scen_path, "scenario_extraction.schema.json")
                if not val:
                    result["errors"].extend(val.errors)
                    logger.warning(f"Scenario extraction schema validation issues: {val.errors}")
                    log_schema_errors_to_qa_log(document_code, "scenario_extraction.json", "scenario", val.errors)

                result["steps_completed"].append("scenario_extraction")
            except Exception as e:
                result["errors"].append(f"Scenario extraction error: {e}")
                logger.error(f"Scenario extraction error for {document_code}: {e}")
        else:
            result["steps_completed"].append("scenario_extraction (cached)")
            scen_path = get_document_ai_output_dir(document_code) / "scenario_extraction.json"
            scen_val = validate_json_file(scen_path, "scenario_extraction.schema.json")
            if not scen_val:
                log_schema_errors_to_qa_log(document_code, "scenario_extraction.json", "scenario", scen_val.errors)

        # Step 8: Space Extraction
        if _needs_step(document_code, "spaces_extracted"):
            console.print(f"\n[blue]Step 6/11: Extracting spaces for {document_code}...[/blue]")
            try:
                sp_result = run_space_extraction(document_code)
                if not sp_result["success"]:
                    result["errors"].append(f"Space extraction failed: {sp_result['error']}")
                
                # Validate schema
                sp_path = get_document_ai_output_dir(document_code) / "space_extraction.json"
                val = validate_json_file(sp_path, "space_extraction.schema.json")
                if not val:
                    result["errors"].extend(val.errors)
                    logger.warning(f"Space extraction schema validation issues: {val.errors}")
                    log_schema_errors_to_qa_log(document_code, "space_extraction.json", "space", val.errors)

                result["steps_completed"].append("space_extraction")
            except Exception as e:
                result["errors"].append(f"Space extraction error: {e}")
                logger.error(f"Space extraction error for {document_code}: {e}")
        else:
            result["steps_completed"].append("space_extraction (cached)")
            sp_path = get_document_ai_output_dir(document_code) / "space_extraction.json"
            sp_val = validate_json_file(sp_path, "space_extraction.schema.json")
            if not sp_val:
                log_schema_errors_to_qa_log(document_code, "space_extraction.json", "space", sp_val.errors)

        # Step 9: Intervention Component Coding
        if _needs_step(document_code, "components_extracted"):
            console.print(f"\n[blue]Step 7/11: Coding intervention components for {document_code}...[/blue]")
            try:
                comp_result = run_intervention_component_extraction(document_code)
                if not comp_result["success"]:
                    result["errors"].append(f"Intervention component coding failed: {comp_result['error']}")
                
                # Validate schema
                comp_path = get_document_ai_output_dir(document_code) / "intervention_component_extraction.json"
                val = validate_json_file(comp_path, "intervention_component_extraction.schema.json")
                if not val:
                    result["errors"].extend(val.errors)
                    logger.warning(f"Intervention component coding schema validation issues: {val.errors}")
                    log_schema_errors_to_qa_log(document_code, "intervention_component_extraction.json", "component", val.errors)

                result["steps_completed"].append("intervention_component_coding")
            except Exception as e:
                result["errors"].append(f"Intervention component coding error: {e}")
                logger.error(f"Intervention component coding error for {document_code}: {e}")
        else:
            result["steps_completed"].append("intervention_component_coding (cached)")
            comp_path = get_document_ai_output_dir(document_code) / "intervention_component_extraction.json"
            comp_val = validate_json_file(comp_path, "intervention_component_extraction.schema.json")
            if not comp_val:
                log_schema_errors_to_qa_log(document_code, "intervention_component_extraction.json", "component", comp_val.errors)

        # Step 10: Outcome extraction + evidence + digitization
        if _needs_step(document_code, "outcomes_extracted"):
            console.print(f"\n[blue]Step 8/11: Extracting outcomes for {document_code}...[/blue]")
            try:
                out_result = run_outcome_extraction(document_code)
                if not out_result["success"]:
                    err = f"Outcome extraction failed: {out_result['error']}"
                    result["errors"].append(err)
                    logger.error(err)
                    _set_failed(document_code)
                    result["final_status"] = "failed"
                    return result

                out_path = get_document_ai_output_dir(document_code) / "outcome_extraction.json"
                if not out_path.exists():
                    err = f"Outcome extraction did not produce output file: {out_path.name}"
                    result["errors"].append(err)
                    logger.error(err)
                    _set_failed(document_code)
                    result["final_status"] = "failed"
                    return result

                out_val = validate_json_file(out_path, "outcome_extraction.schema.json")
                if not out_val:
                    result["errors"].extend(out_val.errors)
                    logger.warning(f"Outcome extraction schema validation issues: {out_val.errors}")
                    log_schema_errors_to_qa_log(document_code, "outcome_extraction.json", "outcome", out_val.errors)

                result["steps_completed"].append("outcome_extraction")
            except Exception as e:
                result["errors"].append(f"Outcome extraction error: {e}")
                logger.error(f"Outcome extraction error for {document_code}: {e}")
                _set_failed(document_code)
                result["final_status"] = "failed"
                return result
        else:
            result["steps_completed"].append("outcome_extraction (cached)")
            out_path = get_document_ai_output_dir(document_code) / "outcome_extraction.json"
            out_val = validate_json_file(out_path, "outcome_extraction.schema.json")
            if not out_val:
                log_schema_errors_to_qa_log(document_code, "outcome_extraction.json", "outcome", out_val.errors)

        # Step 11: Baseline Matching
        if _needs_step(document_code, "baseline_matched"):
            console.print(f"\n[blue]Step 9/11: Matching baselines for {document_code}...[/blue]")
            try:
                bm_result = run_baseline_matching(document_code)
                if not bm_result["success"]:
                    result["errors"].append(f"Baseline matching failed: {bm_result['error']}")
                
                # Validate schema
                bm_path = get_document_ai_output_dir(document_code) / "baseline_matching.json"
                val = validate_json_file(bm_path, "baseline_matching.schema.json")
                if not val:
                    result["errors"].extend(val.errors)
                    logger.warning(f"Baseline matching schema validation issues: {val.errors}")
                    log_schema_errors_to_qa_log(document_code, "baseline_matching.json", "baseline_matching", val.errors)

                result["steps_completed"].append("baseline_matching")
            except Exception as e:
                result["errors"].append(f"Baseline matching error: {e}")
                logger.error(f"Baseline matching error for {document_code}: {e}")
        else:
            result["steps_completed"].append("baseline_matching (cached)")
            bm_path = get_document_ai_output_dir(document_code) / "baseline_matching.json"
            bm_val = validate_json_file(bm_path, "baseline_matching.schema.json")
            if not bm_val:
                log_schema_errors_to_qa_log(document_code, "baseline_matching.json", "baseline_matching", bm_val.errors)

        # Step 12: Audit
        if _needs_step(document_code, "audited"):
            console.print(f"\n[blue]Step 10/11: Running audit for {document_code}...[/blue]")
            try:
                audit_result = run_audit(document_code)
                if not audit_result["success"]:
                    result["errors"].append(f"Audit failed: {audit_result['error']}")
                result["steps_completed"].append("audit")
            except Exception as e:
                result["errors"].append(f"Audit error: {e}")
                logger.error(f"Audit error for {document_code}: {e}")
        else:
            result["steps_completed"].append("audit (cached)")

        # Autonomous Self-Correction Loop
        try:
            from src.workflow.correction_loop import run_self_correction_loop
            logger.info(f"[{document_code}] Checking if autonomous self-correction is needed...")
            corrected = run_self_correction_loop(document_code)
            if corrected:
                console.print(f"\n[green]Self-Correction Loop completed! Re-running Audit to refresh logs...[/green]")
                # Re-run audit to reflect corrected values in SQLite and verify resolved issues
                run_audit(document_code)
        except Exception as e:
            logger.error(f"[{document_code}] Error in Autonomous Self-Correction Loop: {e}")

        # Step 13: Meta-readiness Audit
        if _needs_step(document_code, "meta_readiness_audited"):
            console.print(f"\n[blue]Step 11/11: Running meta-readiness audit for {document_code}...[/blue]")
            try:
                mr_result = run_meta_readiness(document_code)
                if not mr_result["success"]:
                    result["errors"].append(f"Meta-readiness audit failed: {mr_result['error']}")
                
                # Validate schema
                mr_path = get_document_ai_output_dir(document_code) / "meta_readiness.json"
                val = validate_json_file(mr_path, "meta_readiness.schema.json")
                if not val:
                    result["errors"].extend(val.errors)
                    logger.warning(f"Meta-readiness audit schema validation issues: {val.errors}")
                    log_schema_errors_to_qa_log(document_code, "meta_readiness.json", "meta_readiness", val.errors)

                result["steps_completed"].append("meta_readiness_audit")
            except Exception as e:
                result["errors"].append(f"Meta-readiness audit error: {e}")
                logger.error(f"Meta-readiness audit error for {document_code}: {e}")
        else:
            result["steps_completed"].append("meta_readiness_audit (cached)")
            mr_path = get_document_ai_output_dir(document_code) / "meta_readiness.json"
            mr_val = validate_json_file(mr_path, "meta_readiness.schema.json")
            if not mr_val:
                log_schema_errors_to_qa_log(document_code, "meta_readiness.json", "meta_readiness", mr_val.errors)

        # Final Verification and Mark for human review: re-validate all outputs
        # to clear any schema errors that were successfully fixed by the correction loop.
        final_errors = []
        output_dir = get_document_ai_output_dir(document_code)
        
        validation_map = {
            "classification.json": "classification.schema.json",
            "building_case_extraction.json": "building_case_extraction.schema.json",
            "scenario_extraction.json": "scenario_extraction.schema.json",
            "space_extraction.json": "space_extraction.schema.json",
            "intervention_component_extraction.json": "intervention_component_extraction.schema.json",
            "outcome_extraction.json": "outcome_extraction.schema.json",
            "baseline_matching.json": "baseline_matching.schema.json",
            "meta_readiness.json": "meta_readiness.schema.json",
        }
        
        for fname, sname in validation_map.items():
            fpath = output_dir / fname
            if fpath.exists():
                val = validate_json_file(fpath, sname)
                if not val:
                    final_errors.extend(val.errors)
        
        missing_outputs = _get_missing_required_outputs(document_code)
        if missing_outputs:
            final_errors.append(
                f"Missing required outputs: {', '.join(missing_outputs)}"
            )
            
        result["errors"] = final_errors
        
        if not result["errors"] and result["final_status"] not in ("failed", "not_extractable"):
            with DatabaseManager() as session:
                doc = get_document_by_code(session, document_code)
                if doc and doc.status not in ("failed", "not_extractable"):
                    update_document_status(session, doc.id, "needs_human_review", "meta_readiness_audit")
            result["final_status"] = "needs_human_review"

        if result["errors"]:
            result["final_status"] = "failed"
            _set_failed(document_code)
            console.print(f"\n[red]ERROR: {document_code} finished with errors.[/red]")
            for err in result["errors"]:
                console.print(f"  [red]- {err}[/red]")
        else:
            console.print(f"\n[green]OK: {document_code} completed.[/green]")
        
        console.print(f"  Status: {result['final_status']}")
        console.print(f"  Steps: {len(result['steps_completed'])}")
        if result["errors"]:
            console.print(f"  [yellow]Warnings: {len(result['errors'])}[/yellow]")

        return result

    except Exception as e:
        logger.error(f"Fatal error processing {document_code}: {e}")
        result["errors"].append(f"Fatal error: {e}")
        result["final_status"] = "failed"
        return result


def _needs_step(document_code: str, target_status: str) -> bool:
    """Check if a document needs a specific processing step."""
    status_order = [
        "pending", "preprocessed", "classified", "mapped",
        "building_cases_extracted", "scenarios_extracted", "spaces_extracted",
        "components_extracted", "outcomes_extracted", "baseline_matched",
        "audited", "meta_readiness_audited", "needs_human_review", "validated",
    ]

    with DatabaseManager() as session:
        doc = get_document_by_code(session, document_code)
        if not doc:
            return True
        current = doc.status
        if current in ("failed", "not_extractable"):
            return False
        try:
            current_idx = status_order.index(current)
            target_idx = status_order.index(target_status)
            if current_idx < target_idx:
                return True
            return not _has_required_artifact(document_code, target_status)
        except ValueError:
            return True


def _set_failed(document_code: str):
    """Mark a document as failed."""
    with DatabaseManager() as session:
        doc = get_document_by_code(session, document_code)
        if doc:
            update_document_status(session, doc.id, "failed")


def _has_required_artifact(document_code: str, status: str) -> bool:
    """Check if the expected artifact for a status exists."""
    if status == "preprocessed":
        return Path(f"data/01_processed/{document_code}/metadata.json").exists()

    output_map = {
        "classified": "classification.json",
        "mapped": "mapping.json",
        "building_cases_extracted": "building_case_extraction.json",
        "scenarios_extracted": "scenario_extraction.json",
        "spaces_extracted": "space_extraction.json",
        "components_extracted": "intervention_component_extraction.json",
        "outcomes_extracted": "outcome_extraction.json",
        "baseline_matched": "baseline_matching.json",
        "audited": "audit.json",
        "meta_readiness_audited": "meta_readiness.json",
    }

    output_file = output_map.get(status)
    if not output_file:
        return True

    return (get_document_ai_output_dir(document_code) / output_file).exists()


def _get_missing_required_outputs(document_code: str) -> list[str]:
    """Get missing required AI output files for a fully processed document."""
    required_outputs = [
        "classification.json",
        "mapping.json",
        "building_case_extraction.json",
        "scenario_extraction.json",
        "space_extraction.json",
        "intervention_component_extraction.json",
        "outcome_extraction.json",
        "baseline_matching.json",
        "audit.json",
        "meta_readiness.json",
    ]
    output_dir = get_document_ai_output_dir(document_code)
    return [
        output_name
        for output_name in required_outputs
        if not (output_dir / output_name).exists()
    ]


def log_schema_errors_to_qa_log(document_code: str, target_file: str, record_type: str, errors: list[str]):
    """Insert schema validation errors into the qa_log table so the correction loop can resolve them."""
    import re
    from sqlalchemy import text
    from src.database.repository import insert_qa_log, get_document_by_code
    from src.database.db import DatabaseManager
    with DatabaseManager() as session:
        doc = get_document_by_code(session, document_code)
        if not doc:
            return
        
        # Clear existing schema validation issues for this file first to avoid duplicates
        session.execute(
            text("DELETE FROM qa_log WHERE document_id = :doc_id AND record_type = :record_type AND issue_type = 'schema_validation_failed'"),
            {"doc_id": doc.id, "record_type": record_type}
        )
        
        for err in errors:
            record_id = target_file
            match = re.search(r'\(at\s+([^\)]+)\)', err)
            if match:
                path_info = match.group(1)
                parts = [p.strip() for p in re.split(r'→|➔|->|arrows', path_info)]
                if len(parts) >= 2 and parts[1].isdigit():
                    idx = parts[1]
                    if record_type == "outcome":
                        record_id = f"O{int(idx) + 1:03d}"
                    elif record_type == "component":
                        record_id = f"C{int(idx) + 1:02d}"
                    elif record_type == "scenario":
                        record_id = f"S{int(idx) + 1:02d}"
                    elif record_type == "space":
                        record_id = f"SP{int(idx) + 1:02d}"
            
            insert_qa_log(
                session=session,
                document_id=doc.id,
                record_type=record_type,
                record_id=record_id,
                severity="high",
                issue_type="schema_validation_failed",
                description=err,
                required_action="Correct the JSON structure and field values to strictly match the schema.",
            )
        session.commit()
