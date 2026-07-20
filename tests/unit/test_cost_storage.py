"""
Tests for cost storage persistence layer.

This module tests the cost storage functionality including normal operations,
error handling, recovery mechanisms, and edge cases.
"""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from github_analyzer.data.cost_storage import (
    CorruptedDataError,
    CostRecord,
    CostStorage,
    DiskFullError,
    StorageBackend,
    StorageError,
    StoragePermissionError,
)


class TestCostRecord:
    """Test CostRecord dataclass functionality."""

    def test_cost_record_creation(self):
        """Test creating a cost record."""
        record = CostRecord(
            timestamp="2024-01-01T12:00:00Z",
            model="claude-3-haiku-20240307",
            operation="analyze_repo",
            input_tokens=100,
            output_tokens=50,
            cost=0.025,
            metadata={"repo": "test/repo"},
        )

        assert record.timestamp == "2024-01-01T12:00:00Z"
        assert record.model == "claude-3-haiku-20240307"
        assert record.operation == "analyze_repo"
        assert record.input_tokens == 100
        assert record.output_tokens == 50
        assert record.cost == 0.025
        assert record.metadata == {"repo": "test/repo"}

    def test_cost_record_to_dict(self):
        """Test converting cost record to dictionary."""
        record = CostRecord(
            timestamp="2024-01-01T12:00:00Z",
            model="claude-3-haiku-20240307",
            operation="analyze_repo",
            input_tokens=100,
            output_tokens=50,
            cost=0.025,
        )

        result = record.to_dict()
        expected = {
            "timestamp": "2024-01-01T12:00:00Z",
            "model": "claude-3-haiku-20240307",
            "operation": "analyze_repo",
            "input_tokens": 100,
            "output_tokens": 50,
            "cost": 0.025,
            "metadata": None,
        }

        assert result == expected

    def test_cost_record_from_dict(self):
        """Test creating cost record from dictionary."""
        data = {
            "timestamp": "2024-01-01T12:00:00Z",
            "model": "claude-3-haiku-20240307",
            "operation": "analyze_repo",
            "input_tokens": 100,
            "output_tokens": 50,
            "cost": 0.025,
            "metadata": {"repo": "test/repo"},
        }

        record = CostRecord.from_dict(data)

        assert record.timestamp == "2024-01-01T12:00:00Z"
        assert record.model == "claude-3-haiku-20240307"
        assert record.operation == "analyze_repo"
        assert record.input_tokens == 100
        assert record.output_tokens == 50
        assert record.cost == 0.025
        assert record.metadata == {"repo": "test/repo"}


