Se requiere hacer un ajuste a la forma de extracción de la base de datos y a los prompts para la extracción. Ten cuidado de no dañar lo existente ni hacer cambios que generen daños a la extracción ya funcional; la idea es mejorar y aumentar la extracción de forma justificada, no hacer parches y cambios que luego generen un problema mayor. 

La recomendación no es destruir la estructura actual. Es **expandirla de forma quirúrgica**.

# **1\. Lo que debe mantenerse**

## **1.1. Mantener la arquitectura por tablas**

La división actual es correcta:

| Hoja actual | Evaluación |
| ----- | ----- |
| `01_DOCUMENTS` | Mantener. Es útil para trazabilidad documental. |
| `01B_CLASSIFICATIONS` | Mantener. Es necesaria para excluir revisiones, estudios no cuantitativos o artículos no extractables. |
| `02_SCENARIOS` | Mantener y fortalecer. Es la hoja más importante para el enfoque scenario-level. |
| `03_OUTCOMES` | Mantener. El formato largo es correcto. |
| `04_EVIDENCE` | Mantener. Es fundamental para trazabilidad. |
| `05_QA_LOG` | Mantener. Ya está detectando problemas reales y metodológicamente importantes. |
| `06_HUMAN_REVIEW` | Mantener, pero actualmente está subdesarrollada, ademas de desayollarla incluir en el readme que es lo que debe hacer el humano y como debe entregar la data para que el flujo funcione posteriormente |
| `07_DIGITIZATION_TASKS` | Mantener. Muy necesaria para figuras. |

## **1.2. Mantener el formato largo de outcomes**

La hoja `03_OUTCOMES` está bien planteada: una fila por valor numérico. Esto es correcto para metaanálisis porque permite filtrar por outcome, escenario, sala, grupo ocupacional, unidad y fuente.

## **1.3. Mantener `scenario_code`**

El problema no es que algunas columnas estén asociadas a escenarios y otras no. El problema es que **algunas entidades todavía no están suficientemente normalizadas**.

En el la salida de EXCEL actual:

* `02_SCENARIOS` sí tiene `scenario_code`;  
* `03_OUTCOMES` sí tiene `scenario_code`;  
* `04_EVIDENCE` no usa `scenario_code`, sino `linked_record_id`;  
* `05_QA_LOG` usa `record_id`, no necesariamente `scenario_code`.

Eso no es necesariamente incorrecto, pero sí genera fricción para revisión humana. Para un revisor, `linked_record_id` tipo UUID es opaco. Se debe conservar el UUID internamente, pero exportar también los códigos legibles.

# **2\. Problemas críticos encontrados**

## **Problema 1: `02_SCENARIOS` no describe suficientemente el paquete de intervención**

Actualmente hay:

* `baseline_description`  
* `intervention_description`  
* `intervention_type`  
* `is_package`

Eso no basta.

Ejemplo actual: si el escenario tiene sombreado \+ misting, o ventilación \+ masa térmica \+ protección solar, eso queda enterrado en una descripción larga. Para metaanálisis, eso es insuficiente.

Debe añadirse una codificación explícita de componentes.

### **Añadir a `02_SCENARIOS`**

| Nueva columna | Tipo | Motivo |
| ----- | ----- | ----- |
| `intervention_package_simple` | texto corto | Resumen humano legible: “shading \+ misting”, “ventilation \+ thermal mass”. |
| `passive_component_count` | entero | Permite comparar estrategias simples vs paquetes. |
| `has_solar_shading` | 0/1 |  |
| `has_external_shading` | 0/1 |  |
| `has_internal_shading` | 0/1 |  |
| `has_natural_ventilation` | 0/1 |  |
| `has_cross_ventilation` | 0/1 |  |
| `has_night_ventilation` | 0/1 |  |
| `has_stack_ventilation` | 0/1 |  |
| `has_high_thermal_mass` | 0/1 |  |
| `has_pcm` | 0/1 |  |
| `has_cool_roof` | 0/1 |  |
| `has_cool_wall_or_reflective_coating` | 0/1 |  |
| `has_green_roof` | 0/1 |  |
| `has_green_wall` | 0/1 |  |
| `has_insulation_change` | 0/1 |  |
| `has_glazing_change` | 0/1 |  |
| `has_evaporative_cooling` | 0/1 |  |
| `has_misting` | 0/1 |  |
| `has_solar_chimney` | 0/1 |  |
| `has_courtyard_strategy` | 0/1 |  |
| `has_earth_air_heat_exchanger` | 0/1 |  |
| `has_active_system` | 0/1 |  |
| `active_system_type` | texto/categórico |  |

