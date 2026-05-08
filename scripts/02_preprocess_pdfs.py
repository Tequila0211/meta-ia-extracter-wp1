"""Script 02: Preprocess PDFs — extract text and render pages."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ingestion.preprocessing import preprocess_document

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Preprocess a PDF document")
    parser.add_argument("--document", "-d", required=True, help="Document code (e.g., A001)")
    args = parser.parse_args()

    preprocess_document(args.document)
