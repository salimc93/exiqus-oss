# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Authentication dependencies for FastAPI endpoints.

This module provides dependency functions for authenticating users
and validating API keys in FastAPI routes.
"""

from typing import Annotated, Any, List, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ...billing.subscription_manager import PlanFeatures
from ...database.connection import get_db_session
from ...database.models import User, UserRole
from ...database.operations import UserOperations
from ..services.api_key_service import APIKeyService
from .jwt import JWTError, extract_user_id, verify_token

# HTTP Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticationError(HTTPException):
    """Custom authentication error."""

    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationError(HTTPException):
    """Custom authorization error."""

    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


def get_token_from_header(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)
    ],
) -> Optional[str]:
    """
    Extract token from Authorization header.

    Args:
        credentials: HTTP authorization credentials

    Returns:
        Optional[str]: Bearer token if present
    """
    if credentials and credentials.scheme == "Bearer":
        return credentials.credentials
    return None


def get_api_key_from_header(request: Request) -> Optional[str]:
    """
    Extract API key from X-API-Key header.

    Args:
        request: FastAPI request object

    Returns:
        Optional[str]: API key if present
    """
    return request.headers.get("X-API-Key")


async def get_current_user_id(
    token: Annotated[Optional[str], Depends(get_token_from_header)],
) -> str:
    """
    Get current authenticated user ID from JWT token.

    Args:
        token: JWT access token

    Returns:
        str: User ID

    Raises:
        AuthenticationError: If token is invalid or missing
    """
    if not token:
        raise AuthenticationError("Missing authentication token")

    try:
        user_id = extract_user_id(token)
        return user_id
    except JWTError as e:
        raise AuthenticationError(f"Invalid token: {str(e)}")


async def get_current_user_optional(
    token: Annotated[Optional[str], Depends(get_token_from_header)],
) -> Optional[str]:
    """
    Get current user ID if authenticated, None otherwise.

    Args:
        token: Optional JWT access token

    Returns:
        Optional[str]: User ID if authenticated, None otherwise
    """
    if not token:
        return None

    try:
        user_id = extract_user_id(token)
        return user_id
    except JWTError:
        return None


async def verify_api_key(
    request: Request,
    api_key: Annotated[Optional[str], Depends(get_api_key_from_header)],
    db: AsyncSession = Depends(get_db_session),
) -> Optional[str]:
    """
    Verify API key and return associated user ID.

    Args:
        request: FastAPI request object
        api_key: API key from header
        db: Database session

    Returns:
        Optional[str]: User ID if API key is valid

    Raises:
        AuthenticationError: If API key is invalid
    """
    if not api_key:
        return None

    # Use the secure APIKeyService for validation
    try:
        service = APIKeyService(db)
        api_key_record = await service.validate_api_key(api_key)

        if not api_key_record:
            raise AuthenticationError("Invalid or inactive API key")

        # Store the API key record in request state for potential quota checking
        request.state.api_key_record = api_key_record

        return api_key_record.user_id

    except Exception as e:
        # Log the error but don't expose internal details
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"API key verification error: {str(e)}")
        raise AuthenticationError("API key verification failed")


async def get_authenticated_user(
    user_id_jwt: Annotated[Optional[str], Depends(get_current_user_optional)],
    user_id_api: Annotated[Optional[str], Depends(verify_api_key)],
) -> str:
    """
    Get authenticated user ID from either JWT or API key.

    Args:
        user_id_jwt: User ID from JWT token
        user_id_api: User ID from API key

    Returns:
        str: Authenticated user ID

    Raises:
        AuthenticationError: If no valid authentication method provided
    """
    user_id = user_id_jwt or user_id_api

    if not user_id:
        raise AuthenticationError(
            "Authentication required. Provide either Bearer token or X-API-Key header"
        )

    return user_id


async def get_current_user_id_optional(
    user_id_jwt: Annotated[Optional[str], Depends(get_current_user_optional)],
    user_id_api: Annotated[Optional[str], Depends(verify_api_key)],
) -> Optional[str]:
    """
    Get authenticated user ID from either JWT or API key, if provided.

    Args:
        user_id_jwt: Optional user ID from JWT token
        user_id_api: Optional user ID from API key

    Returns:
        Optional[str]: Authenticated user ID if any authentication provided, None otherwise
    """
    return user_id_jwt or user_id_api


async def require_permission(
    permission: str,
    user_id: Annotated[str, Depends(get_authenticated_user)],
    token: Annotated[Optional[str], Depends(get_token_from_header)],
    request: Request,
) -> str:
    """
    Require specific permission for the authenticated user.

    Args:
        permission: Required permission
        user_id: Authenticated user ID
        token: JWT token (for permission checking)
        request: FastAPI request object (to access API key record)

    Returns:
        str: User ID if permission is granted

    Raises:
        AuthorizationError: If user lacks required permission
    """
    # Check if user authenticated via JWT token
    if token:
        try:
            payload = verify_token(token, "access")
            permissions_raw: Any = payload.get("permissions", [])
            user_permissions: List[str] = (
                permissions_raw if isinstance(permissions_raw, list) else []
            )

            if permission not in user_permissions and "admin" not in user_permissions:
                raise AuthorizationError(f"Permission '{permission}' required")

        except JWTError:
            raise AuthenticationError("Invalid token for permission check")
    else:
        # Check API key permissions from the database
        api_key_record = getattr(request.state, "api_key_record", None)
        if api_key_record:
            try:
                import json

                # Parse permissions from API key record
                api_permissions = json.loads(api_key_record.permissions)

                if permission not in api_permissions and "admin" not in api_permissions:
                    raise AuthorizationError(f"API key lacks '{permission}' permission")

            except (json.JSONDecodeError, AttributeError):
                raise AuthorizationError("Invalid API key permissions")
        else:
            # No valid authentication method with permissions
            raise AuthenticationError("Unable to verify permissions")

    return user_id


# Pre-configured dependency functions for common permissions
async def require_analyze_permission(
    user_id: Annotated[str, Depends(get_authenticated_user)],
    token: Annotated[Optional[str], Depends(get_token_from_header)],
    request: Request,
) -> str:
    """Require 'analyze' permission."""
    return await require_permission("analyze", user_id, token, request)


async def require_batch_permission(
    user_id: Annotated[str, Depends(get_authenticated_user)],
    token: Annotated[Optional[str], Depends(get_token_from_header)],
    request: Request,
) -> str:
    """Require 'batch' permission."""
    return await require_permission("batch", user_id, token, request)


async def require_admin_permission(
    user_id: Annotated[str, Depends(get_authenticated_user)],
    token: Annotated[Optional[str], Depends(get_token_from_header)],
    request: Request,
) -> str:
    """Require 'admin' permission."""
    return await require_permission("admin", user_id, token, request)


async def require_admin(
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_db_session),
) -> str:
    """
    Require admin role for the authenticated user.

    Args:
        user_id: Authenticated user ID
        db: Database session

    Returns:
        str: User ID if user is admin

    Raises:
        AuthorizationError: If user is not an admin
        AuthenticationError: If user not found
    """
    user = await UserOperations.get_user_by_id(db, user_id)
    if not user:
        raise AuthenticationError("User not found")

    if user.user_role != UserRole.ADMIN and not user.is_admin:
        raise AuthorizationError("Admin access required")

    return user_id


async def get_current_active_user(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """
    Fetches the current authenticated and active user from the database.
    """
    user = await UserOperations.get_user_by_id(db, user_id)
    if not user:
        raise AuthenticationError("User not found.")
    if not user.is_active:
        raise AuthenticationError("User account is inactive.")
    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Requires the current user to be an admin.
    """
    if not current_user.is_admin:
        raise AuthorizationError("Admin privileges required.")
    return current_user


