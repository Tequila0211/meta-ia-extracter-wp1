"""
Interactive resume manager.

Allows the researcher to:
- See all document statuses
- Choose where to continue from
- Choose how many articles to process
- Pause after each article
"""

from rich.console import Console
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

from src.database.db import DatabaseManager
from src.database.repository import get_all_documents
from src.export.export_review_excel import export_review_excel
from src.utils.logging_config import get_logger
from src.workflow.article_workflow import process_article

logger = get_logger("workflow")
console = Console()


def run_interactive_mode():
    """Run the interactive article processing mode.

    Shows document status, asks where to continue from,
    processes articles sequentially with pause after each.
    """
    # Show current status
    with DatabaseManager() as session:
        docs = get_all_documents(session)

    if not docs:
        console.print("[yellow]No documents registered. Run: python scripts/01_register_pdfs.py[/yellow]")
        return

    # Display status table
    table = Table(title="Detected documents")
    table.add_column("Code", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("File", style="dim")

    for doc in docs:
        status_color = _get_status_color(doc.status)
        table.add_row(
            doc.document_code,
            f"[{status_color}]{doc.status}[/{status_color}]",
            doc.file_name,
        )

    console.print(table)
    console.print()

    # Ask where to continue from
    doc_codes = [d.document_code for d in docs]
    start_code = Prompt.ask(
        "Where do you want to continue from?",
        default=_get_first_pending(docs),
    )

    if start_code not in doc_codes:
        console.print(f"[red]Document {start_code} not found.[/red]")
        return

    # Ask how many articles
    start_idx = doc_codes.index(start_code)
    remaining = len(doc_codes) - start_idx
    count = IntPrompt.ask(
        f"How many articles do you want to process this session?",
        default=min(1, remaining),
    )

    # Build processing list
    to_process = doc_codes[start_idx : start_idx + count]

    console.print(f"\n[bold]The system will process:[/bold]")
    console.print(", ".join(to_process))
    console.print()

    if not Confirm.ask("Continue?", default=True):
        console.print("Cancelled.")
        return

    # Process articles
    for i, code in enumerate(to_process, 1):
        console.print(f"\n{'='*60}")
        console.print(f"[bold]Processing {code} ({i}/{len(to_process)})[/bold]")
        console.print(f"{'='*60}")

        result = process_article(code)

        console.print(f"\n{code} completed.")
        console.print(f"Status: {result['final_status']}")

        # After each article, show options
        if i < len(to_process):
            console.print(f"\n[bold]Options:[/bold]")
            console.print(f"  1. Continue to {to_process[i]}")
            console.print(f"  2. Stop here")
            console.print(f"  3. Export review Excel")
            console.print(f"  4. Show issues")

            choice = Prompt.ask("Choose", choices=["1", "2", "3", "4"], default="1")

            if choice == "2":
                console.print("Stopped.")
                break
            elif choice == "3":
                export_review_excel()
                if not Confirm.ask("Continue processing?", default=True):
                    break
            elif choice == "4":
                _show_issues(result)
                if not Confirm.ask("Continue processing?", default=True):
                    break
            # choice == "1": continue

    console.print(f"\n[green]Session complete.[/green]")


def _get_first_pending(docs) -> str:
    """Get the first pending document code."""
    for doc in docs:
        if doc.status == "pending":
            return doc.document_code
    return docs[0].document_code if docs else "A001"


def _get_status_color(status: str) -> str:
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


def _show_issues(result: dict):
    """Display issues from a processing result."""
    if result.get("errors"):
        console.print("\n[yellow]Issues:[/yellow]")
        for err in result["errors"]:
            console.print(f"  • {err}")
    else:
        console.print("[green]No issues found.[/green]")
