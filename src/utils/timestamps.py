"""
Timestamp utilities.
"""

from datetime import datetime, timezone


def now_iso() -> str:
    """Get current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def now_local_iso() -> str:
    """Get current local timestamp in ISO 8601 format."""
    return datetime.now().isoformat()
