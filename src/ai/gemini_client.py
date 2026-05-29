"""
Gemini and OpenAI API client.

Handles:
- Loading API keys from .env (Gemini and OpenAI)
- Surgical model selection (fast/pro) or mix-and-match per task
- Sending prompts with text and/or images (multimodal)
- Requesting structured JSON output
- Saving raw outputs
- Retry logic
- Logging API calls (never logging API keys)
"""

import json
import os
import time
import base64
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
    """Client for interacting with Gemini and OpenAI APIs dynamically."""

    def __init__(self):
        self.api_key_free = os.getenv("GEMINI_API_KEY_FREE")
        self.api_key_paid = os.getenv("GEMINI_API_KEY_PAID")
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.config = load_project_config()

        # Load configurations first
        self.max_retries = self.config["ai"].get("max_retries", 2)
        self.timeout = self.config["ai"].get("timeout_seconds", 300)

        # Fallbacks for backwards compatibility
        if not self.api_key_free:
            self.api_key_free = self.api_key
        if not self.api_key_paid:
            self.api_key_paid = self.api_key

        self.client_free = None
        self.client_paid = None

        timeout_ms = int(float(self.timeout) * 1000) if self.timeout else 180000

        if self.api_key_free:
            try:
                self.client_free = genai.Client(
                    api_key=self.api_key_free,
                    http_options=types.HttpOptions(timeout=timeout_ms)
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Free Gemini client: {e}")

        if self.api_key_paid:
            try:
                self.client_paid = genai.Client(
                    api_key=self.api_key_paid,
                    http_options=types.HttpOptions(timeout=timeout_ms)
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Paid Gemini client: {e}")

        # Default active client is the free one
        self.client = self.client_free

        # In-memory uploaded files cache to prevent redundant network transfers
        self.cached_files_free = {}
        self.cached_files_paid = {}

        # Model names from env (fallback defaults)
        self.model_fast = os.getenv(
            self.config["ai"]["fast_model_env"], "gemini-2.5-flash"
        )
        self.model_pro = os.getenv(
            self.config["ai"]["pro_model_env"], "gemini-2.5-pro"
        )

    def get_model_for_task(self, task_type: str) -> str:
        """Fallback method for backwards compatibility. Returns the resolved model name."""
        _, model_name = self.get_provider_and_model_for_task(task_type)
        return model_name

    def get_provider_and_model_for_task(self, task_type: str) -> tuple[str, str]:
        """Resolve the provider and model name for a specific task type.

        Supports dynamic mix-and-match values under `task_models:` in project_config.yaml:
          task_type: "fast"                     # Default provider + fast model
          task_type: "pro"                      # Default provider + pro model
          task_type: "openai:fast"              # OpenAI + fast model (gpt-4o-mini)
          task_type: "gemini:pro"               # Gemini + pro model (gemini-2.5-pro)
          task_type: "openai:gpt-4o"            # OpenAI + specific model
        """
        task_models = self.config.get("task_models", {})
        val = task_models.get(task_type, "fast")

        # Determine global provider and model/tier
        provider = self.config.get("ai", {}).get("provider", "gemini")
        tier_or_model = val

        if ":" in val:
            parts = val.split(":", 1)
            provider = parts[0]
            tier_or_model = parts[1]

        # Resolve tier/model name
        if provider == "gemini":
            if tier_or_model == "fast":
                model_name = os.getenv("GEMINI_MODEL_FAST", "gemini-2.5-flash")
            elif tier_or_model == "pro":
                model_name = os.getenv("GEMINI_MODEL_PRO", "gemini-2.5-pro")
            else:
                model_name = tier_or_model
        elif provider == "openai":
            if tier_or_model == "fast":
                model_name = os.getenv("OPENAI_MODEL_FAST", "gpt-4o-mini")
            elif tier_or_model == "pro":
                model_name = os.getenv("OPENAI_MODEL_PRO", "gpt-4o")
            else:
                model_name = tier_or_model
        else:
            model_name = tier_or_model

        return provider, model_name

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
        """Call either Gemini or OpenAI with text-only input."""
        provider, model_name = self.get_provider_and_model_for_task(task_type)

        if provider == "openai":
            return self._call_openai_api(
                model_name=model_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                document_text=document_text,
                image_paths=None,
                document_id=document_id,
                task_type=task_type,
                output_path=output_path,
                schema_dict=schema_dict,
            )
        else:
            # Gemini execution flow
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
        """Call either Gemini or OpenAI with multimodal input (text, PDF, and/or page images)."""
        provider, model_name = self.get_provider_and_model_for_task(task_type)

        if provider == "openai":
            return self._call_openai_api(
                model_name=model_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                document_text=document_text,
                image_paths=image_paths,
                document_id=document_id,
                task_type=task_type,
                output_path=output_path,
                schema_dict=schema_dict,
            )
        else:
            # Gemini execution flow
            contents = [user_prompt]

            # Add text content if provided
            if document_text:
                contents.append(f"\nDOCUMENT TEXT:\n{document_text}")

            return self._call_api(
                model_name=model_name,
                system_prompt=system_prompt,
                contents=contents,
                document_id=document_id,
                task_type=task_type,
                output_path=output_path,
                schema_dict=schema_dict,
                pdf_path=pdf_path,
                image_paths=image_paths,
            )

    def _call_openai_api(
        self,
        model_name: str,
        system_prompt: str,
        user_prompt: str,
        document_text: str | None,
        image_paths: list[Path] | None,
        document_id: str,
        task_type: str,
        output_path: Path,
        schema_dict: dict | None = None,
    ) -> dict[str, Any]:
        """Internal method to call OpenAI API with native JSON schema instruction and base64 images."""
        if not self.openai_key:
            raise ValueError(
                "OPENAI_API_KEY not found in environment. Please add it to your .env file."
            )

        if schema_dict:
            schema_str = json.dumps(schema_dict, indent=2)
            instruction = (
                f"\n\nIMPORTANT: You MUST return ONLY a valid, concrete JSON object instance matching "
                f"this schema structure, populated with the actual extracted data. "
                f"Do NOT return the schema definition itself (i.e., do not include schema keywords like "
                f"'$schema', 'type', 'properties', 'additionalProperties', 'required' at the root of your response). "
                f"Do not include markdown formatting like ```json.\n"
                f"{schema_str}\n"
            )
            user_prompt_with_schema = user_prompt + instruction
        else:
            user_prompt_with_schema = user_prompt

        # Build messages block
        content_blocks = [{"type": "text", "text": user_prompt_with_schema}]
        if document_text:
            content_blocks.append({"type": "text", "text": f"\nDOCUMENT TEXT:\n{document_text}"})

        # Base64 encode and append images
        if image_paths:
            selected_images = []
            if len(image_paths) <= 8:
                selected_images = image_paths
                logger.info(f"[{document_id}] Sending all {len(image_paths)} pages since document is short.")
            else:
                for i, img_path in enumerate(image_paths):
                    # Always include the first and last page
                    if i == 0 or i == len(image_paths) - 1:
                        selected_images.append(img_path)
                        continue
                    
                    # Resolve corresponding text page
                    txt_path = Path(str(img_path).replace("pages_images", "pages_text").replace(".png", ".txt"))
                    if txt_path.exists():
                        try:
                            text = txt_path.read_text(encoding="utf-8").lower()
                            # Check if the page has figure references (e.g. Fig. 1, Figure 2)
                            import re
                            has_figure = bool(re.search(r"\b(figure|fig|figura)\b\.?\s*\d+", text))
                            if has_figure:
                                selected_images.append(img_path)
                        except Exception as e:
                            logger.warning(f"[{document_id}] Error reading text page {txt_path.name}: {e}")
                
                # Deduplicate and sort
                selected_images = sorted(list(set(selected_images)), key=lambda p: p.name)
                logger.info(
                    f"[{document_id}] Dynamically selected {len(selected_images)} pages out of {len(image_paths)} "
                    f"that contain tables, figures, or metadata."
                )

            for img_path in selected_images:
                if img_path.exists():
                    try:
                        with open(img_path, "rb") as image_file:
                            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                        content_blocks.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{encoded_string}",
                                "detail": "high"
                            }
                        })
                    except Exception as e:
                        logger.warning(
                            f"[{document_id}] Failed to process image {img_path.name} for OpenAI: {e}"
                        )

        body = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content_blocks}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }

        import urllib.request
        import urllib.error

        last_error = None
        for attempt in range(1, self.max_retries + 2):
            try:
                logger.info(
                    f"[{document_id}] OpenAI API call: task={task_type}, model={model_name}, "
                    f"attempt={attempt}"
                )

                req = urllib.request.Request(
                    "https://api.openai.com/v1/chat/completions",
                    data=json.dumps(body).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.openai_key}",
                    },
                    method="POST"
                )

                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    res_body = json.loads(response.read().decode("utf-8"))

                raw_text = res_body["choices"][0]["message"]["content"]
                if not raw_text:
                    raise ValueError("Empty response from OpenAI API")

                # Save raw output
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(raw_text, encoding="utf-8")

                # Parse JSON
                from src.utils.json_utils import parse_json_safe
                data = parse_json_safe(raw_text)

                logger.info(
                    f"[{document_id}] OpenAI API call SUCCESS: task={task_type}, "
                    f"model={model_name}, output={output_path.name}"
                )

                return {
                    "success": True,
                    "data": data,
                    "model": model_name,
                    "raw_text": raw_text,
                    "error": None,
                }

            except urllib.error.HTTPError as e:
                try:
                    err_details = json.loads(e.read().decode("utf-8"))
                    err_msg = err_details.get("error", {}).get("message", str(e))
                except Exception:
                    err_msg = str(e)
                last_error = f"HTTP Error {e.code}: {err_msg}"
                logger.warning(
                    f"[{document_id}] OpenAI API HTTP error on attempt {attempt}: {last_error}"
                )

            except json.JSONDecodeError as e:
                last_error = f"JSON parse error: {e}"
                logger.warning(
                    f"[{document_id}] JSON parse error on attempt {attempt}: {e}"
                )
                if 'raw_text' in locals() and raw_text:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_text(raw_text, encoding="utf-8")

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"[{document_id}] OpenAI API error on attempt {attempt}: {e}"
                )

            # Wait before retry (exponential backoff or rate-limit pause)
            if attempt <= self.max_retries:
                if last_error and ("rate limit" in last_error.lower() or "429" in last_error):
                    wait_time = 25 * attempt
                else:
                    wait_time = 2 ** attempt
                logger.info(f"[{document_id}] Retrying in {wait_time}s...")
                time.sleep(wait_time)

        # All attempts failed
        logger.error(
            f"[{document_id}] OpenAI API call FAILED after {self.max_retries + 1} attempts: "
            f"task={task_type}, error={last_error}"
        )

        return {
            "success": False,
            "data": None,
            "model": model_name,
            "raw_text": None,
            "error": last_error,
        }

    def _call_api(
        self,
        model_name: str,
        system_prompt: str,
        contents: list,
        document_id: str,
        task_type: str,
        output_path: Path,
        schema_dict: dict | None = None,
        pdf_path: Path | None = None,
        image_paths: list[Path] | None = None,
    ) -> dict[str, Any]:
        """Internal method to call the Gemini API with retry logic and dynamic paid-tier conmutation."""
        # Build generation config
        gen_config_kwargs = dict(
            system_instruction=system_prompt,
            temperature=0.1,
            response_mime_type="application/json",
        )

        # Enable Google Search grounding for tasks that may need
        # to look up climate zone classifications from location data.
        # This is the ONLY external data the system is allowed to retrieve.
        if task_type in ("mapping", "scenario_extraction"):
            grounding_tool = types.Tool(
                google_search=types.GoogleSearch()
            )
            gen_config_kwargs["tools"] = [grounding_tool]
            del gen_config_kwargs["response_mime_type"]

        gen_config = types.GenerateContentConfig(**gen_config_kwargs)

        # Inject JSON schema into prompt
        if schema_dict:
            schema_str = json.dumps(schema_dict, indent=2)
            instruction = (
                f"\n\nIMPORTANT: You MUST return ONLY a valid JSON object matching "
                f"this schema. Do not include markdown formatting like ```json.\n"
                f"{schema_str}\n"
            )
            for i in range(len(contents)):
                if isinstance(contents[i], str):
                    contents[i] += instruction
                    break

        # Start with the FREE client for every step to optimize costs!
        current_client = self.client_free if self.client_free else self.client

        last_error = None
        for attempt in range(1, self.max_retries + 2):
            try:
                # Prepare contents dynamically for this attempt
                current_contents = contents.copy()

                # Load persistent local cache to prevent redundant network transfers across isolated process steps
                persistent_cache_dir = Path("data/01_processed") / document_id
                persistent_cache_dir.mkdir(parents=True, exist_ok=True)
                persistent_cache_path = persistent_cache_dir / "uploaded_files_cache.json"

                persistent_cache = {"free": {}, "paid": {}}
                if persistent_cache_path.exists():
                    try:
                        with open(persistent_cache_path, "r", encoding="utf-8") as f:
                            persistent_cache = json.load(f)
                    except Exception as e:
                        logger.warning(f"[{document_id}] Failed to load persistent cache: {e}")

                cache_key_tier = "free" if current_client == self.client_free else "paid"
                tier_cache = persistent_cache.setdefault(cache_key_tier, {})

                def get_or_upload_file(client, file_path: Path) -> Any:
                    file_key = str(file_path.absolute())
                    cached_name = tier_cache.get(file_key)
                    if cached_name:
                        try:
                            logger.info(f"[{document_id}] Fetching cached upload '{cached_name}' for {file_path.name}...")
                            up_file = client.files.get(name=cached_name)
                            return up_file
                        except Exception as e:
                            logger.info(f"[{document_id}] Cached upload '{cached_name}' expired or not found. Re-uploading: {e}")
                            if file_key in tier_cache:
                                del tier_cache[file_key]

                    # Upload fresh
                    logger.info(f"[{document_id}] Uploading {file_path.name} using current client...")
                    up_file = client.files.upload(file=file_path)
                    
                    # Update cache
                    tier_cache[file_key] = up_file.name
                    try:
                        with open(persistent_cache_path, "w", encoding="utf-8") as f:
                            json.dump(persistent_cache, f, indent=2)
                    except Exception as ex:
                        logger.warning(f"[{document_id}] Failed to write persistent cache: {ex}")
                    
                    return up_file

                if pdf_path and pdf_path.exists():
                    up_pdf = get_or_upload_file(current_client, pdf_path)
                    current_contents.append(up_pdf)

                if image_paths:
                    for img_path in image_paths:
                        if img_path.exists():
                            up_img = get_or_upload_file(current_client, img_path)
                            current_contents.append(up_img)

                logger.info(
                    f"[{document_id}] API call: task={task_type}, model={model_name}, "
                    f"attempt={attempt} (Using {'Free' if current_client == self.client_free else 'Paid'} Key)"
                )

                if not current_client:
                    raise ValueError("No Gemini API client is initialized. Check GEMINI_API_KEY_FREE in .env")

                response = current_client.models.generate_content(
                    model=model_name,
                    contents=current_contents,
                    config=gen_config,
                )

                raw_text = response.text
                if not raw_text:
                    raise ValueError("Empty response from Gemini API")

                # Save raw output
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(raw_text, encoding="utf-8")

                # Parse JSON
                from src.utils.json_utils import parse_json_safe
                data = parse_json_safe(raw_text)

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
                if 'raw_text' in locals() and raw_text:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_text(raw_text, encoding="utf-8")

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"[{document_id}] API error on attempt {attempt}: {e}"
                )

                # Seamless fallback conmutation! If it is a 503 (Unavailable/Demand Spike), 429 (Rate Limit), or Timeout/Connection issue
                # and we have a paid client configured, switch to it for the next attempts of this step!
                is_capacity_error = any(
                    kw in last_error.lower() for kw in (
                        "503", "unavailable", "rate limit", "429", "high demand", 
                        "spikes in demand", "timeout", "timed out", "readtimeout", "connect"
                    )
                )
                if is_capacity_error and self.client_paid and current_client == self.client_free:
                    logger.warning(
                        f"[{document_id}] Load/Rate/Timeout error detected with Free Key. "
                        f"CONMUTING SEAMLESSLY TO PAID KEY for retry..."
                    )
                    current_client = self.client_paid

            # Wait before retry (exponential backoff or rate-limit pause)
            if attempt <= self.max_retries:
                if last_error and ("rate limit" in last_error.lower() or "429" in last_error or "503" in last_error or "unavailable" in last_error.lower()):
                    wait_time = 15 * attempt
                else:
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


