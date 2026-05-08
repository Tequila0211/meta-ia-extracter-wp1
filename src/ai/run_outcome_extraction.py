"""
Run outcome extraction via Gemini API.

Uses page images for detailed numerical data extraction from tables and figures.
"""

import json
from pathlib import Path

from src.ai.gemini_client import GeminiClient
from src.ai.prompt_loader import get_prompt_loader
from src.database.db import DatabaseManager
from src.database.repository import (
    get_document_by_code,
    get_scenarios_for_document,
    insert_ai_run,
    insert_digitization_task,
    insert_evidence,
    insert_outcome,
    update_document_status,
)
from src.utils.hashing import compute_text_hash
from src.utils.logging_config import get_logger
from src.utils.paths import get_document_ai_output_dir

logger = get_logger("ai_calls")


def run_outcome_extraction(document_code: str, session=None) -> dict:
    """Run outcome extraction on a document.

    Uses multimodal input for accurate extraction from tables and figures.

    Args:
        document_code: Document code (e.g., 'A001').
        session: Optional existing DB session.

    Returns:
        Result dict with success status and data.
    """
    loader = get_prompt_loader()
    client = GeminiClient()

    manage_session = session is None
    if manage_session:
        db = DatabaseManager()
        session = db.get_session()

    try:
        doc = get_document_by_code(session, document_code)
        if not doc:
            raise ValueError(f"Document {document_code} not found")

        output_dir = get_document_ai_output_dir(document_code)
        output_path = output_dir / "outcome_extraction.json"

        # Load text
        processed_dir = Path(f"data/01_processed/{document_code}/pages_text")
        text_pages = sorted(processed_dir.glob("page_*.txt"))
        document_text = "\n\n".join(
            f"--- PAGE {i+1} ---\n{p.read_text(encoding='utf-8')}"
            for i, p in enumerate(text_pages)
        )

        # Load page images
        images_dir = Path(f"data/01_processed/{document_code}/pages_images")
        image_paths = sorted(images_dir.glob("page_*.png")) if images_dir.exists() else []

        # Include scenario context from mapping
        mapping_path = output_dir / "mapping.json"
        scenario_context = ""
        if mapping_path.exists():
            mapping_data = json.loads(mapping_path.read_text(encoding="utf-8"))
            scenario_context = f"\n\nPREVIOUS MAPPING RESULTS:\n{json.dumps(mapping_data, indent=2)}"

        system_prompt = loader.get_system_prompt()
        task_prompt = loader.get_enriched_prompt("outcome_extraction", document_code)
        task_prompt += scenario_context

        schema_name, schema_dict = loader.get_schema_for_task("outcome_extraction")

        pdf_path = Path(doc.file_path)
        input_hash = compute_text_hash(document_text[:5000])

        # Multimodal call with page images for detailed extraction
        result = client.call_with_pdf_and_images(
            task_type="outcome_extraction",
            system_prompt=system_prompt,
            user_prompt=task_prompt,
            pdf_path=pdf_path,
            image_paths=image_paths,
            document_text=document_text,
            document_id=document_code,
            output_path=output_path,
            schema_dict=schema_dict,
        )

        insert_ai_run(
            session=session,
            document_id=doc.id,
            task_type="outcome_extraction",
            model_name=result["model"],
            prompt_version=loader.prompts_version,
            schema_name=schema_name,
            codebook_version=loader.codebook_version,
            input_hash=input_hash,
            output_json_path=str(output_path),
            parsed_successfully=result["success"],
            error_message=result.get("error"),
        )

        if result["success"] and result["data"]:
            outcomes = result["data"].get("extracted_outcomes", [])
            # Build scenario lookup
            db_scenarios = get_scenarios_for_document(session, doc.id)
            scenario_lookup = {s.scenario_temp_id: s.id for s in db_scenarios}

            for i, outcome_data in enumerate(outcomes, 1):
                outcome_code = f"{document_code}_O{i:03d}"

                # Link to scenario if possible
                scenario_temp_id = outcome_data.get("scenario_temp_id")
                scenario_id = scenario_lookup.get(scenario_temp_id)

                outcome = insert_outcome(
                    session, doc.id, scenario_id, outcome_code, outcome_data
                )

                # Create evidence record
                insert_evidence(
                    session=session,
                    document_id=doc.id,
                    linked_table="outcomes",
                    linked_record_id=outcome.id,
                    page_number=outcome_data.get("page"),
                    source_type=outcome_data.get("source_type"),
                    table_or_figure_label=outcome_data.get("table_or_figure"),
                    row_label=outcome_data.get("row_label"),
                    column_label=outcome_data.get("column_label_baseline"),
                    evidence_text=outcome_data.get("evidence_text"),
                )

                # Create digitization task if needed
                if outcome_data.get("needs_digitization"):
                    insert_digitization_task(
                        session=session,
                        document_id=doc.id,
                        outcome_id=outcome.id,
                        page=outcome_data.get("page"),
                        figure_label=outcome_data.get("table_or_figure"),
                        reason="Value from figure requires manual digitization",
                    )

            update_document_status(session, doc.id, "outcomes_extracted", "outcome_extraction")
            logger.info(f"[{document_code}] Inserted {len(outcomes)} outcomes")

        if manage_session:
            session.commit()

        return result

    except Exception as e:
        if manage_session:
            session.rollback()
        logger.error(f"Outcome extraction failed for {document_code}: {e}")
        raise
    finally:
        if manage_session:
            session.close()
