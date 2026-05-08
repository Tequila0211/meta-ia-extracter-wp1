"""Script 05: Export review Excel."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.export.export_review_excel import export_review_excel

if __name__ == "__main__":
    export_review_excel()
