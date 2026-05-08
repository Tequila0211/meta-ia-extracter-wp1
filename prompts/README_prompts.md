# Prompts — Editing Guide

## Location

All prompts are stored in `prompts/prompts.yaml`. They are **never** hardcoded in Python scripts.

## Structure

- `prompts_version`: Version identifier for the current prompt set. Update this when you make meaningful changes.
- `global_system_prompt`: Sent as system context for every Gemini API call. Contains the mandatory rules for the AI.
- `classification_prompt`: Used during article classification step.
- `mapping_prompt`: Used during structural mapping step.
- `scenario_extraction_prompt`: Used during scenario extraction step.
- `outcome_extraction_prompt`: Used during outcome extraction step.
- `audit_prompt`: Used during the audit step.

## How to Edit

1. Open `prompts/prompts.yaml` in any text editor.
2. Modify the prompt text while preserving the YAML `|` block scalar syntax.
3. Update `prompts_version` if you make significant changes.
4. Re-run the pipeline on a test article to verify the updated prompt produces valid output.

## Rules

- All prompts are in **English** (technical language).
- Do not add Python logic inside prompts.
- Do not reference file paths or internal implementation details.
- Each prompt must instruct Gemini to return JSON matching the corresponding schema.
- The `global_system_prompt` is prepended automatically by the pipeline; do not repeat its rules in individual prompts.

## Versioning

When you update prompts, the `prompts_version` is recorded in:
- Every `ai_runs` database record
- Every frozen dataset manifest
- This ensures full traceability of which prompt version produced which output.
