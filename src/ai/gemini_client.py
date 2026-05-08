"""
Gemini API client.

Handles:
- Loading API key from .env
- Model selection (fast/pro) per task
- Sending prompts with text and/or images
- Requesting structured JSON output
- Saving raw outputs
- Retry logic
- Logging API calls (never logging API keys)
"""

import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types

from src.utils.logging_config import get_logger
from src.utils.paths import load_project_config
from src.utils.timestamps import now_iso

load_dotenv()

logger = get_logger("ai_calls")


class GeminiClient:
    """Client for interacting with Gemini API."""

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY not found in environment. "
                "Copy .env.example to .env and set your key."
            )

        self.client = genai.Client(api_key=self.api_key)
        self.config = load_project_config()

        # Model names from env
        self.model_fast = os.getenv(
            self.config["ai"]["fast_model_env"], "gemini-2.5-flash"
        )
        self.model_pro = os.getenv(
            self.config["ai"]["pro_model_env"], "gemini-2.5-pro"
        )

        self.max_retries = self.config["ai"].get("max_retries", 2)
        self.timeout = self.config["ai"].get("timeout_seconds", 300)

    def get_model_for_task(self, task_type: str) -> str:
        """Get the model name for a specific task type.

        Args:
            task_type: One of 'classification', 'mapping', 'scenario_extraction',
                       'outcome_extraction', 'audit'.

        Returns:
            Model name string.
        """
        task_models = self.config.get("task_models", {})
        model_tier = task_models.get(task_type, "pro")

        if model_tier == "fast":
            return self.model_fast
        return self.model_pro

    def call_with_text(
        self,
        task_type: str,
        system_prompt: str,
        user_prompt: str,
        document_text: str,
        document_id: str,
        output_path: Path,
        schema_dict: dict | None = None,
    ) -> dict[str, Any]:
        """Call Gemini with text-only input.

        Args:
            task_type: Task type for model selection.
            system_prompt: System instruction.
            user_prompt: Task-specific prompt.
            document_text: Full document text.
            document_id: Document identifier for logging.
            output_path: Path to save raw JSON output.
            schema_dict: Optional JSON schema for structured output.

        Returns:
            Dict with 'success', 'data', 'model', 'error' keys.
        """
        model_name = self.get_model_for_task(task_type)
        full_prompt = f"{user_prompt}\n\nDOCUMENT CONTENT:\n{document_text}"

        return self._call_api(
            model_name=model_name,
            system_prompt=system_prompt,
            contents=[full_prompt],
            document_id=document_id,
            task_type=task_type,
            output_path=output_path,
            schema_dict=schema_dict,
        )

    def call_with_pdf_and_images(
        self,
        task_type: str,
        system_prompt: str,
        user_prompt: str,
        pdf_path: Path | None = None,
        image_paths: list[Path] | None = None,
        document_text: str | None = None,
        document_id: str = "",
        output_path: Path = None,
        schema_dict: dict | None = None,
    ) -> dict[str, Any]:
        """Call Gemini with multimodal input (PDF + page images).

        Args:
            task_type: Task type for model selection.
            system_prompt: System instruction.
            user_prompt: Task-specific prompt.
            pdf_path: Path to the PDF file (for general overview).
            image_paths: List of page image paths (for detailed extraction).
            document_text: Optional text content to include.
            document_id: Document identifier for logging.
            output_path: Path to save raw JSON output.
            schema_dict: Optional JSON schema for structured output.

        Returns:
            Dict with 'success', 'data', 'model', 'error' keys.
        """
        model_name = self.get_model_for_task(task_type)
        contents = [user_prompt]

        # Add text content if provided
        if document_text:
            contents.append(f"\nDOCUMENT TEXT:\n{document_text}")

        # Upload and add PDF
        if pdf_path and pdf_path.exists():
            try:
                uploaded_pdf = self.client.files.upload(file=pdf_path)
                contents.append(uploaded_pdf)
                logger.info(f"[{document_id}] Uploaded PDF: {pdf_path.name}")
            except Exception as e:
                logger.warning(f"[{document_id}] Failed to upload PDF: {e}")

        # Add page images
        if image_paths:
            for img_path in image_paths:
                if img_path.exists():
                    try:
                        uploaded_img = self.client.files.upload(file=img_path)
                        contents.append(uploaded_img)
                    except Exception as e:
                        logger.warning(f"[{document_id}] Failed to upload image {img_path.name}: {e}")

            logger.info(f"[{document_id}] Uploaded {len(image_paths)} page images")

        return self._call_api(
            model_name=model_name,
            system_prompt=system_prompt,
            contents=contents,
            document_id=document_id,
            task_type=task_type,
            output_path=output_path,
            schema_dict=schema_dict,
        )

    def _call_api(
        self,
        model_name: str,
        system_prompt: str,
        contents: list,
        document_id: str,
        task_type: str,
        output_path: Path,
        schema_dict: dict | None = None,
    ) -> dict[str, Any]:
        """Internal method to call the Gemini API with retry logic.

        Returns:
            Dict with 'success', 'data', 'model', 'error', 'raw_text' keys.
        """
        # Build generation config
        gen_config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.1,
            response_mime_type="application/json",
        )

        # Inject JSON schema into the prompt instead of using response_schema
        # because the SDK's strict Pydantic validation rejects Draft-07 schemas.
        if schema_dict:
            schema_str = json.dumps(schema_dict, indent=2)
            instruction = (
                f"\n\nIMPORTANT: You MUST return ONLY a valid JSON object matching "
                f"this schema. Do not include markdown formatting like ```json.\n"
                f"{schema_str}\n"
            )
            # Find the first string in contents to append the instruction
            for i in range(len(contents)):
                if isinstance(contents[i], str):
                    contents[i] += instruction
                    break

        last_error = None
        for attempt in range(1, self.max_retries + 2):  # max_retries + 1 attempts
            try:
                logger.info(
                    f"[{document_id}] API call: task={task_type}, model={model_name}, "
                    f"attempt={attempt}"
                )

                response = self.client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=gen_config,
                )

                raw_text = response.text
                if not raw_text:
                    raise ValueError("Empty response from Gemini API")

                # Save raw output
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(raw_text, encoding="utf-8")

                # Parse JSON
                data = json.loads(raw_text)

                logger.info(
                    f"[{document_id}] API call SUCCESS: task={task_type}, "
                    f"model={model_name}, output={output_path.name}"
                )

                return {
                    "success": True,
                    "data": data,
                    "model": model_name,
                    "raw_text": raw_text,
                    "error": None,
                }

            except json.JSONDecodeError as e:
                last_error = f"JSON parse error: {e}"
                logger.warning(
                    f"[{document_id}] JSON parse error on attempt {attempt}: {e}"
                )
                # Still save raw output even if JSON parsing fails
                if raw_text:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_text(raw_text, encoding="utf-8")

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"[{document_id}] API error on attempt {attempt}: {e}"
                )

            # Wait before retry (exponential backoff)
            if attempt <= self.max_retries:
                wait_time = 2 ** attempt
                logger.info(f"[{document_id}] Retrying in {wait_time}s...")
                time.sleep(wait_time)

        # All attempts failed
        logger.error(
            f"[{document_id}] API call FAILED after {self.max_retries + 1} attempts: "
            f"task={task_type}, error={last_error}"
        )

        return {
            "success": False,
            "data": None,
            "model": model_name,
            "raw_text": None,
            "error": last_error,
        }
