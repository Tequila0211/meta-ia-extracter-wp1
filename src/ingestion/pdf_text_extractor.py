"""
PDF text extraction using PyMuPDF.

Extracts text from each page and saves as individual .txt files.
"""

from pathlib import Path

import pymupdf  # PyMuPDF

from src.utils.logging_config import get_logger

logger = get_logger("ingestion")


def extract_text_from_pdf(
    pdf_path: str | Path,
    output_dir: str | Path,
) -> list[dict]:
    """Extract text from each page of a PDF.

    Args:
        pdf_path: Path to the PDF file.
        output_dir: Directory to save page text files.

    Returns:
        List of dicts with page info (page_number, text_path, char_count).
    """
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir) / "pages_text"
    output_dir.mkdir(parents=True, exist_ok=True)

    pages_info = []

    doc = pymupdf.open(str(pdf_path))
    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")

            # Save page text
            page_file = output_dir / f"page_{page_num + 1:03d}.txt"
            page_file.write_text(text, encoding="utf-8")

            pages_info.append({
                "page_number": page_num + 1,
                "text_path": str(page_file),
                "char_count": len(text),
            })

            logger.debug(f"Extracted text from page {page_num + 1}: {len(text)} chars")
    finally:
        doc.close()

    logger.info(f"Extracted text from {len(pages_info)} pages of {pdf_path.name}")
    return pages_info


def get_full_text(pdf_path: str | Path) -> str:
    """Extract full concatenated text from a PDF.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Full text content of the PDF.
    """
    doc = pymupdf.open(str(pdf_path))
    try:
        text_parts = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            text_parts.append(f"--- PAGE {page_num + 1} ---\n{text}")
        return "\n\n".join(text_parts)
    finally:
        doc.close()
