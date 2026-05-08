"""
Register PDFs from the raw PDFs directory into the database.

Scans data/00_raw_pdfs/, assigns document codes (A001, A002, ...),
computes SHA-256 hashes, and inserts records into the documents table.
Skips duplicates based on file hash.
"""

from pathlib import Path

from rich.console import Console
from rich.table import Table

from src.database.db import DatabaseManager
from src.database.repository import (
    get_all_documents,
    get_document_by_hash,
    get_next_document_code,
    insert_document,
)
from src.utils.hashing import compute_sha256
from src.utils.logging_config import get_logger
from src.utils.paths import get_raw_pdfs_path, load_project_config

logger = get_logger("ingestion")
console = Console()


def register_pdfs(raw_pdfs_dir: Path | None = None) -> list[dict]:
    """Register all PDFs in the raw PDFs directory.

    Args:
        raw_pdfs_dir: Optional override for the raw PDFs directory.

    Returns:
        List of dicts with registration results.
    """
    config = load_project_config()
    pdfs_dir = raw_pdfs_dir or get_raw_pdfs_path()
    allowed_extensions = config["documents"]["allowed_extensions"]
    prefix = config["documents"]["document_code_prefix"]
    padding = config["documents"]["document_code_padding"]

    # Find all PDF files
    pdf_files = sorted(
        f for f in pdfs_dir.iterdir()
        if f.is_file() and f.suffix.lower() in allowed_extensions
    )

    if not pdf_files:
        console.print("[yellow]No PDF files found in[/yellow]", str(pdfs_dir))
        return []

    results = []

    with DatabaseManager() as session:
        for pdf_path in pdf_files:
            file_hash = compute_sha256(pdf_path)

            # Check for duplicates by hash
            existing = get_document_by_hash(session, file_hash)
            if existing:
                results.append({
                    "file": pdf_path.name,
                    "code": existing.document_code,
                    "status": "skipped (duplicate)",
                })
                logger.info(f"Skipped duplicate: {pdf_path.name} → {existing.document_code}")
                continue

            # Assign next document code
            doc_code = get_next_document_code(session, prefix, padding)

            # Insert document
            doc = insert_document(
                session=session,
                document_code=doc_code,
                file_name=pdf_path.name,
                file_path=str(pdf_path.resolve()),
                file_hash=file_hash,
                status="pending",
            )

            results.append({
                "file": pdf_path.name,
                "code": doc.document_code,
                "status": "registered",
            })
            logger.info(f"Registered: {pdf_path.name} → {doc.document_code}")

    # Display results
    _display_results(results)
    return results


def show_registered_documents() -> None:
    """Display all registered documents."""
    with DatabaseManager() as session:
        docs = get_all_documents(session)
        if not docs:
            console.print("[yellow]No documents registered yet.[/yellow]")
            return

        table = Table(title="Registered Documents")
        table.add_column("Code", style="cyan")
        table.add_column("File", style="white")
        table.add_column("Status", style="green")
        table.add_column("Current Step", style="yellow")

        for doc in docs:
            table.add_row(
                doc.document_code,
                doc.file_name,
                doc.status,
                doc.current_step or "—",
            )

        console.print(table)


def _display_results(results: list[dict]) -> None:
    """Display registration results in a table."""
    table = Table(title="PDF Registration Results")
    table.add_column("File", style="white")
    table.add_column("Code", style="cyan")
    table.add_column("Status", style="green")

    for r in results:
        status_style = "green" if r["status"] == "registered" else "yellow"
        table.add_row(r["file"], r["code"], f"[{status_style}]{r['status']}[/{status_style}]")

    console.print(table)