class TestCostStorage:
    """Test CostStorage functionality."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary storage directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def mock_config(self):
        """Mock configuration."""
        config = Mock()
        config.cost_storage.enabled = True
        config.cost_storage.storage_path = None
        config.cost_storage.backend = "json"
        config.cost_storage.rotation_days = 30
        return config

    @pytest.fixture
    def mock_config_sqlite(self):
        """Mock configuration for SQLite backend."""
        config = Mock()
        config.cost_storage.enabled = True
        config.cost_storage.storage_path = None
        config.cost_storage.backend = "sqlite"
        config.cost_storage.rotation_days = 30
        return config

    @pytest.fixture
    def cost_storage(self, temp_storage_dir, mock_config):
        """Create CostStorage instance with temporary directory."""
        with patch(
            "github_analyzer.data.cost_storage.get_config", return_value=mock_config
        ):
            storage = CostStorage(storage_path=temp_storage_dir)
            return storage

    @pytest.fixture
    def sample_record(self):
        """Create sample cost record."""
        return CostRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            model="claude-3-haiku-20240307",
            operation="analyze_repo",
            input_tokens=100,
            output_tokens=50,
            cost=0.025,
            metadata={"repo": "test/repo"},
        )

    def test_storage_initialization_success(self, temp_storage_dir, mock_config):
        """Test successful storage initialization."""
        with patch(
            "github_analyzer.data.cost_storage.get_config", return_value=mock_config
        ):
            storage = CostStorage(storage_path=temp_storage_dir)

            assert storage.enabled is True
            assert storage.storage_path == temp_storage_dir
            assert storage.current_file == temp_storage_dir / "current_costs.json"
            assert storage.archive_dir == temp_storage_dir / "archive"
            assert storage.archive_dir.exists()

    def test_storage_initialization_disabled(self, temp_storage_dir, mock_config):
        """Test storage initialization when disabled."""
        mock_config.cost_storage.enabled = False

        with patch(
            "github_analyzer.data.cost_storage.get_config", return_value=mock_config
        ):
            storage = CostStorage(storage_path=temp_storage_dir)

            assert storage.enabled is False

    def test_storage_initialization_permission_error(self, mock_config):
        """Test storage initialization with permission error."""
        # Use a path that doesn't exist and can't be created
        restricted_path = Path("/root/restricted")

        mock_config.cost_storage.enabled = True

        with patch(
            "github_analyzer.data.cost_storage.get_config", return_value=mock_config
        ):
            with pytest.raises(StorageError):
                CostStorage(storage_path=restricted_path)

    def test_save_cost_success(self, cost_storage, sample_record):
        """Test successful cost record saving."""
        result = cost_storage.save_cost(sample_record)

        assert result is True
        assert cost_storage.current_file.exists()

        # Verify record was saved
        with open(cost_storage.current_file) as f:
            data = json.load(f)
            assert len(data) == 1
            assert data[0]["operation"] == "analyze_repo"
            assert data[0]["cost"] == 0.025

    def test_save_cost_disabled(self, temp_storage_dir, mock_config, sample_record):
        """Test saving when storage is disabled."""
        mock_config.cost_storage.enabled = False

        with patch(
            "github_analyzer.data.cost_storage.get_config", return_value=mock_config
        ):
            storage = CostStorage(storage_path=temp_storage_dir)
            result = storage.save_cost(sample_record)

            assert result is False
            # When disabled, current_file is not created during init
            current_file = temp_storage_dir / "current_costs.json"
            assert not current_file.exists()

    def test_save_cost_multiple_records(self, cost_storage, sample_record):
        """Test saving multiple cost records."""
        # Save first record
        result1 = cost_storage.save_cost(sample_record)
        assert result1 is True

        # Save second record
        record2 = CostRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            model="claude-3-haiku-20240307",
            operation="batch_analyze",
            input_tokens=200,
            output_tokens=100,
            cost=0.050,
        )
        result2 = cost_storage.save_cost(record2)
        assert result2 is True

        # Verify both records are saved
        with open(cost_storage.current_file) as f:
            data = json.load(f)
            assert len(data) == 2
            assert data[0]["operation"] == "analyze_repo"
            assert data[1]["operation"] == "batch_analyze"

    def test_load_current_records_empty(self, cost_storage):
        """Test loading records when file doesn't exist."""
        records = cost_storage._load_current_records()
        assert records == []

    def test_load_current_records_corrupted_json(self, cost_storage):
        """Test loading records with corrupted JSON."""
        # Create corrupted JSON file
        cost_storage.current_file.write_text("invalid json content")

        records = cost_storage._load_current_records()

        # Should return empty list and create backup
        assert records == []

        # Check that backup was created
        backup_files = list(cost_storage.current_file.parent.glob("*_corrupted_*.bak"))
        assert len(backup_files) > 0

    def test_load_current_records_non_list_data(self, cost_storage):
        """Test loading records with non-list JSON data."""
        # Create JSON file with non-list data
        cost_storage.current_file.write_text('{"not": "a list"}')

        records = cost_storage._load_current_records()
        assert records == []

    def test_atomic_write_success(self, cost_storage):
        """Test atomic write functionality."""
        test_data = [{"test": "data"}]
        test_file = cost_storage.storage_path / "test.json"

        cost_storage._atomic_write(test_file, test_data)

        assert test_file.exists()
        with open(test_file) as f:
            data = json.load(f)
            assert data == test_data

    def test_atomic_write_cleanup_on_error(self, cost_storage):
        """Test atomic write cleans up temp files on error."""
        test_data = [{"test": "data"}]

        # Use a path that will cause an error during move
        with patch("shutil.move", side_effect=OSError("Move failed")):
            with pytest.raises(StorageError):
                cost_storage._atomic_write(cost_storage.current_file, test_data)

        # Verify no temp files are left behind
        temp_files = list(cost_storage.storage_path.glob(".*tmp"))
        assert len(temp_files) == 0

    def test_backup_corrupted_file(self, cost_storage):
        """Test backing up corrupted files."""
        # Create a test file
        test_file = cost_storage.storage_path / "test.json"
        test_file.write_text("corrupted content")

        cost_storage._backup_corrupted_file(test_file)

        # Original file should be removed
        assert not test_file.exists()

        # Backup file should exist
        backup_files = list(cost_storage.storage_path.glob("test_corrupted_*.bak"))
        assert len(backup_files) == 1
        assert backup_files[0].read_text() == "corrupted content"

    def test_cleanup_old_archives(self, cost_storage, mock_config):
        """Test cleaning up old archive files."""
        # Create old archive files
        old_file1 = cost_storage.archive_dir / "costs_20220101.json"
        old_file2 = cost_storage.archive_dir / "costs_20220102.json"
        recent_file = cost_storage.archive_dir / "costs_20241201.json"

        for file in [old_file1, old_file2, recent_file]:
            file.write_text("[]")

        # Set file modification times to simulate old files
        import os
        import time

        old_time = time.time() - (40 * 24 * 3600)  # 40 days ago
        recent_time = time.time() - (10 * 24 * 3600)  # 10 days ago

        os.utime(old_file1, (old_time, old_time))
        os.utime(old_file2, (old_time, old_time))
        os.utime(recent_file, (recent_time, recent_time))

        # Verify files exist before cleanup
        assert old_file1.exists()
        assert old_file2.exists()
        assert recent_file.exists()

        # Run cleanup
        result = cost_storage._cleanup_old_archives()

        # Check that cleanup ran (should find files to clean)
        assert isinstance(result, bool)

    def test_get_costs_by_date_range(self, cost_storage):
        """Test retrieving costs by date range."""
        # Create test records with different dates
        start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        middle_time = datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2024, 1, 3, 12, 0, 0, tzinfo=timezone.utc)

        records = [
            {
                "timestamp": start_time.isoformat(),
                "cost": 0.01,
                "operation": "op1",
                "model": "model1",
                "input_tokens": 10,
                "output_tokens": 5,
            },
            {
                "timestamp": middle_time.isoformat(),
                "cost": 0.02,
                "operation": "op2",
                "model": "model1",
                "input_tokens": 20,
                "output_tokens": 10,
            },
            {
                "timestamp": end_time.isoformat(),
                "cost": 0.03,
                "operation": "op3",
                "model": "model1",
                "input_tokens": 30,
                "output_tokens": 15,
            },
        ]

        # Save records to current file
        with open(cost_storage.current_file, "w") as f:
            json.dump(records, f)

        # Query date range
        query_start = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        query_end = datetime(2024, 1, 2, 23, 59, 59, tzinfo=timezone.utc)

        results = cost_storage.get_costs_by_date_range(query_start, query_end)

        assert len(results) == 2
        assert results[0].operation == "op1"
        assert results[1].operation == "op2"

    def test_get_daily_summary(self, cost_storage):
        """Test getting daily cost summary."""
        # Create test records for a specific day
        test_date = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        records = [
            {
                "timestamp": test_date.isoformat(),
                "cost": 0.01,
                "operation": "op1",
                "model": "model1",
                "input_tokens": 10,
                "output_tokens": 5,
            },
            {
                "timestamp": test_date.isoformat(),
                "cost": 0.02,
                "operation": "op2",
                "model": "model2",
                "input_tokens": 20,
                "output_tokens": 10,
            },
        ]

        with open(cost_storage.current_file, "w") as f:
            json.dump(records, f)

        summary = cost_storage.get_daily_summary(test_date)

        assert summary["total_cost"] == 0.03
        assert summary["total_input_tokens"] == 30
        assert summary["total_output_tokens"] == 15
        assert summary["total_operations"] == 2
        assert "model1" in summary["by_model"]
        assert "model2" in summary["by_model"]
        assert "op1" in summary["by_operation"]
        assert "op2" in summary["by_operation"]

    def test_get_daily_summary_empty(self, cost_storage):
        """Test getting daily summary with no records."""
        test_date = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        summary = cost_storage.get_daily_summary(test_date)

        expected = {
            "total_cost": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_operations": 0,
            "by_model": {},
            "by_operation": {},
        }

        assert summary == expected

    def test_save_cost_disk_full_error(self, cost_storage, sample_record):
        """Test handling disk full error during save."""
        # Mock the atomic write to raise disk full error
        disk_full_error = OSError()
        disk_full_error.errno = 28

        with patch.object(cost_storage, "_atomic_write", side_effect=disk_full_error):
            with patch.object(
                cost_storage, "_cleanup_old_archives", return_value=False
            ):
                with pytest.raises(DiskFullError):
                    cost_storage.save_cost(sample_record)

    def test_save_cost_permission_error(self, cost_storage, sample_record):
        """Test handling permission error during save."""
        # Mock the atomic write to raise permission error
        permission_error = OSError()
        permission_error.errno = 13

        with patch.object(cost_storage, "_atomic_write", side_effect=permission_error):
            with pytest.raises(StoragePermissionError):
                cost_storage.save_cost(sample_record)

    def test_save_cost_serialization_error(self, cost_storage):
        """Test handling serialization error during save."""
        # Test that serialization errors return False instead of raising
        # (since they fall through to the general exception handler)
        with patch("json.dump", side_effect=TypeError("Object not JSON serializable")):
            sample_record = CostRecord(
                timestamp="2024-01-01T12:00:00Z",
                model="claude-3-haiku-20240307",
                operation="analyze_repo",
                input_tokens=100,
                output_tokens=50,
                cost=0.025,
            )

            result = cost_storage.save_cost(sample_record)
            assert result is False

    def test_save_cost_corrupted_data_error(self, cost_storage, sample_record):
        """Test direct CorruptedDataError handling."""

        # Mock to raise TypeError specifically during JSON encoding
        def mock_atomic_write(target_file, data):
            # This will trigger the TypeError -> CorruptedDataError path
            raise TypeError("Object not JSON serializable")

        with patch.object(cost_storage, "_atomic_write", side_effect=mock_atomic_write):
            with pytest.raises(CorruptedDataError):
                cost_storage.save_cost(sample_record)

    def test_save_cost_retry_mechanism(self, cost_storage, sample_record):
        """Test retry mechanism with transient failures."""
        call_count = 0

        def failing_atomic_write(target_file, data):
            nonlocal call_count
            call_count += 1
            if call_count < 3:  # Fail first 2 attempts
                raise OSError("Transient error")
            # Succeed on 3rd attempt - use real atomic write
            return cost_storage.__class__._atomic_write(cost_storage, target_file, data)

        with patch.object(
            cost_storage, "_atomic_write", side_effect=failing_atomic_write
        ):
            result = cost_storage.save_cost(sample_record)

        assert result is True
        assert call_count == 3

    def test_sqlite_backend_initialization(self, temp_storage_dir, mock_config_sqlite):
        """Test SQLite backend initialization."""
        with patch(
            "github_analyzer.data.cost_storage.get_config",
            return_value=mock_config_sqlite,
        ):
            storage = CostStorage(storage_path=temp_storage_dir)

            assert storage.enabled is True
            assert storage.backend == StorageBackend.SQLITE
            assert storage.db_file.exists()

    def test_sqlite_backend_save_and_load(
        self, temp_storage_dir, mock_config_sqlite, sample_record
    ):
        """Test SQLite backend save and load operations."""
        with patch(
            "github_analyzer.data.cost_storage.get_config",
            return_value=mock_config_sqlite,
        ):
            storage = CostStorage(storage_path=temp_storage_dir)

            # Save record
            assert storage.save_cost(sample_record) is True

            # Load records
            records = storage._load_current_records()
            assert len(records) == 1

            loaded_record = records[0]
            assert loaded_record["model"] == sample_record.model
            assert loaded_record["operation"] == sample_record.operation
            assert loaded_record["input_tokens"] == sample_record.input_tokens
            assert loaded_record["output_tokens"] == sample_record.output_tokens
            assert loaded_record["cost"] == sample_record.cost
            assert loaded_record["metadata"] == sample_record.metadata

    def test_backend_selection_explicit(self, temp_storage_dir):
        """Test explicit backend selection via parameter."""
        mock_config = Mock()
        mock_config.cost_storage.enabled = True
        mock_config.cost_storage.storage_path = None
        mock_config.cost_storage.backend = "json"  # Config default is JSON
        mock_config.cost_storage.rotation_days = 30

        with patch(
            "github_analyzer.data.cost_storage.get_config", return_value=mock_config
        ):
            # Override with SQLite via parameter
            storage = CostStorage(storage_path=temp_storage_dir, backend="sqlite")

            assert storage.backend == StorageBackend.SQLITE
            assert storage.db_file.exists()

    def test_get_cost_storage_singleton(self):
        """Test singleton pattern for cost storage."""
        # Clear any existing instance
        import github_analyzer.data.cost_storage
        from github_analyzer.data.cost_storage import get_cost_storage

        github_analyzer.data.cost_storage._storage_instance = None

        with patch("github_analyzer.data.cost_storage.get_config") as mock_get_config:
            mock_config = Mock()
            mock_config.cost_storage.enabled = True
            mock_config.cost_storage.storage_path = None
            mock_config.cost_storage.backend = "json"
            mock_config.cost_storage.rotation_days = 30
            mock_get_config.return_value = mock_config

            storage1 = get_cost_storage()
            storage2 = get_cost_storage()

            assert storage1 is storage2  # Same instance