Esto es prioritario. Sin esto, el metaanálisis no podrá responder qué paquete funciona mejor.

## **Problema 2: `intervention_type` es demasiado pobre**

En el proyecto actual, el vocabulario actual de `intervention_type` incluye valores como:

* `insulation`  
* `glazing`  
* `shading`  
* `ventilation`  
* `hvac`  
* `passive_design`  
* `renewable_energy`  
* `controls`  
* `envelope`  
* `package`  
* `operational_change`  
* `not_applicable`  
* `other`  
* `unclear`

Esto debe modificarse. Ya han aparecido errores concretos al respecto en pruebas como la actualmente presente en el archivo extraction\_review.xlsx en `05_QA_LOG`: el sistema clasificó `misting` como `ventilation`, pero debería ser `evaporative_cooling`. Ese fallo es estructural, no accidental.

### **Vocabulario corregido**

Reemplazar/expandir `intervention_type` así:

intervention\_type:  
  \- not\_applicable  
  \- baseline  
  \- solar\_shading  
  \- natural\_ventilation  
  \- night\_ventilation  
  \- stack\_ventilation  
  \- evaporative\_cooling  
  \- misting  
  \- thermal\_mass  
  \- pcm  
  \- cool\_roof  
  \- cool\_wall\_or\_reflective\_coating  
  \- insulation  
  \- glazing  
  \- green\_roof  
  \- green\_wall  
  \- courtyard\_design  
  \- solar\_chimney  
  \- earth\_air\_heat\_exchanger  
  \- controls  
  \- operational\_change  
  \- active\_system\_change  
  \- passive\_package  
  \- mixed\_passive\_active\_package  
  \- other  
  \- unclear

Además, `passive_design` debería evitarse. Es demasiado genérico. Si aparece, debe forzar revisión humana.

## **Problema 3: falta geometría del espacio evaluado**

Esto es una omisión importante. Para ventilación, confort y sobrecalentamiento, no basta con saber que era una “bedroom” o “courtyard”. Hay que saber tamaño, altura y volumen si el paper lo reporta.

### **Añadir a `02_SCENARIOS` o crear hoja nueva `02B_SPACES`**

Mi recomendación: crear una hoja nueva.

## **Nueva hoja: `02B_SPACES`**

| Columna | Tipo |
| ----- | ----- |
| `document_code` | texto |
| `space_id` | texto |
| `scenario_code` | texto/null |
| `space_name_original` | texto |
| `space_type_standardized` | bedroom, classroom, courtyard, office, whole\_building, etc. |
| `evaluated_area_m2` | numérico |
| `evaluated_height_m` | numérico |
| `evaluated_volume_m3` | numérico |
| `floor_level` | texto |
| `orientation` | texto |
| `window_to_wall_ratio` | numérico |
| `opening_area_m2` | numérico |
| `occupancy_density` | texto/numérico |
| `evidence_page` | entero |
| `evidence_text` | texto |
| `status` | extracted / not\_found / unclear |

¿Por qué hoja separada? Porque un escenario puede tener varias salas: bedroom, greatroom, courtyard, classroom, office zone. Meter todo en `02_SCENARIOS` generaría columnas repetidas y confusas.

## **Problema 4: falta distinguir building/case/space/scenario**

Ahora el sistema usa:

documento → escenario → outcome

Eso es correcto, pero incompleto. Hay artículos con varios edificios, varios prototipos o varios espacios.

La estructura deseable sería:

documento → building\_case → scenario → space → outcome

### **Nueva hoja recomendada: `02A_BUILDING_CASES`**

