"""
SQLAlchemy ORM models for the meta-analysis extraction pipeline.

Tables defined per PRD §13 + Robustecimiento v02:
- documents, pages, ai_runs, article_classification,
- building_cases, scenarios, spaces, intervention_components,
- outcomes, evidence, qa_log, human_review, digitization_tasks,
- meta_readiness
"""

from sqlalchemy import (
    Column,
    Float,
    ForeignKey,
    Integer,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class Document(Base):
    __tablename__ = "documents"

    id = Column(Text, primary_key=True)
    document_code = Column(Text, unique=True, nullable=False)
    file_name = Column(Text, nullable=False)
    file_path = Column(Text, nullable=False)
    file_hash = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="pending")
    current_step = Column(Text)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)

    # Relationships
    pages = relationship("Page", back_populates="document", cascade="all, delete-orphan")
    ai_runs = relationship("AIRun", back_populates="document", cascade="all, delete-orphan")
    classifications = relationship("ArticleClassification", back_populates="document", cascade="all, delete-orphan")
    building_cases = relationship("BuildingCase", back_populates="document", cascade="all, delete-orphan")
    scenarios = relationship("Scenario", back_populates="document", cascade="all, delete-orphan")
    spaces = relationship("Space", back_populates="document", cascade="all, delete-orphan")
    intervention_components = relationship("InterventionComponent", back_populates="document", cascade="all, delete-orphan")
    outcomes = relationship("Outcome", back_populates="document", cascade="all, delete-orphan")
    evidence_records = relationship("Evidence", back_populates="document", cascade="all, delete-orphan")
    qa_logs = relationship("QALog", back_populates="document", cascade="all, delete-orphan")
    human_reviews = relationship("HumanReview", back_populates="document", cascade="all, delete-orphan")
    digitization_tasks = relationship("DigitizationTask", back_populates="document", cascade="all, delete-orphan")
    meta_readiness_records = relationship("MetaReadiness", back_populates="document", cascade="all, delete-orphan")


class Page(Base):
    __tablename__ = "pages"

    id = Column(Text, primary_key=True)
    document_id = Column(Text, ForeignKey("documents.id"), nullable=False)
    page_number = Column(Integer, nullable=False)
    text_path = Column(Text)
    image_path = Column(Text)
    text_char_count = Column(Integer)
    created_at = Column(Text, nullable=False)

    document = relationship("Document", back_populates="pages")


class AIRun(Base):
    __tablename__ = "ai_runs"

    id = Column(Text, primary_key=True)
    document_id = Column(Text, ForeignKey("documents.id"), nullable=False)
    task_type = Column(Text, nullable=False)
    model_name = Column(Text, nullable=False)
    prompt_version = Column(Text, nullable=False)
    schema_name = Column(Text, nullable=False)
    schema_version = Column(Text)
    codebook_version = Column(Text)
    input_hash = Column(Text, nullable=False)
    output_json_path = Column(Text, nullable=False)
    parsed_successfully = Column(Integer, nullable=False)
    error_message = Column(Text)
    created_at = Column(Text, nullable=False)

    document = relationship("Document", back_populates="ai_runs")


class ArticleClassification(Base):
    __tablename__ = "article_classification"

    id = Column(Text, primary_key=True)
    document_id = Column(Text, ForeignKey("documents.id"), nullable=False)
    study_type = Column(Text)
    is_extractable = Column(Integer)
    has_simulation = Column(Integer)
    has_numeric_outcomes = Column(Integer)
    has_tables = Column(Integer)
    has_figures = Column(Integer)
    has_multiple_scenarios = Column(Integer)
    reason = Column(Text)
    status = Column(Text)
    human_review_required = Column(Integer)
    created_at = Column(Text, nullable=False)

    document = relationship("Document", back_populates="classifications")


# ── NEW: Building Cases (02A) ──────────────────────────────────────────

