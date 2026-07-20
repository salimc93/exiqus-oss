# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
JWT token utilities for API authentication.

This module handles JWT token creation, validation, and refresh operations
with enterprise-grade security practices using RS256 asymmetric signing.

Security Features:
- RS256 (RSA) asymmetric signing - private key signs, public key verifies
- Audience and Issuer claim validation
- Unique token IDs (jti) for revocation support
- Separate access and refresh tokens with different expiry
"""

import base64
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import bcrypt
import jwt
from jwt import (
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidTokenError,
    PyJWTError,
)

from ...utils.config import get_config


# Custom exception for backward compatibility
class JWTError(Exception):
    """Custom JWT error for API consistency."""

    pass


# JWT configuration constants
ALGORITHM = "RS256"  # Asymmetric signing (private key signs, public key verifies)
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour
REFRESH_TOKEN_EXPIRE_DAYS = 30  # 30 days

# Audience and Issuer for token validation. These are opaque identifiers,
# not URLs that get resolved - override via JWT_AUDIENCE / JWT_ISSUER if
# your deployment needs them to match an external identity provider.
JWT_AUDIENCE = "exiqus-api"
JWT_ISSUER = "exiqus-api"

# Lazy-loaded keys to allow test environment setup
_PRIVATE_KEY: Optional[str] = None
_PUBLIC_KEY: Optional[str] = None


def _get_jwt_config() -> Dict[str, str]:
    """Get JWT configuration from environment."""
    config = get_config()
    return {
        "algorithm": config._get_str("JWT_ALGORITHM", "RS256"),
        "audience": config._get_str("JWT_AUDIENCE", JWT_AUDIENCE),
        "issuer": config._get_str("JWT_ISSUER", JWT_ISSUER),
        "private_key_path": config._get_str("JWT_PRIVATE_KEY_PATH", ""),
        "public_key_path": config._get_str("JWT_PUBLIC_KEY_PATH", ""),
        "private_key": config._get_str("JWT_PRIVATE_KEY", ""),  # Base64 encoded
        "public_key": config._get_str("JWT_PUBLIC_KEY", ""),  # Base64 encoded
    }


def _load_key_from_file(path: str) -> str:
    """Load a PEM key from file."""
    key_path = Path(path)
    if not key_path.exists():
        raise JWTError(f"Key file not found: {path}")
    return key_path.read_text()


def _load_key_from_base64(encoded: str) -> str:
    """Load a PEM key from base64 encoded string (for Railway/production)."""
    try:
        return base64.b64decode(encoded).decode("utf-8")
    except Exception as e:
        raise JWTError(f"Failed to decode base64 key: {e}")


def get_private_key() -> str:
    """
    Get JWT private key for signing tokens.

    Loads from:
    1. JWT_PRIVATE_KEY env var (base64 encoded, for production)
    2. JWT_PRIVATE_KEY_PATH file path (for local development)
    3. Generates test key if in TESTING mode
    """
    global _PRIVATE_KEY
    if _PRIVATE_KEY is not None:
        return _PRIVATE_KEY

    jwt_config = _get_jwt_config()

    # Check for base64 encoded key (production - Railway)
    if jwt_config["private_key"]:
        _PRIVATE_KEY = _load_key_from_base64(jwt_config["private_key"])
        return _PRIVATE_KEY

    # Check for file path (local development)
    if jwt_config["private_key_path"]:
        _PRIVATE_KEY = _load_key_from_file(jwt_config["private_key_path"])
        return _PRIVATE_KEY

    # Testing mode - generate ephemeral key pair
    if os.getenv("TESTING") or os.getenv("ENV") == "development":
        _generate_test_keys()
        if _PRIVATE_KEY is not None:
            return _PRIVATE_KEY

    raise JWTError(
        "JWT_PRIVATE_KEY or JWT_PRIVATE_KEY_PATH must be set. "
        "Run 'python scripts/generate_rsa_keys.py' to generate keys."
    )


def get_public_key() -> str:
    """
    Get JWT public key for verifying tokens.

    Loads from:
    1. JWT_PUBLIC_KEY env var (base64 encoded, for production)
    2. JWT_PUBLIC_KEY_PATH file path (for local development)
    3. Generates test key if in TESTING mode
    """
    global _PUBLIC_KEY
    if _PUBLIC_KEY is not None:
        return _PUBLIC_KEY

    jwt_config = _get_jwt_config()

    # Check for base64 encoded key (production - Railway)
    if jwt_config["public_key"]:
        _PUBLIC_KEY = _load_key_from_base64(jwt_config["public_key"])
        return _PUBLIC_KEY

    # Check for file path (local development)
    if jwt_config["public_key_path"]:
        _PUBLIC_KEY = _load_key_from_file(jwt_config["public_key_path"])
        return _PUBLIC_KEY

    # Testing mode - generate ephemeral key pair
    if os.getenv("TESTING") or os.getenv("ENV") == "development":
        _generate_test_keys()
        if _PUBLIC_KEY is not None:
            return _PUBLIC_KEY

    raise JWTError(
        "JWT_PUBLIC_KEY or JWT_PUBLIC_KEY_PATH must be set. "
        "Run 'python scripts/generate_rsa_keys.py' to generate keys."
    )


def _generate_test_keys() -> None:
    """Generate ephemeral RSA keys for testing."""
    global _PRIVATE_KEY, _PUBLIC_KEY

    if _PRIVATE_KEY is not None and _PUBLIC_KEY is not None:
        return

    try:
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        # Generate RSA-2048 key pair
        private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )
        public_key = private_key.public_key()

        # Serialize to PEM format
        _PRIVATE_KEY = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")

        _PUBLIC_KEY = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

    except ImportError:
        raise JWTError(
            "cryptography package required for test key generation. "
            "Install with: pip install cryptography"
        )


def get_secret_key() -> str:
    """
    Legacy function for backward compatibility during migration.
    Returns the private key for signing (RS256 uses private key to sign).
    """
    return get_private_key()


def get_algorithm() -> str:
    """Get the JWT algorithm (RS256)."""
    jwt_config = _get_jwt_config()
    return jwt_config.get("algorithm", ALGORITHM)


def get_audience() -> str:
    """Get the JWT audience claim."""
    jwt_config = _get_jwt_config()
    return jwt_config.get("audience", JWT_AUDIENCE)


def get_issuer() -> str:
    """Get the JWT issuer claim."""
    jwt_config = _get_jwt_config()
    return jwt_config.get("issuer", JWT_ISSUER)


def reset_keys() -> None:
    """Reset cached keys (useful for testing)."""
    global _PRIVATE_KEY, _PUBLIC_KEY
    _PRIVATE_KEY = None
    _PUBLIC_KEY = None


def create_access_token(
    data: Dict[str, Union[str, int]], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token signed with RS256.

    Args:
        data: Token payload data
        expires_delta: Optional custom expiration time

    Returns:
        str: Encoded JWT token

    Raises:
        JWTError: If token creation fails
    """
    try:
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=ACCESS_TOKEN_EXPIRE_MINUTES
            )

        to_encode.update(
            {
                "exp": int(expire.timestamp()),
                "iat": int(datetime.now(timezone.utc).timestamp()),
                "type": "access",
                "jti": secrets.token_urlsafe(16),  # Unique token ID for revocation
                "aud": get_audience(),  # Audience claim
                "iss": get_issuer(),  # Issuer claim
            }
        )

        encoded_jwt = jwt.encode(
            to_encode, get_private_key(), algorithm=get_algorithm()
        )
        return encoded_jwt

    except JWTError:
        raise
    except Exception as e:
        raise JWTError(f"Failed to create access token: {str(e)}")


