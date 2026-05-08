# **PDR / PRD Técnico**

# **Proyecto Local de Extracción de Datos para Metaanálisis Asistido por IA**

## **0\. Nombre del proyecto**

meta\_ai\_extraction\_pipeline

## **1\. Propósito general**

Construir un proyecto local, reproducible y versionable en GitHub para asistir la extracción de datos desde artículos científicos en PDF, artículo por artículo, usando scripts Python conectados a la API de Gemini mediante Google AI Studio.

El sistema debe permitir:

1. Leer una carpeta local con PDFs digitales.  
2. Registrar cada artículo con un identificador estable.  
3. Preprocesar cada PDF.  
4. Ejecutar una secuencia controlada de llamadas a Gemini.  
5. Obtener salidas estructuradas en JSON.  
6. Validar esas salidas contra schemas y reglas metodológicas.  
7. Guardar resultados crudos y normalizados.  
8. Exportar una plantilla de revisión humana en Excel.  
9. Permitir continuar el flujo artículo por artículo.  
10. Congelar datasets validados para análisis posterior.

Este sistema **no reemplaza al investigador**. La IA actúa como pre-extractor, mapeador de evidencia y auditor preliminar. Todo dato crítico debe ser revisado y validado por humano antes de entrar al dataset final.

---

# **2\. Principios obligatorios del sistema**

El agente debe construir el proyecto siguiendo estos principios:

1\. Reproducibilidad:  
   Todo paso debe poder repetirse mediante comandos claros.

2\. Trazabilidad:  
   Todo dato extraído debe conectarse con:  
   \- documento  
   \- página  
   \- tabla, figura o sección  
   \- evidencia textual o visual  
   \- prompt usado  
   \- modelo usado  
   \- versión del codebook  
   \- versión del schema

3\. Separación de responsabilidades:  
   \- Codebook: define qué se extrae.  
   \- Prompts YAML: definen cómo se instruye a Gemini.  
   \- Schemas JSON: definen cómo debe responder Gemini.  
   \- Validadores: deciden si la salida es aceptable.  
   \- SQLite: almacena datos estructurados.  
   \- Excel: permite revisión humana.  
   \- JSON crudo: conserva la respuesta original de IA.

4\. Seguridad:  
   Ninguna API key debe quedar en código.  
   El archivo .env nunca debe subirse a GitHub.  
   Se debe entregar .env.example.

5\. Control humano:  
   Ningún dato crítico debe considerarse final sin validación humana.

6\. Flujo incremental:  
   El investigador debe poder procesar artículos uno por uno y continuar desde donde quedó.

7\. No saturar a la IA:  
   El sistema debe dividir el trabajo en varias llamadas:  
   \- clasificación  
   \- mapeo estructural  
   \- extracción de escenarios  
   \- extracción de outcomes  
   \- auditoría

---

# **3\. Alcance del MVP**

## **3.1 Incluido en el MVP**

El agente debe construir un MVP local con:

\- Proyecto Python estructurado.  
\- Lectura de PDFs desde carpeta local.  
\- Registro automático de documentos.  
\- Preprocesamiento de PDFs digitales.  
\- Extracción de texto por página.  
\- Renderizado de páginas como imágenes PNG.  
\- Llamadas a Gemini API.  
\- Prompts editables en YAML.  
\- Schemas JSON separados.  
\- Validación con Pydantic o jsonschema.  
\- Reglas de bloqueo metodológico.  
\- Almacenamiento en SQLite.  
\- Exportación a Excel para revisión humana.  
\- Importación posterior de revisión humana.  
\- Congelación de dataset validado.  
\- Logs de ejecución.  
\- Control de estado por documento.  
\- CLI interactivo para continuar desde cierto artículo.  
\- Tests básicos.  
\- README con flujo de uso.

## **3.2 No incluido en el MVP**

No construir todavía:

\- Interfaz web completa.  
\- Login.  
\- Multiusuario.  
\- Dashboard avanzado.  
\- Integración directa con Google Drive.  
\- Sincronización automática.  
\- Análisis estadístico completo del metaanálisis.  
\- Forest plots.  
\- Funnel plots.  
\- OCR para PDFs escaneados.

Esos elementos quedan para fases futuras.

---

# **4\. Stack técnico requerido**

## **4.1 Lenguaje principal**

Python 3.11+

## **4.2 Librerías recomendadas**

pymupdf  
pandas  
openpyxl  
pydantic  
pyyaml  
python-dotenv  
google-genai  
sqlalchemy  
typer  
rich  
pytest  
jsonschema

## **4.3 Base de datos**

Para el MVP:

SQLite

Archivo:

data/project.sqlite

Para una futura app:

PostgreSQL

---

# **5\. Estructura obligatoria del proyecto**

El agente debe crear esta estructura base:

meta\_ai\_extraction\_pipeline/  
│  
├── README.md  
├── pyproject.toml  
├── .gitignore  
├── .env.example  
│  
├── config/  
│   ├── project\_config.yaml  
│   ├── codebook.yaml  
│   ├── controlled\_vocabularies.yaml  
│   └── extraction\_rules.yaml  
│  
├── prompts/  
│   ├── prompts.yaml  
│   └── README\_prompts.md  
│  
├── schemas/  
│   ├── classification.schema.json  
│   ├── mapping.schema.json  
│   ├── scenario\_extraction.schema.json  
│   ├── outcome\_extraction.schema.json  
│   └── audit.schema.json  
│  
├── data/  
│   ├── 00\_raw\_pdfs/  
│   ├── 01\_processed/  
│   ├── 02\_ai\_outputs/  
│   ├── 03\_human\_review/  
│   ├── 04\_frozen\_datasets/  
│   ├── 05\_logs/  
│   └── project.sqlite  
│  
├── src/  
│   ├── \_\_init\_\_.py  
│   │  
│   ├── cli.py  
│   │  
│   ├── ingestion/  
│   │   ├── \_\_init\_\_.py  
│   │   ├── register\_pdfs.py  
│   │   ├── pdf\_text\_extractor.py  
│   │   ├── pdf\_renderer.py  
│   │   └── preprocessing.py  
│   │  
│   ├── ai/  
│   │   ├── \_\_init\_\_.py  
│   │   ├── gemini\_client.py  
│   │   ├── prompt\_loader.py  
│   │   ├── run\_classification.py  
│   │   ├── run\_mapping.py  
│   │   ├── run\_scenario\_extraction.py  
│   │   ├── run\_outcome\_extraction.py  
│   │   └── run\_audit.py  
│   │  
│   ├── validation/  
│   │   ├── \_\_init\_\_.py  
│   │   ├── schema\_validator.py  
│   │   ├── codebook\_validator.py  
│   │   ├── business\_rules.py  
│   │   └── evidence\_validator.py  
│   │  
│   ├── database/  
│   │   ├── \_\_init\_\_.py  
│   │   ├── db.py  
│   │   ├── models.py  
│   │   ├── repository.py  
│   │   └── init\_db.py  
│   │  
│   ├── export/  
│   │   ├── \_\_init\_\_.py  
│   │   ├── export\_review\_excel.py  
│   │   ├── import\_human\_review.py  
│   │   ├── export\_csv.py  
│   │   └── freeze\_dataset.py  
│   │  
│   ├── workflow/  
│   │   ├── \_\_init\_\_.py  
│   │   ├── article\_workflow.py  
│   │   ├── resume\_manager.py  
│   │   └── status\_manager.py  
│   │  
│   └── utils/  
│       ├── \_\_init\_\_.py  
│       ├── hashing.py  
│       ├── logging\_config.py  
│       ├── paths.py  
│       └── timestamps.py  
│  
├── scripts/  
│   ├── 00\_init\_project.py  
│   ├── 01\_register\_pdfs.py  
│   ├── 02\_preprocess\_pdfs.py  
│   ├── 03\_process\_article.py  
│   ├── 04\_validate\_outputs.py  
│   ├── 05\_export\_review\_excel.py  
│   ├── 06\_import\_human\_review.py  
│   ├── 07\_freeze\_dataset.py  
│   └── 08\_status.py  
│  
├── tests/  
│   ├── test\_schema\_validation.py  
│   ├── test\_business\_rules.py  
│   ├── test\_codebook\_loading.py  
│   ├── test\_document\_registry.py  
│   └── test\_freeze\_dataset.py  
│  
└── docs/  
    ├── workflow.md  
    ├── database\_schema.md  
    ├── ai\_prompts.md  
    ├── validation\_rules.md  
    └── methodology\_note.md

---

# **6\. Variables de entorno**

El agente debe crear un archivo:

.env.example

Contenido:

\# Gemini API key from Google AI Studio  
GEMINI\_API\_KEY=your\_gemini\_api\_key\_here

