# Meta AI Extraction Pipeline

Pipeline local de extracción de datos asistida por IA para revisión sistemática y metaanálisis.

## Descripción

Este proyecto procesa artículos científicos en PDF uno por uno, utilizando la API de Gemini mediante Google AI Studio. El sistema:

1. Lee PDFs desde una carpeta local.
2. Registra cada artículo con un identificador estable (A001, A002, ...).
3. Preprocesa cada PDF (extracción de texto por página + renderizado PNG).
4. Ejecuta una secuencia controlada de llamadas a Gemini (clasificación, mapeo, casos de construcción, escenarios, espacios, componentes, outcomes, baseline matching, auditoría lógica y meta-readiness).
5. Obtiene salidas estructuradas en JSON validadas contra schemas.
6. Valida contra codebook y reglas metodológicas (10 reglas complejas).
7. Guarda resultados crudos y calculados en SQLite.
8. Exporta plantilla de revisión humana en Excel con 13 hojas interconectadas por IDs legibles.
9. Importa correcciones humanas directamente a la base de datos.
10. Congela datasets validados para síntesis cuantitativa.

**La IA actúa como pre-extractor. Todo dato crítico debe ser revisado y validado por humano.**

---

## Protocolo de Revisión Humana (13 Hojas Excel)

El archivo `data/03_human_review/extraction_review.xlsx` es el núcleo de la validación humana. Para asegurar la máxima usabilidad, el sistema ha sido robustecido para evitar IDs del sistema (UUIDs) y en su lugar emplear códigos legibles y trazables entre hojas.

### Hojas de Trabajo y Estructura

| Código y Nombre de Hoja | Propósito | Instrucción para el Revisor Humano |
|---|---|---|
| **`00_README`** | Instrucciones y glosario del protocolo. | Lea detenidamente antes de comenzar la revisión de la tanda. |
| **`01_DOCUMENTS`** | Registro maestro de documentos procesados. | Verifique que el estado sea `needs_human_review` o `validated`. |
| **`01B_CLASSIFICATIONS`** | Decisiones de inclusión y tipos de estudio. | Confirme si el artículo es verdaderamente simulación/experimental y elegible. |
| **`02A_BUILDING_CASES`** | Características físicas de los edificios evaluados. | Verifique el tipo, periodo de construcción, área y descripción del HVAC. |
| **`02_SCENARIOS`** | Configuración de escenarios baseline e intervención. | Evalúe si la IA clasificó correctamente los 21 flags binarios de estrategias pasivas/activas y el tipo de intervención. |
| **`02B_SPACES`** | Espacios y zonas térmicas detalladas por escenario. | Verifique las dimensiones del espacio, tasas de ocupación y orientación física. |
| **`02C_INTERVENTION_COMPONENTS`** | Desglose paramétrico de componentes individuales. | Revise los valores físicos de los componentes (ej. espesor de aislamiento, conductividad,スケジュール). |
| **`03_OUTCOMES`** | Resultados cuantitativos (comfort, temperatura, consumo). | **Hoja Principal de Edición**: Introduzca sus correcciones en `human_value` y `human_unit` si detecta discrepancias con el PDF. |
| **`03B_EFFECT_SIZES`** | Cálculo determinista de tamaños del efecto (MD, %, Ratio). | No editable. Muestra los efectos calculados bajo reglas fijas para síntesis cuantitativa. |
| **`04_EVIDENCE`** | Trazabilidad del texto original y número de página. | Utilice los segmentos de texto y el número de página de origen para contrastar rápidamente sin buscar en todo el PDF. |
| **`05_QA_LOG`** | Registro de violaciones de reglas de validación lógica. | Analice los flags críticos (ej. `misting_classified_as_ventilation`, `active_system_contamination`) para enfocar su revisión. |
| **`06_HUMAN_REVIEW`** | Registro central de decisiones de auditoría. | Registre formalmente su decisión por campo (`accepted`, `corrected`, `rejected`, `unclear`). |
| **`07_DIGITIZATION_TASKS`** | Lista de figuras o gráficos que requieren digitalización. | Si la IA marcó `digitization_required_for_meta`, digitalice el gráfico usando herramientas externas (ej. WebPlotDigitizer) y registre los valores aquí. |
| **`08_META_READINESS`** | Auditoría final de elegibilidad para metaanálisis. | Revise las razones de exclusión cuantitativa en `blocking_reason` antes de exportar el dataset consolidado. |

### Reglas Clave de Trazabilidad por Códigos
- **Sin UUIDs**: Todas las referencias utilizan códigos como `A001_BC01` (para Building Case), `A001_S01` (para Escenarios), `A001_SP01` (para Espacios) o `A001_S01_C01` (para Componentes).
- **Relaciones Claras**: La hoja de `03_OUTCOMES` se conecta a `02_SCENARIOS` vía `scenario_code` y a `02B_SPACES` vía `space_code`.
- **Efectos Deterministas**: Todos los tamaños del efecto (MD - Mean Difference, Porcentaje de Cambio, Ratios) son calculados de forma determinista mediante reglas matemáticas y de dirección (`higher_is_better`), garantizando la neutralidad metodológica.

---

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

## Stack técnico

- Python 3.11+
- PyMuPDF (extracción de texto y renderizado de páginas)
- Gemini API (Google AI Studio)
- SQLite + SQLAlchemy
- Pydantic + jsonschema (validación)
- Typer + Rich (CLI)
- pandas + openpyxl (Excel)
- pytest (tests)
