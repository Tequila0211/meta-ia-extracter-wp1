"""Script 06: Import human review from Excel."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.export.import_human_review import import_human_review

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import human review")
    parser.add_argument(
        "--file", "-f",
        default="data/03_human_review/extraction_review.xlsx",
        help="Path to reviewed Excel file",
    )
    args = parser.parse_args()

    import_human_review(args.file)