| Columna | Tipo |
| ----- | ----- |
| `document_code` | texto |
| `building_case_id` | texto |
| `building_case_label` | texto |
| `building_typology` | categórico |
| `construction_period` | texto |
| `new_or_existing` | new / existing / retrofit / prototype / unclear |
| `conditioned_floor_area_m2` | numérico |
| `number_of_floors` | numérico |
| `envelope_description` | texto |
| `hvac_description` | texto |
| `passive_features_existing` | texto |
| `location` | texto |
| `climate_zone` | texto |
| `evidence_page` | entero |
| `evidence_text` | texto |

Esto agregaría valor fuerte. Si no se puede implementar ahora, al menos añadir `building_case_id` a `02_SCENARIOS`.

## **Problema 5: baseline insuficientemente operacionalizado**

En `02_SCENARIOS` hay `baseline_description`, pero falta una relación explícita entre intervención y baseline.

En `03_OUTCOMES` existe `comparison_baseline_scenario_id` en el esquema del proyecto, pero no aparece exportado en el Excel actual. Esto debe corregirse.

### **Añadir a `02_SCENARIOS`**

| Columna | Motivo |
| ----- | ----- |
| `baseline_scenario_code` | Identifica contra qué escenario se compara. |
| `is_reference_baseline` | Marca si es escenario base. |
| `comparison_logic` | same\_year\_same\_climate / same\_building\_no\_intervention / pre\_post / unclear |
| `baseline_compatibility_status` | valid / partially\_valid / invalid / unclear |

Esto es crítico para metaanálisis. Si se comparan intervenciones contra baselines distintos sin control, el análisis será débil.

## **Problema 6: outcomes no tienen suficiente estructura para tamaño de efecto**

`03_OUTCOMES` tiene:

* `value`  
* `unit`  
* `reported_effect_value`  
* `reported_effect_unit`

Pero falta lo más importante para metaanálisis:

| Nueva columna | Motivo |
| ----- | ----- |
| `baseline_scenario_code` | vínculo explícito |
| `baseline_value` | valor base |
| `intervention_value` | valor intervención, si la fila representa efecto |
| `calculated_effect_value` | diferencia calculada |
| `calculated_effect_type` | mean\_difference / percent\_change / ratio / SMD / not\_calculable |
| `effect_direction_standardized` | beneficial / harmful / neutral / unclear |
| `higher_is_better` | true/false |
| `variance_available` | true/false |
| `sd` | desviación estándar |
| `se` | error estándar |
| `ci_lower` | límite inferior |
| `ci_upper` | límite superior |
| `n` | tamaño muestral si aplica |
| `time_period` | annual, heatwave, summer, daytime, nighttime |
| `aggregation_method` | mean, max, min, median, cumulative, hours\_above\_threshold |
| `threshold_definition` | por ejemplo, adaptive comfort limit, PET range, HI threshold |
| `outcome_standardized_name` | nombre controlado |

Sin esto, se podrá hacer síntesis descriptiva, pero no un metaanálisis robusto. Es importante que si el artículo lo incluye, se sebe reportar si lo calculas; debido a que no se encuentra reportado, debe también haber dos columnas, una mencionando que fue la IA y reportar en base a qué datos lo calculó.

## **Problema 7: `source_type=figure` con valores visuales debe manejarse con más rigor**

En la tablas exportables a  Excel  para la revision humana hay muchos valores extraídos de figuras con:

* `extraction_method = figure_visual_confident`  
* `confidence = medium`  
* `needs_digitization = false`

Esto es peligroso. Para una revisión Q1, un valor leído visualmente de una figura no debería tratarse igual que un valor de tabla o texto.

### **Recomendación**

Crear tres niveles:

| Nivel | Uso |
| ----- | ----- |
| `figure_digitized` | valor extraído con herramienta de digitización o coordenadas calibradas |
| `figure_visual_approximate` | lectura visual aproximada; no apta para metaanálisis principal |
| `figure_visual_confident` | solo aceptable si la figura tiene etiquetas numéricas explícitas |

Añadir columnas:

| Columna | Motivo |
| ----- | ----- |
| `digitization_required_for_meta` | true/false |
| `digitization_tool` | WebPlotDigitizer/manual/AI/none |
| `digitization_error_risk` | low/medium/high |
| `usable_for_quantitative_synthesis` | true/false |
| `usable_for_sensitivity_only` | true/false |

# **3\. Qué eliminar o limitar**

