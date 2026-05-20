"""
Repository layer — CRUD operations for all database tables.
"""

import json
import uuid
from typing import Any

from sqlalchemy.orm import Session

from src.database.models import (
    AIRun,
    ArticleClassification,
    BuildingCase,
    DigitizationTask,
    Document,
    Evidence,
    HumanReview,
    InterventionComponent,
    MetaReadiness,
    Outcome,
    Page,
    QALog,
    Scenario,
    Space,
)
from src.utils.timestamps import now_iso


def generate_id() -> str:
    """Generate a UUID4 string."""
    return str(uuid.uuid4())


# ── Documents ──────────────────────────────────────────────────────────

def insert_document(
    session: Session,
    document_code: str,
    file_name: str,
    file_path: str,
    file_hash: str,
    status: str = "pending",
) -> Document:
    """Insert a new document record."""
    doc = Document(
        id=generate_id(),
        document_code=document_code,
        file_name=file_name,
        file_path=file_path,
        file_hash=file_hash,
        status=status,
        current_step=None,
        created_at=now_iso(),
        updated_at=now_iso(),
    )
    session.add(doc)
    session.flush()
    return doc


def get_document_by_code(session: Session, document_code: str) -> Document | None:
    """Get a document by its code (e.g., A001)."""
    return session.query(Document).filter(Document.document_code == document_code).first()


def get_document_by_hash(session: Session, file_hash: str) -> Document | None:
    """Get a document by its file hash."""
    return session.query(Document).filter(Document.file_hash == file_hash).first()


def get_all_documents(session: Session) -> list[Document]:
    """Get all documents ordered by document_code."""
    return session.query(Document).order_by(Document.document_code).all()


def update_document_status(session: Session, document_id: str, status: str, current_step: str | None = None) -> None:
    """Update a document's status and optionally its current step."""
    doc = session.query(Document).filter(Document.id == document_id).first()
    if doc:
        doc.status = status
        if current_step is not None:
            doc.current_step = current_step
        doc.updated_at = now_iso()
        session.flush()


def get_next_document_code(session: Session, prefix: str = "A", padding: int = 3) -> str:
    """Get the next available document code (e.g., A001 → A002)."""
    docs = session.query(Document).order_by(Document.document_code.desc()).first()
    if docs is None:
        return f"{prefix}{'1'.zfill(padding)}"
    last_num = int(docs.document_code.replace(prefix, ""))
    return f"{prefix}{str(last_num + 1).zfill(padding)}"


# ── Pages ──────────────────────────────────────────────────────────────

def insert_page(
    session: Session,
    document_id: str,
    page_number: int,
    text_path: str | None = None,
    image_path: str | None = None,
    text_char_count: int | None = None,
) -> Page:
    """Insert a page record."""
    page = Page(
        id=generate_id(),
        document_id=document_id,
        page_number=page_number,
        text_path=text_path,
        image_path=image_path,
        text_char_count=text_char_count,
        created_at=now_iso(),
    )
    session.add(page)
    session.flush()
    return page


def get_pages_for_document(session: Session, document_id: str) -> list[Page]:
    """Get all pages for a document, ordered by page number."""
    return (
        session.query(Page)
        .filter(Page.document_id == document_id)
        .order_by(Page.page_number)
        .all()
    )


# ── AI Runs ────────────────────────────────────────────────────────────

def insert_ai_run(
    session: Session,
    document_id: str,
    task_type: str,
    model_name: str,
    prompt_version: str,
    schema_name: str,
    input_hash: str,
    output_json_path: str,
    parsed_successfully: bool,
    schema_version: str | None = None,
    codebook_version: str | None = None,
    error_message: str | None = None,
) -> AIRun:
    """Insert an AI run record."""
    run = AIRun(
        id=generate_id(),
        document_id=document_id,
        task_type=task_type,
        model_name=model_name,
        prompt_version=prompt_version,
        schema_name=schema_name,
        schema_version=schema_version,
        codebook_version=codebook_version,
        input_hash=input_hash,
        output_json_path=output_json_path,
        parsed_successfully=1 if parsed_successfully else 0,
        error_message=error_message,
        created_at=now_iso(),
    )
    session.add(run)
    session.flush()
    return run


# ── Article Classification ─────────────────────────────────────────────