class BuildingCase(Base):
    __tablename__ = "building_cases"

    id = Column(Text, primary_key=True)
    document_id = Column(Text, ForeignKey("documents.id"), nullable=False)
    building_case_code = Column(Text, nullable=False)  # e.g., A001_BC01
    building_case_temp_id = Column(Text)
    building_case_label = Column(Text)
    building_typology = Column(Text)
    construction_period = Column(Text)
    new_or_existing = Column(Text)
    conditioned_floor_area_m2 = Column(Float)
    number_of_floors = Column(Float)
    envelope_description = Column(Text)
    hvac_description = Column(Text)
    passive_features_existing = Column(Text)
    location = Column(Text)
    climate_zone = Column(Text)
    evidence_page = Column(Integer)
    evidence_text = Column(Text)
    status = Column(Text, nullable=False)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)

    document = relationship("Document", back_populates="building_cases")


class Scenario(Base):
    __tablename__ = "scenarios"

    id = Column(Text, primary_key=True)
    document_id = Column(Text, ForeignKey("documents.id"), nullable=False)
    scenario_code = Column(Text, nullable=False)
    scenario_temp_id = Column(Text)
    scenario_label = Column(Text)
    scenario_family = Column(Text)
    year = Column(Text)
    ssp = Column(Text)
    climate_period_type = Column(Text)           # NEW: current/future_projection/historical/heatwave/unclear
    weather_year_or_period = Column(Text)         # NEW: specific year or range
    operational_mode = Column(Text)
    building_typology = Column(Text)
    building_case_id = Column(Text)               # NEW: links to building_cases
    climate_location = Column(Text)
    climate_zone = Column(Text)
    climate_zone_source = Column(Text)            # 'document' or 'external_lookup'
    weather_file = Column(Text)
    simulation_software = Column(Text)
    baseline_description = Column(Text)
    baseline_scenario_temp_id = Column(Text)      # NEW: links to baseline scenario
    is_reference_baseline = Column(Integer)       # NEW: bool
    comparison_logic = Column(Text)               # NEW: comparison type
    baseline_compatibility_status = Column(Text)  # NEW: valid/partially_valid/invalid/unclear
    intervention_description = Column(Text)
    intervention_type = Column(Text)
    is_package = Column(Integer)
    package_components = Column(Text)             # JSON-serialized list
    intervention_package_simple = Column(Text)    # NEW: human-readable summary
    passive_component_count = Column(Integer)     # NEW: number of passive components
    # Binary intervention flags (NEW)
    has_solar_shading = Column(Integer)
    has_external_shading = Column(Integer)
    has_internal_shading = Column(Integer)
    has_natural_ventilation = Column(Integer)
    has_cross_ventilation = Column(Integer)
    has_night_ventilation = Column(Integer)
    has_stack_ventilation = Column(Integer)
    has_high_thermal_mass = Column(Integer)
    has_pcm = Column(Integer)
    has_cool_roof = Column(Integer)
    has_cool_wall_or_reflective_coating = Column(Integer)
    has_green_roof = Column(Integer)
    has_green_wall = Column(Integer)
    has_insulation_change = Column(Integer)
    has_glazing_change = Column(Integer)
    has_evaporative_cooling = Column(Integer)
    has_misting = Column(Integer)
    has_solar_chimney = Column(Integer)
    has_courtyard_strategy = Column(Integer)
    has_earth_air_heat_exchanger = Column(Integer)
    has_active_system = Column(Integer)
    active_system_type = Column(Text)             # NEW
    status = Column(Text, nullable=False)
    human_validated = Column(Integer, default=0)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)

    document = relationship("Document", back_populates="scenarios")
    outcomes = relationship("Outcome", back_populates="scenario", cascade="all, delete-orphan")


# ── NEW: Spaces (02B) ─────────────────────────────────────────────────