## **3.1. Eliminar el uso libre de `passive_design`**

No debe ser una categoría final. Es una etiqueta paraguas. Debe reemplazarse por componentes específicos.

## **3.2. Evitar `current` en `ssp` si no está explícito**

El QA ya detectó esto. Estoy de acuerdo: si el artículo no dice SSP/RCP, `ssp` debe ser `null`, no `current`.

Mejor separar:

| Campo | Valor |
| ----- | ----- |
| `climate_period_type` | current / future\_projection / historical / heatwave / unclear |
| `ssp` | SSP2-4.5, SSP5-8.5, RCP4.5, null |
| `weather_year_or_period` | 2020, 2050, 2080, 2001–2020, etc. |

Así se evita contaminar `ssp`.

## **3.3. No meter outcomes “potenciales” en `reported_outcomes`**

El QA ya detectó listas de outcomes que la IA infirió pero no extrajo. Eso debe prohibirse.

Regla:

`reported_outcomes` solo debe incluir outcomes explícitamente reportados con una forma recuperable: valor, tabla, figura, perfil temporal o texto cuantitativo.

Si el outcome aparece como curva temporal sin valor único, debe marcarse como:

{  
  "outcome\_name": "indoor\_temperature\_profile",  
  "extractability": "profile\_only",  
  "single\_value\_available": false,  
  "digitization\_possible": true  
}

No debe aparecer como outcome numérico convencional.

# **4\. Adecuación recomendada de la estructura de la base de datos y de la hoja de calculo de Excel**

No rehacería el Excel. Lo ampliaría así:

## **Mantener hojas actuales y añadir 5 hojas nuevas**

| Hoja nueva | Prioridad | Función |
| ----- | ----- | ----- |
| `02A_BUILDING_CASES` | Alta | Características del edificio/prototipo/caso. |
| `02B_SPACES` | Alta | Área, altura, volumen, tipo de espacio. |
| `02C_INTERVENTION_COMPONENTS` | Muy alta | Codificación binaria y taxonómica de paquetes. |
| `03B_EFFECT_SIZES` | Muy alta | Tabla calculada para metaanálisis. |
| `08_META_READINESS` | Alta | Determina qué valores son utilizables para análisis cuantitativo. |

## **`02C_INTERVENTION_COMPONENTS`**

Esta tabla sería clave.

| Columna | Ejemplo |
| ----- | ----- |
| `document_code` | A002 |
| `scenario_code` | A002\_S05\_TR3 |
| `component_id` | A002\_S05\_TR3\_C01 |
| `component_family` | evaporative\_cooling |
| `component_type` | misting |
| `component_description_original` | misting 24h |
| `is_passive` | true/false |
| `is_active_support` | true/false |
| `operation_schedule` | daytime/nighttime/24h |
| `parameter_value` | 24 |
| `parameter_unit` | h |
| `evidence_page` | 12 |
| `evidence_text` | texto citado |
| `confidence` | high/medium/low |

Esto permite que un escenario tenga múltiples componentes sin crear 40 columnas en `02_SCENARIOS`.

Mi recomendación práctica: usar ambas cosas:

1. columnas binarias en `02_SCENARIOS` para análisis rápido;  
2. hoja `02C_INTERVENTION_COMPONENTS` para detalle fino.

Nota: es muy importante que en anterior esquema se tome como ejemplo , los valores atomar dependeran del articulo y de las bases ya definiadas

## **`03B_EFFECT_SIZES`**

| Columna | Motivo |
| ----- | ----- |
| `effect_id` | identificador |
| `document_code` | trazabilidad |
| `outcome_name` | outcome |
| `metric_group` | familia |
| `intervention_scenario_code` | intervención |
| `baseline_scenario_code` | comparador |
| `space_id` | espacio |
| `occupant_group` | grupo |
| `baseline_value` | valor base |
| `intervention_value` | valor intervención |
| `effect_value` | resultado calculado |
| `effect_type` | MD / percent\_change / ratio |
| `effect_unit` | °C, %, h, kWh/m² |
| `beneficial_direction` | lower\_is\_better / higher\_is\_better |
| `standardized_effect_direction` | beneficial / harmful |
| `variance_status` | available / unavailable |
| `meta_analysis_eligible` | true/false |
| `exclusion_reason` | sin baseline, sin unidad, figura aproximada, etc. |

