# AI Prompts Documentation

All prompts are stored in `prompts/prompts.yaml`. See `prompts/README_prompts.md` for editing instructions.

## Prompt Types

1. **Global System Prompt**: Sets the AI's role and mandatory extraction rules. Prepended to every API call.
2. **Classification Prompt**: Determines study type, extractability, and document features.
3. **Mapping Prompt**: Maps internal article structure before numerical extraction.
4. **Scenario Extraction Prompt**: Extracts detailed scenario information.
5. **Outcome Extraction Prompt**: Extracts numerical outcomes per scenario.
6. **Audit Prompt**: Audits the extraction for completeness and issues.

## Model Assignment

| Task | Model |
|------|-------|
| Classification | Gemini 2.5 Flash |
| Mapping | Gemini 2.5 Pro |
| Scenario Extraction | Gemini 2.5 Pro |
| Outcome Extraction | Gemini 2.5 Pro |
| Audit | Gemini 2.5 Pro |

## Versioning

The `prompts_version` field in `prompts.yaml` is recorded in every `ai_runs` record and frozen dataset manifest.
