"""Verify regex matching for figures in preprocessed page texts."""
import re
from pathlib import Path

txt_dir = Path("data/01_processed/A001/pages_text")
files = sorted(list(txt_dir.glob("*.txt")))

# Use a corrected regex pattern that handles the optional period safely
pattern = re.compile(r"\b(figure|fig|figura)\b\.?\s*\d+", re.IGNORECASE)

for f in files:
    content = f.read_text(encoding="utf-8")
    matches = pattern.findall(content)
    if matches:
        print(f"{f.name}: matched={matches}")