async def get_admin_user_from_token(
    token: Annotated[Optional[str], Depends(get_token_from_header)],
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """
    Get admin user from admin JWT token.

    This is specifically for admin portal endpoints that use admin JWT tokens.
    Admin tokens have special claims like 'admin_session': True.

    Args:
        token: JWT access token from admin login
        db: Database session

    Returns:
        User: The admin user

    Raises:
        AuthenticationError: If token is invalid or not an admin token
        AuthorizationError: If user is not an admin
    """
    if not token:
        raise AuthenticationError("Admin authentication token required")

    try:
        # Verify the token and get payload
        payload = verify_token(token, "access")

        # Check if this is an admin session token
        if not payload.get("admin_session") or not payload.get("is_admin"):
            raise AuthenticationError("Invalid admin session token")

        # Get user ID from token
        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Invalid token structure")

        # Get user from database
        user = await UserOperations.get_user_by_id(db, str(user_id))

        if not user:
            raise AuthenticationError("User not found")

        if not user.is_active:
            raise AuthenticationError("User account is inactive")

        # Verify admin status
        if not user.is_admin:
            raise AuthorizationError("Admin privileges required")

        return user

    except JWTError as e:
        raise AuthenticationError(f"Invalid admin token: {str(e)}")


async def require_api_access(
    request: Request,
    api_key: Annotated[Optional[str], Depends(get_api_key_from_header)],
    db: AsyncSession = Depends(get_db_session),
) -> str:
    """
    Verify API key and ensure user has API access based on subscription plan.

    This dependency:
    1. Validates the API key
    2. Retrieves the associated user
    3. Checks if the user's subscription plan includes API access
    4. Returns the user ID if authorized

    Args:
        request: FastAPI request object
        api_key: API key from X-API-Key header
        db: Database session

    Returns:
        str: User ID if authorized

    Raises:
        AuthenticationError: If API key is missing, invalid, or user not found
        AuthorizationError: If user's plan doesn't include API access
    """
    if not api_key:
        raise AuthenticationError("API key required for this endpoint")

    # Validate API key using the secure service
    try:
        service = APIKeyService(db)
        api_key_record = await service.validate_api_key(api_key)

        if not api_key_record:
            raise AuthenticationError("Invalid or inactive API key")

        # Get user and check their subscription plan
        user = await UserOperations.get_user_by_id(db, api_key_record.user_id)

        if not user:
            raise AuthenticationError("User not found")

        # Check if user's plan has API access
        if not PlanFeatures.can_access_feature(user.subscription_plan, "api_access"):
            raise AuthorizationError(
                "API access is not available for your current plan. "
                "Please upgrade to Professional or Enterprise for API access."
            )

        # Store API key record in request state for potential quota tracking
        request.state.api_key_record = api_key_record
        request.state.authenticated_user_id = user.user_id

        return user.user_id

    except HTTPException:
        # Re-raise FastAPI exceptions
        raise
    except Exception as e:
        # Log and wrap any other exceptions
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"API access verification error: {str(e)}")
        raise AuthenticationError("API key verification failed")
