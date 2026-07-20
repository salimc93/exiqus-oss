"""
Test suite for scheduler service usage reporting functionality.

Tests the hourly usage reporting task integration with
the scheduler service.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from github_analyzer.api.services.scheduler_service import SchedulerService


class TestSchedulerUsageReporting:
    """Test scheduler service usage reporting functionality."""

    @pytest.fixture
    def scheduler_service(self):
        """Create a SchedulerService instance."""
        service = SchedulerService()
        mock_session_factory = MagicMock()
        service.set_session_factory(mock_session_factory)
        return service

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        session.commit = AsyncMock()
        return session

    def test_usage_reporting_task_registered(self, scheduler_service):
        """Test that usage reporting task is registered."""
        assert "report_usage_to_stripe" in scheduler_service.tasks
        task = scheduler_service.tasks["report_usage_to_stripe"]
        assert task.interval_seconds == 3600  # 1 hour
        assert task.enabled is True
        assert task.run_on_startup is False

    async def test_report_usage_to_stripe_success(
        self, scheduler_service, mock_session
    ):
        """Test successful usage reporting to Stripe."""
        scheduler_service._session_factory.return_value = mock_session

        with patch(
            "github_analyzer.api.services.scheduler_service.UsageReporter"
        ) as mock_reporter_class:
            mock_reporter = MagicMock()
            mock_reporter.process_hourly_usage_reporting = AsyncMock(
                return_value={
                    "success": True,
                    "records_processed": 100,
                    "records_reported": 95,
                    "records_failed": 5,
                }
            )
            mock_reporter_class.return_value = mock_reporter

            with patch(
                "github_analyzer.api.services.scheduler_service.SystemMetricOperations.record_metric"
            ) as mock_record:
                mock_record.return_value = None

                await scheduler_service._report_usage_to_stripe()

                mock_reporter.process_hourly_usage_reporting.assert_awaited_once_with(
                    mock_session
                )
                mock_record.assert_called_once()
                metric_call = mock_record.call_args[1]
                assert metric_call["metric_name"] == "stripe_usage_reporting"
                assert metric_call["metric_value"]["success"] is True
                assert metric_call["metric_value"]["records_reported"] == 95

    async def test_report_usage_to_stripe_no_session_factory(self, scheduler_service):
        """Test usage reporting when no session factory is available."""
        scheduler_service._session_factory = None

        with patch(
            "github_analyzer.api.services.scheduler_service.UsageReporter"
        ) as mock_reporter_class:
            await scheduler_service._report_usage_to_stripe()

            # Should not create reporter when no session factory
            mock_reporter_class.assert_not_called()

    async def test_report_usage_to_stripe_error_handling(
        self, scheduler_service, mock_session
    ):
        """Test error handling in usage reporting."""
        scheduler_service._session_factory.return_value = mock_session

        with patch(
            "github_analyzer.api.services.scheduler_service.UsageReporter"
        ) as mock_reporter_class:
            mock_reporter = MagicMock()
            mock_reporter.process_hourly_usage_reporting = AsyncMock(
                side_effect=Exception("Reporting error")
            )
            mock_reporter_class.return_value = mock_reporter

            with patch(
                "github_analyzer.api.services.scheduler_service.SystemMetricOperations.record_metric"
            ) as mock_record:
                mock_record.return_value = None

                await scheduler_service._report_usage_to_stripe()

                # Should record error metric
                assert mock_record.call_count == 1
                metric_call = mock_record.call_args[1]
                assert metric_call["metric_name"] == "stripe_usage_reporting_error"
                assert "Reporting error" in metric_call["metric_value"]["error"]

    async def test_report_usage_to_stripe_partial_failure(
        self, scheduler_service, mock_session
    ):
        """Test usage reporting with partial failures."""
        scheduler_service._session_factory.return_value = mock_session

        with patch(
            "github_analyzer.api.services.scheduler_service.UsageReporter"
        ) as mock_reporter_class:
            mock_reporter = MagicMock()
            mock_reporter.process_hourly_usage_reporting = AsyncMock(
                return_value={
                    "success": False,
                    "records_processed": 100,
                    "records_reported": 50,
                    "records_failed": 50,
                    "error": "Partial failure",
                }
            )
            mock_reporter_class.return_value = mock_reporter

            with patch(
                "github_analyzer.api.services.scheduler_service.SystemMetricOperations.record_metric"
            ) as mock_record:
                mock_record.return_value = None

                await scheduler_service._report_usage_to_stripe()

                # Should still record metrics even with partial failure
                mock_record.assert_called_once()
                metric_call = mock_record.call_args[1]
                assert metric_call["metric_name"] == "stripe_usage_reporting"
                assert metric_call["metric_value"]["success"] is False
                assert metric_call["metric_value"]["records_failed"] == 50

    async def test_manual_run_usage_reporting(self, scheduler_service, mock_session):
        """Test manually running the usage reporting task."""
        scheduler_service._session_factory.return_value = mock_session

        with patch(
            "github_analyzer.api.services.scheduler_service.UsageReporter"
        ) as mock_reporter_class:
            mock_reporter = MagicMock()
            mock_reporter.process_hourly_usage_reporting = AsyncMock(
                return_value={
                    "success": True,
                    "records_processed": 50,
                    "records_reported": 50,
                    "records_failed": 0,
                }
            )
            mock_reporter_class.return_value = mock_reporter

            with patch(
                "github_analyzer.api.services.scheduler_service.SystemMetricOperations.record_metric"
            ) as mock_record:
                mock_record.return_value = None

                result = await scheduler_service.run_task_manually(
                    "report_usage_to_stripe"
                )

                assert result["task_name"] == "report_usage_to_stripe"
                assert result["run_count"] == 1
                assert result["error_count"] == 0
                mock_reporter.process_hourly_usage_reporting.assert_awaited_once()

    def test_task_status_includes_usage_reporting(self, scheduler_service):
        """Test that task status includes usage reporting task."""
        status = scheduler_service.get_task_status()

        usage_task = next(
            (t for t in status if t["name"] == "report_usage_to_stripe"), None
        )
        assert usage_task is not None
        assert usage_task["enabled"] is True
        assert usage_task["interval_seconds"] == 3600

    async def test_scheduler_lifecycle_with_usage_reporting(
        self, scheduler_service, mock_session
    ):
        """Test scheduler lifecycle including usage reporting task."""
        scheduler_service._session_factory.return_value = mock_session

        # Patch the _run_startup_tasks to avoid actual task execution
        with patch.object(
            scheduler_service, "_run_startup_tasks", new_callable=AsyncMock
        ):
            # Start scheduler
            await scheduler_service.start()
            assert scheduler_service.running is True

            # Verify task is registered
            assert "report_usage_to_stripe" in scheduler_service.tasks
            task = scheduler_service.tasks["report_usage_to_stripe"]
            assert task.enabled is True

            # Stop scheduler
            await scheduler_service.stop()
            assert scheduler_service.running is False

    @pytest.mark.asyncio
    async def test_concurrent_task_execution(self, scheduler_service, mock_session):
        """Test that usage reporting doesn't block other tasks."""
        scheduler_service._session_factory.return_value = mock_session

        # Mock a slow usage reporter
        with patch(
            "github_analyzer.api.services.scheduler_service.UsageReporter"
        ) as mock_reporter_class:
            mock_reporter = MagicMock()

            async def slow_report(session):
                await asyncio.sleep(0.1)
                return {"success": True, "records_reported": 10, "records_failed": 0}

            mock_reporter.process_hourly_usage_reporting = slow_report
            mock_reporter_class.return_value = mock_reporter

            with patch(
                "github_analyzer.api.services.scheduler_service.SystemMetricOperations.record_metric"
            ) as mock_record:
                mock_record.return_value = None

                # Mock _reset_monthly_quotas to avoid database dependencies
                with patch.object(
                    scheduler_service, "_reset_monthly_quotas", new_callable=AsyncMock
                ):
                    # Run multiple tasks concurrently
                    tasks = [
                        scheduler_service._report_usage_to_stripe(),
                        scheduler_service._reset_monthly_quotas(),
                    ]

                    # Should complete without blocking
                    await asyncio.gather(*tasks)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