def insert_classification(
    session: Session,
    document_id: str,
    data: dict[str, Any],
) -> ArticleClassification:
    """Insert a classification record from parsed AI output."""
    cls = ArticleClassification(
        id=generate_id(),
        document_id=document_id,
        study_type=data.get("study_type"),
        is_extractable=_bool_to_int(data.get("is_extractable")),
        has_simulation=_bool_to_int(data.get("has_simulation")),
        has_numeric_outcomes=_bool_to_int(data.get("has_numeric_outcomes")),
        has_tables=_bool_to_int(data.get("has_tables")),
        has_figures=_bool_to_int(data.get("has_figures")),
        has_multiple_scenarios=_bool_to_int(data.get("has_multiple_scenarios")),
        reason=data.get("reason"),
        status=data.get("status"),
        human_review_required=_bool_to_int(data.get("human_review_required")),
        created_at=now_iso(),
    )
    session.add(cls)
    session.flush()
    return cls


# ── Building Cases (NEW) ──────────────────────────────────────────────

def insert_building_case(
    session: Session,
    document_id: str,
    building_case_code: str,
    data: dict[str, Any],
) -> BuildingCase:
    """Insert a building case record."""
    evidence = data.get("evidence", {})
    bc = BuildingCase(
        id=generate_id(),
        document_id=document_id,
        building_case_code=building_case_code,
        building_case_temp_id=data.get("building_case_temp_id"),
        building_case_label=data.get("building_case_label"),
        building_typology=data.get("building_typology"),
        construction_period=data.get("construction_period"),
        new_or_existing=data.get("new_or_existing"),
        conditioned_floor_area_m2=data.get("conditioned_floor_area_m2"),
        number_of_floors=data.get("number_of_floors"),
        envelope_description=data.get("envelope_description"),
        hvac_description=data.get("hvac_description"),
        passive_features_existing=data.get("passive_features_existing"),
        location=data.get("location"),
        climate_zone=data.get("climate_zone"),
        evidence_page=evidence.get("page") if isinstance(evidence, dict) else None,
        evidence_text=evidence.get("evidence_text") if isinstance(evidence, dict) else None,
        status=data.get("status", "extracted"),
        created_at=now_iso(),
        updated_at=now_iso(),
    )
    session.add(bc)
    session.flush()
    return bc


def get_building_cases_for_document(session: Session, document_id: str) -> list[BuildingCase]:
    """Get all building cases for a document."""
    return session.query(BuildingCase).filter(BuildingCase.document_id == document_id).all()


# ── Scenarios ──────────────────────────────────────────────────────────

def insert_scenario(
    session: Session,
    document_id: str,
    scenario_code: str,
    data: dict[str, Any],
) -> Scenario:
    """Insert a scenario record."""
    scenario = Scenario(
        id=generate_id(),
        document_id=document_id,
        scenario_code=scenario_code,
        scenario_temp_id=data.get("scenario_temp_id"),
        scenario_label=data.get("scenario_label"),
        scenario_family=data.get("scenario_family"),
        year=data.get("year"),
        ssp=data.get("ssp"),
        climate_period_type=data.get("climate_period_type"),
        weather_year_or_period=data.get("weather_year_or_period"),
        operational_mode=data.get("operational_mode"),
        building_typology=data.get("building_typology"),
        building_case_id=data.get("building_case_id"),
        climate_location=data.get("climate_location"),
        climate_zone=data.get("climate_zone"),
        climate_zone_source=data.get("climate_zone_source"),
        weather_file=data.get("weather_file"),
        simulation_software=data.get("simulation_software"),
        baseline_description=data.get("baseline_description"),
        baseline_scenario_temp_id=data.get("baseline_scenario_temp_id"),
        is_reference_baseline=_bool_to_int(data.get("is_reference_baseline")),
        comparison_logic=data.get("comparison_logic"),
        baseline_compatibility_status=data.get("baseline_compatibility_status"),
        intervention_description=data.get("intervention_description"),
        intervention_type=data.get("intervention_type"),
        is_package=_bool_to_int(data.get("is_package")),
        package_components=json.dumps(data.get("package_components", [])),
        intervention_package_simple=data.get("intervention_package_simple"),
        passive_component_count=data.get("passive_component_count"),
        has_solar_shading=_bool_to_int(data.get("has_solar_shading")),
        has_external_shading=_bool_to_int(data.get("has_external_shading")),
        has_internal_shading=_bool_to_int(data.get("has_internal_shading")),
        has_natural_ventilation=_bool_to_int(data.get("has_natural_ventilation")),
        has_cross_ventilation=_bool_to_int(data.get("has_cross_ventilation")),
        has_night_ventilation=_bool_to_int(data.get("has_night_ventilation")),
        has_stack_ventilation=_bool_to_int(data.get("has_stack_ventilation")),
        has_high_thermal_mass=_bool_to_int(data.get("has_high_thermal_mass")),
        has_pcm=_bool_to_int(data.get("has_pcm")),
        has_cool_roof=_bool_to_int(data.get("has_cool_roof")),
        has_cool_wall_or_reflective_coating=_bool_to_int(data.get("has_cool_wall_or_reflective_coating")),
        has_green_roof=_bool_to_int(data.get("has_green_roof")),
        has_green_wall=_bool_to_int(data.get("has_green_wall")),
        has_insulation_change=_bool_to_int(data.get("has_insulation_change")),
        has_glazing_change=_bool_to_int(data.get("has_glazing_change")),
        has_evaporative_cooling=_bool_to_int(data.get("has_evaporative_cooling")),
        has_misting=_bool_to_int(data.get("has_misting")),
        has_solar_chimney=_bool_to_int(data.get("has_solar_chimney")),
        has_courtyard_strategy=_bool_to_int(data.get("has_courtyard_strategy")),
        has_earth_air_heat_exchanger=_bool_to_int(data.get("has_earth_air_heat_exchanger")),
        has_active_system=_bool_to_int(data.get("has_active_system")),
        active_system_type=data.get("active_system_type"),
        status=data.get("status", "extracted"),
        human_validated=0,
        created_at=now_iso(),
        updated_at=now_iso(),
    )
    session.add(scenario)
    session.flush()
    return scenario


