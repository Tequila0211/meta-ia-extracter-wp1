"""
Run intervention component extraction via Gemini API.
"""

from pathlib import Path

from src.ai.gemini_client import GeminiClient
from src.ai.prompt_loader import get_prompt_loader
from src.database.db import DatabaseManager
from src.database.models import Scenario
from src.database.repository import (
    get_document_by_code,
    insert_ai_run,
    insert_intervention_component,
    update_document_status,
)
from src.utils.hashing import compute_text_hash
from src.utils.logging_config import get_logger
from src.utils.paths import get_document_ai_output_dir

logger = get_logger("ai_calls")


def run_intervention_component_extraction(document_code: str, session=None) -> dict:
    """Run intervention component extraction on a document.

    Args:
        document_code: Document code (e.g., 'A001').
        session: Optional existing DB session.

    Returns:
        Result dict.
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
        output_path = output_dir / "intervention_component_extraction.json"

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

        system_prompt = loader.get_system_prompt()
        task_prompt = loader.get_enriched_prompt("intervention_component_coding", document_code)
        schema_name, schema_dict = loader.get_schema_for_task("intervention_component_coding")

        pdf_path = Path(doc.file_path)
        input_hash = compute_text_hash(document_text[:5000])

        result = client.call_with_pdf_and_images(
            task_type="intervention_component_coding",
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
            task_type="intervention_component_coding",
            model_name=result["model"],
            prompt_version=loader.prompts_version,
            schema_name=schema_name,
            codebook_version=loader.codebook_version,
            input_hash=input_hash,
            output_json_path=str(output_path),
            parsed_successfully=result["success"],
            error_message=result.get("error"),
        )

        # Insert components into DB
        if result["success"] and result["data"]:
            components = result["data"].get("components", [])
            for i, comp_data in enumerate(components, 1):
                component_code = f"{document_code}_comp_{i:03d}"
                # Find the scenario ORM id based on scenario_temp_id
                scenario_temp_id = comp_data.get("scenario_temp_id")
                scenario_id = None
                if scenario_temp_id:
                    scenario = session.query(Scenario).filter(
                        Scenario.document_id == doc.id,
                        Scenario.scenario_temp_id == scenario_temp_id
                    ).first()
                    if scenario:
                        scenario_id = scenario.id

                insert_intervention_component(session, doc.id, component_code, comp_data, scenario_id=scenario_id)

            update_document_status(session, doc.id, "components_extracted", "intervention_component_coding")
            logger.info(f"[{document_code}] Inserted {len(components)} intervention components")

        if manage_session:
            session.commit()

        return result

    except Exception as e:
        if manage_session:
            session.rollback()
        logger.error(f"Intervention component extraction failed for {document_code}: {e}")
        raise
    finally:
        if manage_session:
            session.close()
