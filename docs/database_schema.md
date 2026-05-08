# Database Schema

## Tables

### documents
Stores registered PDF documents with status tracking.

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | UUID |
| document_code | TEXT UNIQUE | A001, A002, ... |
| file_name | TEXT | Original filename |
| file_path | TEXT | Path to PDF |
| file_hash | TEXT | SHA-256 hash |
| status | TEXT | Current processing status |
| current_step | TEXT | Last completed step |
| created_at | TEXT | ISO timestamp |
| updated_at | TEXT | ISO timestamp |

### pages
Stores per-page text and image paths.

### ai_runs
Logs every AI API call with model, prompt version, schema, and result.

### article_classification
Stores classification results per document.

### scenarios
Stores extracted scenarios with building typology, climate, interventions.

### outcomes
Stores numerical outcomes with baseline/intervention values and evidence.

### evidence
Links evidence (page, text, crop) to specific records.

### qa_log
Stores audit issues and required actions.

### human_review
Stores human review decisions and corrections.

### digitization_tasks
Tracks figure values that need manual digitization.

## Status Values

`pending` → `preprocessed` → `classified` → `mapped` → `scenarios_extracted` → `outcomes_extracted` → `audited` → `needs_human_review` → `validated` | `failed`