def get_scenarios_for_document(session: Session, document_id: str) -> list[Scenario]:
    """Get all scenarios for a document."""
    return session.query(Scenario).filter(Scenario.document_id == document_id).all()


# ── Spaces (NEW) ──────────────────────────────────────────────────────

def insert_space(
    session: Session,
    document_id: str,
    space_code: str,
    data: dict[str, Any],
) -> Space:
    """Insert a space record."""
    space = Space(
        id=generate_id(),
        document_id=document_id,
        space_code=space_code,
        space_temp_id=data.get("space_temp_id"),
        building_case_id=data.get("building_case_temp_id"),
        scenario_id=data.get("scenario_temp_id"),
        space_name_original=data.get("space_name_original"),
        space_type_standardized=data.get("space_type_standardized"),
        evaluated_area_m2=data.get("evaluated_area_m2"),
        evaluated_height_m=data.get("evaluated_height_m"),
        evaluated_volume_m3=data.get("evaluated_volume_m3"),
        floor_level=data.get("floor_level"),
        orientation=data.get("orientation"),
        window_to_wall_ratio=data.get("window_to_wall_ratio"),
        opening_area_m2=data.get("opening_area_m2"),
        occupancy_density=data.get("occupancy_density"),
        evidence_page=data.get("evidence_page"),
        evidence_text=data.get("evidence_text"),
        status=data.get("status", "extracted"),
        created_at=now_iso(),
        updated_at=now_iso(),
    )
    session.add(space)
    session.flush()
    return space


def get_spaces_for_document(session: Session, document_id: str) -> list[Space]:
    """Get all spaces for a document."""
    return session.query(Space).filter(Space.document_id == document_id).all()


# ── Intervention Components (NEW) ─────────────────────────────────────

def insert_intervention_component(
    session: Session,
    document_id: str,
    component_code: str,
    data: dict[str, Any],
    scenario_id: str | None = None,
) -> InterventionComponent:
    """Insert an intervention component record."""
    comp = InterventionComponent(
        id=generate_id(),
        document_id=document_id,
        scenario_id=scenario_id,
        scenario_temp_id=data.get("scenario_temp_id"),
        component_code=component_code,
        component_id=data.get("component_id"),
        component_family=data.get("component_family"),
        component_type=data.get("component_type"),
        component_description_original=data.get("component_description_original"),
        is_passive=_bool_to_int(data.get("is_passive")),
        is_active_support=_bool_to_int(data.get("is_active_support")),
        is_existing_feature=_bool_to_int(data.get("is_existing_feature")),
        operation_schedule=data.get("operation_schedule"),
        parameter_value=data.get("parameter_value"),
        parameter_unit=data.get("parameter_unit"),
        evidence_page=data.get("evidence_page"),
        evidence_text=data.get("evidence_text"),
        confidence=data.get("confidence"),
        status=data.get("status", "extracted"),
        created_at=now_iso(),
        updated_at=now_iso(),
    )
    session.add(comp)
    session.flush()
    return comp


