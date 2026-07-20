# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Training data export routes for AI model preparation.

This module provides admin-only endpoints for exporting anonymized
analysis data for training AI models.
"""

from typing import Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.connection import get_db_session
from ...database.models import SubscriptionPlan, User
from ...utils.logging import get_logger
from ..auth.dependencies import get_current_active_user
from ..services.training_data_exporter import TrainingDataExporter

logger = get_logger(__name__)
router = APIRouter(prefix="/training-data", tags=["Training Data"])


class TrainingDataExportRequest(BaseModel):
    """Request model for training data export."""

    days_back: int = 30
    min_analyses_per_user: int = 5
    tier_filter: Optional[List[str]] = None
    format: str = "jsonl"


class TrainingDataMetrics(BaseModel):
    """Response model for training data metrics."""

    total_examples: int
    unique_users: int
    context_distribution: Dict[str, int]
    repository_types: Dict[str, int]
    date_range: Dict[str, Optional[str]]
    examples_per_user: float
    consent_compliance: Dict[str, Union[float, int]]


@router.post("/export", response_model=Dict[str, Union[str, int]])
async def export_training_data(
    request: TrainingDataExportRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Union[str, int]]:
    """
    Export anonymized training data for AI model training (Admin only).

    Exports analysis data from users who have consented to training usage.
    All data is anonymized before export.
    """
    # Admin only
    if user.user_role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Training data export requires admin privileges",
        )

    try:
        # Convert tier filter strings to enums
        tier_filter = None
        if request.tier_filter:
            tier_filter = [SubscriptionPlan(tier) for tier in request.tier_filter]

        # Export training data
        training_data = await TrainingDataExporter.export_training_data(
            db,
            days_back=request.days_back,
            min_analyses_per_user=request.min_analyses_per_user,
            tier_filter=tier_filter,
        )

        if not training_data:
            return {
                "message": "No training data available with current filters",
                "examples_exported": 0,
            }

        # Validate consent compliance
        compliance = await TrainingDataExporter.validate_consent_compliance(
            db, training_data
        )

        if compliance["non_compliant"] > 0:
            logger.warning(
                f"Found {compliance['non_compliant']} non-compliant records "
                f"during export"
            )
            # Filter out non-compliant records
            training_data = [
                ex
                for ex in training_data
                if ex["analysis_id"] not in compliance["non_compliant_ids"]
            ]

        # Prepare for export
        export_content = TrainingDataExporter.prepare_for_export(
            training_data, format=request.format
        )

        # Log export event
        logger.info(
            f"Admin {user.user_id} exported {len(training_data)} training examples"
        )

        # For now, return the export as a response
        # In production, this would save to S3 or similar
        return {
            "message": "Training data exported successfully",
            "examples_exported": len(training_data),
            "format": request.format,
            "export_size_bytes": len(export_content.encode()),
            "compliance_rate": compliance["compliance_rate"],
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to export training data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export training data",
        )


@router.get("/metrics", response_model=TrainingDataMetrics)
async def get_training_data_metrics(
    days_back: int = Query(30, ge=1, le=365),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> TrainingDataMetrics:
    """
    Get metrics about available training data (Admin only).

    Provides insights into the diversity and volume of training data.
    """
    # Admin only
    if user.user_role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Training data metrics require admin privileges",
        )

    try:
        # Export data to calculate metrics
        training_data = await TrainingDataExporter.export_training_data(
            db, days_back=days_back, min_analyses_per_user=1
        )

        # Calculate diversity metrics
        metrics = await TrainingDataExporter.export_diversity_metrics(training_data)

        # Validate consent compliance
        compliance = await TrainingDataExporter.validate_consent_compliance(
            db, training_data
        )

        return TrainingDataMetrics(
            total_examples=metrics["total_examples"],
            unique_users=metrics["unique_users"],
            context_distribution=metrics["context_distribution"],
            repository_types=metrics["repository_types"],
            date_range=metrics["date_range"],
            examples_per_user=metrics["examples_per_user"],
            consent_compliance={
                "compliant_examples": compliance["compliant"],
                "compliance_rate": compliance["compliance_rate"],
            },
        )

    except Exception as e:
        logger.error(f"Failed to get training data metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve training data metrics",
        )


@router.get("/download/{export_id}")
async def download_training_data(
    export_id: str,
    user: User = Depends(get_current_active_user),
) -> Response:
    """
    Download previously exported training data (Admin only).

    In production, this would retrieve from S3 or similar storage.
    """
    # Admin only
    if user.user_role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Training data download requires admin privileges",
        )

    # TODO: In production, retrieve from S3 using export_id
    # For now, return a placeholder
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Training data download not yet implemented",
    )
