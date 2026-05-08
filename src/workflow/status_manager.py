"""
Status manager — displays document processing status.
"""

from rich.console import Console
from rich.table import Table

from src.database.db import DatabaseManager
from src.database.repository import get_all_documents

console = Console()


def show_status():
    """Display the status of all registered documents."""
    with DatabaseManager() as session:
        docs = get_all_documents(session)

    if not docs:
        console.print("[yellow]No documents registered yet.[/yellow]")
        console.print("Run: python scripts/01_register_pdfs.py")
        return

    table = Table(title="Project Status")
    table.add_column("Code", style="cyan", no_wrap=True)
    table.add_column("Status", style="green")
    table.add_column("Step", style="yellow")
    table.add_column("File", style="dim")

    status_counts = {}
    for doc in docs:
        status = doc.status
        status_counts[status] = status_counts.get(status, 0) + 1

        color = _get_color(status)
        table.add_row(
            doc.document_code,
            f"[{color}]{status}[/{color}]",
            doc.current_step or "—",
            doc.file_name,
        )

    console.print(table)

    # Summary
    console.print(f"\n[bold]Summary:[/bold] {len(docs)} documents")
    for status, count in sorted(status_counts.items()):
        color = _get_color(status)
        console.print(f"  [{color}]{status}[/{color}]: {count}")


def _get_color(status: str) -> str:
    """Get a color for a status value."""
    colors = {
        "pending": "yellow",
        "preprocessed": "blue",
        "classified": "blue",
        "mapped": "blue",
        "scenarios_extracted": "blue",
        "outcomes_extracted": "blue",
        "audited": "cyan",
        "needs_human_review": "magenta",
        "validated": "green",
        "failed": "red",
        "not_extractable": "dim",
    }
    return colors.get(status, "white")
