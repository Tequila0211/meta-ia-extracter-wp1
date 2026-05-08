"""
PDF page rendering using PyMuPDF.

Renders each page as a PNG image for evidence and multimodal AI input.
"""

from pathlib import Path

import pymupdf  # PyMuPDF

from src.utils.logging_config import get_logger

logger = get_logger("ingestion")


def render_pages_as_images(
    pdf_path: str | Path,
    output_dir: str | Path,
    dpi: int = 200,
) -> list[dict]:
    """Render each page of a PDF as a PNG image.

    Args:
        pdf_path: Path to the PDF file.
        output_dir: Directory to save page images.
        dpi: Resolution for rendering (default: 200 DPI).

    Returns:
        List of dicts with page info (page_number, image_path).
    """
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir) / "pages_images"
    output_dir.mkdir(parents=True, exist_ok=True)

    pages_info = []
    zoom = dpi / 72  # PyMuPDF default is 72 DPI

    doc = pymupdf.open(str(pdf_path))
    try:
        for page_num in range(len(doc)):
            page = doc[page_num]

            # Render at specified DPI
            mat = pymupdf.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            # Save as PNG
            image_path = output_dir / f"page_{page_num + 1:03d}.png"
            pix.save(str(image_path))

            pages_info.append({
                "page_number": page_num + 1,
                "image_path": str(image_path),
            })

            logger.debug(f"Rendered page {page_num + 1} as image: {image_path.name}")
    finally:
        doc.close()

    logger.info(f"Rendered {len(pages_info)} pages as images from {pdf_path.name}")
    return pages_info