def create_refresh_token(data: Dict[str, Union[str, int]]) -> str:
    """
    Create a JWT refresh token signed with RS256.

    Args:
        data: Token payload data

    Returns:
        str: Encoded JWT refresh token

    Raises:
        JWTError: If token creation fails
    """
    try:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        to_encode.update(
            {
                "exp": int(expire.timestamp()),
                "iat": int(datetime.now(timezone.utc).timestamp()),
                "type": "refresh",
                "jti": secrets.token_urlsafe(16),  # Unique token ID for revocation
                "aud": get_audience(),  # Audience claim
                "iss": get_issuer(),  # Issuer claim
            }
        )

        encoded_jwt = jwt.encode(
            to_encode, get_private_key(), algorithm=get_algorithm()
        )
        return encoded_jwt

    except JWTError:
        raise
    except Exception as e:
        raise JWTError(f"Failed to create refresh token: {str(e)}")


def verify_token(token: str, token_type: str = "access") -> Dict[str, Union[str, int]]:  # nosec B107  # noqa: S107 - not a credential
    """
    Verify and decode a JWT token using RS256 public key.

    Args:
        token: JWT token to verify
        token_type: Expected token type ("access" or "refresh")

    Returns:
        Dict: Decoded token payload

    Raises:
        JWTError: If token is invalid, expired, or wrong type
    """
    try:
        # Verify with public key (RS256 asymmetric verification)
        payload = jwt.decode(
            token,
            get_public_key(),
            algorithms=[get_algorithm()],
            audience=get_audience(),
            issuer=get_issuer(),
            options={
                "verify_exp": True,
                "verify_aud": True,
                "verify_iss": True,
            },
        )

        # Verify token type
        if payload.get("type") != token_type:
            raise JWTError(f"Invalid token type. Expected {token_type}")

        # Verify expiration (redundant but explicit)
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(
            timezone.utc
        ):
            raise JWTError("Token has expired")

        return dict(payload)

    except ExpiredSignatureError:
        raise JWTError("Token has expired")
    except InvalidAudienceError:
        raise JWTError("Invalid token audience")
    except InvalidIssuerError:
        raise JWTError("Invalid token issuer")
    except InvalidTokenError:
        raise JWTError("Invalid token claims")
    except PyJWTError as jwt_error:
        raise JWTError(f"Invalid token: {str(jwt_error)}")
    except JWTError:
        raise
    except Exception as e:
        raise JWTError(f"Token verification failed: {str(e)}")