Esta hoja no debería depender de la IA únicamente. Debe ser generada por reglas.

## **`08_META_READINESS`**

| Columna | Función |
| ----- | ----- |
| `record_id` | outcome/effect |
| `has_valid_scenario` | true/false |
| `has_valid_baseline` | true/false |
| `has_numeric_value` | true/false |
| `has_unit` | true/false |
| `has_page` | true/false |
| `has_evidence` | true/false |
| `source_quality` | text/table/figure\_digitized/figure\_visual |
| `human_validated` | true/false |
| `eligible_for_primary_meta_analysis` | true/false |
| `eligible_for_sensitivity_analysis` | true/false |
| `blocking_reason` | texto |

Esto es muy importante. Evita que el dataset “parezca” listo cuando todavía no lo está.

# **5\. Cambios concretos al proyecto**

## **5.1. Cambiar schemas**

### **`scenario_extraction.schema.json`**

Añadir propiedades:

{  
  "building\_case\_id": { "type": \["string", "null"\] },  
  "baseline\_scenario\_temp\_id": { "type": \["string", "null"\] },  
  "comparison\_logic": {  
    "type": \["string", "null"\],  
    "enum": \[  
      "same\_building\_no\_intervention",  
      "same\_year\_same\_climate",  
      "pre\_post",  
      "factorial\_reference",  
      "not\_applicable",  
      "unclear",  
      null  
    \]  
  },  
  "intervention\_package\_simple": { "type": \["string", "null"\] },  
  "passive\_component\_count": { "type": \["integer", "null"\] },  
  "has\_solar\_shading": { "type": \["boolean", "null"\] },  
  "has\_natural\_ventilation": { "type": \["boolean", "null"\] },  
  "has\_night\_ventilation": { "type": \["boolean", "null"\] },  
  "has\_high\_thermal\_mass": { "type": \["boolean", "null"\] },  
  "has\_pcm": { "type": \["boolean", "null"\] },  
  "has\_cool\_roof": { "type": \["boolean", "null"\] },  
  "has\_green\_roof": { "type": \["boolean", "null"\] },  
  "has\_evaporative\_cooling": { "type": \["boolean", "null"\] },  
  "has\_misting": { "type": \["boolean", "null"\] },  
  "has\_active\_system": { "type": \["boolean", "null"\] },  
  "active\_system\_type": { "type": \["string", "null"\] }  
}

### **Crear `building_case_extraction.schema.json`**

{  
  "type": "object",  
  "required": \["document\_id", "building\_cases"\],  
  "properties": {  
    "document\_id": { "type": "string" },  
    "building\_cases": {  
      "type": "array",  
      "items": {  
        "type": "object",  
        "required": \[  
          "building\_case\_temp\_id",  
          "building\_typology",  
          "evidence"  
        \],  
        "properties": {  
          "building\_case\_temp\_id": { "type": "string" },  
          "building\_case\_label": { "type": \["string", "null"\] },  
          "building\_typology": { "type": \["string", "null"\] },  
          "new\_or\_existing": {  
            "type": \["string", "null"\],  
            "enum": \["new", "existing", "retrofit", "prototype", "unclear", null\]  
          },  
          "conditioned\_floor\_area\_m2": { "type": \["number", "null"\] },  
          "number\_of\_floors": { "type": \["number", "null"\] },  
          "envelope\_description": { "type": \["string", "null"\] },  
          "hvac\_description": { "type": \["string", "null"\] },  
          "location": { "type": \["string", "null"\] },  
          "climate\_zone": { "type": \["string", "null"\] },  
          "evidence": {  
            "type": "object",  
            "properties": {  
              "page": { "type": \["integer", "null"\] },  
              "source\_type": { "type": \["string", "null"\] },  
              "evidence\_text": { "type": \["string", "null"\] }  
            }  
          },  
          "status": {  
            "type": "string",  
            "enum": \["extracted", "not\_found", "unclear"\]  
          }  
        }  
      }  
    }  
  }  
}

### **Crear `space_extraction.schema.json`**