\# Gemini models  
GEMINI\_MODEL\_FAST=gemini-2.5-flash  
GEMINI\_MODEL\_PRO=gemini-2.5-pro

\# Database  
DATABASE\_URL=sqlite:///data/project.sqlite

\# Runtime  
PROJECT\_ENV=local  
LOG\_LEVEL=INFO

El archivo `.gitignore` debe incluir:

.env  
data/project.sqlite  
data/00\_raw\_pdfs/\*  
data/01\_processed/\*  
data/02\_ai\_outputs/\*  
data/03\_human\_review/\*  
data/04\_frozen\_datasets/\*  
data/05\_logs/\*  
\_\_pycache\_\_/  
\*.pyc  
.DS\_Store

Importante:

Nunca guardar GEMINI\_API\_KEY dentro del código.  
Nunca incluir PDFs, outputs de IA ni bases SQLite en commits.

---

# **7\. Configuración general del proyecto**

Archivo:

config/project\_config.yaml

Contenido inicial:

project:  
  name: "meta\_ai\_extraction\_pipeline"  
  version: "0.1.0"  
  language: "es"  
  description: "Local AI-assisted extraction pipeline for systematic review and meta-analysis."

paths:  
  raw\_pdfs: "data/00\_raw\_pdfs"  
  processed: "data/01\_processed"  
  ai\_outputs: "data/02\_ai\_outputs"  
  human\_review: "data/03\_human\_review"  
  frozen\_datasets: "data/04\_frozen\_datasets"  
  logs: "data/05\_logs"  
  database: "data/project.sqlite"

workflow:  
  process\_mode: "article\_by\_article"  
  require\_human\_validation: true  
  allow\_batch\_processing: false  
  default\_articles\_per\_session: 1

ai:  
  provider: "gemini"  
  fast\_model\_env: "GEMINI\_MODEL\_FAST"  
  pro\_model\_env: "GEMINI\_MODEL\_PRO"  
  use\_structured\_outputs: true  
  save\_raw\_outputs: true  
  max\_retries: 2  
  timeout\_seconds: 300

documents:  
  allowed\_extensions:  
    \- ".pdf"  
  assign\_document\_codes: true  
  document\_code\_prefix: "A"  
  document\_code\_padding: 3

review:  
  export\_excel: true  
  require\_reviewer\_name: true  
  valid\_decisions:  
    \- accepted  
    \- corrected  
    \- rejected  
    \- unclear

---

# **8\. Codebook**

El codebook debe estar en YAML y ser editable.

Archivo:

config/codebook.yaml

Contenido inicial recomendado:

codebook:  
  version: "v01"  
  description: "Codebook for AI-assisted extraction of building simulation studies for systematic review/meta-analysis."

fields:

  \- field\_name: article\_title  
    entity\_level: article  
    label: "Article title"  
    definition: "Full title of the article."  
    data\_type: string  
    required: true  
    critical: false  
    evidence\_required: false  
    human\_validation\_required: false

  \- field\_name: authors  
    entity\_level: article  
    label: "Authors"  
    definition: "Authors of the article."  
    data\_type: string  
    required: true  
    critical: false  
    evidence\_required: false  
    human\_validation\_required: false

  \- field\_name: publication\_year  
    entity\_level: article  
    label: "Publication year"  
    definition: "Year of publication."  
    data\_type: integer  
    required: true  
    critical: false  
    evidence\_required: false  
    human\_validation\_required: false

  \- field\_name: doi  
    entity\_level: article  
    label: "DOI"  
    definition: "Digital Object Identifier if reported."  
    data\_type: string  
    required: false  
    critical: false  
    evidence\_required: false  
    human\_validation\_required: false

  \- field\_name: study\_type  
    entity\_level: article  
    label: "Study type"  
    definition: "Type of study design."  
    data\_type: categorical  
    allowed\_values:  
      \- simulation  
      \- measured  
      \- hybrid  
      \- review  
      \- unclear  
    required: true  
    critical: true  
    evidence\_required: true  
    human\_validation\_required: true

  \- field\_name: simulation\_software  
    entity\_level: article  
    label: "Simulation software"  
    definition: "Software or engine used for building performance simulation."  
    data\_type: string  
    required: false  
    critical: true  
    evidence\_required: true  
    human\_validation\_required: true  
    extraction\_instruction: "Extract only software explicitly mentioned, e.g., EnergyPlus, DesignBuilder, TRNSYS, IESVE, OpenStudio."

  \- field\_name: scenario\_label  
    entity\_level: scenario  
    label: "Scenario label"  
    definition: "Label or description of a specific simulation scenario, case, alternative, or model."  
    data\_type: string  
    required: true  
    critical: true  
    evidence\_required: true  
    human\_validation\_required: true

  \- field\_name: building\_typology  
    entity\_level: scenario  
    label: "Building typology"  
    definition: "Main building type evaluated in the scenario."  
    data\_type: categorical  
    allowed\_values:  
      \- residential  
      \- office  
      \- school  
      \- hospital  
      \- commercial  
      \- mixed\_use  
      \- prototype  
      \- other  
      \- unclear  
    required: true  
    critical: true  
    evidence\_required: true  
    human\_validation\_required: true

  \- field\_name: climate\_location  
    entity\_level: scenario  
    label: "Climate location"  
    definition: "City, country, region, or climate location used in the scenario."  
    data\_type: string  
    required: false  
    critical: true  
    evidence\_required: true  
    human\_validation\_required: true

  \- field\_name: climate\_zone  
    entity\_level: scenario  
    label: "Climate zone"  
    definition: "Climate classification if explicitly reported."  
    data\_type: string  
    required: false  
    critical: false  
    evidence\_required: true  
    human\_validation\_required: true

  \- field\_name: weather\_file  
    entity\_level: scenario  
    label: "Weather file"  
    definition: "Weather file or climate dataset used in the simulation."  
    data\_type: string  
    required: false  
    critical: false  
    evidence\_required: true  
    human\_validation\_required: true

  \- field\_name: baseline\_description  
    entity\_level: scenario  
    label: "Baseline description"  
    definition: "Description of the reference, control, or base case scenario."  
    data\_type: string  
    required: true  
    critical: true  
    evidence\_required: true  
    human\_validation\_required: true

  \- field\_name: intervention\_description  
    entity\_level: intervention  
    label: "Intervention description"  
    definition: "Description of the evaluated strategy, measure, or package."  
    data\_type: string  
    required: true  
    critical: true  
    evidence\_required: true  
    human\_validation\_required: true

  \- field\_name: intervention\_type  
    entity\_level: intervention  
    label: "Intervention type"  
    definition: "Type of strategy evaluated."  
    data\_type: categorical  
    allowed\_values:  
      \- insulation  
      \- glazing  
      \- shading  
      \- ventilation  
      \- hvac  
      \- passive\_design  
      \- renewable\_energy  
      \- controls  
      \- envelope  
      \- package  
      \- other  
      \- unclear  
    required: true  
    critical: true  
    evidence\_required: true  
    human\_validation\_required: true

  \- field\_name: is\_package  
    entity\_level: intervention  
    label: "Is package"  
    definition: "Whether the intervention combines multiple strategies."  
    data\_type: boolean  
    required: true  
    critical: true  
    evidence\_required: true  
    human\_validation\_required: true  
    extraction\_instruction: "If the paper reports a combined package, do not separate individual effects unless explicitly reported."

  \- field\_name: cooling\_demand  
    entity\_level: outcome  
    label: "Cooling demand"  
    definition: "Cooling energy demand for a specific scenario."  
    data\_type: numeric  
    original\_unit\_required: true  
    standard\_unit: "kWh/m2.year"  
    required: false  
    critical: true  
    evidence\_required: true  
    human\_validation\_required: true  
    allowed\_source\_types:  
      \- text  
      \- table  
      \- figure  
    extraction\_instruction: "Extract only if cooling demand is explicitly reported. Do not infer from total energy use."

  \- field\_name: heating\_demand  
    entity\_level: outcome  
    label: "Heating demand"  
    definition: "Heating energy demand for a specific scenario."  
    data\_type: numeric  
    original\_unit\_required: true  
    standard\_unit: "kWh/m2.year"  
    required: false  
    critical: true  
    evidence\_required: true  
    human\_validation\_required: true  
    allowed\_source\_types:  
      \- text  
      \- table  
      \- figure

  \- field\_name: total\_energy\_use  
    entity\_level: outcome  
    label: "Total energy use"  
    definition: "Total building energy use, consumption, or demand."  
    data\_type: numeric  
    original\_unit\_required: true  
    standard\_unit: "kWh/m2.year"  
    required: false  
    critical: true  
    evidence\_required: true  
    human\_validation\_required: true  
    allowed\_source\_types:  
      \- text  
      \- table  
      \- figure

  \- field\_name: carbon\_emissions  
    entity\_level: outcome  
    label: "Carbon emissions"  
    definition: "Operational carbon emissions or equivalent emissions."  
    data\_type: numeric  
    original\_unit\_required: true  
    standard\_unit: "kgCO2/m2.year"  
    required: false  
    critical: true  
    evidence\_required: true  
    human\_validation\_required: true

  \- field\_name: discomfort\_hours  
    entity\_level: outcome  
    label: "Discomfort hours"  
    definition: "Number of hours outside thermal comfort range."  
    data\_type: numeric  
    original\_unit\_required: true  
    standard\_unit: "h/year"  
    required: false  
    critical: true  
    evidence\_required: true  
    human\_validation\_required: true

  \- field\_name: indoor\_temperature  
    entity\_level: outcome  
    label: "Indoor temperature"  
    definition: "Reported indoor temperature outcome."  
    data\_type: numeric  
    original\_unit\_required: true  
    standard\_unit: "degC"  
    required: false  
    critical: false  
    evidence\_required: true  
    human\_validation\_required: true

