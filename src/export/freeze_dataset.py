"""
Dataset freezing.

Exports only validated data to CSV/XLSX with manifest and changelog.
"""

import json
from pathlib import Path

import pandas as pd
from rich.console import Console

from src.database.db import DatabaseManager
from src.database.models import Document, Outcome, Scenario
from src.utils.hashing import compute_sha256
from src.utils.logging_config import get_logger
from src.utils.paths import get_frozen_datasets_path
from src.utils.timestamps import now_iso
from src.validation.codebook_validator import load_codebook

logger = get_logger("export")
console = Console()


def freeze_dataset(version: str) -> dict:
    """Freeze validated data into a versioned dataset.

    Creates:
    - data_frozen_{version}.xlsx
    - data_frozen_{version}.csv
    - changelog_{version}.md
    - manifest_{version}.json

    Args:
        version: Version string (e.g., 'v01').

    Returns:
        Manifest dict.
    """
    output_dir = get_frozen_datasets_path()
    output_dir.mkdir(parents=True, exist_ok=True)

    with DatabaseManager() as session:
        # Get validated documents
        docs = (
            session.query(Document)
            .filter(Document.status == "validated")
            .order_by(Document.document_code)
            .all()
        )

        # Get validated outcomes
        validated_outcomes = (
            session.query(Outcome)
            .filter(Outcome.human_validated == 1)
            .all()
        )

        # Build data
        outcomes_data = []
        for o in validated_outcomes:
            doc = session.query(Document).filter(Document.id == o.document_id).first()
            scenario = session.query(Scenario).filter(Scenario.id == o.scenario_id).first() if o.scenario_id else None

            outcomes_data.append({
                "document_code": doc.document_code if doc else "",
                "scenario_code": scenario.scenario_code if scenario else "",
                "scenario_label": scenario.scenario_label if scenario else "",
                "building_typology": scenario.building_typology if scenario else "",
                "climate_location": scenario.climate_location if scenario else "",
                "outcome_name": o.outcome_name,
                "baseline_value": o.baseline_value,
                "baseline_unit": o.baseline_unit,
                "intervention_value": o.intervention_value,
                "intervention_unit": o.intervention_unit,
                "reported_effect_value": o.reported_effect_value,
                "reported_effect_unit": o.reported_effect_unit,
                "effect_direction": o.effect_direction,
                "standardized_baseline_value": o.standardized_baseline_value,
                "standardized_intervention_value": o.standardized_intervention_value,
                "standardized_unit": o.standardized_unit,
                "source_type": o.source_type,
                "page": o.page,
                "status": o.status,
                "human_validated": True,
            })

    df = pd.DataFrame(outcomes_data)

    # Export CSV
    csv_path = output_dir / f"data_frozen_{version}.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8")

    # Export XLSX
    xlsx_path = output_dir / f"data_frozen_{version}.xlsx"
    df.to_excel(xlsx_path, index=False, engine="openpyxl")

    # Create changelog
    changelog_path = output_dir / f"changelog_{version}.md"
    changelog_content = f"""# Changelog — {version}

## Date
{now_iso()}

## Summary
- Documents: {len(docs)}
- Validated outcomes: {len(validated_outcomes)}

## Notes
Initial frozen dataset.
"""
    changelog_path.write_text(changelog_content, encoding="utf-8")

    # Compute hash of CSV
    csv_hash = compute_sha256(csv_path) if csv_path.exists() else ""

    # Load codebook version
    codebook = load_codebook()
    codebook_version = codebook.get("codebook", {}).get("version", "unknown")

    # Load prompts version
    from src.ai.prompt_loader import get_prompt_loader
    loader = get_prompt_loader()
    prompts_version = loader.prompts_version

    # Create manifest
    manifest = {
        "dataset_version": version,
        "created_at": now_iso(),
        "codebook_version": codebook_version,
        "prompts_version": prompts_version,
        "schemas": [
            "classification.schema.json",
            "mapping.schema.json",
            "scenario_extraction.schema.json",
            "outcome_extraction.schema.json",
            "audit.schema.json",
        ],
        "number_of_documents": len(docs),
        "number_of_validated_outcomes": len(validated_outcomes),
        "hash": csv_hash,
    }

    manifest_path = output_dir / f"manifest_{version}.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    console.print(f"[green]✓[/green] Dataset frozen: {version}")
    console.print(f"  Documents: {len(docs)}")
    console.print(f"  Validated outcomes: {len(validated_outcomes)}")
    console.print(f"  Files: {csv_path.name}, {xlsx_path.name}, {changelog_path.name}, {manifest_path.name}")

    logger.info(f"Dataset frozen: {version}, {len(docs)} docs, {len(validated_outcomes)} outcomes")
    return manifest
