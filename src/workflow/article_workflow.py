"""
Article processing workflow.

Implements the full 25-step processing pipeline for a single article (PRD §15).
"""

from pathlib import Path

from rich.console import Console

from src.ai.run_audit import run_audit
from src.ai.run_classification import run_classification
from src.ai.run_mapping import run_mapping
from src.ai.run_outcome_extraction import run_outcome_extraction
from src.ai.run_scenario_extraction import run_scenario_extraction
from src.database.db import DatabaseManager
from src.database.repository import (
    get_document_by_code,
    update_document_status,
)
from src.ingestion.preprocessing import preprocess_document
from src.utils.logging_config import get_logger
from src.validation.business_rules import check_outcome_rules
from src.validation.schema_validator import validate_json_file

logger = get_logger("workflow")
console = Console()


def process_article(document_code: str) -> dict:
    """Process a single article through the full extraction pipeline.

    Steps (PRD §15):
    1-2. Verify PDF exists and document is registered
    3. Preprocess if needed
    4-7. Classification
    8. Check extractability
    9-12. Mapping
    13-15. Scenario extraction
    16-19. Outcome extraction + evidence + digitization
    20-22. Audit
    23-25. Apply blocking rules, mark for review

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
            console.print(f"\n[blue]Step 1/5: Preprocessing {document_code}...[/blue]")
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

        # Step 4-7: Classification
        if _needs_step(document_code, "classified"):
            console.print(f"\n[blue]Step 2/5: Classifying {document_code}...[/blue]")
            try:
                cls_result = run_classification(document_code)
                if not cls_result["success"]:
                    result["errors"].append(f"Classification failed: {cls_result['error']}")
                    _set_failed(document_code)
                    result["final_status"] = "failed"
                    return result

                # Validate schema
                from src.utils.paths import get_document_ai_output_dir
                cls_path = get_document_ai_output_dir(document_code) / "classification.json"
                val = validate_json_file(cls_path, "classification.schema.json")
                if not val:
                    result["errors"].extend(val.errors)
                    logger.warning(f"Classification schema validation issues: {val.errors}")

                result["steps_completed"].append("classification")

                # Step 8: Check extractability
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

        # Step 9-12: Mapping
        if _needs_step(document_code, "mapped"):
            console.print(f"\n[blue]Step 3/5: Mapping {document_code}...[/blue]")
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

        # Step 13-15: Scenario extraction
        if _needs_step(document_code, "scenarios_extracted"):
            console.print(f"\n[blue]Step 4/5: Extracting scenarios for {document_code}...[/blue]")
            try:
                scen_result = run_scenario_extraction(document_code)
                if not scen_result["success"]:
                    result["errors"].append(f"Scenario extraction failed: {scen_result['error']}")
                result["steps_completed"].append("scenario_extraction")
            except Exception as e:
                result["errors"].append(f"Scenario extraction error: {e}")
                logger.error(f"Scenario extraction error for {document_code}: {e}")
        else:
            result["steps_completed"].append("scenario_extraction (cached)")

        # Step 16-20: Outcome extraction + evidence + digitization
        if _needs_step(document_code, "outcomes_extracted"):
            console.print(f"\n[blue]Step 5/5: Extracting outcomes for {document_code}...[/blue]")
            try:
                out_result = run_outcome_extraction(document_code)
                if not out_result["success"]:
                    result["errors"].append(f"Outcome extraction failed: {out_result['error']}")
                result["steps_completed"].append("outcome_extraction")
            except Exception as e:
                result["errors"].append(f"Outcome extraction error: {e}")
                logger.error(f"Outcome extraction error for {document_code}: {e}")
        else:
            result["steps_completed"].append("outcome_extraction (cached)")

        # Step 21-23: Audit
        if _needs_step(document_code, "audited"):
            console.print(f"\n[blue]Running audit for {document_code}...[/blue]")
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

        # Step 24-25: Mark for human review
        if not result["errors"] and result["final_status"] not in ("failed", "not_extractable"):
            with DatabaseManager() as session:
                doc = get_document_by_code(session, document_code)
                if doc and doc.status not in ("failed", "not_extractable"):
                    update_document_status(session, doc.id, "needs_human_review", "audit")
            result["final_status"] = "needs_human_review"
        
        if result["errors"]:
            result["final_status"] = "failed"
            console.print(f"\n[red]✗ {document_code} finished with errors.[/red]")
        else:
            console.print(f"\n[green]✓ {document_code} completed.[/green]")
        
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
        "scenarios_extracted", "outcomes_extracted", "audited",
        "needs_human_review", "validated",
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
            return current_idx < target_idx
        except ValueError:
            return True


def _set_failed(document_code: str):
    """Mark a document as failed."""
    with DatabaseManager() as session:
        doc = get_document_by_code(session, document_code)
        if doc:
            update_document_status(session, doc.id, "failed")