---

# **9\. Vocabularios controlados**

Archivo:

config/controlled\_vocabularies.yaml

Contenido:

study\_type:  
  \- simulation  
  \- measured  
  \- hybrid  
  \- review  
  \- unclear

source\_type:  
  \- text  
  \- table  
  \- figure  
  \- mixed  
  \- not\_found

record\_status:  
  \- pending  
  \- pre\_extracted  
  \- extracted  
  \- not\_found  
  \- unclear  
  \- needs\_digitization  
  \- blocked  
  \- human\_review\_required  
  \- validated  
  \- rejected

building\_typology:  
  \- residential  
  \- office  
  \- school  
  \- hospital  
  \- commercial  
  \- mixed\_use  
  \- prototype  
  \- other  
  \- unclear

intervention\_type:  
  \- insulation  
  \- glazing  
  \- shading  
  \- ventilation  
  \- hvac  
  \- passive\_design  
  \- renewable\_energy  
  \- controls  
  \- envelope  
  \- package  
  \- other  
  \- unclear

effect\_direction:  
  \- increase  
  \- reduction  
  \- neutral  
  \- unclear

review\_decision:  
  \- accepted  
  \- corrected  
  \- rejected  
  \- unclear

---

# **10\. Reglas de extracción y bloqueo**

Archivo:

config/extraction\_rules.yaml

Contenido:

rules:  
  no\_guessing:  
    enabled: true  
    description: "If evidence is not explicit, return null and status not\_found or unclear."

  evidence\_required\_for\_critical\_fields:  
    enabled: true  
    action\_if\_missing: "block"

  page\_required\_for\_extracted\_values:  
    enabled: true  
    action\_if\_missing: "block"

  unit\_required\_for\_numeric\_outcomes:  
    enabled: true  
    action\_if\_missing: "block"

  figure\_values\_require\_digitization:  
    enabled: true  
    action\_if\_violation: "set\_needs\_digitization"

  baseline\_intervention\_pair\_required:  
    enabled: true  
    action\_if\_missing: "unclear"

  do\_not\_split\_packages\_without\_explicit\_reporting:  
    enabled: true  
    action\_if\_violation: "block"

  do\_not\_mix\_scenarios:  
    enabled: true  
    action\_if\_violation: "block"

  raw\_ai\_output\_must\_be\_saved:  
    enabled: true

  human\_validation\_required\_for\_critical\_fields:  
    enabled: true

blocking\_conditions:  
  \- name: "missing\_page"  
    condition: "status \== extracted and page is null"  
    action: "block"

  \- name: "missing\_evidence"  
    condition: "critical \== true and evidence\_text is null and crop\_path is null"  
    action: "block"

  \- name: "missing\_numeric\_unit"  
    condition: "numeric\_value\_present \== true and unit is null"  
    action: "block"

  \- name: "figure\_without\_digitization"  
    condition: "source\_type \== figure and needs\_digitization \== false"  
    action: "set\_needs\_digitization"

  \- name: "unknown\_codebook\_field"  
    condition: "field\_name not in codebook"  
    action: "reject"

---

# **11\. Prompts en YAML**

Los prompts deben estar en un único archivo editable:

prompts/prompts.yaml

No deben estar hardcodeados en scripts.

Contenido:

prompts\_version: "v01"

global\_system\_prompt: |  
  You are an AI assistant supporting data extraction for a systematic review and meta-analysis of building performance studies.

  Your role is not to interpret freely or complete missing information.  
  Your role is to locate, structure, and report data explicitly present in the provided document.

  Mandatory rules:  
  1\. Use only the provided document content.  
  2\. Do not use external knowledge.  
  3\. Do not infer missing values.  
  4\. If a value is not explicitly reported, return null and status \= "not\_found" or "unclear".  
  5\. Every critical extracted value must include evidence: page number, source type, table/figure/section, and evidence text or crop reference.  
  6\. Do not combine different scenarios.  
  7\. Do not split intervention packages unless the paper explicitly reports separate effects.  
  8\. Do not calculate final effect sizes unless baseline and intervention values are clearly paired.  
  9\. If a value is only available in a figure, mark needs\_digitization \= true.  
  10\. Return only valid JSON following the requested schema.

classification\_prompt: |  
  TASK: Article classification.

  Analyze the provided PDF/text and classify the article for a systematic review/meta-analysis.

  Determine:  
  \- study type  
  \- whether the article is extractable  
  \- whether it includes simulations  
  \- whether it includes numerical outcomes  
  \- whether it includes tables  
  \- whether it includes figures  
  \- whether multiple scenarios/cases are present

  Use the codebook definitions provided below.  
  Return only JSON following the classification schema.

mapping\_prompt: |  
  TASK: Structural mapping of the article.

  Before extracting numerical outcomes, identify the internal structure of the article.

  Identify:  
  \- simulation software  
  \- building typologies  
  \- climate locations  
  \- climate zones  
  \- baselines  
  \- interventions  
  \- whether interventions are individual strategies or packages  
  \- scenarios/cases/models  
  \- reported outcomes  
  \- relevant tables  
  \- relevant figures  
  \- risks for extraction

  Important:  
  \- One article can contain multiple scenarios.  
  \- A scenario may correspond to a simulation case, building type, climate case, intervention package, or baseline/intervention comparison.  
  \- Do not extract final numerical outcomes in this step.  
  \- If the structure is ambiguous, mark status \= "unclear".

  Return only JSON following the mapping schema.

scenario\_extraction\_prompt: |  
  TASK: Scenario extraction.

  Extract structured information for each scenario identified in the article.

  A scenario is a specific simulation/model/case/comparison that may include:  
  \- building typology  
  \- climate location  
  \- baseline  
  \- intervention or package  
  \- simulation software  
  \- assumptions  
  \- reported outcomes

  Rules:  
  \- Create one record per scenario.  
  \- Do not merge different scenarios.  
  \- Do not invent scenario labels.  
  \- If a scenario is unclear, mark status \= "unclear".  
  \- Include evidence for each scenario.

  Return only JSON following the scenario extraction schema.

outcome\_extraction\_prompt: |  
  TASK: Outcome extraction.

  Extract numerical outcomes by scenario.

  Extract only values explicitly reported in the article.  
  For each outcome, report:  
  \- scenario identifier  
  \- outcome name  
  \- baseline value and unit if available  
  \- intervention value and unit if available  
  \- reported effect if available  
  \- source type  
  \- page  
  \- table or figure label  
  \- evidence text  
  \- whether digitization is required

  Rules:  
  \- Do not calculate values not explicitly reported unless the prompt explicitly asks for a simple paired difference and both values are present.  
  \- Do not convert units unless the original unit is explicit.  
  \- If the value is in a figure, mark needs\_digitization \= true.  
  \- If baseline and intervention are not clearly paired, mark status \= "unclear".  
  \- If no value is found, return null and status \= "not\_found".

  Return only JSON following the outcome extraction schema.

audit\_prompt: |  
  TASK: Audit the previous AI extraction.

  Compare the extracted data against the provided document text and evidence.

  Identify:  
  \- missing evidence  
  \- missing units  
  \- unsupported inferences  
  \- mixed scenarios  
  \- separated packages without explicit reporting  
  \- figure-derived values not marked for digitization  
  \- duplicate outcomes  
  \- ambiguous baselines  
  \- extraction omissions

  Do not correct data unless explicit evidence is available.  
  Instead, flag issues and required actions.

  Return only JSON following the audit schema.

---

# **12\. Schemas JSON**

Los schemas deben estar en `/schemas/`.

## **12.1 `classification.schema.json`**