{  
  "type": "object",  
  "required": \["document\_id", "spaces"\],  
  "properties": {  
    "document\_id": { "type": "string" },  
    "spaces": {  
      "type": "array",  
      "items": {  
        "type": "object",  
        "required": \["space\_temp\_id", "space\_type\_standardized", "status"\],  
        "properties": {  
          "space\_temp\_id": { "type": "string" },  
          "building\_case\_temp\_id": { "type": \["string", "null"\] },  
          "scenario\_temp\_id": { "type": \["string", "null"\] },  
          "space\_name\_original": { "type": \["string", "null"\] },  
          "space\_type\_standardized": {  
            "type": \["string", "null"\],  
            "enum": \[  
              "bedroom",  
              "living\_room",  
              "greatroom",  
              "classroom",  
              "office",  
              "courtyard",  
              "whole\_building",  
              "test\_cell",  
              "other",  
              "unclear",  
              null  
            \]  
          },  
          "evaluated\_area\_m2": { "type": \["number", "null"\] },  
          "evaluated\_height\_m": { "type": \["number", "null"\] },  
          "evaluated\_volume\_m3": { "type": \["number", "null"\] },  
          "orientation": { "type": \["string", "null"\] },  
          "window\_to\_wall\_ratio": { "type": \["number", "null"\] },  
          "opening\_area\_m2": { "type": \["number", "null"\] },  
          "occupancy\_density": { "type": \["string", "null"\] },  
          "evidence\_page": { "type": \["integer", "null"\] },  
          "evidence\_text": { "type": \["string", "null"\] },  
          "status": {  
            "type": "string",  
            "enum": \["extracted", "not\_found", "unclear"\]  
          }  
        }  
      }  
    }  
  }  
}

---

# **6\. Prompts adicionales necesarios**

Actualmente el proyecto tiene prompts para:

* clasificación;  
* mapping;  
* scenario extraction;  
* outcome extraction;  
* audit.

Faltan prompts especializados.

## **6.1. Prompt nuevo: extracción de edificio/caso**

building\_case\_extraction\_prompt: |  
  TASK: Extract building/case-level information.

  Identify every distinct building, prototype, dwelling, test cell, courtyard, room cluster, or case study evaluated in the article.

  Extract only information explicitly reported in the document. Do not infer missing geometry, HVAC systems, envelope features, or construction characteristics.

  A building\_case is NOT the same as a scenario. A scenario is a condition/intervention applied to a building\_case.

  For each building\_case, return:  
  \- building\_case\_temp\_id  
  \- building\_case\_label  
  \- building\_typology  
  \- new\_or\_existing  
  \- conditioned\_floor\_area\_m2  
  \- number\_of\_floors  
  \- envelope\_description  
  \- hvac\_description  
  \- passive\_features\_existing  
  \- location  
  \- climate\_zone  
  \- evidence page and evidence text  
  \- status

  Rules:  
  1\. If area, floors, envelope or HVAC are not explicitly reported, return null.  
  2\. Do not estimate area from drawings.  
  3\. Do not merge multiple buildings into one case unless the paper treats them as a single prototype.  
  4\. If the article studies only a courtyard or single space, create one building\_case for the host building or study case if described.

  Return only JSON following building\_case\_extraction.schema.json.

## **6.2. Prompt nuevo: extracción de espacios**

space\_extraction\_prompt: |  
  TASK: Extract evaluated spaces/zones.

  Identify every room, zone, courtyard, test cell, apartment, house, or whole-building space for which outcomes are reported.

  Extract geometry and spatial descriptors when explicitly reported:  
  \- area  
  \- height  
  \- volume  
  \- orientation  
  \- window-to-wall ratio  
  \- opening area  
  \- occupancy density  
  \- floor level

  Critical rules:  
  1\. Do not infer dimensions from figures unless numerical dimensions are explicitly labeled.  
  2\. Do not assign one room's geometry to another room.  
  3\. If outcomes are reported separately for bedroom and greatroom, create separate space records.  
  4\. If the paper reports only whole-building outcomes, use space\_type\_standardized \= "whole\_building".  
  5\. If geometry is absent, return null, not an estimate.

  Return only JSON following space\_extraction.schema.json.

## **6.3. Prompt nuevo: codificación de paquetes de intervención**

