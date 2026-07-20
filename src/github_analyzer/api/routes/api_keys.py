# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
API key management endpoints.

Provides secure endpoints for creating, managing, and monitoring API keys
with proper authentication, authorization, and audit logging.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.connection import get_db_session
from ...database.models import APIKey
from ..auth.dependencies import (
    get_current_user_id,
    require_admin,
)
from ..models.responses import APIKeyListResponse, APIKeyResponse, APIKeyUsageResponse
from ..services.api_key_service import APIKeyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/keys", tags=["API Keys"])


@router.post("/", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: Request,
    name: str,
    permissions: List[str] = Query(
        ...,
        description="List of permissions to grant to this key. Allowed values: 'analyze', 'batch', 'admin'.",
    ),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> APIKeyResponse:
    """
    Create a new API key for the authenticated user.

    Args:
        name: Descriptive name for the API key
        permissions: List of permissions to grant to this key
        user_id: Authenticated user ID
        db: Database session
        request: HTTP request object for audit logging

    Returns:
        APIKeyResponse: Created API key details (plain key shown only once)

    Raises:
        HTTPException: If user not found or invalid permissions

    Security:
        - Requires valid JWT authentication
        - Validates permissions against allowed values
        - Logs API key creation for audit trail
        - Plain text API key returned only once
    """
    # Validate permissions against allowed values
    allowed_permissions = {"analyze", "batch", "admin"}
    invalid_permissions = set(permissions) - allowed_permissions
    if invalid_permissions:
        logger.warning(
            f"User {user_id} attempted to create API key with invalid permissions: {invalid_permissions}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid permissions: {', '.join(invalid_permissions)}. "
            f"Allowed: {', '.join(allowed_permissions)}",
        )

    # Validate name length and content
    if not name or len(name.strip()) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key name must be at least 3 characters long",
        )

    if len(name) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key name must be less than 100 characters",
        )

    try:
        service = APIKeyService(db)
        api_key_record, plain_key = await service.create_api_key(
            user_id=user_id,
            name=name.strip(),
            permissions=permissions,
        )

        # Log successful API key creation for audit
        client_ip = "unknown"
        if (
            hasattr(request, "client")
            and request.client
            and hasattr(request.client, "host")
        ):
            client_ip = request.client.host
        logger.info(
            f"API key created successfully: user_id={user_id}, key_id={api_key_record.key_id}, "
            f"name='{name}', permissions={permissions}, client_ip={client_ip}"
        )

        import json

        stored_permissions = json.loads(api_key_record.permissions)

        return APIKeyResponse(
            key_id=api_key_record.key_id,
            name=api_key_record.name,
            api_key=plain_key,  # Only shown once
            permissions=stored_permissions,
            monthly_quota=api_key_record.monthly_quota,
            monthly_usage=api_key_record.monthly_usage,
            is_active=api_key_record.is_active,
            created_at=api_key_record.created_at,
            last_used=api_key_record.last_used,
            expires_at=api_key_record.expires_at,
            user_id=None,
        )

    except ValueError as e:
        logger.error(f"Failed to create API key for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    except Exception as e:
        logger.error(f"Unexpected error creating API key for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key",
        )


@router.get("/", response_model=APIKeyListResponse)
async def list_api_keys(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> APIKeyListResponse:
    """
    List all API keys for the authenticated user.

    Args:
        user_id: Authenticated user ID
        db: Database session

    Returns:
        APIKeyListResponse: List of user's API keys (without plain text keys)

    Security:
        - Requires valid JWT authentication
        - Only returns keys belonging to authenticated user
        - Never exposes plain text API keys
    """
    try:
        service = APIKeyService(db)
        api_keys = await service.get_user_api_keys(user_id)

        import json

        keys_data = [
            APIKeyResponse(
                key_id=key.key_id,
                name=key.name,
                api_key=None,  # Never expose plain text keys in list
                permissions=json.loads(key.permissions),
                monthly_quota=key.monthly_quota,
                monthly_usage=key.monthly_usage,
                is_active=key.is_active,
                created_at=key.created_at,
                last_used=key.last_used,
                expires_at=key.expires_at,
                user_id=None,
            )
            for key in api_keys
        ]

        logger.debug(f"Listed {len(keys_data)} API keys for user {user_id}")

        return APIKeyListResponse(keys=keys_data, total_count=len(keys_data))

    except Exception as e:
        logger.error(f"Failed to list API keys for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve API keys",
        )


@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> APIKeyResponse:
    """
    Get details of a specific API key.

    Args:
        key_id: API key ID to retrieve
        user_id: Authenticated user ID
        db: Database session

    Returns:
        APIKeyResponse: API key details (without plain text key)

    Raises:
        HTTPException: If key not found or access denied

    Security:
        - Requires valid JWT authentication
        - Verifies key ownership before returning details
        - Never exposes plain text API key
    """
    try:
        service = APIKeyService(db)
        api_key_record = await service.get_api_key_by_id(key_id)

        if not api_key_record:
            logger.warning(
                f"User {user_id} attempted to access non-existent API key {key_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
            )

        # Verify ownership
        if api_key_record.user_id != user_id:
            logger.warning(
                f"User {user_id} attempted to access API key {key_id} owned by {api_key_record.user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )

        import json

        permissions = json.loads(api_key_record.permissions)

        return APIKeyResponse(
            key_id=api_key_record.key_id,
            name=api_key_record.name,
            api_key=None,  # Never expose plain text key
            permissions=permissions,
            monthly_quota=api_key_record.monthly_quota,
            monthly_usage=api_key_record.monthly_usage,
            is_active=api_key_record.is_active,
            created_at=api_key_record.created_at,
            last_used=api_key_record.last_used,
            expires_at=api_key_record.expires_at,
            user_id=None,
        )

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Failed to get API key {key_id} for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve API key",
        )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    request: Request,
    key_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """
    Revoke (deactivate) an API key.

    Args:
        key_id: API key ID to revoke
        user_id: Authenticated user ID
        db: Database session
        request: HTTP request object for audit logging

    Raises:
        HTTPException: If key not found or access denied

    Security:
        - Requires valid JWT authentication
        - Verifies key ownership before revocation
        - Logs revocation for audit trail
        - Immediate deactivation prevents further use
    """
    try:
        service = APIKeyService(db)

        # Verify ownership and revoke
        success = await service.revoke_api_key(key_id, user_id)

        if not success:
            # Could be not found or access denied - check which
            api_key_record = await service.get_api_key_by_id(key_id)
            if not api_key_record:
                logger.warning(
                    f"User {user_id} attempted to revoke non-existent API key {key_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
                )
            else:
                logger.warning(
                    f"User {user_id} attempted to revoke API key {key_id} owned by {api_key_record.user_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
                )

        # Log successful revocation for audit
        client_ip = "unknown"
        if (
            hasattr(request, "client")
            and request.client
            and hasattr(request.client, "host")
        ):
            client_ip = request.client.host
        logger.info(
            f"API key revoked successfully: user_id={user_id}, key_id={key_id}, client_ip={client_ip}"
        )

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Failed to revoke API key {key_id} for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke API key",
        )


@router.get("/{key_id}/usage", response_model=APIKeyUsageResponse)
async def get_api_key_usage(
    key_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> APIKeyUsageResponse:
    """
    Get usage statistics for an API key.

    Args:
        key_id: API key ID to check usage
        user_id: Authenticated user ID
        db: Database session

    Returns:
        APIKeyUsageResponse: Usage statistics and quota information

    Raises:
        HTTPException: If key not found or access denied

    Security:
        - Requires valid JWT authentication
        - Verifies key ownership before returning usage data
        - Provides quota and usage visibility for billing
    """
    try:
        service = APIKeyService(db)
        api_key_record = await service.get_api_key_by_id(key_id)

        if not api_key_record:
            logger.warning(
                f"User {user_id} attempted to check usage for non-existent API key {key_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
            )

        # Verify ownership
        if api_key_record.user_id != user_id:
            logger.warning(
                f"User {user_id} attempted to check usage for API key {key_id} owned by {api_key_record.user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )

        # Check current quota status
        has_quota, remaining = await service.check_quota_available(api_key_record)

        return APIKeyUsageResponse(
            key_id=api_key_record.key_id,
            name=api_key_record.name,
            monthly_quota=api_key_record.monthly_quota,
            monthly_usage=api_key_record.monthly_usage,
            remaining_quota=remaining if remaining >= 0 else None,
            has_quota_available=has_quota,
            last_quota_reset=api_key_record.last_quota_reset,
            last_used=api_key_record.last_used,
        )

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(
            f"Failed to get usage for API key {key_id} for user {user_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve usage statistics",
        )


# Admin endpoints for API key management
@router.get("/admin/all", response_model=APIKeyListResponse)
async def admin_list_all_api_keys(
    user_id: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
    skip: int = 0,
    limit: int = 100,
) -> APIKeyListResponse:
    """
    Admin endpoint to list all API keys across all users.

    Args:
        user_id: Admin user ID
        db: Database session
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return

    Returns:
        APIKeyListResponse: List of all API keys (without plain text keys)

    Security:
        - Requires admin role authentication
        - Never exposes plain text API keys
        - Provides audit visibility for administrators
    """
    try:
        # Note: This would need a new service method to get all keys with pagination
        # For now, implementing basic version
        from sqlalchemy import select

        result = await db.execute(
            select(APIKey).order_by(APIKey.created_at.desc()).offset(skip).limit(limit)
        )
        api_keys = result.scalars().all()

        keys_data = []
        for key in api_keys:
            import json

            permissions = json.loads(key.permissions)

            keys_data.append(
                APIKeyResponse(
                    key_id=key.key_id,
                    name=key.name,
                    api_key=None,  # Never expose plain text keys
                    permissions=permissions,
                    monthly_quota=key.monthly_quota,
                    monthly_usage=key.monthly_usage,
                    is_active=key.is_active,
                    created_at=key.created_at,
                    last_used=key.last_used,
                    expires_at=key.expires_at,
                    user_id=key.user_id,  # Include user_id for admin view
                )
            )

        logger.info(f"Admin {user_id} listed {len(keys_data)} API keys")

        return APIKeyListResponse(keys=keys_data, total_count=len(keys_data))

    except Exception as e:
        logger.error(f"Failed to list all API keys for admin {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve API keys",
        )


@router.post("/{key_id}/admin/quota", status_code=status.HTTP_200_OK)
async def admin_update_api_key_quota(
    request: Request,
    key_id: str,
    new_quota: int,
    user_id: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """
    Admin endpoint to update API key quota.

    Args:
        key_id: API key ID to update
        new_quota: New monthly quota (-1 for unlimited, 0 for disabled)
        user_id: Admin user ID
        db: Database session
        request: HTTP request object for audit logging

    Raises:
        HTTPException: If key not found or invalid quota

    Security:
        - Requires admin role authentication
        - Validates quota values for safety
        - Logs quota changes for audit trail
    """
    # Validate quota value
    if new_quota < -1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quota must be -1 (unlimited), 0 (disabled), or positive integer",
        )

    try:
        service = APIKeyService(db)

        # Verify key exists
        api_key_record = await service.get_api_key_by_id(key_id)
        if not api_key_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
            )

        # Update quota
        success = await service.update_api_key_quota(key_id, new_quota)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update quota",
            )

        # Log quota change for audit
        client_ip = "unknown"
        if (
            hasattr(request, "client")
            and request.client
            and hasattr(request.client, "host")
        ):
            client_ip = request.client.host
        logger.info(
            f"API key quota updated by admin: admin_user_id={user_id}, key_id={key_id}, "
            f"key_owner={api_key_record.user_id}, old_quota={api_key_record.monthly_quota}, "
            f"new_quota={new_quota}, client_ip={client_ip}"
        )

        return {"message": "Quota updated successfully"}

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(
            f"Failed to update quota for API key {key_id} by admin {user_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update API key quota",
        )
