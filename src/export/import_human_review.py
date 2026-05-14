"""
Import human review decisions from Excel.

Reads the 03_OUTCOMES sheet from the review Excel, validates IDs,
and inserts human decisions into the human_review table.
Never overwrites raw AI values.
"""

from pathlib import Path

import pandas as pd
from rich.console import Console

from src.database.db import DatabaseManager
from src.database.models import Document, Outcome
from src.database.repository import insert_human_review
from src.utils.logging_config import get_logger
from src.utils.paths import get_human_review_path, load_project_config

logger = get_logger("export")
console = Console()

VALID_DECISIONS = {"accepted", "corrected", "rejected", "unclear"}


def import_human_review(file_path: str | Path | None = None) -> dict:
    """Import human review decisions from Excel.

    Args:
        file_path: Path to the review Excel file.

    Returns:
        Dict with import statistics.
    """
    if file_path is None:
        file_path = get_human_review_path() / "extraction_review.xlsx"
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Review file not found: {file_path}")

    config = load_project_config()
    require_reviewer = config["review"].get("require_reviewer_name", True)

    # Read outcomes sheet
    df = pd.read_excel(file_path, sheet_name="03_OUTCOMES")

    stats = {
        "total_rows": len(df),
        "imported": 0,
        "skipped_empty": 0,
        "skipped_invalid": 0,
        "errors": [],
    }

    with DatabaseManager() as session:
        for _, row in df.iterrows():
            decision = str(row.get("human_decision", "")).strip().lower()

            # Skip rows without a decision
            if not decision or decision == "" or decision == "nan":
                stats["skipped_empty"] += 1
                continue

            # Validate decision
            if decision not in VALID_DECISIONS:
                msg = f"Invalid decision '{decision}' for {row.get('document_code')}/{row.get('outcome_name')}"
                stats["errors"].append(msg)
                stats["skipped_invalid"] += 1
                logger.warning(msg)
                continue

            # Validate reviewer
            reviewer = str(row.get("reviewer", "")).strip()
            if require_reviewer and not reviewer:
                msg = f"Missing reviewer for {row.get('document_code')}/{row.get('outcome_name')}"
                stats["errors"].append(msg)
                stats["skipped_invalid"] += 1
                continue

            # Find document
            doc_code = str(row.get("document_code", "")).strip()
            doc = session.query(Document).filter(Document.document_code == doc_code).first()
            if not doc:
                msg = f"Document not found: {doc_code}"
                stats["errors"].append(msg)
                stats["skipped_invalid"] += 1
                continue

            # Find outcome
            outcome_name = str(row.get("outcome_name", "")).strip()
            outcome = (
                session.query(Outcome)
                .filter(Outcome.document_id == doc.id, Outcome.outcome_name == outcome_name)
                .first()
            )

            outcome_id = outcome.id if outcome else "unknown"

            # Insert human review for relevant fields
            fields_to_review = [
                ("value", row.get("human_value")),
                ("unit", row.get("human_unit")),
            ]

            for field_name, human_value in fields_to_review:
                ai_value = str(row.get(field_name.replace("human_", ""), ""))
                human_val_str = str(human_value).strip() if pd.notna(human_value) else None

                if decision == "corrected" and human_val_str:
                    insert_human_review(
                        session=session,
                        document_id=doc.id,
                        record_type="outcome",
                        record_id=outcome_id,
                        field_name=field_name,
                        ai_value=ai_value,
                        human_value=human_val_str,
                        decision=decision,
                        reviewer=reviewer,
                        reviewer_comment=str(row.get("reviewer_comment", "")).strip() or None,
                    )

            # Also insert a summary review record
            insert_human_review(
                session=session,
                document_id=doc.id,
                record_type="outcome",
                record_id=outcome_id,
                field_name="decision",
                ai_value=None,
                human_value=decision,
                decision=decision,
                reviewer=reviewer,
                reviewer_comment=str(row.get("reviewer_comment", "")).strip() or None,
            )

            # Update outcome human_validated flag
            if outcome:
                outcome.human_validated = 1
                session.flush()

            stats["imported"] += 1

    console.print(f"[green]✓[/green] Import complete:")
    console.print(f"  Total rows: {stats['total_rows']}")
    console.print(f"  Imported: {stats['imported']}")
    console.print(f"  Skipped (no decision): {stats['skipped_empty']}")
    console.print(f"  Skipped (invalid): {stats['skipped_invalid']}")
    if stats["errors"]:
        console.print(f"  [yellow]Errors: {len(stats['errors'])}[/yellow]")
        for err in stats["errors"][:5]:
            console.print(f"    {err}")

    logger.info(f"Human review import: {stats}")
    return stats
