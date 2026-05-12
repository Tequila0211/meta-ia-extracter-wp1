"""
CLI — Command-line interface using Typer.

All commands per PRD §21.
"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

app = typer.Typer(
    name="meta-pipeline",
    help="Meta AI Extraction Pipeline — CLI for systematic review data extraction.",
    add_completion=False,
)
console = Console()


@app.command()
def init():
    """Initialize project: create directories and database."""
    from src.database.init_db import init_database

    # Ensure data directories exist
    dirs = [
        "data/00_raw_pdfs", "data/01_processed", "data/02_ai_outputs",
        "data/03_human_review", "data/04_frozen_datasets", "data/05_logs",
    ]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)

    init_database()
    console.print("[green]✓[/green] Project initialized.")


@app.command()
def register():
    """Register PDFs from data/00_raw_pdfs/."""
    from src.ingestion.register_pdfs import register_pdfs
    register_pdfs()


@app.command()
def preprocess(
    document: str = typer.Option(..., "--document", "-d", help="Document code (e.g., A001)"),
):
    """Preprocess a document (extract text + render pages)."""
    from src.ingestion.preprocessing import preprocess_document
    preprocess_document(document)


@app.command()
def process(
    document: Optional[str] = typer.Option(None, "--document", "-d", help="Document code (e.g., A001)"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactive mode"),
):
    """Process an article through the full extraction pipeline."""
    if interactive:
        from src.workflow.resume_manager import run_interactive_mode
        run_interactive_mode()
    elif document:
        from src.workflow.article_workflow import process_article
        result = process_article(document)
        if result["errors"]:
            console.print(f"\n[yellow]Issues:[/yellow]")
            for err in result["errors"]:
                console.print(f"  • {err}")
    else:
        console.print("[red]Specify --document or --interactive[/red]")
        raise typer.Exit(1)


@app.command()
def validate(
    document: str = typer.Option(..., "--document", "-d", help="Document code"),
):
    """Validate outputs for a document."""
    from src.utils.paths import get_document_ai_output_dir
    from src.validation.schema_validator import TASK_SCHEMA_MAP, validate_json_file

    output_dir = get_document_ai_output_dir(document)
    all_valid = True
    required_tasks = set(TASK_SCHEMA_MAP.keys())

    for task_type, schema_name in TASK_SCHEMA_MAP.items():
        json_file = output_dir / schema_name.replace(".schema.json", ".json")
        if json_file.exists():
            result = validate_json_file(json_file, schema_name)
            status = "[green]OK[/green]" if result else "[red]FAIL[/red]"
            console.print(f"  {status} {json_file.name}")
            if not result:
                all_valid = False
                for err in result.errors:
                    console.print(f"    {err}")
        else:
            if task_type in required_tasks:
                all_valid = False
                console.print(f"  [red]FAIL[/red] {json_file.name} (not found)")
            else:
                console.print(f"  [dim]SKIP {json_file.name} (not found)[/dim]")

    if all_valid:
        console.print(f"\n[green]All validations passed for {document}.[/green]")
    else:
        console.print(f"\n[red]Validation failed for {document}.[/red]")
        raise typer.Exit(1)


@app.command(name="export-review")
def export_review():
    """Export review Excel for human review."""
    from src.export.export_review_excel import export_review_excel
    export_review_excel()


@app.command(name="import-review")
def import_review(
    file: str = typer.Option(
        "data/03_human_review/extraction_review.xlsx",
        "--file", "-f",
        help="Path to reviewed Excel file",
    ),
):
    """Import human review decisions from Excel."""
    from src.export.import_human_review import import_human_review
    import_human_review(file)


@app.command()
def freeze(
    version: str = typer.Option(..., "--version", "-v", help="Dataset version (e.g., v01)"),
):
    """Freeze validated dataset."""
    from src.export.freeze_dataset import freeze_dataset
    freeze_dataset(version)


@app.command()
def status():
    """Show project status."""
    from src.workflow.status_manager import show_status
    show_status()


if __name__ == "__main__":
    app()
