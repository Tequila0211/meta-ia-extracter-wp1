# Meta AI Extraction Pipeline

Pipeline local de extracción de datos asistida por IA para revisión sistemática y metaanálisis.

## Descripción

Este proyecto procesa artículos científicos en PDF uno por uno, utilizando la API de Gemini mediante Google AI Studio. El sistema:

1. Lee PDFs desde una carpeta local.
2. Registra cada artículo con un identificador estable (A001, A002, ...).
3. Preprocesa cada PDF (extracción de texto por página + renderizado PNG).
4. Ejecuta una secuencia controlada de llamadas a Gemini (clasificación, mapeo, escenarios, outcomes, auditoría).
5. Obtiene salidas estructuradas en JSON validadas contra schemas.
6. Valida contra codebook y reglas metodológicas.
7. Guarda resultados crudos y normalizados en SQLite.
8. Exporta plantilla de revisión humana en Excel.
9. Importa correcciones humanas.
10. Congela datasets validados.

**La IA actúa como pre-extractor. Todo dato crítico debe ser revisado y validado por humano.**

## Instalación

```bash
# Clonar repositorio
git clone <repo-url>
cd meta_ai_extraction_pipeline

# Crear entorno virtual
python -m venv .venv

# Activar entorno virtual
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Instalar dependencias
pip install -e ".[dev]"
```

## Configuración

```bash
# Copiar archivo de entorno
cp .env.example .env

# Editar .env y agregar tu GEMINI_API_KEY
# Obtener key desde: https://aistudio.google.com/
```

## Estructura de carpetas

```
meta_ai_extraction_pipeline/
├── config/              # Configuración YAML (codebook, reglas, vocabularios)
├── prompts/             # Prompts para Gemini (YAML editable)
├── schemas/             # JSON Schemas para validación de salidas
├── data/
│   ├── 00_raw_pdfs/     # PDFs originales (no se suben a Git)
│   ├── 01_processed/    # Texto e imágenes por página
│   ├── 02_ai_outputs/   # Salidas JSON de la IA
│   ├── 03_human_review/ # Excel de revisión humana
│   ├── 04_frozen_datasets/  # Datasets congelados
│   ├── 05_logs/         # Logs de ejecución
│   └── project.sqlite   # Base de datos SQLite
├── src/                 # Código fuente
├── scripts/             # Scripts de ejecución
├── tests/               # Tests automatizados
└── docs/                # Documentación
```

## Flujo de uso

### 1. Inicializar proyecto
```bash
python scripts/00_init_project.py
```

### 2. Agregar PDFs
Copiar los PDFs a `data/00_raw_pdfs/`.

### 3. Registrar PDFs
```bash
python scripts/01_register_pdfs.py
```

### 4. Preprocesar un artículo
```bash
python scripts/02_preprocess_pdfs.py --document A001
```

### 5. Procesar un artículo específico
```bash
python scripts/03_process_article.py --document A001
```

### 6. Continuar procesamiento interactivo
```bash
python scripts/03_process_article.py --interactive
```
El sistema muestra el estado de todos los documentos, permite elegir desde qué artículo continuar y cuántos procesar.

### 7. Ver estado
```bash
python scripts/08_status.py
```

### 8. Exportar revisión humana
```bash
python scripts/05_export_review_excel.py
```

### 9. Importar revisión humana
```bash
python scripts/06_import_human_review.py --file data/03_human_review/extraction_review.xlsx
```

### 10. Congelar dataset
```bash
python scripts/07_freeze_dataset.py --version v01
```

## CLI alternativo

Todos los comandos también están disponibles vía CLI:

```bash
python -m src.cli init
python -m src.cli register
python -m src.cli preprocess --document A001
python -m src.cli process --document A001
python -m src.cli process --interactive
python -m src.cli validate --document A001
python -m src.cli export-review
python -m src.cli import-review --file data/03_human_review/extraction_review.xlsx
python -m src.cli freeze --version v01
python -m src.cli status
```

## Tests

```bash
pytest tests/ -v
```

## Archivos que NO deben subirse a GitHub

- `.env` (contiene API key)
- `data/project.sqlite`
- `data/00_raw_pdfs/*`
- `data/01_processed/*`
- `data/02_ai_outputs/*`
- `data/03_human_review/*`
- `data/04_frozen_datasets/*`
- `data/05_logs/*`

## Limitaciones metodológicas

- La IA puede cometer errores de extracción; toda información crítica requiere validación humana.
- Los valores extraídos de figuras necesitan digitalización manual.
- El sistema no realiza OCR para PDFs escaneados.
- No se calculan tamaños de efecto automáticamente a menos que los valores estén explícitamente pareados.
- Los paquetes de estrategias no se separan sin evidencia explícita.

## Stack técnico

- Python 3.11+
- PyMuPDF (extracción de texto y renderizado de páginas)
- Gemini API (Google AI Studio)
- SQLite + SQLAlchemy
- Pydantic + jsonschema (validación)
- Typer + Rich (CLI)
- pandas + openpyxl (Excel)
- pytest (tests)
