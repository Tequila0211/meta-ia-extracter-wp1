"""
Tests for dataset freezing.

Tests:
- Freeze generates expected files.
- Manifest structure is correct.
- Only validated records are included.
"""

import json
from pathlib import Path

import pytest

from src.database.db import get_engine
from src.database.models import Base, Document, Outcome, Scenario
from src.database.repository import generate_id
from src.utils.timestamps import now_iso


class TestFreezeDataset:

    @pytest.fixture
    def setup_db(self, tmp_path, monkeypatch):
        """Create a temporary database with test data."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        db_path = tmp_path / "test.sqlite"
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)()

        # Insert test document
        doc = Document(
            id=generate_id(),
            document_code="A001",
            file_name="test.pdf",
            file_path="/path/test.pdf",
            file_hash="abc123",
            status="validated",
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        session.add(doc)

        # Insert scenario
        scenario = Scenario(
            id=generate_id(),
            document_id=doc.id,
            scenario_code="A001_S01",
            scenario_label="Test scenario",
            status="extracted",
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        session.add(scenario)

        # Insert validated outcome
        outcome = Outcome(
            id=generate_id(),
            document_id=doc.id,
            scenario_id=scenario.id,
            outcome_name="cooling_demand",
            value=120.5,
            unit="kWh/m2.year",
            status="extracted",
            human_validated=1,
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        session.add(outcome)

        # Insert non-validated outcome (should be excluded)
        outcome_nv = Outcome(
            id=generate_id(),
            document_id=doc.id,
            outcome_name="heating_demand",
            value=80.0,
            status="extracted",
            human_validated=0,
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        session.add(outcome_nv)

        session.commit()

        # Monkeypatch database URL
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

        # Monkeypatch frozen datasets path
        frozen_dir = tmp_path / "frozen"
        frozen_dir.mkdir()
        monkeypatch.setattr(
            "src.export.freeze_dataset.get_frozen_datasets_path",
            lambda: frozen_dir,
        )

        yield {
            "session": session,
            "tmp_path": tmp_path,
            "frozen_dir": frozen_dir,
            "doc": doc,
        }

        session.close()

    def test_manifest_structure(self, setup_db):
        """Manifest should have all required fields."""
        from src.export.freeze_dataset import freeze_dataset

        manifest = freeze_dataset("v01")

        assert "dataset_version" in manifest
        assert manifest["dataset_version"] == "v01"
        assert "created_at" in manifest
        assert "codebook_version" in manifest
        assert "prompts_version" in manifest
        assert "schemas" in manifest
        assert len(manifest["schemas"]) == 5
        assert "number_of_documents" in manifest
        assert "number_of_validated_outcomes" in manifest
        assert "hash" in manifest

    def test_freeze_creates_files(self, setup_db):
        """Freeze should create CSV, XLSX, changelog, and manifest."""
        from src.export.freeze_dataset import freeze_dataset

        freeze_dataset("v01")
        frozen_dir = setup_db["frozen_dir"]

        assert (frozen_dir / "data_frozen_v01.csv").exists()
        assert (frozen_dir / "data_frozen_v01.xlsx").exists()
        assert (frozen_dir / "changelog_v01.md").exists()
        assert (frozen_dir / "manifest_v01.json").exists()

    def test_only_validated_included(self, setup_db):
        """Only human-validated outcomes should be in the frozen dataset."""
        from src.export.freeze_dataset import freeze_dataset

        manifest = freeze_dataset("v01")

        # Only 1 validated outcome should be included
        assert manifest["number_of_validated_outcomes"] == 1
