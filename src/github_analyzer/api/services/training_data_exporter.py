# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Training data export service for AI model training.

This module provides functionality to export anonymized analysis data
for training AI models while respecting user consent and privacy.
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import AnalysisResult, SubscriptionPlan, User
from ...utils.logging import get_logger
from .consent_service import ConsentService

logger = get_logger(__name__)


class TrainingDataExporter:
    """Export anonymized analysis data for AI training."""

    @staticmethod
    def anonymize_user_id(user_id: str) -> str:
        """
        Create a stable anonymized ID from user ID.

        Uses SHA-256 to create consistent anonymous IDs that cannot
        be reversed to get the original user ID.
        """
        return hashlib.sha256(user_id.encode()).hexdigest()[:16]

    @staticmethod
    def sanitize_repository_url(url: str) -> str:
        """
        Remove potentially identifying information from repository URLs.

        Keeps only the repository structure, not the owner.
        """
        parts = url.rstrip("/").split("/")
        if len(parts) >= 2:
            # Return generic owner with real repo name
            repo_name = parts[-1]
            return f"https://github.com/anonymous/{repo_name}"
        return "https://github.com/anonymous/repository"

    @staticmethod
    def extract_training_features(analysis: AnalysisResult) -> Optional[Dict[str, Any]]:
        """
        Extract features suitable for training from analysis result.

        Returns None if the analysis is not suitable for training.
        """
        # Skip if no evidence patterns (legacy analysis)
        if not analysis.evidence_patterns:
            return None

        # Skip if analysis method is not evidence-based
        if analysis.analysis_method != "evidence_based":
            return None

        try:
            # Parse stored JSON data
            evidence_patterns = json.loads(analysis.evidence_patterns)
            screening_insights = (
                json.loads(analysis.screening_insights)
                if analysis.screening_insights
                else {}
            )

            # Extract training-relevant features
            features = {
                "analysis_id": analysis.id,
                "anonymized_user": TrainingDataExporter.anonymize_user_id(
                    analysis.user_id
                ),
                "repository_type": analysis.repository_name.split("/")[-1],
                "context": analysis.context,
                "analysis_date": analysis.created_at.isoformat(),
                "evidence_patterns": evidence_patterns,
                "screening_insights": {
                    "overall_impression": screening_insights.get(
                        "overall_impression", ""
                    ),
                    "key_strengths": screening_insights.get("key_strengths", []),
                    "areas_to_explore": screening_insights.get("areas_to_explore", []),
                    "confidence_explanation": screening_insights.get(
                        "confidence_explanation", ""
                    ),
                },
                "evidence_version": analysis.evidence_version,
            }

            # Add other evidence fields if available
            if analysis.technical_patterns:
                features["technical_patterns"] = json.loads(analysis.technical_patterns)
            if analysis.collaboration_patterns:
                features["collaboration_patterns"] = json.loads(
                    analysis.collaboration_patterns
                )
            if analysis.quality_indicators:
                features["quality_indicators"] = json.loads(analysis.quality_indicators)
            if analysis.temporal_insights:
                features["temporal_insights"] = json.loads(analysis.temporal_insights)
            if analysis.context_alignment:
                features["context_alignment"] = json.loads(analysis.context_alignment)
            if analysis.verification_gaps:
                features["verification_gaps"] = json.loads(analysis.verification_gaps)

            return features

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(
                f"Failed to extract features from analysis {analysis.id}: {e}"
            )
            return None

    @staticmethod
    async def export_training_data(
        db: AsyncSession,
        days_back: int = 30,
        min_analyses_per_user: int = 5,
        tier_filter: Optional[List[SubscriptionPlan]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Export anonymized training data from recent analyses.

        Args:
            db: Database session
            days_back: How many days of data to export
            min_analyses_per_user: Minimum analyses per user to include
            tier_filter: Optional list of tiers to include

        Returns:
            List of anonymized training examples
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)

        # Build query for eligible analyses
        query = (
            select(AnalysisResult)
            .where(
                and_(
                    AnalysisResult.created_at >= cutoff_date,
                    AnalysisResult.training_eligible.is_(True),
                    AnalysisResult.analysis_method == "evidence_based",
                    AnalysisResult.deleted_at.is_(None),
                )
            )
            .order_by(AnalysisResult.created_at.desc())
        )

        result = await db.execute(query)
        analyses = result.scalars().all()

        # Group by user to check minimum analyses
        user_analyses: Dict[str, List[AnalysisResult]] = {}
        for analysis in analyses:
            if analysis.user_id not in user_analyses:
                user_analyses[analysis.user_id] = []
            user_analyses[analysis.user_id].append(analysis)

        # Filter users with enough analyses
        training_data = []
        included_users = 0

        for user_id, user_analyses_list in user_analyses.items():
            if len(user_analyses_list) < min_analyses_per_user:
                continue

            # Check if user's tier is in filter (if specified)
            if tier_filter:
                # Get user to check tier
                user_result = await db.execute(
                    select(User).where(User.user_id == user_id)
                )
                user = user_result.scalar_one_or_none()
                if not user or user.subscription_plan not in tier_filter:
                    continue

            included_users += 1

            # Extract features from each analysis
            for analysis in user_analyses_list:
                features = TrainingDataExporter.extract_training_features(analysis)
                if features:
                    training_data.append(features)

        logger.info(
            f"Exported {len(training_data)} training examples from "
            f"{included_users} users (last {days_back} days)"
        )

        return training_data

    @staticmethod
    async def export_diversity_metrics(
        training_data: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Calculate diversity metrics for the training data.

        Helps ensure balanced training sets.
        """
        if not training_data:
            return {
                "total_examples": 0,
                "unique_users": 0,
                "context_distribution": {},
                "repository_types": {},
                "date_range": None,
            }

        # Calculate metrics
        unique_users = set()
        contexts: Dict[str, int] = {}
        repo_types: Dict[str, int] = {}
        dates = []

        for example in training_data:
            unique_users.add(example["anonymized_user"])

            context = example["context"]
            contexts[context] = contexts.get(context, 0) + 1

            repo_type = example["repository_type"]
            repo_types[repo_type] = repo_types.get(repo_type, 0) + 1

            dates.append(example["analysis_date"])

        # Sort dates to get range
        dates.sort()

        return {
            "total_examples": len(training_data),
            "unique_users": len(unique_users),
            "context_distribution": contexts,
            "repository_types": dict(
                sorted(repo_types.items(), key=lambda x: x[1], reverse=True)[:20]
            ),  # Top 20 types
            "date_range": {
                "earliest": dates[0] if dates else None,
                "latest": dates[-1] if dates else None,
            },
            "examples_per_user": (
                len(training_data) / len(unique_users) if unique_users else 0
            ),
        }

    @staticmethod
    async def validate_consent_compliance(
        db: AsyncSession, training_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate that all exported data complies with consent.

        Double-checks that only consented data is included.
        """
        analysis_ids = [ex["analysis_id"] for ex in training_data]

        # Query analyses to verify consent
        query = select(AnalysisResult).where(AnalysisResult.id.in_(analysis_ids))
        result = await db.execute(query)
        analyses = result.scalars().all()

        compliant_count = 0
        non_compliant_ids = []

        for analysis in analyses:
            # Parse stored consent
            if analysis.data_consent:
                consent = json.loads(analysis.data_consent)
                if ConsentService.should_allow_training(consent):
                    compliant_count += 1
                else:
                    non_compliant_ids.append(analysis.id)
            else:
                non_compliant_ids.append(analysis.id)

        return {
            "total_checked": len(analyses),
            "compliant": compliant_count,
            "non_compliant": len(non_compliant_ids),
            "non_compliant_ids": non_compliant_ids,
            "compliance_rate": (compliant_count / len(analyses) if analyses else 0),
        }

    @staticmethod
    def prepare_for_export(
        training_data: List[Dict[str, Any]], format: str = "jsonl"
    ) -> str:
        """
        Prepare training data for export in specified format.

        Args:
            training_data: List of training examples
            format: Export format (jsonl, json)

        Returns:
            Formatted string ready for file export
        """
        if format == "jsonl":
            # One JSON object per line (common for ML training)
            lines = [json.dumps(example, sort_keys=True) for example in training_data]
            return "\n".join(lines)
        elif format == "json":
            # Single JSON array
            return json.dumps(training_data, indent=2, sort_keys=True)
        else:
            raise ValueError(f"Unsupported format: {format}")
