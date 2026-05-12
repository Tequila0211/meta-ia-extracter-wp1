"""
Export extraction data to Excel for human review.

Creates a multi-sheet Excel file with all extraction data,
including columns for human review decisions.
"""

from pathlib import Path

import pandas as pd
from rich.console import Console

from src.database.db import DatabaseManager
from src.database.models import (
    DigitizationTask,
    Document,
    Evidence,
    HumanReview,
    Outcome,
    QALog,
    Scenario,
)
from src.utils.logging_config import get_logger
from src.utils.paths import get_human_review_path

logger = get_logger("export")
console = Console()


def export_review_excel(output_path: str | Path | None = None) -> Path:
    """Export extraction data to Excel for human review.

    Creates sheets: 00_README, 01_DOCUMENTS, 02_SCENARIOS, 03_OUTCOMES,
    04_EVIDENCE, 05_QA_LOG, 06_HUMAN_REVIEW, 07_DIGITIZATION_TASKS

    Args:
        output_path: Optional path override for the Excel file.

    Returns:
        Path to the created Excel file.
    """
    if output_path is None:
        output_path = get_human_review_path() / "extraction_review.xlsx"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with DatabaseManager() as session:
        # 01_DOCUMENTS
        docs = session.query(Document).order_by(Document.document_code).all()
        docs_data = [{
            "document_code": d.document_code,
            "file_name": d.file_name,
            "status": d.status,
            "current_step": d.current_step,
            "created_at": d.created_at,
            "updated_at": d.updated_at,
        } for d in docs]

        # 02_SCENARIOS
        scenarios = session.query(Scenario).all()
        scenarios_data = []
        for s in scenarios:
            doc = session.query(Document).filter(Document.id == s.document_id).first()
            scenarios_data.append({
                "document_code": doc.document_code if doc else "",
                "scenario_code": s.scenario_code,
                "scenario_label": s.scenario_label,
                "scenario_family": s.scenario_family,
                "year": s.year,
                "ssp": s.ssp,
                "operational_mode": s.operational_mode,
                "building_typology": s.building_typology,
                "climate_location": s.climate_location,
                "climate_zone": s.climate_zone,
                "simulation_software": s.simulation_software,
                "baseline_description": s.baseline_description,
                "intervention_description": s.intervention_description,
                "intervention_type": s.intervention_type,
                "is_package": bool(s.is_package) if s.is_package is not None else None,
                "status": s.status,
                "human_validated": bool(s.human_validated),
            })

        # 03_OUTCOMES
        outcomes = session.query(Outcome).all()
        outcomes_data = []
        for o in outcomes:
            doc = session.query(Document).filter(Document.id == o.document_id).first()
            scenario = session.query(Scenario).filter(Scenario.id == o.scenario_id).first() if o.scenario_id else None
            outcomes_data.append({
                "document_code": doc.document_code if doc else "",
                "scenario_code": scenario.scenario_code if scenario else "",
                "outcome_name": o.outcome_name,
                "metric_group": o.metric_group,
                "room_or_space": o.room_or_space,
                "occupant_group": o.occupant_group,
                "value": o.value,
                "unit": o.unit,
                "reported_effect_value": o.reported_effect_value,
                "reported_effect_unit": o.reported_effect_unit,
                "extraction_method": o.extraction_method,
                "confidence": o.confidence,
                "source_type": o.source_type,
                "page": o.page,
                "table_or_figure": o.table_or_figure,
                "evidence_text": getattr(o, '_evidence_text', None),
                "needs_digitization": bool(o.needs_digitization),
                "status": o.status,
                "human_decision": "",
                "human_value": None,
                "human_unit": "",
                "reviewer": "",
                "reviewer_comment": "",
            })

        # 04_EVIDENCE
        evidence_records = session.query(Evidence).all()
        evidence_data = [{
            "document_id": e.document_id,
            "linked_table": e.linked_table,
            "linked_record_id": e.linked_record_id,
            "page_number": e.page_number,
            "source_type": e.source_type,
            "table_or_figure_label": e.table_or_figure_label,
            "evidence_text": e.evidence_text,
            "validation_status": e.validation_status,
        } for e in evidence_records]

        # 05_QA_LOG
        qa_logs = session.query(QALog).all()
        qa_data = [{
            "document_id": q.document_id,
            "record_type": q.record_type,
            "record_id": q.record_id,
            "severity": q.severity,
            "issue_type": q.issue_type,
            "description": q.description,
            "required_action": q.required_action,
            "resolved": bool(q.resolved),
        } for q in qa_logs]

        # 06_HUMAN_REVIEW
        reviews = session.query(HumanReview).all()
        review_data = [{
            "document_id": r.document_id,
            "record_type": r.record_type,
            "record_id": r.record_id,
            "field_name": r.field_name,
            "ai_value": r.ai_value,
            "human_value": r.human_value,
            "decision": r.decision,
            "reviewer": r.reviewer,
            "reviewer_comment": r.reviewer_comment,
            "reviewed_at": r.reviewed_at,
        } for r in reviews]

        # 07_DIGITIZATION_TASKS
        dig_tasks = session.query(DigitizationTask).all()
        dig_data = [{
            "document_id": d.document_id,
            "outcome_id": d.outcome_id,
            "page": d.page,
            "figure_label": d.figure_label,
            "reason": d.reason,
            "status": d.status,
            "digitized_value": d.digitized_value,
            "digitized_unit": d.digitized_unit,
        } for d in dig_tasks]

    # Create Excel
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        # 00_README
        readme_df = pd.DataFrame({
            "Instructions": [
                "This file contains extracted data for human review.",
                "Review the 03_OUTCOMES sheet and fill in:",
                "  - human_decision: accepted / corrected / rejected / unclear",
                "  - human_value: corrected value if needed",
                "  - human_unit: corrected unit if needed",
                "  - reviewer: your name",
                "  - reviewer_comment: any notes",
                "",
                "Do NOT modify AI-generated columns.",
                "Save this file and run: python scripts/06_import_human_review.py",
            ]
        })
        readme_df.to_excel(writer, sheet_name="00_README", index=False)

        pd.DataFrame(docs_data).to_excel(writer, sheet_name="01_DOCUMENTS", index=False)
        pd.DataFrame(scenarios_data).to_excel(writer, sheet_name="02_SCENARIOS", index=False)
        pd.DataFrame(outcomes_data).to_excel(writer, sheet_name="03_OUTCOMES", index=False)
        pd.DataFrame(evidence_data).to_excel(writer, sheet_name="04_EVIDENCE", index=False)
        pd.DataFrame(qa_data).to_excel(writer, sheet_name="05_QA_LOG", index=False)
        pd.DataFrame(review_data).to_excel(writer, sheet_name="06_HUMAN_REVIEW", index=False)
        pd.DataFrame(dig_data).to_excel(writer, sheet_name="07_DIGITIZATION_TASKS", index=False)

    console.print(f"[green]✓[/green] Review Excel exported: {output_path}")
    logger.info(f"Review Excel exported: {output_path}")
    return output_path
