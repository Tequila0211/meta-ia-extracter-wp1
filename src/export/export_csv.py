"""
CSV export utility.
"""

from pathlib import Path

import pandas as pd
from rich.console import Console

from src.database.db import DatabaseManager
from src.database.models import Document, Outcome, Scenario

console = Console()


def export_outcomes_csv(output_path: str | Path) -> Path:
    """Export outcomes to CSV.

    Args:
        output_path: Path for the CSV file.

    Returns:
        Path to the created CSV file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with DatabaseManager() as session:
        outcomes = session.query(Outcome).all()
        data = []
        for o in outcomes:
            doc = session.query(Document).filter(Document.id == o.document_id).first()
            scenario = session.query(Scenario).filter(Scenario.id == o.scenario_id).first() if o.scenario_id else None
            data.append({
                "document_code": doc.document_code if doc else "",
                "scenario_code": scenario.scenario_code if scenario else "",
                "outcome_name": o.outcome_name,
                "value": o.value,
                "unit": o.unit,
                "reported_effect_value": o.reported_effect_value,
                "reported_effect_unit": o.reported_effect_unit,
                "effect_direction": o.effect_direction,
                "status": o.status,
                "human_validated": bool(o.human_validated),
            })

    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False, encoding="utf-8")
    console.print(f"[green]✓[/green] CSV exported: {output_path}")
    return output_path