{  
  "$schema": "http://json-schema.org/draft-07/schema\#",  
  "title": "ClassificationOutput",  
  "type": "object",  
  "additionalProperties": false,  
  "required": \[  
    "document\_id",  
    "study\_type",  
    "is\_extractable",  
    "has\_simulation",  
    "has\_numeric\_outcomes",  
    "has\_tables",  
    "has\_figures",  
    "has\_multiple\_scenarios",  
    "reason",  
    "status",  
    "human\_review\_required"  
  \],  
  "properties": {  
    "document\_id": {  
      "type": "string"  
    },  
    "study\_type": {  
      "type": "string",  
      "enum": \[  
        "simulation",  
        "measured",  
        "hybrid",  
        "review",  
        "unclear"  
      \]  
    },  
    "is\_extractable": {  
      "type": \[  
        "boolean",  
        "null"  
      \]  
    },  
    "has\_simulation": {  
      "type": \[  
        "boolean",  
        "null"  
      \]  
    },  
    "has\_numeric\_outcomes": {  
      "type": \[  
        "boolean",  
        "null"  
      \]  
    },  
    "has\_tables": {  
      "type": \[  
        "boolean",  
        "null"  
      \]  
    },  
    "has\_figures": {  
      "type": \[  
        "boolean",  
        "null"  
      \]  
    },  
    "has\_multiple\_scenarios": {  
      "type": \[  
        "boolean",  
        "null"  
      \]  
    },  
    "simulation\_software": {  
      "type": "array",  
      "items": {  
        "type": "object",  
        "additionalProperties": false,  
        "required": \[  
          "value",  
          "page",  
          "evidence\_text"  
        \],  
        "properties": {  
          "value": {  
            "type": \[  
              "string",  
              "null"  
            \]  
          },  
          "page": {  
            "type": \[  
              "integer",  
              "null"  
            \]  
          },  
          "evidence\_text": {  
            "type": \[  
              "string",  
              "null"  
            \]  
          }  
        }  
      }  
    },  
    "reason": {  
      "type": \[  
        "string",  
        "null"  
      \]  
    },  
    "status": {  
      "type": "string",  
      "enum": \[  
        "ready\_for\_mapping",  
        "not\_extractable",  
        "needs\_human\_review",  
        "unclear"  
      \]  
    },  
    "human\_review\_required": {  
      "type": "boolean"  
    }  
  }  
}

---

## **12.2 `mapping.schema.json`**

{  
  "$schema": "http://json-schema.org/draft-07/schema\#",  
  "title": "MappingOutput",  
  "type": "object",  
  "additionalProperties": false,  
  "required": \[  
    "document\_id",  
    "article\_summary",  
    "scenario\_inventory",  
    "relevant\_tables",  
    "relevant\_figures",  
    "mapping\_warnings"  
  \],  
  "properties": {  
    "document\_id": {  
      "type": "string"  
    },  
    "article\_summary": {  
      "type": \[  
        "string",  
        "null"  
      \]  
    },  
    "scenario\_inventory": {  
      "type": "array",  
      "items": {  
        "type": "object",  
        "additionalProperties": false,  
        "required": \[  
          "scenario\_temp\_id",  
          "scenario\_label",  
          "building\_typology",  
          "climate\_location",  
          "climate\_zone",  
          "baseline\_present",  
          "intervention\_present",  
          "intervention\_summary",  
          "reported\_outcomes",  
          "evidence",  
          "status",  
          "uncertainty"  
        \],  
        "properties": {  
          "scenario\_temp\_id": {  
            "type": "string"  
          },  
          "scenario\_label": {  
            "type": \[  
              "string",  
              "null"  
            \]  
          },  
          "building\_typology": {  
            "type": \[  
              "string",  
              "null"  
            \]  
          },  
          "climate\_location": {  
            "type": \[  
              "string",  
              "null"  
            \]  
          },  
          "climate\_zone": {  
            "type": \[  
              "string",  
              "null"  
            \]  
          },  
          "baseline\_present": {  
            "type": \[  
              "boolean",  
              "null"  
            \]  
          },  
          "intervention\_present": {  
            "type": \[  
              "boolean",  
              "null"  
            \]  
          },  
          "intervention\_summary": {  
            "type": \[  
              "string",  
              "null"  
            \]  
          },  
          "reported\_outcomes": {  
            "type": "array",  
            "items": {  
              "type": "string"  
            }  
          },  
          "evidence": {  
            "type": "object",  
            "additionalProperties": false,  
            "required": \[  
              "page",  
              "source\_type",  
              "table\_or\_figure",  
              "evidence\_text"  
            \],  
            "properties": {  
              "page": {  
                "type": \[  
                  "integer",  
                  "null"  
                \]  
              },  
              "source\_type": {  
                "type": \[  
                  "string",  
                  "null"  
                \],  
                "enum": \[  
                  "text",  
                  "table",  
                  "figure",  
                  "mixed",  
                  "not\_found",  
                  null  
                \]  
              },  
              "table\_or\_figure": {  
                "type": \[  
                  "string",  
                  "null"  
                \]  
              },  
              "evidence\_text": {  
                "type": \[  
                  "string",  
                  "null"  
                \]  
              }  
            }  
          },  
          "status": {  
            "type": "string",  
            "enum": \[  
              "mapped",  
              "unclear",  
              "not\_found"  
            \]  
          },  
          "uncertainty": {  
            "type": "string",  
            "enum": \[  
              "low",  
              "medium",  
              "high"  
            \]  
          }  
        }  
      }  
    },  
    "relevant\_tables": {  
      "type": "array",  
      "items": {  
        "type": "object",  
        "additionalProperties": false,  
        "required": \[  
          "page",  
          "label",  
          "reason"  
        \],  
        "properties": {  
          "page": {  
            "type": \[  
              "integer",  
              "null"  
            \]  
          },  
          "label": {  
            "type": \[  
              "string",  
              "null"  
            \]  
          },  
          "reason": {  
            "type": \[  
              "string",  
              "null"  
            \]  
          }  
        }  
      }  
    },  
    "relevant\_figures": {  
      "type": "array",  
      "items": {  
        "type": "object",  
        "additionalProperties": false,  
        "required": \[  
          "page",  
          "label",  
          "reason",  
          "requires\_digitization"  
        \],  
        "properties": {  
          "page": {  
            "type": \[  
              "integer",  
              "null"  
            \]  
          },  
          "label": {  
            "type": \[  
              "string",  
              "null"  
            \]  
          },  
          "reason": {  
            "type": \[  
              "string",  
              "null"  
            \]  
          },  
          "requires\_digitization": {  
            "type": \[  
              "boolean",  
              "null"  
            \]  
          }  
        }  
      }  
    },  
    "mapping\_warnings": {  
      "type": "array",  
      "items": {  
        "type": "string"  
      }  
    }  
  }  
}

---

## **12.3 `scenario_extraction.schema.json`**

{  
  "$schema": "http://json-schema.org/draft-07/schema\#",  
  "title": "ScenarioExtractionOutput",  
  "type": "object",  
  "additionalProperties": false,  
  "required": \[  
    "document\_id",  
    "scenarios"  
  \],  
  "properties": {  
    "document\_id": {  
      "type": "string"  
    },  
    "scenarios": {  
      "type": "array",  
      "items": {  
        "type": "object",  
        "additionalProperties": false,  
        "required": \[  
          "scenario\_temp\_id",  
          "scenario\_label",  
          "building\_typology",  
          "climate\_location",  
          "climate\_zone",  
          "weather\_file",  
          "simulation\_software",  
          "baseline\_description",  
          "intervention\_description",  
          "intervention\_type",  
          "is\_package",  
          "package\_components",  
          "reported\_outcomes",  
          "page",  
          "source\_type",  
          "evidence\_text",  
          "status",  
          "human\_review\_required"  
        \],  
        "properties": {  
          "scenario\_temp\_id": {  
            "type": "string"  
          },  
          "scenario\_label": {  
            "type": \[  
              "string",  
              "null"  
            \]  
          },  
          "building\_typology": {  
            "type": \[  
              "string",  
              "null"  
            \]  
          },  
          "climate\_location": {  
            "type": \[  
              "string",  
              "null"  
            \]  
          },  
          "climate\_zone": {  
            "type": \[  
              "string",  
              "null"  
            \]  
          },  
          "weather\_file": {  
            "type": \[  
              "string",  
              "null"  
            \]  
          },  
          "simulation\_software": {  
            "type": \[  
              "string",  
              "null"  
            \]  
          },  
          "baseline\_description": {  
            "type": \[  
              "string",  
              "null"  
            \]  
          },  
          "intervention\_description": {  
            "type": \[  
              "string",  
              "null"  
            \]  
          },  
          "intervention\_type": {  
            "type": \[  
              "string",  
              "null"  
            \]  
          },  
          "is\_package": {  
            "type": \[  
              "boolean",  
              "null"  
            \]  
          },  
          "package\_components": {  
            "type": "array",  
            "items": {  
              "type": "string"  
            }  
          },  
          "reported\_outcomes": {  
            "type": "array",  
            "items": {  
              "type": "string"  
            }  
          },  
          "page": {  
            "type": \[  
              "integer",  
              "null"  
            \]  
          },  
          "source\_type": {  
            "type": \[  
              "string",  
              "null"  
            \],  
            "enum": \[  
              "text",  
              "table",  
              "figure",  
              "mixed",  
              "not\_found",  
              null  
            \]  
          },  
          "evidence\_text": {  
            "type": \[  
              "string",  
              "null"  
            \]  
          },  
          "status": {  
            "type": "string",  
            "enum": \[  
              "extracted",  
              "not\_found",  
              "unclear",  
              "blocked"  
            \]  
          },  
          "human\_review\_required": {  
            "type": "boolean"  
          }  
        }  
      }  
    }  
  }  
}

