"""Script 08: Show project status."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.workflow.status_manager import show_status

if __name__ == "__main__":
    show_status()
