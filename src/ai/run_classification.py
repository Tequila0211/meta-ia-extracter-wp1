"""
Run article classification via Gemini API.
"""

from pathlib import Path

from src.ai.gemini_client import GeminiClient
from src.ai.prompt_loader import get_prompt_loader
from src.database.db import DatabaseManager
from src.database.repository import (
    get_document_by_code,
    insert_ai_run,
    insert_classification,
    update_document_status,
)
from src.utils.hashing import compute_text_hash
from src.utils.logging_config import get_logger
from src.utils.paths import get_document_ai_output_dir

logger = get_logger("ai_calls")


def run_classification(document_code: str, session=None) -> dict:
    """Run classification on a document.

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

        # Prepare paths
        output_dir = get_document_ai_output_dir(document_code)
        output_path = output_dir / "classification.json"

        # Load text content
        processed_dir = Path(f"data/01_processed/{document_code}/pages_text")
        text_pages = sorted(processed_dir.glob("page_*.txt"))
        document_text = "\n\n".join(
            f"--- PAGE {i+1} ---\n{p.read_text(encoding='utf-8')}"
            for i, p in enumerate(text_pages)
        )

        # Get prompt and schema
        system_prompt = loader.get_system_prompt()
        task_prompt = loader.get_enriched_prompt("classification", document_code)
        schema_name, schema_dict = loader.get_schema_for_task("classification")

        # Prepare multimodal input
        pdf_path = Path(doc.file_path)
        input_hash = compute_text_hash(document_text[:5000])

        # Call Gemini with PDF for overview
        result = client.call_with_pdf_and_images(
            task_type="classification",
            system_prompt=system_prompt,
            user_prompt=task_prompt,
            pdf_path=pdf_path,
            document_text=document_text,
            document_id=document_code,
            output_path=output_path,
            schema_dict=schema_dict,
        )

        # Record AI run
        insert_ai_run(
            session=session,
            document_id=doc.id,
            task_type="classification",
            model_name=result["model"],
            prompt_version=loader.prompts_version,
            schema_name=schema_name,
            codebook_version=loader.codebook_version,
            input_hash=input_hash,
            output_json_path=str(output_path),
            parsed_successfully=result["success"],
            error_message=result.get("error"),
        )

        # Insert classification data if successful
        if result["success"] and result["data"]:
            insert_classification(session, doc.id, result["data"])
            
            # Save bibliographic metadata
            classification_data = result["data"]
            doc.title = classification_data.get("title")
            doc.authors = classification_data.get("authors")
            doc.year = classification_data.get("year")
            doc.journal = classification_data.get("journal")
            
            update_document_status(session, doc.id, "classified", "classification")

        if manage_session:
            session.commit()

        return result

    except Exception as e:
        if manage_session:
            session.rollback()
        logger.error(f"Classification failed for {document_code}: {e}")
        raise
    finally:
        if manage_session:
            session.close()