---

## **12.4 `outcome_extraction.schema.json`**

{  
  "$schema": "http://json-schema.org/draft-07/schema\#",  
  "title": "OutcomeExtractionOutput",  
  "type": "object",  
  "additionalProperties": false,  
  "required": \[  
    "document\_id",  
    "extracted\_outcomes"  
  \],  
  "properties": {  
    "document\_id": {  
      "type": "string"  
    },  
    "extracted\_outcomes": {  
      "type": "array",  
      "items": {  
        "type": "object",  
        "additionalProperties": false,  
        "required": \[  
          "outcome\_temp\_id",  
          "scenario\_temp\_id",  
          "outcome\_name",  
          "baseline\_value",  
          "baseline\_unit",  
          "intervention\_value",  
          "intervention\_unit",  
          "reported\_effect\_value",  
          "reported\_effect\_unit",  
          "effect\_direction",  
          "source\_type",  
          "page",  
          "table\_or\_figure",  
          "row\_label",  
          "column\_label\_baseline",  
          "column\_label\_intervention",  
          "evidence\_text",  
          "needs\_digitization",  
          "status",  
          "human\_review\_required"  
        \],  
        "properties": {  
          "outcome\_temp\_id": {  
            "type": "string"  
          },  
          "scenario\_temp\_id": {  
            "type": \[  
              "string",  
              "null"  
            \]  
          },  
          "outcome\_name": {  
            "type": "string"  
          },  
          "baseline\_value": {  
            "type": \[  
              "number",  
              "null"  
            \]  
          },  
          "baseline\_unit": {  
            "type": \[  
              "string",  
              "null"  
            \]  
          },  
          "intervention\_value": {  
            "type": \[  
              "number",  
              "null"  
            \]  
          },  
          "intervention\_unit": {  
            "type": \[  
              "string",  
              "null"  
            \]  
          },  
          "reported\_effect\_value": {  
            "type": \[  
              "number",  
              "null"  
            \]  
          },  
          "reported\_effect\_unit": {  
            "type": \[  
              "string",  
              "null"  
            \]  
          },  
          "effect\_direction": {  
            "type": "string",  
            "enum": \[  
              "increase",  
              "reduction",  
              "neutral",  
              "unclear"  
            \]  
          },  
          "source\_type": {  
            "type": "string",  
            "enum": \[  
              "text",  
              "table",  
              "figure",  
              "mixed",  
              "not\_found"  
            \]  
          },  
          "page": {  
            "type": \[  
              "integer",  
              "null"  
            \]  
          },  
          "table\_or\_figure": {  
            "type": \[  
              "string",  
              "null"  
            \]  
          },  
          "row\_label": {  
            "type": \[  
              "string",  
              "null"  
            \]  
          },  
          "column\_label\_baseline": {  
            "type": \[  
              "string",  
              "null"  
            \]  
          },  
          "column\_label\_intervention": {  
            "type": \[  
              "string",  
              "null"  
            \]  
          },  
          "evidence\_text": {  
            "type": \[  
              "string",  
              "null"  
            \]  
          },  
          "needs\_digitization": {  
            "type": "boolean"  
          },  
          "status": {  
            "type": "string",  
            "enum": \[  
              "extracted",  
              "not\_found",  
              "unclear",  
              "needs\_digitization",  
              "blocked"  
            \]  
          },  
          "human\_review\_required": {  
            "type": "boolean"  
          }  
        }  
      }  
    }  
  }  
}

---

## **12.5 `audit.schema.json`**

{  
  "$schema": "http://json-schema.org/draft-07/schema\#",  
  "title": "AuditOutput",  
  "type": "object",  
  "additionalProperties": false,  
  "required": \[  
    "document\_id",  
    "audit\_status",  
    "issues",  
    "fields\_to\_block",  
    "records\_ready\_for\_review"  
  \],  
  "properties": {  
    "document\_id": {  
      "type": "string"  
    },  
    "audit\_status": {  
      "type": "string",  
      "enum": \[  
        "pass",  
        "minor\_issues",  
        "major\_issues"  
      \]  
    },  
    "issues": {  
      "type": "array",  
      "items": {  
        "type": "object",  
        "additionalProperties": false,  
        "required": \[  
          "severity",  
          "issue\_type",  
          "affected\_record",  
          "description",  
          "required\_action"  
        \],  
        "properties": {  
          "severity": {  
            "type": "string",  
            "enum": \[  
              "low",  
              "medium",  
              "high"  
            \]  
          },  
          "issue\_type": {  
            "type": "string",  
            "enum": \[  
              "missing\_evidence",  
              "missing\_unit",  
              "missing\_page",  
              "scenario\_mixing",  
              "unsupported\_inference",  
              "digitization\_needed",  
              "duplicate\_outcome",  
              "ambiguous\_baseline",  
              "package\_split\_error",  
              "unknown\_field",  
              "other"  
            \]  
          },  
          "affected\_record": {  
            "type": \[  
              "string",  
              "null"  
            \]  
          },  
          "description": {  
            "type": "string"  
          },  
          "required\_action": {  
            "type": "string"  
          }  
        }  
      }  
    },  
    "fields\_to\_block": {  
      "type": "array",  
      "items": {  
        "type": "string"  
      }  
    },  
    "records\_ready\_for\_review": {  
      "type": "array",  
      "items": {  
        "type": "string"  
      }  
    }  
  }  
}

---

# **13\. Base de datos SQLite**

El agente debe crear las siguientes tablas.

## **13.1 `documents`**

CREATE TABLE IF NOT EXISTS documents (  
  id TEXT PRIMARY KEY,  
  document\_code TEXT UNIQUE NOT NULL,  
  file\_name TEXT NOT NULL,  
  file\_path TEXT NOT NULL,  
  file\_hash TEXT NOT NULL,  
  status TEXT NOT NULL,  
  current\_step TEXT,  
  created\_at TEXT NOT NULL,  
  updated\_at TEXT NOT NULL  
);

Estados posibles:

pending  
preprocessed  
classified  
mapped  
scenarios\_extracted  
outcomes\_extracted  
audited  
needs\_human\_review  
validated  
failed

---

## **13.2 `pages`**

CREATE TABLE IF NOT EXISTS pages (  
  id TEXT PRIMARY KEY,  
  document\_id TEXT NOT NULL,  
  page\_number INTEGER NOT NULL,  
  text\_path TEXT,  
  image\_path TEXT,  
  text\_char\_count INTEGER,  
  created\_at TEXT NOT NULL,  
  FOREIGN KEY(document\_id) REFERENCES documents(id)  
);

---

## **13.3 `ai_runs`**

CREATE TABLE IF NOT EXISTS ai\_runs (  
  id TEXT PRIMARY KEY,  
  document\_id TEXT NOT NULL,  
  task\_type TEXT NOT NULL,  
  model\_name TEXT NOT NULL,  
  prompt\_version TEXT NOT NULL,  
  schema\_name TEXT NOT NULL,  
  schema\_version TEXT,  
  codebook\_version TEXT,  
  input\_hash TEXT NOT NULL,  
  output\_json\_path TEXT NOT NULL,  
  parsed\_successfully INTEGER NOT NULL,  
  error\_message TEXT,  
  created\_at TEXT NOT NULL,  
  FOREIGN KEY(document\_id) REFERENCES documents(id)  
);

---

## **13.4 `article_classification`**

