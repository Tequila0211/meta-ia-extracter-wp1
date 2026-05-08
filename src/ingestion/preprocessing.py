"""
PDF preprocessing orchestrator.

Coordinates text extraction and page rendering for a document.
Creates metadata.json and inserts page records into the database.
"""

import json
from pathlib import Path

from rich.console import Console

from src.database.db import DatabaseManager
from src.database.repository import (
    get_document_by_code,
    insert_page,
    update_document_status,
)
from src.ingestion.pdf_renderer import render_pages_as_images
from src.ingestion.pdf_text_extractor import extract_text_from_pdf
from src.utils.logging_config import get_logger
from src.utils.paths import get_document_processed_dir
from src.utils.timestamps import now_iso

logger = get_logger("ingestion")
console = Console()

# Threshold for possible non-digital PDFs (scanned documents)
MIN_CHARS_PER_PAGE = 50


def preprocess_document(document_code: str) -> dict:
    """Preprocess a registered document.

    Steps:
    1. Extract text per page.
    2. Render pages as PNG images.
    3. Create metadata.json.
    4. Insert page records into DB.
    5. Update document status to 'preprocessed'.

    Args:
        document_code: Document code (e.g., 'A001').

    Returns:
        Metadata dict for the document.

    Raises:
        ValueError: If document is not registered.
        FileNotFoundError: If PDF file doesn't exist.
    """
    with DatabaseManager() as session:
        doc = get_document_by_code(session, document_code)
        if not doc:
            raise ValueError(f"Document {document_code} is not registered.")

        pdf_path = Path(doc.file_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        # Output directory
        output_dir = get_document_processed_dir(document_code)

        console.print(f"[blue]Preprocessing {document_code}...[/blue]")

        # Step 1: Extract text
        console.print("  Extracting text...")
        text_pages = extract_text_from_pdf(pdf_path, output_dir)

        # Step 2: Render images
        console.print("  Rendering pages as images...")
        image_pages = render_pages_as_images(pdf_path, output_dir)

        # Step 3: Create metadata
        total_chars = sum(p["char_count"] for p in text_pages)
        num_pages = len(text_pages)
        has_text = total_chars > 0
        possible_non_digital = (
            has_text and (total_chars / max(num_pages, 1)) < MIN_CHARS_PER_PAGE
        )

        metadata = {
            "document_id": document_code,
            "file_name": doc.file_name,
            "number_of_pages": num_pages,
            "total_characters": total_chars,
            "has_text": has_text,
            "possible_non_digital": possible_non_digital,
            "processed_at": now_iso(),
        }

        metadata_path = output_dir / "metadata.json"
        metadata_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # Step 4: Insert page records
        # Build image path lookup
        image_lookup = {p["page_number"]: p["image_path"] for p in image_pages}

        for page_info in text_pages:
            page_num = page_info["page_number"]
            insert_page(
                session=session,
                document_id=doc.id,
                page_number=page_num,
                text_path=page_info["text_path"],
                image_path=image_lookup.get(page_num),
                text_char_count=page_info["char_count"],
            )

        # Step 5: Update document status
        update_document_status(session, doc.id, "preprocessed", "preprocessing")

        console.print(f"[green]✓[/green] {document_code} preprocessed:")
        console.print(f"  Pages: {num_pages}")
        console.print(f"  Total characters: {total_chars}")
        if possible_non_digital:
            console.print(
                "[yellow]  ⚠ Low text content — possible scanned/non-digital PDF[/yellow]"
            )

        logger.info(
            f"Preprocessed {document_code}: {num_pages} pages, {total_chars} chars"
        )

        return metadata