class Space(Base):
    __tablename__ = "spaces"

    id = Column(Text, primary_key=True)
    document_id = Column(Text, ForeignKey("documents.id"), nullable=False)
    space_code = Column(Text, nullable=False)      # e.g., A001_SP01
    space_temp_id = Column(Text)
    building_case_id = Column(Text)                # links to building_cases
    scenario_id = Column(Text)                     # optional link to scenario
    space_name_original = Column(Text)
    space_type_standardized = Column(Text)
    evaluated_area_m2 = Column(Float)
    evaluated_height_m = Column(Float)
    evaluated_volume_m3 = Column(Float)
    floor_level = Column(Text)
    orientation = Column(Text)
    window_to_wall_ratio = Column(Float)
    opening_area_m2 = Column(Float)
    occupancy_density = Column(Text)
    evidence_page = Column(Integer)
    evidence_text = Column(Text)
    status = Column(Text, nullable=False)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)

    document = relationship("Document", back_populates="spaces")


# ── NEW: Intervention Components (02C) ─────────────────────────────────

class InterventionComponent(Base):
    __tablename__ = "intervention_components"

    id = Column(Text, primary_key=True)
    document_id = Column(Text, ForeignKey("documents.id"), nullable=False)
    scenario_id = Column(Text)                     # links to scenarios.id
    scenario_temp_id = Column(Text)                # temp linkage
    component_code = Column(Text, nullable=False)  # e.g., A001_S01_C01
    component_id = Column(Text)                    # from AI output
    component_family = Column(Text)
    component_type = Column(Text)
    component_description_original = Column(Text)
    is_passive = Column(Integer)
    is_active_support = Column(Integer)
    is_existing_feature = Column(Integer)
    operation_schedule = Column(Text)
    parameter_value = Column(Float)
    parameter_unit = Column(Text)
    evidence_page = Column(Integer)
    evidence_text = Column(Text)
    confidence = Column(Text)
    status = Column(Text, nullable=False)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)

    document = relationship("Document", back_populates="intervention_components")


class Outcome(Base):
    __tablename__ = "outcomes"

    id = Column(Text, primary_key=True)
    document_id = Column(Text, ForeignKey("documents.id"), nullable=False)
    scenario_id = Column(Text, ForeignKey("scenarios.id"))
    outcome_code = Column(Text)
    outcome_temp_id = Column(Text)
    outcome_name = Column(Text, nullable=False)
    outcome_standardized_name = Column(Text)       # NEW: controlled name
    metric_group = Column(Text)
    room_or_space = Column(Text)
    space_id = Column(Text)                        # NEW: links to spaces
    occupant_group = Column(Text)
    value = Column(Float)
    unit = Column(Text)
    baseline_value = Column(Float)                 # NEW: explicit baseline value
    intervention_value = Column(Float)             # NEW: explicit intervention value
    reported_effect_value = Column(Float)
    reported_effect_unit = Column(Text)
    calculated_effect_value = Column(Float)
    calculated_effect_type = Column(Text)
    is_ai_calculated = Column(Integer)             # NEW: bool
    ai_calculation_basis = Column(Text)            # NEW: explanation
    standardized_value = Column(Float)
    standardized_unit = Column(Text)
    effect_direction = Column(Text)
    effect_direction_standardized = Column(Text)   # NEW: beneficial/harmful/neutral/unclear
    higher_is_better = Column(Integer)             # NEW: bool
    variance_available = Column(Integer)           # NEW: bool
    sd = Column(Float)                             # NEW
    se = Column(Float)                             # NEW
    ci_lower = Column(Float)                       # NEW
    ci_upper = Column(Float)                       # NEW
    n = Column(Integer)                            # NEW: sample size
    time_period = Column(Text)                     # NEW
    aggregation_method = Column(Text)              # NEW
    threshold_definition = Column(Text)            # NEW
    extraction_method = Column(Text)
    confidence = Column(Text)
    source_type = Column(Text)
    page = Column(Integer)
    table_or_figure = Column(Text)
    row_label = Column(Text)
    column_label = Column(Text)
    needs_digitization = Column(Integer, default=0)
    digitization_required_for_meta = Column(Integer)   # NEW: bool
    digitization_tool = Column(Text)                   # NEW
    digitization_error_risk = Column(Text)              # NEW
    usable_for_quantitative_synthesis = Column(Integer) # NEW: bool
    usable_for_sensitivity_only = Column(Integer)       # NEW: bool
    status = Column(Text, nullable=False)
    human_validated = Column(Integer, default=0)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)

    document = relationship("Document", back_populates="outcomes")
    scenario = relationship("Scenario", back_populates="outcomes")


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Text, primary_key=True)
    document_id = Column(Text, ForeignKey("documents.id"), nullable=False)
    linked_table = Column(Text, nullable=False)
    linked_record_id = Column(Text, nullable=False)
    page_number = Column(Integer)
    source_type = Column(Text)
    table_or_figure_label = Column(Text)
    row_label = Column(Text)
    column_label = Column(Text)
    evidence_text = Column(Text)
    crop_path = Column(Text)
    validation_status = Column(Text)
    created_at = Column(Text, nullable=False)

    document = relationship("Document", back_populates="evidence_records")


