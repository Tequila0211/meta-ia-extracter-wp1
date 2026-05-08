"""Script 00: Initialize project — create directories and database."""

import sys
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.init_db import init_database

if __name__ == "__main__":
    # Create data directories
    dirs = [
        "data/00_raw_pdfs", "data/01_processed", "data/02_ai_outputs",
        "data/03_human_review", "data/04_frozen_datasets", "data/05_logs",
    ]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
        print(f"  ✓ {d}")

    # Initialize database
    init_database()
