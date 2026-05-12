"""Script 04: Validate outputs for a document."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.paths import get_document_ai_output_dir
from src.validation.schema_validator import TASK_SCHEMA_MAP, validate_json_file

REQUIRED_TASKS = set(TASK_SCHEMA_MAP.keys())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate AI outputs")
    parser.add_argument("--document", "-d", required=True, help="Document code")
    args = parser.parse_args()

    output_dir = get_document_ai_output_dir(args.document)
    all_valid = True

    for task_type, schema_name in TASK_SCHEMA_MAP.items():
        json_file = output_dir / schema_name.replace(".schema.json", ".json")
        if json_file.exists():
            result = validate_json_file(json_file, schema_name)
            status = "OK" if result else "FAIL"
            print(f"  {status} {json_file.name}")
            if not result:
                all_valid = False
                for err in result.errors:
                    print(f"    {err}")
        else:
            if task_type in REQUIRED_TASKS:
                all_valid = False
                print(f"  FAIL {json_file.name} (not found)")
            else:
                print(f"  SKIP {json_file.name} (not found)")

    if all_valid:
        print(f"\nAll validations passed for {args.document}.")
    else:
        print(f"\nValidation failed for {args.document}.")
        sys.exit(1)