intervention\_component\_coding\_prompt: |  
  TASK: Code passive and active intervention components for each scenario.

  For every scenario extracted, identify whether the intervention contains any of the following components:  
  \- solar shading  
  \- external shading  
  \- internal shading  
  \- natural ventilation  
  \- cross ventilation  
  \- night ventilation  
  \- stack ventilation  
  \- high thermal mass  
  \- phase change material  
  \- cool roof  
  \- cool wall or reflective coating  
  \- insulation change  
  \- glazing change  
  \- green roof  
  \- green wall  
  \- courtyard strategy  
  \- evaporative cooling  
  \- misting  
  \- solar chimney  
  \- earth-air heat exchanger  
  \- HVAC or other active system  
  \- controls or operational change

  For each component:  
  \- mark present only if explicitly supported by the document;  
  \- provide evidence page and evidence text;  
  \- specify whether it is passive, active, or mixed;  
  \- specify operation schedule if reported.

  Critical rules:  
  1\. Do not code generic "passive design" unless the component is specified.  
  2\. Do not classify misting as ventilation; classify it as evaporative\_cooling/misting.  
  3\. Do not split packages into separate intervention effects unless the paper reports separate outcomes.  
  4\. If a component is part of the existing baseline building, mark it as existing\_feature, not intervention\_component.

  Return JSON with one record per scenario-component pair.

## **6.4. Prompt nuevo: baseline matching**

baseline\_matching\_prompt: |  
  TASK: Match each intervention scenario to the correct baseline/reference scenario.

  For every non-baseline scenario, identify the most appropriate baseline scenario from the extracted scenario list.

  Matching rules:  
  1\. Prefer same building/case.  
  2\. Prefer same climate location.  
  3\. Prefer same weather year or climate pathway.  
  4\. Prefer same operational mode unless the intervention is explicitly an operational mode change.  
  5\. Do not match across different spaces unless the outcome is whole-building.  
  6\. If no valid baseline exists, set baseline\_scenario\_temp\_id \= null and status \= "unclear".

  Return:  
  \- intervention\_scenario\_temp\_id  
  \- baseline\_scenario\_temp\_id  
  \- comparison\_logic  
  \- match\_confidence  
  \- evidence\_page  
  \- evidence\_text  
  \- reason  
  \- status

  Do not calculate effects in this step.

## **6.5. Prompt nuevo: meta-readiness audit**

meta\_readiness\_audit\_prompt: |  
  TASK: Determine whether each extracted outcome/effect is eligible for quantitative synthesis.

  Evaluate each outcome record using the following criteria:  
  \- valid scenario linkage  
  \- valid baseline linkage if an effect is required  
  \- numeric value present  
  \- unit present  
  \- page present  
  \- evidence text or table/figure reference present  
  \- source type acceptable  
  \- extraction method acceptable  
  \- human validation status  
  \- uncertainty or variance availability  
  \- outcome is comparable with other studies

  Classify each record as:  
  \- eligible\_primary\_meta\_analysis  
  \- eligible\_sensitivity\_analysis\_only  
  \- descriptive\_only  
  \- exclude\_from\_quantitative\_synthesis

  Provide blocking reasons:  
  \- no\_valid\_baseline  
  \- no\_unit  
  \- figure\_visual\_only  
  \- no\_numeric\_value  
  \- profile\_without\_single\_value  
  \- scenario\_unclear  
  \- unsupported\_inference  
  \- duplicate  
  \- wrong\_outcome\_family

  Return JSON only.

# **7\. Reglas de validación nuevas**

Añadir estas reglas al módulo de validación.

| Regla | Acción |
| ----- | ----- |
| `generic_passive_design_forbidden` | Si `intervention_type = passive_design`, marcar `human_review_required`. |
| `misting_not_ventilation` | Si descripción contiene misting/fogging/spray y tipo es ventilation, justificar el porque el articulo lo define de esta forma e incluirlo como erro para revision humana |
| `package_requires_components` | Si `is_package=true`, debe haber al menos dos componentes. |
| `components_require_evidence` | Cada componente debe tener evidencia. |
| `intervention_requires_baseline_for_effect` | Si hay efecto calculado, debe haber baseline válido. |
| `visual_figure_not_primary_meta` | Figura visual sin digitización no entra a análisis principal. |
| `ssp_current_forbidden_unless_reported` | No usar `current` en SSP salvo que el documento lo diga como pathway, lo cual es raro. |
| `space_specific_outcomes_require_space_id` | Si hay `room_or_space`, debe mapearse a `space_id`. |
| `active_system_contamination_flag` | Si hay HVAC/fan/misting activo, marcar escenario como mixed/passive-active. |
| `profile_outcome_not_single_value` | Curvas temporales sin valor agregado no se extraen como outcome escalar. |

