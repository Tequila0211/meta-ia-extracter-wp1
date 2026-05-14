"""
SQLAlchemy ORM models for the meta-analysis extraction pipeline.

Tables defined per PRD §13:
- documents, pages, ai_runs, article_classification,
- scenarios, outcomes, evidence, qa_log, human_review, digitization_tasks
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
    scenarios = relationship("Scenario", back_populates="document", cascade="all, delete-orphan")
    outcomes = relationship("Outcome", back_populates="document", cascade="all, delete-orphan")
    evidence_records = relationship("Evidence", back_populates="document", cascade="all, delete-orphan")
    qa_logs = relationship("QALog", back_populates="document", cascade="all, delete-orphan")
    human_reviews = relationship("HumanReview", back_populates="document", cascade="all, delete-orphan")
    digitization_tasks = relationship("DigitizationTask", back_populates="document", cascade="all, delete-orphan")


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
    operational_mode = Column(Text)
    building_typology = Column(Text)
    climate_location = Column(Text)
    climate_zone = Column(Text)
    climate_zone_source = Column(Text)  # 'document' or 'external_lookup'
    weather_file = Column(Text)
    simulation_software = Column(Text)
    baseline_description = Column(Text)
    intervention_description = Column(Text)
    intervention_type = Column(Text)
    is_package = Column(Integer)
    package_components = Column(Text)  # JSON-serialized list
    status = Column(Text, nullable=False)
    human_validated = Column(Integer, default=0)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)

    document = relationship("Document", back_populates="scenarios")
    outcomes = relationship("Outcome", back_populates="scenario", cascade="all, delete-orphan")


class Outcome(Base):
    __tablename__ = "outcomes"

    id = Column(Text, primary_key=True)
    document_id = Column(Text, ForeignKey("documents.id"), nullable=False)
    scenario_id = Column(Text, ForeignKey("scenarios.id"))
    outcome_code = Column(Text)
    outcome_temp_id = Column(Text)
    outcome_name = Column(Text, nullable=False)
    metric_group = Column(Text)
    room_or_space = Column(Text)
    occupant_group = Column(Text)
    value = Column(Float)
    unit = Column(Text)
    reported_effect_value = Column(Float)
    reported_effect_unit = Column(Text)
    calculated_effect_value = Column(Float)
    calculated_effect_type = Column(Text)
    standardized_value = Column(Float)
    standardized_unit = Column(Text)
    effect_direction = Column(Text)
    extraction_method = Column(Text)
    confidence = Column(Text)
    source_type = Column(Text)
    page = Column(Integer)
    table_or_figure = Column(Text)
    row_label = Column(Text)
    column_label = Column(Text)
    needs_digitization = Column(Integer, default=0)
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
