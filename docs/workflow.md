# Workflow — Article Processing Pipeline

## Overview

Each article goes through the following steps:

1. **Registration**: PDF detected in `data/00_raw_pdfs/`, assigned document code (A001, A002...).
2. **Preprocessing**: Text extracted per page, pages rendered as PNG images.
3. **Classification**: Gemini classifies study type, extractability, and features.
4. **Mapping**: Gemini maps the article structure (scenarios, tables, figures, interventions).
5. **Scenario Extraction**: Gemini extracts detailed scenario information.
6. **Outcome Extraction**: Gemini extracts numerical outcomes per scenario.
7. **Audit**: Gemini audits the extraction for issues and completeness.
8. **Validation**: Schema, codebook, and business rule validation applied.
9. **Human Review**: Excel exported for researcher review.
10. **Import**: Human corrections imported back.
11. **Freezing**: Validated dataset exported with manifest and changelog.

## Interactive Mode

The researcher can:
- See the status of all documents.
- Choose where to continue from (e.g., A016).
- Choose how many articles to process.
- Pause after each article to review, export, or stop.

## Document Status Flow

```
pending → preprocessed → classified → mapped → scenarios_extracted → outcomes_extracted → audited → needs_human_review → validated
```

At any step, a document may be marked as `failed` if a critical error occurs.
