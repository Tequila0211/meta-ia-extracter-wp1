"""
Run extraction audit via Gemini API.

Compares extracted data against document content to identify issues.
"""

import json
from pathlib import Path

from src.ai.gemini_client import GeminiClient
from src.ai.prompt_loader import get_prompt_loader
from src.database.db import DatabaseManager
from src.database.repository import (
    get_document_by_code,
    insert_ai_run,
    insert_qa_log,
    update_document_status,
)
from src.utils.hashing import compute_text_hash
from src.utils.logging_config import get_logger
from src.utils.paths import get_document_ai_output_dir

logger = get_logger("ai_calls")


def run_audit(document_code: str, session=None) -> dict:
    """Run audit on a document's extraction.

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
        output_path = output_dir / "audit.json"

        # Load text
        processed_dir = Path(f"data/01_processed/{document_code}/pages_text")
        text_pages = sorted(processed_dir.glob("page_*.txt"))
        document_text = "\n\n".join(
            f"--- PAGE {i+1} ---\n{p.read_text(encoding='utf-8')}"
            for i, p in enumerate(text_pages)
        )

        # Include all prior extraction results as context
        prior_results = {}
        from src.utils.json_utils import load_ai_json
        for fname in ["classification.json", "mapping.json", "scenario_extraction.json", "outcome_extraction.json"]:
            fpath = output_dir / fname
            if fpath.exists():
                prior_results[fname] = load_ai_json(fpath)

        prior_context = f"\n\nPREVIOUS EXTRACTION RESULTS:\n{json.dumps(prior_results, indent=2)}"

        system_prompt = loader.get_system_prompt()
        task_prompt = loader.get_enriched_prompt("audit", document_code)
        task_prompt += prior_context

        schema_name, schema_dict = loader.get_schema_for_task("audit")
        input_hash = compute_text_hash(document_text[:5000])

        # Audit uses text + prior extraction context
        result = client.call_with_text(
            task_type="audit",
            system_prompt=system_prompt,
            user_prompt=task_prompt,
            document_text=document_text,
            document_id=document_code,
            output_path=output_path,
            schema_dict=schema_dict,
        )

        insert_ai_run(
            session=session,
            document_id=doc.id,
            task_type="audit",
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
            # Insert QA log entries for each issue
            issues = result["data"].get("issues", [])
            for issue in issues:
                insert_qa_log(
                    session=session,
                    document_id=doc.id,
                    record_type="audit",
                    record_id=issue.get("affected_record"),
                    severity=issue.get("severity"),
                    issue_type=issue.get("issue_type"),
                    description=issue.get("description"),
                    required_action=issue.get("required_action"),
                )

            update_document_status(session, doc.id, "audited", "audit")
            logger.info(f"[{document_code}] Audit complete: {len(issues)} issues found")

        if manage_session:
            session.commit()

        return result

    except Exception as e:
        if manage_session:
            session.rollback()
        logger.error(f"Audit failed for {document_code}: {e}")
        raise
    finally:
        if manage_session:
            session.close()
