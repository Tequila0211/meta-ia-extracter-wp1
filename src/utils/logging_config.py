"""
Logging configuration for the pipeline.

Creates four log files in data/05_logs/:
- pipeline.log (general pipeline activity)
- errors.log (errors only)
- ai_calls.log (AI API call details)
- validation.log (validation results)
"""

import logging
from pathlib import Path

from src.utils.paths import get_logs_path


_configured = False


def setup_logging(level: str = "INFO") -> None:
    """Configure logging for the pipeline.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR).
    """
    global _configured
    if _configured:
        return

    logs_dir = get_logs_path()
    logs_dir.mkdir(parents=True, exist_ok=True)

    log_level = getattr(logging, level.upper(), logging.INFO)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Format
    fmt = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(fmt)
    root_logger.addHandler(console_handler)

    # Pipeline log
    pipeline_handler = logging.FileHandler(logs_dir / "pipeline.log", encoding="utf-8")
    pipeline_handler.setLevel(log_level)
    pipeline_handler.setFormatter(fmt)
    root_logger.addHandler(pipeline_handler)

    # Errors log
    error_handler = logging.FileHandler(logs_dir / "errors.log", encoding="utf-8")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(fmt)
    root_logger.addHandler(error_handler)

    # AI calls log
    ai_logger = logging.getLogger("ai_calls")
    ai_handler = logging.FileHandler(logs_dir / "ai_calls.log", encoding="utf-8")
    ai_handler.setLevel(logging.DEBUG)
    ai_handler.setFormatter(fmt)
    ai_logger.addHandler(ai_handler)

    # Validation log
    val_logger = logging.getLogger("validation")
    val_handler = logging.FileHandler(logs_dir / "validation.log", encoding="utf-8")
    val_handler.setLevel(logging.DEBUG)
    val_handler.setFormatter(fmt)
    val_logger.addHandler(val_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Get a named logger, ensuring logging is configured.

    Args:
        name: Logger name (e.g., 'ai_calls', 'validation', 'ingestion').
    """
    setup_logging()
    return logging.getLogger(name)