def get_components_for_document(session: Session, document_id: str) -> list[InterventionComponent]:
    """Get all intervention components for a document."""
    return session.query(InterventionComponent).filter(InterventionComponent.document_id == document_id).all()


# ── Outcomes ───────────────────────────────────────────────────────────

def insert_outcome(
    session: Session,
    document_id: str,
    scenario_id: str | None,
    outcome_code: str,
    data: dict[str, Any],
) -> Outcome:
    """Insert an outcome record."""
    outcome = Outcome(
        id=generate_id(),
        document_id=document_id,
        scenario_id=scenario_id,
        outcome_code=outcome_code,
        outcome_temp_id=data.get("outcome_temp_id"),
        outcome_name=data.get("outcome_name"),
        outcome_standardized_name=data.get("outcome_standardized_name"),
        metric_group=data.get("metric_group"),
        room_or_space=data.get("room_or_space"),
        space_id=data.get("space_id"),
        occupant_group=data.get("occupant_group"),
        value=data.get("value"),
        unit=data.get("unit"),
        baseline_value=data.get("baseline_value"),
        intervention_value=data.get("intervention_value"),
        reported_effect_value=data.get("reported_effect_value"),
        reported_effect_unit=data.get("reported_effect_unit"),
        calculated_effect_value=data.get("calculated_effect_value"),
        calculated_effect_type=data.get("calculated_effect_type"),
        is_ai_calculated=_bool_to_int(data.get("is_ai_calculated")),
        ai_calculation_basis=data.get("ai_calculation_basis"),
        effect_direction=data.get("effect_direction"),
        effect_direction_standardized=data.get("effect_direction_standardized"),
        higher_is_better=_bool_to_int(data.get("higher_is_better")),
        variance_available=_bool_to_int(data.get("variance_available")),
        sd=data.get("sd"),
        se=data.get("se"),
        ci_lower=data.get("ci_lower"),
        ci_upper=data.get("ci_upper"),
        n=data.get("n"),
        time_period=data.get("time_period"),
        aggregation_method=data.get("aggregation_method"),
        threshold_definition=data.get("threshold_definition"),
        extraction_method=data.get("extraction_method"),
        confidence=data.get("confidence"),
        source_type=data.get("source_type"),
        page=data.get("page"),
        table_or_figure=data.get("table_or_figure"),
        row_label=data.get("row_label"),
        column_label=data.get("column_label"),
        needs_digitization=_bool_to_int(data.get("needs_digitization", False)),
        digitization_required_for_meta=_bool_to_int(data.get("digitization_required_for_meta")),
        digitization_tool=data.get("digitization_tool"),
        digitization_error_risk=data.get("digitization_error_risk"),
        usable_for_quantitative_synthesis=_bool_to_int(data.get("usable_for_quantitative_synthesis")),
        usable_for_sensitivity_only=_bool_to_int(data.get("usable_for_sensitivity_only")),
        status=data.get("status", "extracted"),
        human_validated=0,
        created_at=now_iso(),
        updated_at=now_iso(),
    )
    session.add(outcome)
    session.flush()
    return outcome


def get_outcomes_for_document(session: Session, document_id: str) -> list[Outcome]:
    """Get all outcomes for a document."""
    return session.query(Outcome).filter(Outcome.document_id == document_id).all()


# ── Evidence ───────────────────────────────────────────────────────────

def insert_evidence(
    session: Session,
    document_id: str,
    linked_table: str,
    linked_record_id: str,
    page_number: int | None = None,
    source_type: str | None = None,
    table_or_figure_label: str | None = None,
    row_label: str | None = None,
    column_label: str | None = None,
    evidence_text: str | None = None,
    crop_path: str | None = None,
) -> Evidence:
    """Insert an evidence record."""
    ev = Evidence(
        id=generate_id(),
        document_id=document_id,
        linked_table=linked_table,
        linked_record_id=linked_record_id,
        page_number=page_number,
        source_type=source_type,
        table_or_figure_label=table_or_figure_label,
        row_label=row_label,
        column_label=column_label,
        evidence_text=evidence_text,
        crop_path=crop_path,
        validation_status="pending",
        created_at=now_iso(),
    )
    session.add(ev)
    session.flush()
    return ev