class QALog(Base):
    __tablename__ = "qa_log"

    id = Column(Text, primary_key=True)
    document_id = Column(Text, ForeignKey("documents.id"), nullable=False)
    record_type = Column(Text)
    record_id = Column(Text)
    severity = Column(Text)
    issue_type = Column(Text)
    description = Column(Text)
    required_action = Column(Text)
    resolved = Column(Integer, default=0)
    created_at = Column(Text, nullable=False)

    document = relationship("Document", back_populates="qa_logs")


class HumanReview(Base):
    __tablename__ = "human_review"

    id = Column(Text, primary_key=True)
    document_id = Column(Text, ForeignKey("documents.id"), nullable=False)
    record_type = Column(Text, nullable=False)
    record_id = Column(Text, nullable=False)
    field_name = Column(Text, nullable=False)
    ai_value = Column(Text)
    human_value = Column(Text)
    decision = Column(Text, nullable=False)
    reviewer = Column(Text)
    reviewer_comment = Column(Text)
    reviewed_at = Column(Text)

    document = relationship("Document", back_populates="human_reviews")


class DigitizationTask(Base):
    __tablename__ = "digitization_tasks"

    id = Column(Text, primary_key=True)
    document_id = Column(Text, ForeignKey("documents.id"), nullable=False)
    outcome_id = Column(Text, ForeignKey("outcomes.id"))
    page = Column(Integer)
    figure_label = Column(Text)
    crop_path = Column(Text)
    reason = Column(Text)
    status = Column(Text, nullable=False)
    digitized_value = Column(Float)
    digitized_unit = Column(Text)
    digitized_by = Column(Text)
    checked_by = Column(Text)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)

    document = relationship("Document", back_populates="digitization_tasks")


# ── NEW: Meta-Readiness (08) ──────────────────────────────────────────

class MetaReadiness(Base):
    __tablename__ = "meta_readiness"

    id = Column(Text, primary_key=True)
    document_id = Column(Text, ForeignKey("documents.id"), nullable=False)
    record_id = Column(Text, nullable=False)       # outcome_temp_id or effect_id
    has_valid_scenario = Column(Integer)
    has_valid_baseline = Column(Integer)
    has_numeric_value = Column(Integer)
    has_unit = Column(Integer)
    has_page = Column(Integer)
    has_evidence = Column(Integer)
    source_quality = Column(Text)
    human_validated = Column(Integer, default=0)
    eligible_for_primary_meta_analysis = Column(Integer)
    eligible_for_sensitivity_analysis = Column(Integer)
    classification = Column(Text)
    blocking_reason = Column(Text)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)

    document = relationship("Document", back_populates="meta_readiness_records")