CREATE TABLE IF NOT EXISTS article\_classification (  
  id TEXT PRIMARY KEY,  
  document\_id TEXT NOT NULL,  
  study\_type TEXT,  
  is\_extractable INTEGER,  
  has\_simulation INTEGER,  
  has\_numeric\_outcomes INTEGER,  
  has\_tables INTEGER,  
  has\_figures INTEGER,  
  has\_multiple\_scenarios INTEGER,  
  reason TEXT,  
  status TEXT,  
  human\_review\_required INTEGER,  
  created\_at TEXT NOT NULL,  
  FOREIGN KEY(document\_id) REFERENCES documents(id)  
);

---

## **13.5 `scenarios`**

CREATE TABLE IF NOT EXISTS scenarios (  
  id TEXT PRIMARY KEY,  
  document\_id TEXT NOT NULL,  
  scenario\_code TEXT NOT NULL,  
  scenario\_temp\_id TEXT,  
  scenario\_label TEXT,  
  building\_typology TEXT,  
  climate\_location TEXT,  
  climate\_zone TEXT,  
  weather\_file TEXT,  
  simulation\_software TEXT,  
  baseline\_description TEXT,  
  intervention\_description TEXT,  
  intervention\_type TEXT,  
  is\_package INTEGER,  
  package\_components TEXT,  
  status TEXT NOT NULL,  
  human\_validated INTEGER DEFAULT 0,  
  created\_at TEXT NOT NULL,  
  updated\_at TEXT NOT NULL,  
  FOREIGN KEY(document\_id) REFERENCES documents(id)  
);

---

## **13.6 `outcomes`**

CREATE TABLE IF NOT EXISTS outcomes (  
  id TEXT PRIMARY KEY,  
  document\_id TEXT NOT NULL,  
  scenario\_id TEXT,  
  outcome\_code TEXT,  
  outcome\_temp\_id TEXT,  
  outcome\_name TEXT NOT NULL,  
  baseline\_value REAL,  
  baseline\_unit TEXT,  
  intervention\_value REAL,  
  intervention\_unit TEXT,  
  reported\_effect\_value REAL,  
  reported\_effect\_unit TEXT,  
  calculated\_effect\_value REAL,  
  calculated\_effect\_type TEXT,  
  standardized\_baseline\_value REAL,  
  standardized\_intervention\_value REAL,  
  standardized\_unit TEXT,  
  effect\_direction TEXT,  
  source\_type TEXT,  
  page INTEGER,  
  table\_or\_figure TEXT,  
  row\_label TEXT,  
  column\_label\_baseline TEXT,  
  column\_label\_intervention TEXT,  
  needs\_digitization INTEGER DEFAULT 0,  
  status TEXT NOT NULL,  
  human\_validated INTEGER DEFAULT 0,  
  created\_at TEXT NOT NULL,  
  updated\_at TEXT NOT NULL,  
  FOREIGN KEY(document\_id) REFERENCES documents(id),  
  FOREIGN KEY(scenario\_id) REFERENCES scenarios(id)  
);

---

## **13.7 `evidence`**

CREATE TABLE IF NOT EXISTS evidence (  
  id TEXT PRIMARY KEY,  
  document\_id TEXT NOT NULL,  
  linked\_table TEXT NOT NULL,  
  linked\_record\_id TEXT NOT NULL,  
  page\_number INTEGER,  
  source\_type TEXT,  
  table\_or\_figure\_label TEXT,  
  row\_label TEXT,  
  column\_label TEXT,  
  evidence\_text TEXT,  
  crop\_path TEXT,  
  validation\_status TEXT,  
  created\_at TEXT NOT NULL,  
  FOREIGN KEY(document\_id) REFERENCES documents(id)  
);

---

## **13.8 `qa_log`**

CREATE TABLE IF NOT EXISTS qa\_log (  
  id TEXT PRIMARY KEY,  
  document\_id TEXT NOT NULL,  
  record\_type TEXT,  
  record\_id TEXT,  
  severity TEXT,  
  issue\_type TEXT,  
  description TEXT,  
  required\_action TEXT,  
  resolved INTEGER DEFAULT 0,  
  created\_at TEXT NOT NULL,  
  FOREIGN KEY(document\_id) REFERENCES documents(id)  
);

---

## **13.9 `human_review`**

CREATE TABLE IF NOT EXISTS human\_review (  
  id TEXT PRIMARY KEY,  
  document\_id TEXT NOT NULL,  
  record\_type TEXT NOT NULL,  
  record\_id TEXT NOT NULL,  
  field\_name TEXT NOT NULL,  
  ai\_value TEXT,  
  human\_value TEXT,  
  decision TEXT NOT NULL,  
  reviewer TEXT,  
  reviewer\_comment TEXT,  
  reviewed\_at TEXT,  
  FOREIGN KEY(document\_id) REFERENCES documents(id)  
);

---

## **13.10 `digitization_tasks`**

CREATE TABLE IF NOT EXISTS digitization\_tasks (  
  id TEXT PRIMARY KEY,  
  document\_id TEXT NOT NULL,  
  outcome\_id TEXT,  
  page INTEGER,  
  figure\_label TEXT,  
  crop\_path TEXT,  
  reason TEXT,  
  status TEXT NOT NULL,  
  digitized\_value REAL,  
  digitized\_unit TEXT,  
  digitized\_by TEXT,  
  checked\_by TEXT,  
  created\_at TEXT NOT NULL,  
  updated\_at TEXT NOT NULL,  
  FOREIGN KEY(document\_id) REFERENCES documents(id),  
  FOREIGN KEY(outcome\_id) REFERENCES outcomes(id)  
);

---

# **14\. Flujo artículo por artículo**

El sistema debe permitir que el investigador procese los documentos uno por uno.

## **14.1 Comando para ver estado**

python scripts/08\_status.py

Debe mostrar algo como:

Project status

A001 | validated  
A002 | validated  
A003 | audited | needs\_human\_review  
A004 | pending  
A005 | pending  
...

## **14.2 Comando para procesar un artículo específico**

python scripts/03\_process\_article.py \--document A016

## **14.3 Comando interactivo para continuar**

python scripts/03\_process\_article.py \--interactive

El sistema debe preguntar:

Detected documents:

A001 validated  
A002 validated  
...  
A015 validated  
A016 pending  
A017 pending

Where do you want to continue from?  
\> A016

How many articles do you want to process this session?  
\> 6

The system will process:  
A016, A017, A018, A019, A020, A021

Continue? \[y/n\]

Luego debe procesar cada artículo secuencialmente.

Después de cada artículo:

A016 completed.  
Status: needs\_human\_review.

Options:  
1\. Continue to A017  
2\. Stop here  
3\. Export review Excel  
4\. Show issues

El sistema no debe continuar automáticamente si el artículo falla de forma crítica.

---

# **15\. Flujo de procesamiento de un artículo**

Para cada artículo, el script debe ejecutar:

1\. Verificar que el PDF existe.  
2\. Verificar que el documento está registrado.  
3\. Preprocesar PDF si no está preprocesado.  
4\. Ejecutar clasificación IA.  
5\. Validar classification.json.  
6\. Guardar classification.json.  
7\. Insertar classification en SQLite.  
8\. Si no es extraíble, marcar y detener.  
9\. Ejecutar mapeo estructural IA.  
10\. Validar mapping.json.  
11\. Guardar mapping.json.  
12\. Insertar escenarios preliminares.  
13\. Ejecutar extracción de escenarios IA.  
14\. Validar scenario\_extraction.json.  
15\. Insertar escenarios.  
16\. Ejecutar extracción de outcomes IA.  
17\. Validar outcome\_extraction.json.  
18\. Insertar outcomes pre-extraídos.  
19\. Crear evidence records.  
20\. Crear digitization\_tasks si aplica.  
21\. Ejecutar auditoría IA.  
22\. Validar audit.json.  
23\. Insertar qa\_log.  
24\. Aplicar reglas de bloqueo.  
25\. Marcar documento como needs\_human\_review.

---

# **16\. Outputs esperados por documento**

Para cada documento `A001`, el sistema debe crear:

data/01\_processed/A001/  
├── metadata.json  
├── pages\_text/  
│   ├── page\_001.txt  
│   ├── page\_002.txt  
│   └── ...  
└── pages\_images/  
    ├── page\_001.png  
    ├── page\_002.png  
    └── ...

data/02\_ai\_outputs/A001/  
├── classification.json  
├── mapping.json  
├── scenario\_extraction.json  
├── outcome\_extraction.json  
└── audit.json

Cada JSON debe guardarse aunque luego falle la validación. Si falla, debe registrarse en `ai_runs`.

---

# **17\. Validadores obligatorios**

El agente debe implementar validadores en:

src/validation/

## **17.1 Validación de schema**

schema\_validator.py

Debe:

\- Cargar el schema correspondiente.  
\- Validar el JSON.  
\- Devolver errores claros.  
\- Registrar errores en logs y ai\_runs.

## **17.2 Validación contra codebook**