def extract_user_id(token: str) -> str:
    """
    Extract user ID from a JWT token.

    Args:
        token: JWT access token

    Returns:
        str: User ID from token

    Raises:
        JWTError: If token is invalid or doesn't contain user_id
    """
    payload = verify_token(token, "access")
    user_id = payload.get("sub")

    if not user_id:
        raise JWTError("Token does not contain user ID")

    return str(user_id)


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        str: Hashed password
    """
    # Convert password to bytes and hash with salt
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password to verify against

    Returns:
        bool: True if password matches
    """
    # Convert to bytes and verify
    password_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def generate_api_key() -> str:
    """
    Generate a secure API key.

    Returns:
        str: Secure API key with prefix
    """
    # Generate a secure random key
    key_part = secrets.token_urlsafe(32)
    return f"sk_live_{key_part}"


def validate_api_key_format(api_key: str) -> bool:
    """
    Validate API key format.

    Args:
        api_key: API key to validate

    Returns:
        bool: True if format is valid
    """
    return api_key.startswith("sk_live_") and len(api_key) > 10


def create_token_pair(
    user_id: str, email: str, permissions: Optional[List[str]] = None
) -> Dict[str, str]:
    """
    Create both access and refresh tokens for a user.

    Args:
        user_id: User identifier
        email: User email
        permissions: Optional user permissions

    Returns:
        Dict: Contains access_token and refresh_token
    """
    token_data: Dict[str, Union[str, int]] = {
        "sub": user_id,
        "email": email,
    }

    # Create access token with permissions
    to_encode: Dict[str, Any] = token_data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update(
        {
            "exp": int(expire.timestamp()),
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "type": "access",
            "jti": secrets.token_urlsafe(16),
            "aud": get_audience(),
            "iss": get_issuer(),
            "permissions": permissions or ["analyze"],  # Add permissions as list
        }
    )

    access_token = jwt.encode(to_encode, get_private_key(), algorithm=get_algorithm())
    refresh_token = create_refresh_token({"sub": user_id, "email": email})

    return {"access_token": access_token, "refresh_token": refresh_token}


def refresh_access_token(refresh_token: str) -> str:
    """
    Create a new access token from a valid refresh token.

    Args:
        refresh_token: Valid refresh token

    Returns:
        str: New access token

    Raises:
        JWTError: If refresh token is invalid
    """
    # Verify refresh token
    payload = verify_token(refresh_token, "refresh")

    user_id = payload.get("sub")
    email = payload.get("email")

    if not user_id or not email:
        raise JWTError("Invalid refresh token payload")

    # Create new access token
    token_data: Dict[str, Union[str, int]] = {
        "sub": user_id,
        "email": email,
    }

    return create_access_token(token_data)
