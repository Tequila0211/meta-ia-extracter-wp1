"""
File hashing utilities.
"""

import hashlib
from pathlib import Path


def compute_sha256(file_path: str | Path) -> str:
    """Compute SHA-256 hash of a file.

    Args:
        file_path: Path to the file.

    Returns:
        Hex digest of the SHA-256 hash.
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def compute_text_hash(text: str) -> str:
    """Compute SHA-256 hash of a text string.

    Args:
        text: Input text.

    Returns:
        Hex digest of the SHA-256 hash.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
