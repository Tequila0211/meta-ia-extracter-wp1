"""
Tests for document registration.

Tests:
- Registration creates proper document codes.
- Duplicate documents are skipped.
- Hash is computed correctly.
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from src.database.db import get_engine
from src.database.models import Base
from src.database.repository import (
    generate_id,
    get_document_by_code,
    get_document_by_hash,
    get_next_document_code,
    insert_document,
)
from src.utils.hashing import compute_sha256, compute_text_hash


class TestDocumentRegistry:

    @pytest.fixture
    def db_session(self, tmp_path):
        """Create a temporary database session."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        db_path = tmp_path / "test.sqlite"
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)()
        yield session
        session.close()

    def test_generate_id(self):
        """UUID generation produces unique strings."""
        id1 = generate_id()
        id2 = generate_id()
        assert id1 != id2
        assert len(id1) == 36

    def test_next_document_code_empty(self, db_session):
        """First document code should be A001."""
        code = get_next_document_code(db_session, "A", 3)
        assert code == "A001"

    def test_next_document_code_increment(self, db_session):
        """Document codes increment correctly."""
        insert_document(db_session, "A001", "test.pdf", "/path/test.pdf", "hash1")
        db_session.commit()
        code = get_next_document_code(db_session, "A", 3)
        assert code == "A002"

    def test_insert_document(self, db_session):
        """Documents can be inserted and retrieved."""
        doc = insert_document(db_session, "A001", "test.pdf", "/path/test.pdf", "abc123")
        db_session.commit()

        retrieved = get_document_by_code(db_session, "A001")
        assert retrieved is not None
        assert retrieved.document_code == "A001"
        assert retrieved.file_name == "test.pdf"
        assert retrieved.status == "pending"

    def test_duplicate_detection_by_hash(self, db_session):
        """Documents with the same hash are detected."""
        insert_document(db_session, "A001", "test.pdf", "/path/test.pdf", "same_hash")
        db_session.commit()

        existing = get_document_by_hash(db_session, "same_hash")
        assert existing is not None
        assert existing.document_code == "A001"


class TestHashing:

    def test_file_hash(self, tmp_path):
        """File hashing produces consistent results."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        hash1 = compute_sha256(test_file)
        hash2 = compute_sha256(test_file)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex digest

    def test_text_hash(self):
        """Text hashing produces consistent results."""
        hash1 = compute_text_hash("test content")
        hash2 = compute_text_hash("test content")
        assert hash1 == hash2

    def test_different_content_different_hash(self, tmp_path):
        """Different files produce different hashes."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("Content A")
        file2.write_text("Content B")

        hash1 = compute_sha256(file1)
        hash2 = compute_sha256(file2)
        assert hash1 != hash2
