"""
Project path resolution helpers.
"""

from pathlib import Path

import yaml


def get_project_root() -> Path:
    """Get the project root directory (where pyproject.toml lives)."""
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


def load_project_config() -> dict:
    """Load the project configuration YAML."""
    config_path = get_project_root() / "config" / "project_config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_data_path(subdir: str) -> Path:
    """Get a data subdirectory path.

    Args:
        subdir: Key from paths config (e.g., 'raw_pdfs', 'processed').
    """
    config = load_project_config()
    relative_path = config["paths"].get(subdir, f"data/{subdir}")
    path = get_project_root() / relative_path
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_raw_pdfs_path() -> Path:
    """Get the raw PDFs directory path."""
    return get_data_path("raw_pdfs")


def get_processed_path() -> Path:
    """Get the processed data directory path."""
    return get_data_path("processed")


def get_ai_outputs_path() -> Path:
    """Get the AI outputs directory path."""
    return get_data_path("ai_outputs")


def get_human_review_path() -> Path:
    """Get the human review directory path."""
    return get_data_path("human_review")


def get_frozen_datasets_path() -> Path:
    """Get the frozen datasets directory path."""
    return get_data_path("frozen_datasets")


def get_logs_path() -> Path:
    """Get the logs directory path."""
    return get_data_path("logs")


def get_document_processed_dir(document_code: str) -> Path:
    """Get the processed directory for a specific document."""
    path = get_processed_path() / document_code
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_document_ai_output_dir(document_code: str) -> Path:
    """Get the AI output directory for a specific document."""
    path = get_ai_outputs_path() / document_code
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_schemas_dir() -> Path:
    """Get the schemas directory path."""
    return get_project_root() / "schemas"


def get_prompts_path() -> Path:
    """Get the prompts YAML path."""
    return get_project_root() / "prompts" / "prompts.yaml"


def get_codebook_path() -> Path:
    """Get the codebook YAML path."""
    return get_project_root() / "config" / "codebook.yaml"


def get_extraction_rules_path() -> Path:
    """Get the extraction rules YAML path."""
    return get_project_root() / "config" / "extraction_rules.yaml"


def get_controlled_vocabularies_path() -> Path:
    """Get the controlled vocabularies YAML path."""
    return get_project_root() / "config" / "controlled_vocabularies.yaml"
