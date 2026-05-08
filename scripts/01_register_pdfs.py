"""Script 01: Register PDFs from data/00_raw_pdfs/."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ingestion.register_pdfs import register_pdfs

if __name__ == "__main__":
    register_pdfs()
