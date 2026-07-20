# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Async batch history service for tracking and retrieving batch analysis history.
Provides comprehensive batch tracking for Scale and Scale+ tiers with async database operations.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from github_analyzer.database.models import AnalysisStatus, BatchAnalysis

logger = logging.getLogger(__name__)


class AsyncBatchHistoryService:
    """Async service for managing batch analysis history."""

    def __init__(self, db_session: AsyncSession) -> None:
        """Initialize the service with an async database session."""
        self.db = db_session
        self.logger = logger

    async def create_batch_record(
        self,
        user_id: str,
        repository_count: int,
        contexts: List[str],
        concurrency_mode: str = "sequential",
    ) -> str:
        """
        Create a new batch analysis record.

        Args:
            user_id: ID of the user starting the batch
            repository_count: Number of repositories in the batch
            contexts: List of analysis contexts (e.g., ["startup", "enterprise"])
            concurrency_mode: Concurrency mode (sequential, balanced, fast)

        Returns:
            Batch ID for tracking
        """
        batch_id = str(uuid.uuid4())

        batch_record = BatchAnalysis(
            batch_id=batch_id,
            user_id=user_id,
            repository_count=repository_count,
            contexts=json.dumps(contexts),
            status=AnalysisStatus.PENDING,
            concurrency_mode=concurrency_mode,
            created_at=datetime.now(timezone.utc),
        )

        self.db.add(batch_record)
        await self.db.commit()

        self.logger.info(
            f"Created batch record {batch_id} for user {user_id} "
            f"with {repository_count} repositories in {concurrency_mode} mode"
        )

        return batch_id

    async def start_batch_processing(self, batch_id: str) -> None:
        """
        Mark batch as processing started.

        Args:
            batch_id: ID of the batch to update
        """
        result = await self.db.execute(
            select(BatchAnalysis).filter_by(batch_id=batch_id)
        )
        batch = result.scalar_one_or_none()

        if not batch:
            raise ValueError(f"Batch {batch_id} not found")

        batch.status = AnalysisStatus.PROCESSING
        await self.db.commit()

        self.logger.info(f"Started processing batch {batch_id}")

    async def update_batch_progress(
        self,
        batch_id: str,
        successful_count: int,
        failed_count: int,
        current_cost: Optional[float] = None,
        error_messages: Optional[List[str]] = None,
    ) -> None:
        """
        Update batch processing progress.

        Args:
            batch_id: ID of the batch to update
            successful_count: Number of successful analyses
            failed_count: Number of failed analyses
            current_cost: Current total cost (optional)
            error_messages: List of error messages (optional)
        """
        result = await self.db.execute(
            select(BatchAnalysis).filter_by(batch_id=batch_id)
        )
        batch = result.scalar_one_or_none()

        if not batch:
            raise ValueError(f"Batch {batch_id} not found")

        batch.successful_count = successful_count
        batch.failed_count = failed_count

        if current_cost is not None:
            batch.total_cost = current_cost

        if error_messages:
            batch.error_messages = json.dumps(error_messages)

        await self.db.commit()

        self.logger.debug(
            f"Updated batch {batch_id} progress: {successful_count} success, "
            f"{failed_count} failed"
        )

    async def complete_batch(
        self,
        batch_id: str,
        successful_count: int,
        failed_count: int,
        total_cost: float,
        processing_time_ms: int,
        error_messages: Optional[List[str]] = None,
    ) -> None:
        """
        Mark batch as completed and update final statistics.

        Args:
            batch_id: ID of the batch to complete
            successful_count: Final number of successful analyses
            failed_count: Final number of failed analyses
            total_cost: Total cost incurred
            processing_time_ms: Total processing time in milliseconds
            error_messages: List of error messages (optional)
        """
        result = await self.db.execute(
            select(BatchAnalysis).filter_by(batch_id=batch_id)
        )
        batch = result.scalar_one_or_none()

        if not batch:
            raise ValueError(f"Batch {batch_id} not found")

        batch.status = AnalysisStatus.COMPLETED
        batch.successful_count = successful_count
        batch.failed_count = failed_count
        batch.total_cost = total_cost
        batch.processing_time_ms = processing_time_ms
        batch.completed_at = datetime.now(timezone.utc)

        if error_messages:
            batch.error_messages = json.dumps(error_messages)

        await self.db.commit()

        self.logger.info(
            f"Completed batch {batch_id}: {successful_count} success, "
            f"{failed_count} failed, cost ${total_cost:.4f}, "
            f"time {processing_time_ms}ms"
        )

    async def fail_batch(
        self,
        batch_id: str,
        error_message: str,
        processing_time_ms: Optional[int] = None,
    ) -> None:
        """
        Mark batch as failed with error information.

        Args:
            batch_id: ID of the batch that failed
            error_message: Error message describing the failure
            processing_time_ms: Processing time before failure (optional)
        """
        result = await self.db.execute(
            select(BatchAnalysis).filter_by(batch_id=batch_id)
        )
        batch = result.scalar_one_or_none()

        if not batch:
            raise ValueError(f"Batch {batch_id} not found")

        batch.status = AnalysisStatus.FAILED
        batch.error_messages = json.dumps([error_message])
        batch.completed_at = datetime.now(timezone.utc)

        if processing_time_ms is not None:
            batch.processing_time_ms = processing_time_ms

        await self.db.commit()

        self.logger.error(f"Failed batch {batch_id}: {error_message}")

    async def get_batch_history(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        status_filter: Optional[str] = None,
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Get batch history for a user with total count.

        Args:
            user_id: ID of the user
            limit: Maximum number of records to return
            offset: Number of records to skip
            status_filter: Filter by status (optional)

        Returns:
            Tuple of (list of batch history records, total count)
        """
        # Build base query for counting
        base_query = select(BatchAnalysis).filter(BatchAnalysis.user_id == user_id)

        if status_filter:
            # Convert string status to enum
            status_enum = AnalysisStatus(status_filter)
            base_query = base_query.filter(BatchAnalysis.status == status_enum)

        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await self.db.execute(count_query)
        total_count = count_result.scalar() or 0

        # Get paginated results
        query = (
            base_query.order_by(desc(BatchAnalysis.created_at))
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(query)
        batches = result.scalars().all()

        return [self._batch_to_dict(batch) for batch in batches], total_count

    async def get_batch_details(
        self, batch_id: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific batch.

        Args:
            batch_id: ID of the batch
            user_id: ID of the user (for security)

        Returns:
            Batch details or None if not found
        """
        # Import AnalysisResult model
        from github_analyzer.database.models import AnalysisResult

        result = await self.db.execute(
            select(BatchAnalysis).filter(
                and_(
                    BatchAnalysis.batch_id == batch_id,
                    BatchAnalysis.user_id == user_id,
                )
            )
        )
        batch = result.scalar_one_or_none()

        if not batch:
            return None

        batch_dict = self._batch_to_dict(batch, include_details=True)

        # Fetch individual analyses that belong to this batch
        analyses_result = await self.db.execute(
            select(AnalysisResult)
            .filter(AnalysisResult.batch_id == batch_id)
            .order_by(AnalysisResult.created_at)
        )
        analyses = analyses_result.scalars().all()

        # Format the results for frontend consumption
        results = []
        for analysis in analyses:
            # Parse the full_analysis JSON
            full_analysis = None
            try:
                full_analysis = (
                    json.loads(analysis.full_analysis)
                    if analysis.full_analysis
                    else None
                )
            except (json.JSONDecodeError, TypeError):
                full_analysis = None

            repo_result = {
                "analysis_id": analysis.id,  # Field is 'id' not 'analysis_id'
                "repository_url": analysis.repository_url,
                "repository_name": analysis.repository_name,
                "context": analysis.context,
                "status": "completed" if full_analysis else "failed",
                "analysis": full_analysis.get("analysis") if full_analysis else None,
                "error": None if full_analysis else "Analysis failed or incomplete",
                "created_at": (
                    analysis.created_at.isoformat() if analysis.created_at else None
                ),
            }
            results.append(repo_result)

        # Add results to the batch dict
        batch_dict["results"] = results

        return batch_dict

    async def get_batch_statistics(
        self, user_id: str, days: int = 30
    ) -> Dict[str, Any]:
        """
        Get batch processing statistics for a user.

        Args:
            user_id: ID of the user
            days: Number of days to look back

        Returns:
            Statistics summary
        """
        from datetime import timedelta

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Get basic statistics
        stats_result = await self.db.execute(
            select(
                func.count(BatchAnalysis.batch_id).label("total_batches"),
                func.sum(BatchAnalysis.repository_count).label("total_repositories"),
                func.sum(BatchAnalysis.successful_count).label("total_successful"),
                func.sum(BatchAnalysis.failed_count).label("total_failed"),
                func.sum(BatchAnalysis.total_cost).label("total_cost"),
                func.avg(BatchAnalysis.processing_time_ms).label("avg_processing_time"),
            ).filter(
                and_(
                    BatchAnalysis.user_id == user_id,
                    BatchAnalysis.created_at >= cutoff_date,
                )
            )
        )
        stats_query = stats_result.one()

        # Get status breakdown
        status_result = await self.db.execute(
            select(
                BatchAnalysis.status,
                func.count(BatchAnalysis.batch_id).label("count"),
            )
            .filter(
                and_(
                    BatchAnalysis.user_id == user_id,
                    BatchAnalysis.created_at >= cutoff_date,
                )
            )
            .group_by(BatchAnalysis.status)
        )
        status_breakdown = status_result.all()

        return {
            "period_days": days,
            "total_batches": stats_query.total_batches or 0,
            "total_repositories": stats_query.total_repositories or 0,
            "total_successful": stats_query.total_successful or 0,
            "total_failed": stats_query.total_failed or 0,
            "total_cost": float(stats_query.total_cost or 0),
            "avg_processing_time_ms": int(stats_query.avg_processing_time or 0),
            "success_rate": (
                (stats_query.total_successful or 0)
                / max(stats_query.total_repositories or 1, 1)
                * 100
            ),
            "status_breakdown": {
                status.value: count for status, count in status_breakdown
            },
        }

    async def get_recent_batches(
        self, user_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent batch analyses for quick overview.

        Args:
            user_id: ID of the user
            limit: Number of recent batches to return

        Returns:
            List of recent batch summaries
        """
        result = await self.db.execute(
            select(BatchAnalysis)
            .filter(BatchAnalysis.user_id == user_id)
            .order_by(desc(BatchAnalysis.created_at))
            .limit(limit)
        )
        batches = result.scalars().all()

        return [
            {
                "batch_id": batch.batch_id,
                "repository_count": batch.repository_count,
                "status": batch.status,
                "successful_count": batch.successful_count,
                "failed_count": batch.failed_count,
                "total_cost": batch.total_cost,
                "created_at": batch.created_at.isoformat(),
                "completed_at": (
                    batch.completed_at.isoformat() if batch.completed_at else None
                ),
            }
            for batch in batches
        ]

    def _batch_to_dict(
        self, batch: BatchAnalysis, include_details: bool = False
    ) -> Dict[str, Any]:
        """
        Convert BatchAnalysis object to dictionary.

        Args:
            batch: BatchAnalysis object
            include_details: Whether to include detailed information

        Returns:
            Dictionary representation
        """
        # Parse contexts to get the primary context
        contexts: List[str] = []
        try:
            contexts = json.loads(batch.contexts) if batch.contexts else []
        except (json.JSONDecodeError, TypeError):
            contexts = []

        # Get the first context or default to "enterprise"
        primary_context = contexts[0] if contexts else "enterprise"

        result = {
            "batch_id": batch.batch_id,
            "user_id": batch.user_id,
            "total_repositories": batch.repository_count,  # Frontend expects this name
            "completed_count": batch.successful_count,  # Frontend expects this name
            "failed_count": batch.failed_count,
            "status": batch.status,
            "context": primary_context,  # Frontend expects single context
            "concurrency_mode": getattr(
                batch, "concurrency_mode", "sequential"
            ),  # Include concurrency mode
            "total_cost": batch.total_cost,
            "processing_time_ms": batch.processing_time_ms,
            "created_at": batch.created_at.isoformat(),
            "updated_at": (  # Frontend expects updated_at
                batch.completed_at.isoformat()
                if batch.completed_at
                else batch.created_at.isoformat()
            ),
        }

        if include_details:
            # Parse error messages
            error_messages: List[str] = []
            try:
                error_messages = (
                    json.loads(batch.error_messages) if batch.error_messages else []
                )
            except (json.JSONDecodeError, TypeError):
                error_messages = []

            result.update(
                {
                    "contexts": contexts,
                    "error_messages": error_messages,
                    "success_rate": (
                        batch.successful_count / max(batch.repository_count, 1) * 100
                    ),
                    "duration_seconds": (
                        (batch.processing_time_ms or 0) / 1000
                        if batch.processing_time_ms
                        else None
                    ),
                }
            )

        return result

    async def get_batch_aggregated_insights(
        self, batch_id: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Generate aggregated insights across all repositories in a batch.

        This provides cross-repository pattern detection, technology distribution,
        and common strengths/weaknesses analysis.

        Args:
            batch_id: ID of the batch to analyze
            user_id: ID of the user (for security)

        Returns:
            Aggregated insights or None if batch not found
        """
        # Get the batch details first
        batch_details = await self.get_batch_details(batch_id, user_id)
        if not batch_details or not batch_details.get("results"):
            return None

        results = batch_details["results"]
        completed_analyses = [
            r for r in results if r.get("status") == "completed" and r.get("analysis")
        ]

        if not completed_analyses:
            return {
                "batch_id": batch_id,
                "total_repositories": len(results),
                "analyzed_repositories": 0,
                "message": "No completed analyses to aggregate",
            }

        # Initialize aggregation structures with proper types
        aggregated: Dict[str, Any] = {
            "batch_id": batch_id,
            "total_repositories": len(results),
            "analyzed_repositories": len(completed_analyses),
            "common_patterns": {},
            "technology_distribution": {},
            "skill_indicators": {},
            "quality_indicators": {
                "repositories_with_tests": [],
                "repositories_with_ci_cd": [],
                "repositories_with_documentation": [],
                "actively_maintained_repositories": [],
            },
            "top_strengths": [],
            "common_challenges": [],
            "repository_comparison": [],
        }
        # Cast nested dictionaries to proper types for mypy
        common_patterns: Dict[str, Dict[str, Any]] = aggregated["common_patterns"]
        technology_distribution: Dict[str, int] = aggregated["technology_distribution"]
        quality_indicators: Dict[str, List[str]] = aggregated["quality_indicators"]
        top_strengths: List[Dict[str, Any]] = aggregated["top_strengths"]
        common_challenges: List[Dict[str, Any]] = aggregated["common_challenges"]
        repository_comparison: List[Dict[str, Any]] = aggregated[
            "repository_comparison"
        ]

        # Process each completed analysis
        for repo_result in completed_analyses:
            analysis = repo_result["analysis"]
            repo_name = repo_result["repository_name"]

            # Extract evidence patterns
            if "evidence_patterns" in analysis:
                for pattern in analysis["evidence_patterns"]:
                    pattern_name = pattern.get("name", "unknown")
                    if pattern_name not in common_patterns:
                        common_patterns[pattern_name] = {
                            "count": 0,
                            "repositories": [],
                            "evidence_samples": [],
                        }
                    common_patterns[pattern_name]["count"] += 1
                    common_patterns[pattern_name]["repositories"].append(repo_name)
                    if pattern.get("evidence"):
                        common_patterns[pattern_name]["evidence_samples"].append(
                            pattern["evidence"][:100]  # First 100 chars as sample
                        )

            # Extract technology indicators
            if "insights" in analysis:
                for insight in analysis["insights"]:
                    # Look for technology-related insights
                    description = insight.get("description", "").lower()
                    if "typescript" in description:
                        technology_distribution["TypeScript"] = (
                            technology_distribution.get("TypeScript", 0) + 1
                        )
                    if "javascript" in description:
                        technology_distribution["JavaScript"] = (
                            technology_distribution.get("JavaScript", 0) + 1
                        )
                    if "python" in description:
                        technology_distribution["Python"] = (
                            technology_distribution.get("Python", 0) + 1
                        )
                    if "react" in description:
                        technology_distribution["React"] = (
                            technology_distribution.get("React", 0) + 1
                        )

                    # Extract quality indicators (store repos, not counts)
                    if (
                        "test" in description or "testing" in description
                    ) and repo_name not in quality_indicators[
                        "repositories_with_tests"
                    ]:
                        quality_indicators["repositories_with_tests"].append(repo_name)
                    if (
                        "ci/cd" in description or "continuous" in description
                    ) and repo_name not in quality_indicators[
                        "repositories_with_ci_cd"
                    ]:
                        quality_indicators["repositories_with_ci_cd"].append(repo_name)
                    if (
                        "documentation" in description or "readme" in description
                    ) and repo_name not in quality_indicators[
                        "repositories_with_documentation"
                    ]:
                        quality_indicators["repositories_with_documentation"].append(
                            repo_name
                        )
                    if (
                        "maintain" in description or "active" in description
                    ) and repo_name not in quality_indicators[
                        "actively_maintained_repositories"
                    ]:
                        quality_indicators["actively_maintained_repositories"].append(
                            repo_name
                        )

            # Build repository comparison entry
            comparison_entry = {
                "repository": repo_name,
                "context": repo_result.get("context"),
                "insights_count": analysis.get("insights_count", 0),
                "questions_count": analysis.get("questions_count", 0),
                "patterns_count": analysis.get("evidence_patterns_count", 0),
                "key_strengths": [],
                "key_areas": [],
            }

            # Extract strengths from recommendations
            if "recommendations" in analysis:
                for rec in analysis["recommendations"][:3]:  # Top 3 recommendations
                    if rec.get("type") == "strength":
                        comparison_entry["key_strengths"].append(rec.get("text", ""))
                        # Add to top strengths across batch
                        strength_text = rec.get("text", "")
                        if strength_text:
                            found = False
                            for strength in top_strengths:
                                if strength["text"] == strength_text:
                                    strength["count"] += 1
                                    strength["repositories"].append(repo_name)
                                    found = True
                                    break
                            if not found:
                                top_strengths.append(
                                    {
                                        "text": strength_text,
                                        "count": 1,
                                        "repositories": [repo_name],
                                    }
                                )
                    elif rec.get("type") == "area_for_exploration":
                        comparison_entry["key_areas"].append(rec.get("text", ""))
                        # Add to common challenges
                        area_text = rec.get("text", "")
                        if area_text:
                            found = False
                            for challenge in common_challenges:
                                if challenge["text"] == area_text:
                                    challenge["count"] += 1
                                    challenge["repositories"].append(repo_name)
                                    found = True
                                    break
                            if not found:
                                common_challenges.append(
                                    {
                                        "text": area_text,
                                        "count": 1,
                                        "repositories": [repo_name],
                                    }
                                )

            repository_comparison.append(comparison_entry)

        # Sort and limit results
        aggregated["common_patterns"] = dict(
            sorted(
                aggregated["common_patterns"].items(),
                key=lambda x: x[1]["count"],
                reverse=True,
            )[:10]  # Top 10 patterns
        )

        aggregated["top_strengths"] = sorted(
            aggregated["top_strengths"], key=lambda x: x["count"], reverse=True
        )[:5]  # Top 5 strengths

        aggregated["common_challenges"] = sorted(
            aggregated["common_challenges"], key=lambda x: x["count"], reverse=True
        )[:5]  # Top 5 challenges

        # Add summary of quality indicators (just lists, no percentages!)
        aggregated["quality_summary"] = {
            "testing_evidence": f"{len(quality_indicators['repositories_with_tests'])} repositories show evidence of testing practices",
            "ci_cd_evidence": f"{len(quality_indicators['repositories_with_ci_cd'])} repositories show CI/CD integration",
            "documentation_evidence": f"{len(quality_indicators['repositories_with_documentation'])} repositories have documentation",
            "maintenance_evidence": f"{len(quality_indicators['actively_maintained_repositories'])} repositories show active maintenance",
        }

        return aggregated
