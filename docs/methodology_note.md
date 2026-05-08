# Methodology Note — AI-Assisted Data Extraction

This project implements a human-in-the-loop AI-assisted extraction workflow for systematic review and meta-analysis.

PDF documents are processed individually. Text is extracted page by page, and pages are rendered as images to preserve visual evidence from tables and figures. Gemini API is used to perform structured tasks: article classification, structural mapping, scenario extraction, outcome extraction, and extraction audit.

The AI model is constrained by versioned prompts and JSON schemas. Raw AI outputs are saved for auditability. Extracted data are validated against a project codebook and methodological business rules. Critical fields require explicit evidence, including page number and textual or visual support.

No extracted value is considered final until reviewed and accepted by a human researcher. The system preserves both AI-generated values and human corrections. Final analysis datasets are exported only after validation and dataset freezing.

## Multimodal Input

The pipeline uses a multimodal approach:
- The **full PDF** is uploaded to Gemini for a general overview during classification and mapping.
- Individual **page images (PNG)** are sent for detailed extraction of information from figures and tables during scenario extraction and outcome extraction steps.

This ensures that the AI can both understand the overall article structure and accurately extract data from visual elements.
