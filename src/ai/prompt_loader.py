"""
Prompt and schema loader.

Loads prompts from prompts/prompts.yaml and schemas from schemas/.
Never hardcodes prompts in Python.
"""

import json
from pathlib import Path
from typing import Any

import yaml

from src.utils.logging_config import get_logger
from src.utils.paths import (
    get_codebook_path,
    get_prompts_path,
    get_schemas_dir,
)

logger = get_logger("ai_calls")


class PromptLoader:
    """Loads and manages prompts and schemas."""

    def __init__(self):
        self._prompts: dict | None = None
        self._codebook: dict | None = None
        self._schemas: dict[str, dict] = {}

    @property
    def prompts(self) -> dict:
        """Load prompts from YAML (cached)."""
        if self._prompts is None:
            prompts_path = get_prompts_path()
            with open(prompts_path, "r", encoding="utf-8") as f:
                self._prompts = yaml.safe_load(f)
            logger.info(f"Loaded prompts v{self._prompts.get('prompts_version', '?')}")
        return self._prompts

    @property
    def prompts_version(self) -> str:
        """Get the prompts version."""
        return self.prompts.get("prompts_version", "unknown")

    @property
    def codebook(self) -> dict:
        """Load codebook from YAML (cached)."""
        if self._codebook is None:
            codebook_path = get_codebook_path()
            with open(codebook_path, "r", encoding="utf-8") as f:
                self._codebook = yaml.safe_load(f)
            logger.info(f"Loaded codebook v{self._codebook.get('codebook', {}).get('version', '?')}")
        return self._codebook

    @property
    def codebook_version(self) -> str:
        """Get the codebook version."""
        return self.codebook.get("codebook", {}).get("version", "unknown")

    def get_system_prompt(self) -> str:
        """Get the global system prompt."""
        return self.prompts["global_system_prompt"]

    def get_task_prompt(self, task_type: str) -> str:
        """Get the prompt for a specific task.

        Args:
            task_type: One of 'classification', 'mapping', 'scenario_extraction',
                       'outcome_extraction', 'audit'.
        """
        key = f"{task_type}_prompt"
        prompt = self.prompts.get(key)
        if not prompt:
            raise ValueError(f"Prompt not found for task: {task_type}")
        return prompt

    def get_enriched_prompt(self, task_type: str, document_id: str) -> str:
        """Get a task prompt enriched with codebook context.

        Args:
            task_type: Task type.
            document_id: Document identifier to inject.
        """
        prompt = self.get_task_prompt(task_type)

        # Add codebook context for tasks that need it
        if task_type in ("classification", "scenario_extraction", "outcome_extraction"):
            codebook_context = self._format_codebook_context()
            prompt = f"{prompt}\n\nCODEBOOK DEFINITIONS:\n{codebook_context}"

        # Add document_id instruction
        prompt = f"{prompt}\n\nDOCUMENT_ID: {document_id}\nInclude this document_id in your JSON response."

        return prompt

    def load_schema(self, schema_name: str) -> dict:
        """Load a JSON schema from the schemas directory.

        Args:
            schema_name: Schema filename (e.g., 'classification.schema.json').

        Returns:
            Parsed JSON schema as dict.
        """
        if schema_name not in self._schemas:
            schema_path = get_schemas_dir() / schema_name
            if not schema_path.exists():
                raise FileNotFoundError(f"Schema not found: {schema_path}")
            with open(schema_path, "r", encoding="utf-8") as f:
                self._schemas[schema_name] = json.load(f)
            logger.debug(f"Loaded schema: {schema_name}")
        return self._schemas[schema_name]

    def get_schema_for_task(self, task_type: str) -> tuple[str, dict]:
        """Get the schema name and content for a task.

        Args:
            task_type: Task type.

        Returns:
            Tuple of (schema_name, schema_dict).
        """
        schema_map = {
            "classification": "classification.schema.json",
            "mapping": "mapping.schema.json",
            "scenario_extraction": "scenario_extraction.schema.json",
            "outcome_extraction": "outcome_extraction.schema.json",
            "audit": "audit.schema.json",
        }
        schema_name = schema_map.get(task_type)
        if not schema_name:
            raise ValueError(f"No schema defined for task: {task_type}")

        schema_dict = self.load_schema(schema_name)
        return schema_name, schema_dict

    def _format_codebook_context(self) -> str:
        """Format codebook fields as context for prompts."""
        fields = self.codebook.get("fields", [])
        lines = []
        for field in fields:
            line = (
                f"- {field['field_name']} ({field['entity_level']}): "
                f"{field['definition']}"
            )
            if field.get("allowed_values"):
                line += f" Allowed: {', '.join(field['allowed_values'])}"
            if field.get("extraction_instruction"):
                line += f" Instruction: {field['extraction_instruction']}"
            lines.append(line)
        return "\n".join(lines)


# Module-level singleton
_loader: PromptLoader | None = None


def get_prompt_loader() -> PromptLoader:
    """Get the singleton PromptLoader instance."""
    global _loader
    if _loader is None:
        _loader = PromptLoader()
    return _loader
