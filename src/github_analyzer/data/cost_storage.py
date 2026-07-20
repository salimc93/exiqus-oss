# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Cost storage persistence layer for GitHub Analyzer.

This module provides persistent storage for API usage costs, enabling
historical tracking, analytics, and budget management.
"""

import json
import shutil
import sqlite3
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils.config import get_config
from ..utils.logging import get_logger

logger = get_logger(__name__)


class StorageBackend(Enum):
    """Available storage backends."""

    JSON = "json"
    SQLITE = "sqlite"


class StorageError(Exception):
    """Base exception for storage-related errors."""

    pass


class DiskFullError(StorageError):
    """Raised when disk is full."""

    pass


class StoragePermissionError(StorageError):
    """Raised when permission is denied."""

    pass


class CorruptedDataError(StorageError):
    """Raised when data is corrupted beyond recovery."""

    pass


@dataclass
class CostRecord:
    """Individual cost record."""

    timestamp: str
    model: str
    operation: str
    input_tokens: int
    output_tokens: int
    cost: float
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CostRecord":
        """Create from dictionary."""
        return cls(**data)


class CostStorage:
    """Persistent storage for cost tracking data."""

    def __init__(
        self, storage_path: Optional[Path] = None, backend: Optional[str] = None
    ):
        """
        Initialize cost storage with resilient directory creation.

        Args:
            storage_path: Path to storage location (defaults to config or ~/.exiqus/costs/)
            backend: Storage backend ("json" or "sqlite", defaults to config)

        Raises:
            StorageError: If storage cannot be initialized
        """
        config = get_config()
        self.storage_path = storage_path or self._get_storage_path()
        self.enabled = config.cost_storage.enabled
        self.backend = StorageBackend(backend or config.cost_storage.backend)

        if not self.enabled:
            logger.info("Cost storage disabled in configuration")
            return

        try:
            # Create storage directories with proper error handling
            self._ensure_directories()

            # Initialize backend-specific storage
            if self.backend == StorageBackend.JSON:
                self.current_file = self.storage_path / "current_costs.json"
                self.archive_dir = self.storage_path / "archive"
            elif self.backend == StorageBackend.SQLITE:
                self.db_file = self.storage_path / "costs.db"
                self._init_sqlite_db()

            # Verify we can write to the directory
            self._verify_write_access()

            logger.info(
                f"Initialized cost storage at {self.storage_path} (enabled: {self.enabled})"
            )

        except Exception as e:
            logger.error(f"Failed to initialize cost storage: {e}")
            self.enabled = False  # Disable on init failure
            raise StorageError(f"Storage initialization failed: {e}") from e

    def _get_storage_path(self) -> Path:
        """Get storage path from config or default."""
        config = get_config()
        if config.cost_storage.storage_path:
            return Path(config.cost_storage.storage_path)

        # Default path
        home = Path.home()
        return home / ".exiqus" / "costs"

    def _ensure_directories(self) -> None:
        """
        Ensure storage directories exist with proper error handling.

        Raises:
            PermissionError: If directory creation is denied
            StorageError: If directory creation fails
        """
        try:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            archive_dir = self.storage_path / "archive"
            archive_dir.mkdir(exist_ok=True)
        except OSError as e:
            if e.errno == 13:  # Permission denied
                raise StoragePermissionError(
                    f"Cannot create storage directory: {self.storage_path}"
                ) from e
            else:
                raise StorageError(f"Failed to create storage directories: {e}") from e

    def _verify_write_access(self) -> None:
        """
        Verify write access to storage directory.

        Raises:
            PermissionError: If write access is denied
        """
        test_file = self.storage_path / ".write_test"
        try:
            # Test write access
            test_file.write_text("test")
            test_file.unlink()
        except OSError as e:
            if e.errno == 13:  # Permission denied
                raise StoragePermissionError(
                    f"No write access to storage directory: {self.storage_path}"
                ) from e
            else:
                raise StorageError(f"Write access test failed: {e}") from e

    def save_cost(self, record: CostRecord) -> bool:
        """
        Save a cost record to persistent storage with atomic writes.

        Args:
            record: Cost record to save

        Returns:
            True if saved successfully, False otherwise
        """
        if not self.enabled:
            return False

        if self.backend == StorageBackend.SQLITE:
            return self._save_cost_sqlite(record)
        else:
            return self._save_cost_json(record)

    def _save_cost_json(self, record: CostRecord) -> bool:
        """Save cost record to JSON backend."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Load existing records
                records = self._load_current_records()

                # Add new record
                records.append(record.to_dict())

                # Atomic write using temporary file
                self._atomic_write(self.current_file, records)

                logger.debug(
                    f"Saved cost record: {record.operation} - ${record.cost:.4f}"
                )

                # Check if we need to rotate files (daily rotation)
                self._rotate_if_needed()

                return True

            except OSError as e:
                if e.errno == 28:  # No space left on device
                    logger.critical(f"Disk full - cannot save cost record: {e}")
                    # Try to free up space by cleaning old archives
                    if self._cleanup_old_archives():
                        continue  # Retry after cleanup
                    raise DiskFullError("Disk is full and cleanup failed") from e
                elif e.errno == 13:  # Permission denied
                    logger.error(f"Permission denied saving cost record: {e}")
                    raise StoragePermissionError(
                        f"Cannot write to {self.current_file}"
                    ) from e
                else:
                    logger.warning(f"OS error on attempt {attempt + 1}: {e}")
                    if attempt == max_retries - 1:
                        raise StorageError(
                            f"Failed after {max_retries} attempts"
                        ) from e

            except (TypeError, ValueError) as e:
                logger.error(f"JSON encoding error: {e}")
                raise CorruptedDataError("Invalid data cannot be serialized") from e

            except Exception as e:
                logger.warning(f"Storage error on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    logger.error(
                        f"Failed to save cost record after {max_retries} attempts: {e}"
                    )
                    return False

        return False

    def _save_cost_sqlite(self, record: CostRecord) -> bool:
        """Save cost record to SQLite backend."""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()

                # Serialize metadata as JSON
                metadata_json = json.dumps(record.metadata) if record.metadata else None

                cursor.execute(
                    """
                    INSERT INTO cost_records
                    (timestamp, model, operation, input_tokens, output_tokens, cost, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        record.timestamp,
                        record.model,
                        record.operation,
                        record.input_tokens,
                        record.output_tokens,
                        record.cost,
                        metadata_json,
                    ),
                )

                conn.commit()

                logger.debug(
                    f"Saved cost record to SQLite: {record.operation} - ${record.cost:.4f}"
                )
                return True

        except Exception as e:
            logger.error(f"Failed to save cost record to SQLite: {e}")
            return False

    def _load_current_records(self) -> List[Dict[str, Any]]:
        """Load current cost records with enhanced error handling."""
        if self.backend == StorageBackend.SQLITE:
            return self._load_records_sqlite()
        else:
            return self._load_records_json()

    def _load_records_json(self) -> List[Dict[str, Any]]:
        """Load records from JSON backend."""
        if not self.current_file.exists():
            return []

        max_retries = 3
        for attempt in range(max_retries):
            try:
                with open(self.current_file, "r") as f:
                    records = json.load(f)
                    if isinstance(records, list):
                        return records
                    else:
                        logger.warning(
                            "Cost file contains non-list data, starting fresh"
                        )
                        return []
            except json.JSONDecodeError as e:
                logger.warning(f"JSON decode error on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    # Try to create backup and start fresh
                    self._backup_corrupted_file(self.current_file)
                    logger.error("Corrupted cost file backed up, starting fresh")
                    return []
            except OSError as e:
                logger.warning(f"OS error reading file on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    logger.error(
                        f"Failed to read cost file after {max_retries} attempts"
                    )
                    return []

        return []

    def _load_records_sqlite(self) -> List[Dict[str, Any]]:
        """Load records from SQLite backend."""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT timestamp, model, operation, input_tokens, output_tokens, cost, metadata
                    FROM cost_records
                    ORDER BY created_at
                """
                )

                records = []
                for row in cursor.fetchall():
                    (
                        timestamp,
                        model,
                        operation,
                        input_tokens,
                        output_tokens,
                        cost,
                        metadata_json,
                    ) = row

                    # Deserialize metadata
                    metadata = json.loads(metadata_json) if metadata_json else None

                    record = {
                        "timestamp": timestamp,
                        "model": model,
                        "operation": operation,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "cost": cost,
                        "metadata": metadata,
                    }
                    records.append(record)

                return records

        except Exception as e:
            logger.error(f"Failed to load records from SQLite: {e}")
            return []

    def _atomic_write(self, target_file: Path, data: List[Dict[str, Any]]) -> None:
        """
        Atomically write data to file using temporary file.

        Args:
            target_file: Target file path
            data: Data to write

        Raises:
            StorageError: If write fails
        """
        temp_file = None
        try:
            # Create temporary file in same directory as target
            temp_fd, temp_path = tempfile.mkstemp(
                dir=target_file.parent, prefix=f".{target_file.name}.", suffix=".tmp"
            )
            temp_file = Path(temp_path)

            # Write data to temporary file
            with open(temp_fd, "w") as f:
                json.dump(data, f, indent=2)

            # Atomic move
            shutil.move(temp_file, target_file)
            temp_file = None  # Successfully moved, don't clean up

        except Exception as e:
            # Clean up temp file on error
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass  # Best effort cleanup
            raise StorageError(f"Atomic write failed: {e}") from e

    def _backup_corrupted_file(self, file_path: Path) -> None:
        """
        Create backup of corrupted file for potential recovery.

        Args:
            file_path: Path to corrupted file
        """
        try:
            if file_path.exists():
                backup_name = f"{file_path.stem}_corrupted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
                backup_path = file_path.parent / backup_name
                shutil.copy2(file_path, backup_path)
                logger.info(f"Backed up corrupted file to {backup_path}")
                # Remove original corrupted file
                file_path.unlink()
        except OSError as e:
            logger.warning(f"Failed to backup corrupted file: {e}")

    def _cleanup_old_archives(self) -> bool:
        """
        Clean up old archive files to free disk space.

        Returns:
            True if cleanup freed space, False otherwise
        """
        try:
            config = get_config()
            max_age_days = config.cost_storage.rotation_days
            cutoff_date = datetime.now().timestamp() - (max_age_days * 24 * 3600)

            cleaned_count = 0
            for archive_file in self.archive_dir.glob("costs_*.json"):
                try:
                    if archive_file.stat().st_mtime < cutoff_date:
                        archive_file.unlink()
                        cleaned_count += 1
                        logger.info(f"Cleaned up old archive: {archive_file.name}")
                except OSError:
                    continue  # Skip files we can't delete

            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old archive files")
                return True
            return False

        except Exception as e:
            logger.warning(f"Archive cleanup failed: {e}")
            return False

    def _rotate_if_needed(self) -> None:
        """Rotate cost file if it's a new day."""
        if not self.current_file.exists():
            return

        # Get file modification time
        file_mtime = datetime.fromtimestamp(self.current_file.stat().st_mtime)
        today = datetime.now().date()

        # If file is from a previous day, rotate it
        if file_mtime.date() < today:
            archive_name = f"costs_{file_mtime.strftime('%Y%m%d')}.json"
            archive_path = self.archive_dir / archive_name

            # Move current file to archive
            self.current_file.rename(archive_path)
            logger.info(f"Rotated cost file to {archive_path}")

    def get_costs_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[CostRecord]:
        """
        Get costs within a date range.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of cost records
        """
        if not self.enabled:
            return []

        records = []

        # Load current file
        current_records = self._load_current_records()
        records.extend(self._filter_by_date(current_records, start_date, end_date))

        # Load archived files in date range
        for archive_file in self.archive_dir.glob("costs_*.json"):
            try:
                # Extract date from filename
                date_str = archive_file.stem.split("_")[1]
                file_date = datetime.strptime(date_str, "%Y%m%d").date()

                # Skip if outside date range
                if file_date < start_date.date() or file_date > end_date.date():
                    continue

                # Load and filter records
                with open(archive_file, "r") as f:
                    archived_records = json.load(f)
                    records.extend(
                        self._filter_by_date(archived_records, start_date, end_date)
                    )
            except (ValueError, json.JSONDecodeError) as e:
                logger.warning(f"Skipping corrupted archive {archive_file}: {e}")
                continue

        # Convert to CostRecord objects
        return [CostRecord.from_dict(r) for r in records]

    def _filter_by_date(
        self, records: List[Dict[str, Any]], start_date: datetime, end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Filter records by date range."""
        filtered = []
        for record in records:
            try:
                record_time = datetime.fromisoformat(record["timestamp"])
                if start_date <= record_time <= end_date:
                    filtered.append(record)
            except (ValueError, KeyError):
                logger.warning(
                    f"Invalid record timestamp: {record.get('timestamp', 'missing')}"
                )
                continue
        return filtered

    def get_daily_summary(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get cost summary for a specific day.

        Args:
            date: Date to get summary for (defaults to today)

        Returns:
            Summary dict with total cost, token counts, etc.
        """
        if date is None:
            date = datetime.now()

        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = date.replace(hour=23, minute=59, second=59, microsecond=999999)

        records = self.get_costs_by_date_range(start, end)

        return self._calculate_summary(records)

    def _calculate_summary(self, records: List[CostRecord]) -> Dict[str, Any]:
        """Calculate summary statistics for a list of records."""
        if not records:
            return {
                "total_cost": 0.0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_operations": 0,
                "by_model": {},
                "by_operation": {},
            }

        summary: Dict[str, Any] = {
            "total_cost": sum(r.cost for r in records),
            "total_input_tokens": sum(r.input_tokens for r in records),
            "total_output_tokens": sum(r.output_tokens for r in records),
            "total_operations": len(records),
            "by_model": {},
            "by_operation": {},
        }

        # Group by model
        for record in records:
            if record.model not in summary["by_model"]:
                summary["by_model"][record.model] = {
                    "cost": 0.0,
                    "operations": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                }

            summary["by_model"][record.model]["cost"] += record.cost
            summary["by_model"][record.model]["operations"] += 1
            summary["by_model"][record.model]["input_tokens"] += record.input_tokens
            summary["by_model"][record.model]["output_tokens"] += record.output_tokens

        # Group by operation
        for record in records:
            if record.operation not in summary["by_operation"]:
                summary["by_operation"][record.operation] = {"cost": 0.0, "count": 0}

            summary["by_operation"][record.operation]["cost"] += record.cost
            summary["by_operation"][record.operation]["count"] += 1

        return summary

    def _init_sqlite_db(self) -> None:
        """Initialize SQLite database with cost tracking schema."""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()

                # Create cost_records table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS cost_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        model TEXT NOT NULL,
                        operation TEXT NOT NULL,
                        input_tokens INTEGER NOT NULL,
                        output_tokens INTEGER NOT NULL,
                        cost REAL NOT NULL,
                        metadata TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Create indexes for better query performance
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_timestamp
                    ON cost_records(timestamp)
                """
                )

                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_model_operation
                    ON cost_records(model, operation)
                """
                )

                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_created_at
                    ON cost_records(created_at)
                """
                )

                conn.commit()
                logger.debug(f"SQLite database initialized at {self.db_file}")

        except Exception as e:
            raise StorageError(f"Failed to initialize SQLite database: {e}")


# Singleton instance for easy access
_storage_instance: Optional[CostStorage] = None


def get_cost_storage() -> CostStorage:
    """Get or create the singleton cost storage instance."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = CostStorage()
    return _storage_instance