# **8\. Evaluación crítica del estado actual**

## **Fortalezas**

1. El pipeline ya reconoce documentos, escenarios, outcomes, evidencia y QA.  
2. La hoja `05_QA_LOG` demuestra que el sistema detecta errores metodológicos reales.  
3. El formato largo de outcomes es correcto.  
4. Hay trazabilidad básica por página, figura y texto.  
5. La arquitectura ya contempla revisión humana y auditoría, que son requisitos explícitos del sistema.

## **Debilidades**

1. La codificación de intervención todavía es demasiado gruesa.  
2. No hay extracción suficiente de geometría del espacio.  
3. No hay tabla formal de building/case.  
4. No hay tabla formal de componentes de paquetes.  
5. No hay hoja de tamaños de efecto.  
6. No hay control fuerte de elegibilidad para metaanálisis.  
7. Las figuras visuales se están aceptando con demasiada facilidad.  
8. Los UUID internos hacen difícil la revisión humana si no se exportan junto con códigos legibles.  
9. Algunos campos inducen inferencia: especialmente `ssp=current`, `passive_design`, `reported_outcomes`.  
10. Falta separar escenarios pasivos puros de escenarios mixtos pasivo-activo.

---

# **9\. Qué haría ahora, en orden**

## **Prioridad 1: corregir taxonomía de intervención**

Corregir:

* `controlled_vocabularies.yaml`  
* `codebook.yaml`  
* `scenario_extraction.schema.json`  
* `scenario_extraction_prompt`  
* `audit_prompt`

Esto evitará que se acumulen cientos de escenarios mal clasificados.

## **Prioridad 2: añadir componentes de paquete**

No basta con `intervention_description`. Añadir:

* `intervention_package_simple`  
* `passive_component_count`  
* columnas binarias principales;  
* hoja `02C_INTERVENTION_COMPONENTS`.

## **Prioridad 3: añadir `02B_SPACES`**

Tu observación sobre área y altura es correcta. Yo añadiría también volumen. Para ventilación y confort térmico, el volumen puede ser más importante que el área.

## **Prioridad 4: añadir baseline matching**

Sin baseline matching, los efectos comparativos serán débiles.

## **Prioridad 5: generar `03B_EFFECT_SIZES`**

Esta tabls/hoja debe ser calculada por reglas, no inventada por IA.

# **10\. Decisión final: mantener, añadir, eliminar**

| Elemento | Decisión | Motivo |
| ----- | ----- | ----- |
| `01_DOCUMENTS` | Mantener | Correcto para trazabilidad. |
| `01B_CLASSIFICATIONS` | Mantener | Útil y necesario. |
| `02_SCENARIOS` | Mantener \+ ampliar | Es la tabla central. |
| `03_OUTCOMES` | Mantener \+ ampliar | Formato largo correcto, pero falta metaanálisis. |
| `04_EVIDENCE` | Mantener \+ añadir códigos legibles | Muy necesaria, pero UUID solo no basta. |
| `05_QA_LOG` | Mantener \+ ampliar reglas | Está funcionando bien. |
| `06_HUMAN_REVIEW` | Mantener \+ fortalecer | Debe revisar también escenarios, componentes y espacios. |
| `07_DIGITIZATION_TASKS` | Mantener | Necesaria para valores de figuras. |
| `passive_design` | Eliminar como categoría final | Demasiado genérica. |
| `ssp=current` | Evitar | Debe ser `climate_period_type=current`, no SSP. |
| `figure_visual_confident` | Limitar | Solo aceptable con etiquetas numéricas claras. |
| `reported_outcomes` inferidos | Eliminar | Solo outcomes explícitos o perfiles claramente marcados. |