# ── QA Log ─────────────────────────────────────────────────────────────

def insert_qa_log(
    session: Session,
    document_id: str,
    record_type: str | None,
    record_id: str | None,
    severity: str | None,
    issue_type: str | None,
    description: str | None,
    required_action: str | None,
) -> QALog:
    """Insert a QA log entry."""
    qa = QALog(
        id=generate_id(),
        document_id=document_id,
        record_type=record_type,
        record_id=record_id,
        severity=severity,
        issue_type=issue_type,
        description=description,
        required_action=required_action,
        resolved=0,
        created_at=now_iso(),
    )
    session.add(qa)
    session.flush()
    return qa


def get_qa_logs_for_document(session: Session, document_id: str) -> list[QALog]:
    """Get all QA log entries for a document."""
    return session.query(QALog).filter(QALog.document_id == document_id).all()


# ── Human Review ───────────────────────────────────────────────────────

def insert_human_review(
    session: Session,
    document_id: str,
    record_type: str,
    record_id: str,
    field_name: str,
    ai_value: str | None,
    human_value: str | None,
    decision: str,
    reviewer: str | None = None,
    reviewer_comment: str | None = None,
) -> HumanReview:
    """Insert a human review record."""
    hr = HumanReview(
        id=generate_id(),
        document_id=document_id,
        record_type=record_type,
        record_id=record_id,
        field_name=field_name,
        ai_value=ai_value,
        human_value=human_value,
        decision=decision,
        reviewer=reviewer,
        reviewer_comment=reviewer_comment,
        reviewed_at=now_iso(),
    )
    session.add(hr)
    session.flush()
    return hr


# ── Digitization Tasks ────────────────────────────────────────────────

def insert_digitization_task(
    session: Session,
    document_id: str,
    outcome_id: str | None,
    page: int | None,
    figure_label: str | None,
    reason: str | None,
    crop_path: str | None = None,
) -> DigitizationTask:
    """Insert a digitization task."""
    task = DigitizationTask(
        id=generate_id(),
        document_id=document_id,
        outcome_id=outcome_id,
        page=page,
        figure_label=figure_label,
        crop_path=crop_path,
        reason=reason,
        status="pending",
        created_at=now_iso(),
        updated_at=now_iso(),
    )
    session.add(task)
    session.flush()
    return task


def get_digitization_tasks_for_document(session: Session, document_id: str) -> list[DigitizationTask]:
    """Get all digitization tasks for a document."""
    return session.query(DigitizationTask).filter(DigitizationTask.document_id == document_id).all()


# ── Meta-Readiness (NEW) ──────────────────────────────────────────────

def insert_meta_readiness(
    session: Session,
    document_id: str,
    data: dict[str, Any],
) -> MetaReadiness:
    """Insert a meta-readiness record."""
    mr = MetaReadiness(
        id=generate_id(),
        document_id=document_id,
        record_id=data.get("record_id", ""),
        has_valid_scenario=_bool_to_int(data.get("has_valid_scenario")),
        has_valid_baseline=_bool_to_int(data.get("has_valid_baseline")),
        has_numeric_value=_bool_to_int(data.get("has_numeric_value")),
        has_unit=_bool_to_int(data.get("has_unit")),
        has_page=_bool_to_int(data.get("has_page")),
        has_evidence=_bool_to_int(data.get("has_evidence")),
        source_quality=data.get("source_quality"),
        human_validated=_bool_to_int(data.get("human_validated", False)),
        eligible_for_primary_meta_analysis=_bool_to_int(data.get("eligible_for_primary_meta_analysis")),
        eligible_for_sensitivity_analysis=_bool_to_int(data.get("eligible_for_sensitivity_analysis")),
        classification=data.get("classification"),
        blocking_reason=data.get("blocking_reason"),
        created_at=now_iso(),
        updated_at=now_iso(),
    )
    session.add(mr)
    session.flush()
    return mr


def get_meta_readiness_for_document(session: Session, document_id: str) -> list[MetaReadiness]:
    """Get all meta-readiness records for a document."""
    return session.query(MetaReadiness).filter(MetaReadiness.document_id == document_id).all()


# ── Helpers ────────────────────────────────────────────────────────────

def _bool_to_int(value: bool | None) -> int | None:
    """Convert a boolean to integer for SQLite storage."""
    if value is None:
        return None
    return 1 if value else 0
