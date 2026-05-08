"""Script 03: Process article — full pipeline or interactive mode."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.workflow.article_workflow import process_article
from src.workflow.resume_manager import run_interactive_mode

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process articles")
    parser.add_argument("--document", "-d", help="Document code (e.g., A001)")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    args = parser.parse_args()

    if args.interactive:
        run_interactive_mode()
    elif args.document:
        result = process_article(args.document)
        if result["errors"]:
            print(f"\nIssues:")
            for err in result["errors"]:
                print(f"  • {err}")
    else:
        print("Specify --document or --interactive")
        sys.exit(1)
