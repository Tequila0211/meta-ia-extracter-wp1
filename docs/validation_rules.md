# Validation Rules

## Schema Validation
Every AI output is validated against its corresponding JSON schema in `schemas/`.

## Codebook Validation
- `outcome_name` must exist in the codebook.
- `entity_level` must match the codebook definition.
- `data_type` must be consistent.
- Numeric fields must include units if `original_unit_required` is true.
- Source types must match `allowed_source_types` if specified.

## Business Rules (Blocking Conditions)

| Rule | Condition | Action |
|------|-----------|--------|
| Missing page | Extracted value without page number | Block |
| Missing evidence | Critical field without evidence_text or crop_path | Block |
| Missing unit | Numeric value without unit | Block |
| Figure without digitization | source_type=figure but needs_digitization=false | Set needs_digitization |
| Unknown field | field_name not in codebook | Reject |
| Package split | Package separated without explicit evidence | Block |
| Scenario mixing | Different scenarios merged | Block |

## Evidence Validation
- Page must exist in the document.
- source_type must be valid vocabulary.
- Either evidence_text or crop_path must be present for critical fields.