codebook\_validator.py

Debe revisar:

\- outcome\_name existe en codebook.  
\- entity\_level es coherente.  
\- tipo de dato es coherente.  
\- unidad obligatoria si el campo lo exige.  
\- fuente permitida si el campo restringe allowed\_source\_types.

## **17.3 Reglas de negocio/metodológicas**

business\_rules.py

Debe bloquear:

\- Dato numérico sin unidad.  
\- Dato crítico sin evidencia.  
\- Dato extraído sin página.  
\- Figura sin needs\_digitization.  
\- Escenario sin baseline si el outcome requiere comparador.  
\- Paquete de estrategias separado sin evidencia explícita.  
\- Campos desconocidos.

## **17.4 Validación de evidencia**

evidence\_validator.py

Debe comprobar:

\- La página existe.  
\- El source\_type es válido.  
\- Si hay table\_or\_figure, debe guardarse como string.  
\- Si no hay evidence\_text ni crop\_path, la evidencia es insuficiente.

---

# **18\. Exportación a Excel para revisión humana**

Comando:

python scripts/05\_export\_review\_excel.py

Debe generar:

data/03\_human\_review/extraction\_review.xlsx

Hojas:

00\_README  
01\_DOCUMENTS  
02\_SCENARIOS  
03\_OUTCOMES  
04\_EVIDENCE  
05\_QA\_LOG  
06\_HUMAN\_REVIEW  
07\_DIGITIZATION\_TASKS

La hoja `03_OUTCOMES` debe incluir:

document\_code  
scenario\_code  
outcome\_name  
baseline\_value  
baseline\_unit  
intervention\_value  
intervention\_unit  
reported\_effect\_value  
reported\_effect\_unit  
source\_type  
page  
table\_or\_figure  
evidence\_text  
needs\_digitization  
status  
human\_decision  
human\_baseline\_value  
human\_intervention\_value  
human\_unit  
reviewer  
reviewer\_comment

Valores permitidos para `human_decision`:

accepted  
corrected  
rejected  
unclear

---

# **19\. Importación de revisión humana**

Comando:

python scripts/06\_import\_human\_review.py \--file data/03\_human\_review/extraction\_review.xlsx

Debe:

1\. Leer decisiones humanas.  
2\. Validar que los IDs existen.  
3\. Insertar decisiones en human\_review.  
4\. Actualizar human\_validated.  
5\. No borrar valores IA originales.  
6\. Guardar valores humanos como corrección.  
7\. Registrar timestamp y reviewer.

Regla:

La IA nunca sobrescribe la revisión humana.

---

# **20\. Congelación del dataset**

Comando:

python scripts/07\_freeze\_dataset.py \--version v01

Debe generar:

data/04\_frozen\_datasets/data\_frozen\_v01.xlsx  
data/04\_frozen\_datasets/data\_frozen\_v01.csv  
data/04\_frozen\_datasets/changelog\_v01.md  
data/04\_frozen\_datasets/manifest\_v01.json

El `manifest_v01.json` debe incluir:

{  
  "dataset\_version": "v01",  
  "created\_at": "ISO\_TIMESTAMP",  
  "codebook\_version": "v01",  
  "prompts\_version": "v01",  
  "schemas": \[  
    "classification.schema.json",  
    "mapping.schema.json",  
    "scenario\_extraction.schema.json",  
    "outcome\_extraction.schema.json",  
    "audit.schema.json"  
  \],  
  "number\_of\_documents": 0,  
  "number\_of\_validated\_outcomes": 0,  
  "hash": "..."  
}

---

# **21\. CLI esperada**

El agente debe construir un CLI con Typer.

Comandos deseados:

python \-m src.cli init  
python \-m src.cli register  
python \-m src.cli preprocess \--document A001  
python \-m src.cli process \--document A001  
python \-m src.cli process \--interactive  
python \-m src.cli validate \--document A001  
python \-m src.cli export-review  
python \-m src.cli import-review \--file data/03\_human\_review/extraction\_review.xlsx  
python \-m src.cli freeze \--version v01  
python \-m src.cli status

Los scripts en `/scripts/` pueden llamar internamente a estos comandos.

---

# **22\. Uso de Gemini API**

El módulo:

src/ai/gemini\_client.py

Debe:

\- Leer GEMINI\_API\_KEY desde .env.  
\- Cargar modelo fast o pro.  
\- Recibir prompt, schema y contenido del documento.  
\- Pedir respuesta JSON.  
\- Guardar respuesta cruda.  
\- Manejar errores.  
\- Reintentar si falla la llamada.

Debe permitir seleccionar modelo según tarea:

task\_models:  
  classification: "fast"  
  mapping: "pro"  
  scenario\_extraction: "pro"  
  outcome\_extraction: "pro"  
  audit: "pro"

Esto puede ir en `config/project_config.yaml`.

---

# **23\. Manejo de PDFs**

El módulo de preprocesamiento debe:

1\. Leer PDF con PyMuPDF.  
2\. Extraer texto por página.  
3\. Renderizar cada página como imagen PNG.  
4\. Guardar metadata:  
   \- document\_id  
   \- number\_of\_pages  
   \- has\_text  
   \- total\_characters  
   \- processing\_timestamp  
5\. Si el PDF no tiene texto suficiente, marcar como possible\_non\_digital.

Archivo de metadata:

{  
  "document\_id": "A001",  
  "file\_name": "A001.pdf",  
  "number\_of\_pages": 18,  
  "total\_characters": 45821,  
  "has\_text": true,  
  "possible\_non\_digital": false,  
  "processed\_at": "ISO\_TIMESTAMP"  
}

---

# **24\. Logs**

El sistema debe guardar logs en:

data/05\_logs/

Archivos:

pipeline.log  
errors.log  
ai\_calls.log  
validation.log

Cada llamada a IA debe registrar:

document\_id  
task\_type  
model  
prompt\_version  
schema  
timestamp  
success/failure  
output\_path

Nunca registrar API keys.

---

# **25\. Tests mínimos**

El agente debe implementar tests con `pytest`.

## **25.1 Tests de schema**

tests/test\_schema\_validation.py

Debe probar:

\- JSON válido pasa.  
\- JSON con campo faltante falla.  
\- JSON con status inválido falla.  
\- JSON con source\_type inválido falla.

## **25.2 Tests de reglas**

tests/test\_business\_rules.py

Debe probar:

\- Outcome numérico sin unidad queda bloqueado.  
\- Outcome sin página queda bloqueado.  
\- Outcome crítico sin evidencia queda bloqueado.  
\- Figure sin digitization queda marcada como needs\_digitization.

## **25.3 Tests de codebook**

tests/test\_codebook\_loading.py

Debe probar:

\- codebook.yaml carga correctamente.  
\- field\_name duplicado falla.  
\- campo crítico sin evidence\_required falla.

---

# **26\. README esperado**

El README debe incluir:

1\. Descripción del proyecto.  
2\. Instalación.  
3\. Configuración de .env.  
4\. Estructura de carpetas.  
5\. Cómo agregar PDFs.  
6\. Cómo registrar PDFs.  
7\. Cómo procesar un artículo.  
8\. Cómo continuar desde un artículo.  
9\. Cómo exportar revisión humana.  
10\. Cómo importar revisión humana.  
11\. Cómo congelar dataset.  
12\. Qué archivos no deben subirse a GitHub.  
13\. Limitaciones metodológicas.

Ejemplo de comandos:

cp .env.example .env  
\# edit .env and add GEMINI\_API\_KEY

python scripts/00\_init\_project.py  
python scripts/01\_register\_pdfs.py  
python scripts/03\_process\_article.py \--interactive  
python scripts/05\_export\_review\_excel.py  
python scripts/07\_freeze\_dataset.py \--version v01

---

# **27\. Nota metodológica para documentar el uso de IA**

Archivo:

docs/methodology\_note.md

Debe incluir este texto base:

This project implements a human-in-the-loop AI-assisted extraction workflow for systematic review and meta-analysis.

PDF documents are processed individually. Text is extracted page by page, and pages are rendered as images to preserve visual evidence from tables and figures. Gemini API is used to perform structured tasks: article classification, structural mapping, scenario extraction, outcome extraction, and extraction audit.

The AI model is constrained by versioned prompts and JSON schemas. Raw AI outputs are saved for auditability. Extracted data are validated against a project codebook and methodological business rules. Critical fields require explicit evidence, including page number and textual or visual support.

No extracted value is considered final until reviewed and accepted by a human researcher. The system preserves both AI-generated values and human corrections. Final analysis datasets are exported only after validation and dataset freezing.

---

# **28\. Reglas para el agente Antigravity**

El agente debe seguir estas instrucciones durante el desarrollo:

