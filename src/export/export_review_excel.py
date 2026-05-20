"""
Export extraction data to Excel for human review.

Creates a multi-sheet Excel file with all extraction data,
including columns for human review decisions and detailed schemas.
"""

from pathlib import Path
import json

import pandas as pd
from rich.console import Console

from src.database.db import DatabaseManager
from src.database.models import (
    ArticleClassification,
    DigitizationTask,
    Document,
    Evidence,
    HumanReview,
    Outcome,
    QALog,
    Scenario,
    BuildingCase,
    Space,
    InterventionComponent,
    MetaReadiness,
)
from src.export.compute_effect_sizes import compute_document_effect_sizes
from src.utils.logging_config import get_logger
from src.utils.paths import get_human_review_path

logger = get_logger("export")
console = Console()


def export_review_excel(output_path: str | Path | None = None) -> Path:
    """Export extraction data to Excel for human review.

    Creates sheets:
    - 00_README
    - 01_DOCUMENTS
    - 01B_CLASSIFICATIONS
    - 02A_BUILDING_CASES
    - 02_SCENARIOS
    - 02B_SPACES
    - 02C_INTERVENTION_COMPONENTS
    - 03_OUTCOMES
    - 03B_EFFECT_SIZES
    - 04_EVIDENCE
    - 05_QA_LOG
    - 06_HUMAN_REVIEW
    - 07_DIGITIZATION_TASKS
    - 08_META_READINESS

    Args:
        output_path: Optional path override for the Excel file.

    Returns:
        Path to the created Excel file.
    """
    if output_path is None:
        output_path = get_human_review_path() / "extraction_review.xlsx"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with DatabaseManager() as session:
        docs = session.query(Document).order_by(Document.document_code).all()

        # Step 0: Recalculate effect sizes for all documents to ensure database is perfectly synchronized
        console.print("[blue]Recalculating effect sizes for all articles...[/blue]")
        for d in docs:
            try:
                compute_document_effect_sizes(session, d.id)
            except Exception as e:
                logger.error(f"Error computing effect sizes for {d.document_code}: {e}")
        session.commit()

        # Build lookups to replace UUIDs with human-readable codes in all exported sheets
        doc_code_map = {d.id: d.document_code for d in docs}
        scen_code_map = {s.id: s.scenario_code for s in session.query(Scenario).all()}
        space_code_map = {sp.id: sp.space_code for sp in session.query(Space).all()}
        bc_code_map = {bc.id: bc.building_case_code for bc in session.query(BuildingCase).all()}
        outcome_code_map = {o.id: o.outcome_code for o in session.query(Outcome).all()}

        # 01_DOCUMENTS
        docs_data = [{
            "document_code": d.document_code,
            "file_name": d.file_name,
            "status": d.status,
            "current_step": d.current_step,
            "created_at": d.created_at,
            "updated_at": d.updated_at,
        } for d in docs]

        # 01B_CLASSIFICATIONS
        classifications = session.query(ArticleClassification).all()
        classifications_data = []
        for c in classifications:
            classifications_data.append({
                "document_code": doc_code_map.get(c.document_id, ""),
                "study_type": c.study_type,
                "is_extractable": bool(c.is_extractable) if c.is_extractable is not None else None,
                "has_simulation": bool(c.has_simulation) if c.has_simulation is not None else None,
                "has_numeric_outcomes": bool(c.has_numeric_outcomes) if c.has_numeric_outcomes is not None else None,
                "reason": c.reason,
                "status": c.status,
            })

        # 02A_BUILDING_CASES
        building_cases = session.query(BuildingCase).all()
        building_cases_data = []
        for bc in building_cases:
            building_cases_data.append({
                "document_code": doc_code_map.get(bc.document_id, ""),
                "building_case_code": bc.building_case_code,
                "building_case_temp_id": bc.building_case_temp_id,
                "building_case_label": bc.building_case_label,
                "building_typology": bc.building_typology,
                "construction_period": bc.construction_period,
                "new_or_existing": bc.new_or_existing,
                "conditioned_floor_area_m2": bc.conditioned_floor_area_m2,
                "number_of_floors": bc.number_of_floors,
                "envelope_description": bc.envelope_description,
                "hvac_description": bc.hvac_description,
                "passive_features_existing": bc.passive_features_existing,
                "location": bc.location,
                "climate_zone": bc.climate_zone,
                "evidence_page": bc.evidence_page,
                "evidence_text": bc.evidence_text,
                "status": bc.status,
            })

        # 02_SCENARIOS
        scenarios = session.query(Scenario).all()
        scenarios_data = []
        for s in scenarios:
            scenarios_data.append({
                "document_code": doc_code_map.get(s.document_id, ""),
                "scenario_code": s.scenario_code,
                "scenario_label": s.scenario_label,
                "scenario_family": s.scenario_family,
                "year": s.year,
                "ssp": s.ssp,
                "climate_period_type": s.climate_period_type,
                "weather_year_or_period": s.weather_year_or_period,
                "operational_mode": s.operational_mode,
                "building_typology": s.building_typology,
                "building_case_code": bc_code_map.get(s.building_case_id, s.building_case_id) if s.building_case_id else "",
                "climate_location": s.climate_location,
                "climate_zone": s.climate_zone,
                "climate_zone_source": s.climate_zone_source,
                "weather_file": s.weather_file,
                "simulation_software": s.simulation_software,
                "baseline_description": s.baseline_description,
                "baseline_scenario_code": scen_code_map.get(s.baseline_scenario_temp_id, s.baseline_scenario_temp_id) if s.baseline_scenario_temp_id else "",
                "is_reference_baseline": bool(s.is_reference_baseline) if s.is_reference_baseline is not None else None,
                "comparison_logic": s.comparison_logic,
                "baseline_compatibility_status": s.baseline_compatibility_status,
                "intervention_description": s.intervention_description,
                "intervention_type": s.intervention_type,
                "is_package": bool(s.is_package) if s.is_package is not None else None,
                "intervention_package_simple": s.intervention_package_simple,
                "passive_component_count": s.passive_component_count,
                # Binary flags
                "has_solar_shading": bool(s.has_solar_shading) if s.has_solar_shading is not None else None,
                "has_external_shading": bool(s.has_external_shading) if s.has_external_shading is not None else None,
                "has_internal_shading": bool(s.has_internal_shading) if s.has_internal_shading is not None else None,
                "has_natural_ventilation": bool(s.has_natural_ventilation) if s.has_natural_ventilation is not None else None,
                "has_cross_ventilation": bool(s.has_cross_ventilation) if s.has_cross_ventilation is not None else None,
                "has_night_ventilation": bool(s.has_night_ventilation) if s.has_night_ventilation is not None else None,
                "has_stack_ventilation": bool(s.has_stack_ventilation) if s.has_stack_ventilation is not None else None,
                "has_high_thermal_mass": bool(s.has_high_thermal_mass) if s.has_high_thermal_mass is not None else None,
                "has_pcm": bool(s.has_pcm) if s.has_pcm is not None else None,
                "has_cool_roof": bool(s.has_cool_roof) if s.has_cool_roof is not None else None,
                "has_cool_wall_or_reflective_coating": bool(s.has_cool_wall_or_reflective_coating) if s.has_cool_wall_or_reflective_coating is not None else None,
                "has_green_roof": bool(s.has_green_roof) if s.has_green_roof is not None else None,
                "has_green_wall": bool(s.has_green_wall) if s.has_green_wall is not None else None,
                "has_insulation_change": bool(s.has_insulation_change) if s.has_insulation_change is not None else None,
                "has_glazing_change": bool(s.has_glazing_change) if s.has_glazing_change is not None else None,
                "has_evaporative_cooling": bool(s.has_evaporative_cooling) if s.has_evaporative_cooling is not None else None,
                "has_misting": bool(s.has_misting) if s.has_misting is not None else None,
                "has_solar_chimney": bool(s.has_solar_chimney) if s.has_solar_chimney is not None else None,
                "has_courtyard_strategy": bool(s.has_courtyard_strategy) if s.has_courtyard_strategy is not None else None,
                "has_earth_air_heat_exchanger": bool(s.has_earth_air_heat_exchanger) if s.has_earth_air_heat_exchanger is not None else None,
                "has_active_system": bool(s.has_active_system) if s.has_active_system is not None else None,
                "active_system_type": s.active_system_type,
                "status": s.status,
                "human_validated": bool(s.human_validated),
            })

        # 02B_SPACES
        spaces = session.query(Space).all()
        spaces_data = []
        for sp in spaces:
            spaces_data.append({
                "document_code": doc_code_map.get(sp.document_id, ""),
                "space_code": sp.space_code,
                "space_temp_id": sp.space_temp_id,
                "building_case_code": bc_code_map.get(sp.building_case_id, sp.building_case_id) if sp.building_case_id else "",
                "scenario_code": scen_code_map.get(sp.scenario_id, sp.scenario_id) if sp.scenario_id else "",
                "space_name_original": sp.space_name_original,
                "space_type_standardized": sp.space_type_standardized,
                "evaluated_area_m2": sp.evaluated_area_m2,
                "evaluated_height_m": sp.evaluated_height_m,
                "evaluated_volume_m3": sp.evaluated_volume_m3,
                "floor_level": sp.floor_level,
                "orientation": sp.orientation,
                "window_to_wall_ratio": sp.window_to_wall_ratio,
                "opening_area_m2": sp.opening_area_m2,
                "occupancy_density": sp.occupancy_density,
                "evidence_page": sp.evidence_page,
                "evidence_text": sp.evidence_text,
                "status": sp.status,
            })

        # 02C_INTERVENTION_COMPONENTS
        components = session.query(InterventionComponent).all()
        components_data = []
        for c in components:
            components_data.append({
                "document_code": doc_code_map.get(c.document_id, ""),
                "scenario_code": scen_code_map.get(c.scenario_id, c.scenario_id) if c.scenario_id else "",
                "scenario_temp_id": c.scenario_temp_id,
                "component_code": c.component_code,
                "component_id": c.component_id,
                "component_family": c.component_family,
                "component_type": c.component_type,
                "component_description_original": c.component_description_original,
                "is_passive": bool(c.is_passive) if c.is_passive is not None else None,
                "is_active_support": bool(c.is_active_support) if c.is_active_support is not None else None,
                "is_existing_feature": bool(c.is_existing_feature) if c.is_existing_feature is not None else None,
                "operation_schedule": c.operation_schedule,
                "parameter_value": c.parameter_value,
                "parameter_unit": c.parameter_unit,
                "evidence_page": c.evidence_page,
                "evidence_text": c.evidence_text,
                "confidence": c.confidence,
                "status": c.status,
            })

        # 03_OUTCOMES
        outcomes = session.query(Outcome).all()
        outcomes_data = []
        for o in outcomes:
            outcomes_data.append({
                "document_code": doc_code_map.get(o.document_id, ""),
                "scenario_code": scen_code_map.get(o.scenario_id, o.scenario_id) if o.scenario_id else "",
                "outcome_code": o.outcome_code,
                "outcome_name": o.outcome_name,
                "outcome_standardized_name": o.outcome_standardized_name,
                "metric_group": o.metric_group,
                "room_or_space": o.room_or_space,
                "space_code": space_code_map.get(o.space_id, o.space_id) if o.space_id else "",
                "occupant_group": o.occupant_group,
                "value": o.value,
                "unit": o.unit,
                "baseline_value": o.baseline_value,
                "intervention_value": o.intervention_value,
                "reported_effect_value": o.reported_effect_value,
                "reported_effect_unit": o.reported_effect_unit,
                "calculated_effect_value": o.calculated_effect_value,
                "calculated_effect_type": o.calculated_effect_type,
                "is_ai_calculated": bool(o.is_ai_calculated) if o.is_ai_calculated is not None else None,
                "ai_calculation_basis": o.ai_calculation_basis,
                "standardized_value": o.standardized_value,
                "standardized_unit": o.standardized_unit,
                "effect_direction": o.effect_direction,
                "effect_direction_standardized": o.effect_direction_standardized,
                "higher_is_better": bool(o.higher_is_better) if o.higher_is_better is not None else None,
                "variance_available": bool(o.variance_available) if o.variance_available is not None else None,
                "sd": o.sd,
                "se": o.se,
                "ci_lower": o.ci_lower,
                "ci_upper": o.ci_upper,
                "n": o.n,
                "time_period": o.time_period,
                "aggregation_method": o.aggregation_method,
                "threshold_definition": o.threshold_definition,
                "extraction_method": o.extraction_method,
                "confidence": o.confidence,
                "source_type": o.source_type,
                "page": o.page,
                "table_or_figure": o.table_or_figure,
                "needs_digitization": bool(o.needs_digitization),
                "digitization_required_for_meta": bool(o.digitization_required_for_meta) if o.digitization_required_for_meta is not None else None,
                "digitization_tool": o.digitization_tool,
                "digitization_error_risk": o.digitization_error_risk,
                "usable_for_quantitative_synthesis": bool(o.usable_for_quantitative_synthesis) if o.usable_for_quantitative_synthesis is not None else None,
                "usable_for_sensitivity_only": bool(o.usable_for_sensitivity_only) if o.usable_for_sensitivity_only is not None else None,
                "status": o.status,
                "human_decision": "",
                "human_value": None,
                "human_unit": "",
                "reviewer": "",
                "reviewer_comment": "",
            })

        # 03B_EFFECT_SIZES
        effect_sizes_data = []
        for o in outcomes:
            effect_sizes_data.append({
                "document_code": doc_code_map.get(o.document_id, ""),
                "scenario_code": scen_code_map.get(o.scenario_id, o.scenario_id) if o.scenario_id else "",
                "outcome_code": o.outcome_code,
                "outcome_name": o.outcome_name,
                "outcome_standardized_name": o.outcome_standardized_name,
                "baseline_value": o.baseline_value,
                "intervention_value": o.intervention_value,
                "calculated_effect_value": o.calculated_effect_value,
                "calculated_effect_type": o.calculated_effect_type,
                "effect_direction_standardized": o.effect_direction_standardized,
                "higher_is_better": bool(o.higher_is_better) if o.higher_is_better is not None else None,
                "variance_available": bool(o.variance_available) if o.variance_available is not None else None,
                "sd": o.sd,
                "se": o.se,
                "ci_lower": o.ci_lower,
                "ci_upper": o.ci_upper,
                "n": o.n,
                "time_period": o.time_period,
                "aggregation_method": o.aggregation_method,
                "usable_for_quantitative_synthesis": bool(o.usable_for_quantitative_synthesis) if o.usable_for_quantitative_synthesis is not None else None,
                "usable_for_sensitivity_only": bool(o.usable_for_sensitivity_only) if o.usable_for_sensitivity_only is not None else None,
                "ai_calculation_basis": o.ai_calculation_basis,
            })

        # 04_EVIDENCE
        evidence_records = session.query(Evidence).all()
        evidence_data = []
        for e in evidence_records:
            linked_code = e.linked_record_id
            if e.linked_table == "scenarios":
                linked_code = scen_code_map.get(e.linked_record_id, e.linked_record_id)
            elif e.linked_table == "outcomes":
                linked_code = outcome_code_map.get(e.linked_record_id, e.linked_record_id)
            elif e.linked_table == "spaces":
                linked_code = space_code_map.get(e.linked_record_id, e.linked_record_id)
            elif e.linked_table == "building_cases":
                linked_code = bc_code_map.get(e.linked_record_id, e.linked_record_id)
            
            evidence_data.append({
                "document_code": doc_code_map.get(e.document_id, ""),
                "linked_table": e.linked_table,
                "linked_record_code": linked_code,
                "page_number": e.page_number,
                "source_type": e.source_type,
                "table_or_figure_label": e.table_or_figure_label,
                "row_label": e.row_label,
                "column_label": e.column_label,
                "evidence_text": e.evidence_text,
                "validation_status": e.validation_status,
            })

        # 05_QA_LOG
        qa_logs = session.query(QALog).all()
        qa_data = []
        for q in qa_logs:
            rec_code = q.record_id
            if q.record_type == "scenarios":
                rec_code = scen_code_map.get(q.record_id, q.record_id)
            elif q.record_type == "outcomes":
                rec_code = outcome_code_map.get(q.record_id, q.record_id)
            elif q.record_type == "spaces":
                rec_code = space_code_map.get(q.record_id, q.record_id)
            elif q.record_type == "building_cases":
                rec_code = bc_code_map.get(q.record_id, q.record_id)
            
            qa_data.append({
                "document_code": doc_code_map.get(q.document_id, ""),
                "record_type": q.record_type,
                "record_code": rec_code,
                "severity": q.severity,
                "issue_type": q.issue_type,
                "description": q.description,
                "required_action": q.required_action,
                "resolved": bool(q.resolved),
            })

        # 06_HUMAN_REVIEW
        reviews = session.query(HumanReview).all()
        comp_id_map = {ic.id: ic.component_code for ic in session.query(InterventionComponent).all()}
        review_data = []
        for r in reviews:
            rec_code = r.record_id
            if r.record_type == "scenarios":
                rec_code = scen_code_map.get(r.record_id, r.record_id)
            elif r.record_type == "outcomes":
                rec_code = outcome_code_map.get(r.record_id, r.record_id)
            elif r.record_type == "spaces":
                rec_code = space_code_map.get(r.record_id, r.record_id)
            elif r.record_type == "building_cases":
                rec_code = bc_code_map.get(r.record_id, r.record_id)
            elif r.record_type == "intervention_components":
                rec_code = comp_id_map.get(r.record_id, r.record_id)

            review_data.append({
                "document_code": doc_code_map.get(r.document_id, ""),
                "record_type": r.record_type,
                "record_code": rec_code,
                "field_name": r.field_name,
                "ai_value": r.ai_value,
                "human_value": r.human_value,
                "decision": r.decision,
                "reviewer": r.reviewer,
                "reviewer_comment": r.reviewer_comment,
                "reviewed_at": r.reviewed_at,
            })

        # 07_DIGITIZATION_TASKS
        dig_tasks = session.query(DigitizationTask).all()
        dig_data = [{
            "document_code": doc_code_map.get(d.document_id, ""),
            "outcome_code": outcome_code_map.get(d.outcome_id, d.outcome_id) if d.outcome_id else "",
            "page": d.page,
            "figure_label": d.figure_label,
            "reason": d.reason,
            "status": d.status,
            "digitized_value": d.digitized_value,
            "digitized_unit": d.digitized_unit,
        } for d in dig_tasks]

        # 08_META_READINESS
        meta_readiness_records = session.query(MetaReadiness).all()
        meta_readiness_data = []
        for mr in meta_readiness_records:
            # record_id in MetaReadiness points to outcome_temp_id or outcome_id
            outcome = session.query(Outcome).filter(
                (Outcome.document_id == mr.document_id) & 
                ((Outcome.outcome_temp_id == mr.record_id) | (Outcome.id == mr.record_id))
            ).first()
            rec_code = outcome.outcome_code if outcome else mr.record_id
            
            meta_readiness_data.append({
                "document_code": doc_code_map.get(mr.document_id, ""),
                "record_code": rec_code,
                "has_valid_scenario": bool(mr.has_valid_scenario) if mr.has_valid_scenario is not None else None,
                "has_valid_baseline": bool(mr.has_valid_baseline) if mr.has_valid_baseline is not None else None,
                "has_numeric_value": bool(mr.has_numeric_value) if mr.has_numeric_value is not None else None,
                "has_unit": bool(mr.has_unit) if mr.has_unit is not None else None,
                "has_page": bool(mr.has_page) if mr.has_page is not None else None,
                "has_evidence": bool(mr.has_evidence) if mr.has_evidence is not None else None,
                "source_quality": mr.source_quality,
                "eligible_for_primary_meta_analysis": bool(mr.eligible_for_primary_meta_analysis) if mr.eligible_for_primary_meta_analysis is not None else None,
                "eligible_for_sensitivity_analysis": bool(mr.eligible_for_sensitivity_analysis) if mr.eligible_for_sensitivity_analysis is not None else None,
                "classification": mr.classification,
                "blocking_reason": mr.blocking_reason,
                "human_validated": bool(mr.human_validated),
            })

    # Create Excel
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        # 00_README
        readme_df = pd.DataFrame({
            "Instructions": [
                "=========================================================================",
                "SYSTEMATIC REVIEW & META-ANALYSIS DATA EXTRACTION — HUMAN REVIEW PROTOCOL",
                "=========================================================================",
                "This workbook contains the automated extracts from the AI workflow.",
                "To validate and finalize the dataset, review the following sheets:",
                "",
                "1. [06_HUMAN_REVIEW]: Main review interface. Mark decisions (accepted / corrected / rejected / unclear).",
                "2. [03_OUTCOMES]: Inspect outcomes and calculated parameters. Correct values/units in columns 'human_value' and 'human_unit'.",
                "3. [02C_INTERVENTION_COMPONENTS]: Check that all intervention package components are detailed.",
                "4. [08_META_READINESS]: Review quantitative synthesis eligibility criteria and blocking reasons.",
                "",
                "CRITICAL PROTOCOLS:",
                "- Do NOT modify columns that are AI-generated (no prefix). Only modify columns intended for human input.",
                "- To import your decisions back into the SQLite database, run:",
                "  python src/export/import_human_review.py",
                "",
                "SHEET SUMMARY:",
                "- 01_DOCUMENTS: List of processed documents and statuses.",
                "- 01B_CLASSIFICATIONS: Extraction eligibility and study types.",
                "- 02A_BUILDING_CASES: Physical, construction, envelope, and HVAC properties of evaluated cases.",
                "- 02_SCENARIOS: Evaluated baselines and intervention scenarios.",
                "- 02B_SPACES: Evaluated spaces, dimensions, typologies, and physical traits.",
                "- 02C_INTERVENTION_COMPONENTS: Detail of intervention elements inside packages (with physical values).",
                "- 03_OUTCOMES: Extracted thermal comfort, indoor temp, and energy outcomes.",
                "- 03B_EFFECT_SIZES: Calculated effect size estimates (Mean Difference, Percent Change, Ratio) by rules.",
                "- 04_EVIDENCE: Text segments and coordinates linked directly to the PDF sources.",
                "- 05_QA_LOG: Logical errors and compliance warnings raised by the business rules validator.",
                "- 06_HUMAN_REVIEW: Table of overrides and validation logs.",
                "- 07_DIGITIZATION_TASKS: Log of figures flagged for digitization.",
                "- 08_META_READINESS: Systematic review eligibility audit findings.",
            ]
        })
        readme_df.to_excel(writer, sheet_name="00_README", index=False)

        pd.DataFrame(docs_data).to_excel(writer, sheet_name="01_DOCUMENTS", index=False)
        pd.DataFrame(classifications_data).to_excel(writer, sheet_name="01B_CLASSIFICATIONS", index=False)
        pd.DataFrame(building_cases_data).to_excel(writer, sheet_name="02A_BUILDING_CASES", index=False)
        pd.DataFrame(scenarios_data).to_excel(writer, sheet_name="02_SCENARIOS", index=False)
        pd.DataFrame(spaces_data).to_excel(writer, sheet_name="02B_SPACES", index=False)
        pd.DataFrame(components_data).to_excel(writer, sheet_name="02C_INTERVENTION_COMPONENTS", index=False)
        pd.DataFrame(outcomes_data).to_excel(writer, sheet_name="03_OUTCOMES", index=False)
        pd.DataFrame(effect_sizes_data).to_excel(writer, sheet_name="03B_EFFECT_SIZES", index=False)
        pd.DataFrame(evidence_data).to_excel(writer, sheet_name="04_EVIDENCE", index=False)
        pd.DataFrame(qa_data).to_excel(writer, sheet_name="05_QA_LOG", index=False)
        pd.DataFrame(review_data).to_excel(writer, sheet_name="06_HUMAN_REVIEW", index=False)
        pd.DataFrame(dig_data).to_excel(writer, sheet_name="07_DIGITIZATION_TASKS", index=False)
        pd.DataFrame(meta_readiness_data).to_excel(writer, sheet_name="08_META_READINESS", index=False)

    console.print(f"[green]✓[/green] Review Excel exported with 13 sheets: {output_path}")
    logger.info(f"Review Excel exported: {output_path}")
    return output_path
