# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Contact form API routes.

This module defines public endpoints for contact form submission.
Rate limiting is applied to prevent spam.
"""

from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.connection import get_db_session
from ...database.operations import ContactOperations, UserOperations
from ..auth.dependencies import get_current_user_id_optional
from ..dependencies import get_client_ip
from ..models.requests import ContactFormRequest
from ..models.responses import ContactFormSubmitResponse, ContactMessageListResponse
from ..services.priority_support_service import PrioritySupportService

# Create router
router = APIRouter(prefix="/contact", tags=["Contact"])


@router.post("", response_model=ContactFormSubmitResponse)
async def submit_contact_form(
    request: ContactFormRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    client_ip: Annotated[str, Depends(get_client_ip)],
    background_tasks: BackgroundTasks,
    current_user_id: Annotated[Optional[str], Depends(get_current_user_id_optional)],
) -> ContactFormSubmitResponse:
    """
    Submit a contact form message.

    This endpoint allows anyone to submit a contact form without authentication.
    Rate limiting is applied at the middleware level to prevent spam.

    Args:
        request: Contact form data
        db: Database session
        client_ip: Client IP address (for logging)
        background_tasks: Background task queue

    Returns:
        ContactFormSubmitResponse: Confirmation of submission

    Raises:
        HTTPException: If submission fails
    """
    try:
        # Create the contact message
        message = await ContactOperations.create_message(
            db=db,
            name=request.name,
            email=request.email,
            subject=request.subject,
            message=request.message,
            user_id=current_user_id,  # Will be None for non-authenticated users
        )

        # Enhance with priority if user is authenticated
        if current_user_id:
            user = await UserOperations.get_user_by_id(db, current_user_id)
            if user:
                priority_service = PrioritySupportService(db)
                message = await priority_service.enhance_message_with_priority(
                    message, user
                )
                await db.commit()

        # Log the submission (could be extended to send notifications)
        # For now, we'll just use the client_ip for rate limiting context
        # The actual rate limiting is handled by middleware

        # Customize response based on priority
        response_message = (
            "Thank you for contacting us. We'll respond as soon as possible."
        )
        if message.is_priority:
            if message.priority_level >= 3:  # URGENT (Scale+)
                response_message = "Thank you for contacting us. As a Scale+ customer, your message has been marked as urgent priority and will be addressed within 4 hours."
            elif message.priority_level >= 2:  # HIGH (Scale/Enterprise)
                response_message = "Thank you for contacting us. As a Scale customer, your message has been marked as high priority and will be addressed within 12 hours."
            elif message.priority_level >= 1:  # MEDIUM (Professional)
                response_message = "Thank you for contacting us. As a Professional customer, your message has been marked as priority and will be addressed within 24 hours."

        return ContactFormSubmitResponse(
            message_id=message.message_id,
            message=response_message,
            timestamp=datetime.now(timezone.utc),
        )

    except Exception as e:
        # Log the error (in production, you'd use proper logging)
        raise HTTPException(
            status_code=500,
            detail="Failed to submit contact form. Please try again later.",
        ) from e


@router.get("/my-messages", response_model=ContactMessageListResponse)
async def get_my_messages(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user_id: Annotated[str, Depends(get_current_user_id_optional)],
    page: int = 1,
    page_size: int = 20,
) -> ContactMessageListResponse:
    """
    Get paginated list of contact messages for the authenticated user.

    Args:
        db: Database session
        current_user_id: Authenticated user ID
        page: Page number
        page_size: Number of items per page

    Returns:
        ContactMessageListResponse: Paginated list of user's messages

    Raises:
        HTTPException: If user is not authenticated
    """
    if not current_user_id:
        raise HTTPException(
            status_code=401, detail="Authentication required to view your messages"
        )

    # Calculate pagination
    offset = (page - 1) * page_size

    # Get messages from database
    messages, total = await ContactOperations.get_messages_by_user_id(
        db, current_user_id, limit=page_size, offset=offset
    )

    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    # Import here to avoid circular import
    from ...database.models import ContactStatus
    from ..models.responses import ContactMessageResponse

    return ContactMessageListResponse(
        messages=[
            ContactMessageResponse(
                message_id=msg.message_id,
                name=msg.name,
                email=msg.email,
                subject=msg.subject,
                message=msg.message,
                status=(
                    ContactStatus(msg.status)
                    if isinstance(msg.status, str)
                    else msg.status
                ),
                created_at=msg.created_at,
                admin_response=msg.admin_response,
                responded_at=msg.responded_at,
                responded_by=msg.responded_by,
            )
            for msg in messages
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