1\. No hardcodear prompts en archivos Python.  
2\. No hardcodear la API key.  
3\. No modificar ni borrar PDFs originales.  
4\. No crear funciones destructivas sin confirmación.  
5\. No subir data/ a Git.  
6\. Crear commits pequeños y legibles.  
7\. Crear tests junto con cada módulo importante.  
8\. Mantener README actualizado.  
9\. Mantener schemas separados.  
10\. Mantener prompts en prompts/prompts.yaml.  
11\. Mantener reglas metodológicas en config/extraction\_rules.yaml.  
12\. Mantener codebook en config/codebook.yaml.  
13\. Guardar siempre salidas crudas de IA.  
14\. No considerar datos como finales sin revisión humana.

---

# **29\. Secuencia de construcción solicitada al agente**

El agente debe construir en este orden:

## **Fase 1 — Inicialización del proyecto**

\- Crear estructura de carpetas.  
\- Crear pyproject.toml.  
\- Crear .gitignore.  
\- Crear .env.example.  
\- Crear README inicial.  
\- Crear config YAML inicial.  
\- Crear prompts YAML inicial.  
\- Crear schemas JSON iniciales.

Criterio de aceptación:

El proyecto instala dependencias y pasa pytest aunque todavía no procese PDFs.

---

## **Fase 2 — Base de datos**

\- Crear modelos SQLite.  
\- Crear script init\_db.  
\- Crear repository básico.  
\- Crear tabla documents.  
\- Crear tabla ai\_runs.  
\- Crear tablas scenarios, outcomes, evidence, qa\_log, human\_review, digitization\_tasks.

Criterio de aceptación:

python scripts/00\_init\_project.py crea data/project.sqlite con todas las tablas.

---

## **Fase 3 — Registro de PDFs**

\- Leer data/00\_raw\_pdfs.  
\- Detectar PDFs.  
\- Asignar A001, A002, etc.  
\- Calcular hash.  
\- Insertar en documents.  
\- Mostrar estado.

Criterio de aceptación:

python scripts/01\_register\_pdfs.py registra PDFs sin duplicarlos.

---

## **Fase 4 — Preprocesamiento**

\- Extraer texto por página.  
\- Renderizar páginas como PNG.  
\- Guardar metadata.  
\- Insertar páginas en DB.

Criterio de aceptación:

python scripts/02\_preprocess\_pdfs.py \--document A001 crea pages\_text y pages\_images.

---

## **Fase 5 — Cliente Gemini**

\- Implementar gemini\_client.py.  
\- Leer .env.  
\- Enviar prompt.  
\- Usar schema JSON.  
\- Guardar salida cruda.  
\- Registrar ai\_run.

Criterio de aceptación:

Una llamada de clasificación devuelve classification.json válido o registra error.

---

## **Fase 6 — Pipeline de IA**

\- Implementar clasificación.  
\- Implementar mapeo.  
\- Implementar extracción de escenarios.  
\- Implementar extracción de outcomes.  
\- Implementar auditoría.

Criterio de aceptación:

python scripts/03\_process\_article.py \--document A001 ejecuta el flujo completo y guarda todos los JSON.

---

## **Fase 7 — Validación**

\- Validar schemas.  
\- Validar codebook.  
\- Aplicar reglas de bloqueo.  
\- Insertar datos normalizados.

Criterio de aceptación:

Los datos sin evidencia, unidad o página quedan bloqueados o marcados para revisión.

---

## **Fase 8 — Revisión humana**

\- Exportar Excel de revisión.  
\- Importar decisiones humanas.  
\- Actualizar human\_validated.

Criterio de aceptación:

El investigador puede revisar outcomes en Excel y reimportar decisiones.

---

## **Fase 9 — Continuación interactiva**

\- Mostrar estado de documentos.  
\- Preguntar desde qué artículo continuar.  
\- Preguntar cuántos artículos procesar.  
\- Procesar secuencialmente.  
\- Permitir detener después de cada artículo.

Criterio de aceptación:

python scripts/03\_process\_article.py \--interactive permite continuar desde A016 y procesar 6 artículos.

---

## **Fase 10 — Congelación**

\- Exportar solo datos validados.  
\- Crear CSV/XLSX.  
\- Crear manifest.  
\- Crear changelog.  
\- Calcular hash.

Criterio de aceptación:

python scripts/07\_freeze\_dataset.py \--version v01 genera dataset congelado.

---

# **30\. TENER EN CUENTA EL SIGUIENTE APARTADO**

Build the local Python project described in the PRD.

Project name:  
meta-ai-extraction-pipeline

The project is a reproducible local AI-assisted data extraction pipeline for systematic review and meta-analysis. It processes scientific PDFs one article at a time, uses Gemini API through Google AI Studio, forces structured JSON outputs using JSON schemas, validates outputs against a YAML codebook and methodological rules, stores raw and normalized data, exports Excel files for human review, imports human corrections, and freezes validated datasets.

Confirmed implementation decisions:  
1\. Use SQLite for the local MVP.  
2\. Use Gemini 2.5 Flash for article classification.  
3\. Use Gemini 2.5 Pro for structural mapping, scenario extraction, outcome extraction, and audit.  
4\. Use an interactive article-by-article workflow.  
5\. During the pilot, pause after each processed article and ask the researcher whether to continue.  
6\. Use Excel as the first human review interface.  
7\. Keep technical prompts in English.  
8\. Keep project documentation in Spanish.  
9\. Use repository name: meta-ai-extraction-pipeline.  
10\. Render all PDF pages as PNG images during preprocessing.

Critical requirements:  
\- Do not hardcode prompts in Python.  
\- Store all prompts in prompts/prompts.yaml.  
\- Do not hardcode API keys.  
\- Use .env and .env.example.  
\- Do not commit PDFs, AI outputs, SQLite databases, logs, review files, or frozen datasets.  
\- Store the codebook in config/codebook.yaml.  
\- Store extraction rules in config/extraction\_rules.yaml.  
\- Store controlled vocabularies in config/controlled\_vocabularies.yaml.  
\- Store JSON schemas in schemas/.  
\- Save all raw AI outputs under data/02\_ai\_outputs/{document\_id}/.  
\- Use Python 3.11+.  
\- Use PyMuPDF for PDF text extraction and page rendering.  
\- Use Pydantic and/or jsonschema for validation.  
\- Use SQLAlchemy or a clean SQLite repository layer.  
\- Build CLI commands and scripts as specified in the PRD.  
\- Build tests for schema validation, business rules, codebook loading, document registry, and dataset freezing.  
\- No extracted critical value is final without human validation.  
\- The workflow must support interactive continuation from a selected document, e.g., continue from A016 and process 6 articles sequentially.  
\- After each article in pilot mode, show status and ask whether to continue, stop, export review Excel, or show issues.  
\- All raw AI outputs must be preserved for auditability.  
\- Human corrections must never overwrite raw AI outputs.  
\- Dataset freezing must include manifest, changelog, codebook version, prompt version, schema list, and hash.

Development order:  
1\. Create full project structure.  
2\. Create pyproject.toml, .gitignore, .env.example, README.md.  
3\. Create config YAML files.  
4\. Create prompts/prompts.yaml.  
5\. Create JSON schemas.  
6\. Create SQLite database initialization.  
7\. Implement PDF registration.  
8\. Implement PDF preprocessing.  
9\. Implement Gemini client.  
10\. Implement classification call.  
11\. Implement mapping call.  
12\. Implement scenario extraction call.  
13\. Implement outcome extraction call.  
14\. Implement audit call.  
15\. Implement schema validation.  
16\. Implement codebook validation.  
17\. Implement methodological business rules.  
18\. Implement normalized database insertion.  
19\. Implement Excel export for human review.  
20\. Implement Excel import for human decisions.  
21\. Implement interactive continuation workflow.  
22\. Implement dataset freezing.  
23\. Implement tests.  
24\. Update README and docs.

Acceptance criteria for v0.1:  
\- The repository can be installed locally.  
\- The database can be initialized.  
\- PDFs placed in data/00\_raw\_pdfs/ can be registered as A001, A002, etc.  
\- A selected PDF can be preprocessed into page text files and PNG page images.  
\- The system can call Gemini using .env credentials.  
\- The system saves classification.json, mapping.json, scenario\_extraction.json, outcome\_extraction.json, and audit.json.  
\- JSON outputs are validated against schemas.  
\- Outputs are checked against codebook and business rules.  
\- Invalid or unsafe records are blocked or marked for review.  
\- Normalized records are stored in SQLite.  
\- An Excel review file can be exported.  
\- Human review decisions can be imported.  
\- A validated dataset can be frozen to CSV/XLSX with manifest and changelog.  
\- The interactive CLI can continue from a selected article and process a selected number of articles with pause after each article.

