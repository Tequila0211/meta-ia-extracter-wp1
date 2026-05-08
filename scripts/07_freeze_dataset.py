"""Script 07: Freeze validated dataset."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.export.freeze_dataset import freeze_dataset

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Freeze dataset")
    parser.add_argument("--version", "-v", required=True, help="Version (e.g., v01)")
    args = parser.parse_args()

    freeze_dataset(args.version)
