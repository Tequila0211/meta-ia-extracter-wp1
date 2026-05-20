"""
Run building case extraction via Gemini API.
"""

from pathlib import Path

from src.ai.gemini_client import GeminiClient
from src.ai.prompt_loader import get_prompt_loader
from src.database.db import DatabaseManager
from src.database.repository import (
    get_document_by_code,
    insert_ai_run,
    insert_building_case,
    update_document_status,
)
from src.utils.hashing import compute_text_hash
from src.utils.logging_config import get_logger
from src.utils.paths import get_document_ai_output_dir

logger = get_logger("ai_calls")


def run_building_case_extraction(document_code: str, session=None) -> dict:
    """Run building case extraction on a document.

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
        output_path = output_dir / "building_case_extraction.json"

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
        task_prompt = loader.get_enriched_prompt("building_case_extraction", document_code)
        schema_name, schema_dict = loader.get_schema_for_task("building_case_extraction")

        pdf_path = Path(doc.file_path)
        input_hash = compute_text_hash(document_text[:5000])

        result = client.call_with_pdf_and_images(
            task_type="building_case_extraction",
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
            task_type="building_case_extraction",
            model_name=result["model"],
            prompt_version=loader.prompts_version,
            schema_name=schema_name,
            codebook_version=loader.codebook_version,
            input_hash=input_hash,
            output_json_path=str(output_path),
            parsed_successfully=result["success"],
            error_message=result.get("error"),
        )

        # Insert building cases into DB
        if result["success"] and result["data"]:
            building_cases = result["data"].get("building_cases", [])
            for i, bc_data in enumerate(building_cases, 1):
                building_case_code = f"{document_code}_BC{i:02d}"
                insert_building_case(session, doc.id, building_case_code, bc_data)

            update_document_status(session, doc.id, "building_cases_extracted", "building_case_extraction")
            logger.info(f"[{document_code}] Inserted {len(building_cases)} building cases")

        if manage_session:
            session.commit()

        return result

    except Exception as e:
        if manage_session:
            session.rollback()
        logger.error(f"Building case extraction failed for {document_code}: {e}")
        raise
    finally:
        if manage_session:
            session.close()
