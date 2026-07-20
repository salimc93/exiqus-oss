"""
Tests for JWT authentication utilities.

This module tests JWT token creation, validation, and security features
using RS256 asymmetric signing.
"""

import time
from datetime import datetime, timedelta, timezone

import jwt as pyjwt
import pytest

from github_analyzer.api.auth.jwt import (
    ALGORITHM,
    JWTError,
    create_access_token,
    create_refresh_token,
    create_token_pair,
    extract_user_id,
    generate_api_key,
    get_algorithm,
    get_audience,
    get_issuer,
    get_private_key,
    get_public_key,
    hash_password,
    refresh_access_token,
    reset_keys,
    validate_api_key_format,
    verify_password,
    verify_token,
)


@pytest.fixture(autouse=True)
def reset_jwt_keys():
    """Reset JWT keys before each test to ensure clean state."""
    reset_keys()
    yield
    reset_keys()


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password(self):
        """Test password hashing produces different hashes."""
        password = "test_password_123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Different hashes due to salt
        assert hash1 != hash2
        assert len(hash1) > 50  # bcrypt hashes are long
        assert isinstance(hash1, str)

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "test_password_123"
        password_hash = hash_password(password)

        assert verify_password(password, password_hash) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "test_password_123"
        wrong_password = "wrong_password"
        password_hash = hash_password(password)

        assert verify_password(wrong_password, password_hash) is False

    def test_password_encoding_handling(self):
        """Test password with special characters."""
        password = "test_pässwörd_123!@#"
        password_hash = hash_password(password)

        assert verify_password(password, password_hash) is True


class TestRS256Algorithm:
    """Test RS256 asymmetric signing."""

    def test_algorithm_is_rs256(self):
        """Verify algorithm is RS256."""
        assert ALGORITHM == "RS256"
        assert get_algorithm() == "RS256"

    def test_create_access_token_uses_rs256(self):
        """Verify tokens are signed with RS256."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)

        header = pyjwt.get_unverified_header(token)
        assert header["alg"] == "RS256"

    def test_private_and_public_keys_are_different(self):
        """Verify private and public keys are different (asymmetric)."""
        private_key = get_private_key()
        public_key = get_public_key()

        assert private_key != public_key
        assert "PRIVATE KEY" in private_key
        assert "PUBLIC KEY" in public_key

    def test_hs256_tokens_rejected(self):
        """Verify HS256 tokens are rejected."""
        # Create HS256 token (old format)
        old_token = pyjwt.encode(
            {
                "sub": "test",
                "type": "access",
                "aud": get_audience(),
                "iss": get_issuer(),
            },
            "secret",
            algorithm="HS256",
        )

        with pytest.raises(JWTError, match="Invalid token"):
            verify_token(old_token, "access")


class TestAudienceAndIssuer:
    """Test audience and issuer claim validation."""

    def test_token_contains_audience_claim(self):
        """Verify tokens contain audience claim."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)

        # Decode without verification to check claims
        payload = pyjwt.decode(token, options={"verify_signature": False})
        assert "aud" in payload
        assert payload["aud"] == get_audience()

    def test_token_contains_issuer_claim(self):
        """Verify tokens contain issuer claim."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)

        payload = pyjwt.decode(token, options={"verify_signature": False})
        assert "iss" in payload
        assert payload["iss"] == get_issuer()

    def test_verify_token_validates_audience(self):
        """Verify audience claim is validated."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)

        # Should succeed with correct audience (via verify_token)
        payload = verify_token(token, "access")
        assert payload["aud"] == get_audience()

    def test_wrong_audience_rejected(self):
        """Verify tokens with wrong audience are rejected."""
        # Create token with wrong audience directly
        payload = {
            "sub": "test",
            "email": "test@example.com",
            "type": "access",
            "aud": "wrong-audience",
            "iss": get_issuer(),
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        }

        token = pyjwt.encode(payload, get_private_key(), algorithm="RS256")

        with pytest.raises(JWTError, match="Invalid token audience"):
            verify_token(token, "access")

    def test_wrong_issuer_rejected(self):
        """Verify tokens with wrong issuer are rejected."""
        payload = {
            "sub": "test",
            "email": "test@example.com",
            "type": "access",
            "aud": get_audience(),
            "iss": "wrong-issuer",
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        }

        token = pyjwt.encode(payload, get_private_key(), algorithm="RS256")

        with pytest.raises(JWTError, match="Invalid token issuer"):
            verify_token(token, "access")


class TestJWTTokens:
    """Test JWT token creation and validation."""

    def test_create_access_token(self):
        """Test access token creation."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 100  # JWT tokens are long
        assert token.count(".") == 2  # JWT format: header.payload.signature

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_refresh_token(data)

        assert isinstance(token, str)
        assert len(token) > 100
        assert token.count(".") == 2

    def test_verify_access_token(self):
        """Test access token verification."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)

        payload = verify_token(token, "access")
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"

    def test_verify_refresh_token(self):
        """Test refresh token verification."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_refresh_token(data)

        payload = verify_token(token, "refresh")
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "refresh"

    def test_verify_wrong_token_type(self):
        """Test token verification with wrong type."""
        data = {"sub": "user123", "email": "test@example.com"}
        access_token = create_access_token(data)

        with pytest.raises(JWTError, match="Invalid token type"):
            verify_token(access_token, "refresh")

    def test_token_with_custom_expiration(self):
        """Test token creation with custom expiration."""
        data = {"sub": "user123", "email": "test@example.com"}
        custom_expiry = timedelta(minutes=30)
        token = create_access_token(data, expires_delta=custom_expiry)

        payload = verify_token(token, "access")
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)

        # Should expire in about 30 minutes
        time_diff = exp_time - now
        assert 25 <= time_diff.total_seconds() / 60 <= 35

    def test_expired_token(self):
        """Test verification of expired token."""
        data = {"sub": "user123", "email": "test@example.com"}
        # Create token that expires immediately
        expired_token = create_access_token(data, expires_delta=timedelta(seconds=-1))

        with pytest.raises(JWTError, match="Token has expired"):
            verify_token(expired_token, "access")

    def test_invalid_token_format(self):
        """Test verification of malformed token."""
        invalid_token = "invalid.token.format"

        with pytest.raises(JWTError, match="Invalid token"):
            verify_token(invalid_token, "access")

    def test_extract_user_id(self):
        """Test extracting user ID from token."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)

        user_id = extract_user_id(token)
        assert user_id == "user123"

    def test_extract_user_id_missing(self):
        """Test extracting user ID from token without sub claim."""
        data = {"email": "test@example.com"}  # Missing 'sub'
        token = create_access_token(data)

        with pytest.raises(JWTError, match="does not contain user ID"):
            extract_user_id(token)


class TestTokenPair:
    """Test token pair creation and refresh."""

    def test_create_token_pair(self):
        """Test creating access and refresh token pair."""
        user_id = "user123"
        email = "test@example.com"
        permissions = ["analyze", "batch"]

        tokens = create_token_pair(user_id, email, permissions)

        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert isinstance(tokens["access_token"], str)
        assert isinstance(tokens["refresh_token"], str)

        # Verify access token
        access_payload = verify_token(tokens["access_token"], "access")
        assert access_payload["sub"] == user_id
        assert access_payload["email"] == email
        assert access_payload["permissions"] == permissions

        # Verify refresh token
        refresh_payload = verify_token(tokens["refresh_token"], "refresh")
        assert refresh_payload["sub"] == user_id
        assert refresh_payload["email"] == email

    def test_refresh_access_token(self):
        """Test refreshing access token with refresh token."""
        user_id = "user123"
        email = "test@example.com"
        tokens = create_token_pair(user_id, email)

        # Refresh the access token
        new_access_token = refresh_access_token(tokens["refresh_token"])

        # Verify new access token
        payload = verify_token(new_access_token, "access")
        assert payload["sub"] == user_id
        assert payload["email"] == email

    def test_refresh_with_invalid_token(self):
        """Test refresh with invalid refresh token."""
        invalid_refresh_token = "invalid.token.here"

        with pytest.raises(JWTError):
            refresh_access_token(invalid_refresh_token)

    def test_refresh_with_access_token(self):
        """Test refresh using access token instead of refresh token."""
        data = {"sub": "user123", "email": "test@example.com"}
        access_token = create_access_token(data)

        with pytest.raises(JWTError, match="Invalid token type"):
            refresh_access_token(access_token)


class TestAPIKeys:
    """Test API key generation and validation."""

    def test_generate_api_key(self):
        """Test API key generation."""
        api_key = generate_api_key()

        assert isinstance(api_key, str)
        assert api_key.startswith("sk_live_")
        assert len(api_key) > 40  # Should be long and secure

    def test_generate_unique_api_keys(self):
        """Test that generated API keys are unique."""
        key1 = generate_api_key()
        key2 = generate_api_key()

        assert key1 != key2

    def test_validate_api_key_format_valid(self):
        """Test API key format validation with valid key."""
        valid_key = generate_api_key()
        assert validate_api_key_format(valid_key) is True

    def test_validate_api_key_format_invalid(self):
        """Test API key format validation with invalid keys."""
        invalid_keys = [
            "invalid_key",
            "sk_test_123",  # Wrong prefix
            "sk_live_",  # Too short
            "",  # Empty
            "random_string",
        ]

        for invalid_key in invalid_keys:
            assert validate_api_key_format(invalid_key) is False


class TestTokenSecurity:
    """Test JWT token security features."""

    def test_tokens_are_different(self):
        """Test that identical data produces different tokens."""
        data = {"sub": "user123", "email": "test@example.com"}

        # Create tokens at different times (need at least 1 second for different iat)
        token1 = create_access_token(data)
        time.sleep(1.1)  # Ensure different timestamp (1+ second for iat difference)
        token2 = create_access_token(data)

        assert token1 != token2  # Different due to different iat (issued at) and jti

    def test_token_contains_security_claims(self):
        """Test that tokens contain required security claims."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)

        payload = verify_token(token, "access")

        # Check required claims
        assert "exp" in payload  # Expiration
        assert "iat" in payload  # Issued at
        assert "type" in payload  # Token type
        assert "sub" in payload  # Subject (user ID)
        assert "jti" in payload  # Unique token ID
        assert "aud" in payload  # Audience
        assert "iss" in payload  # Issuer

        # Verify claim types
        assert isinstance(payload["exp"], int)
        assert isinstance(payload["iat"], int)
        assert payload["type"] == "access"

    def test_token_contains_jti_for_revocation(self):
        """Test that tokens contain unique jti for revocation support."""
        data = {"sub": "user123", "email": "test@example.com"}

        token1 = create_access_token(data)
        token2 = create_access_token(data)

        payload1 = verify_token(token1, "access")
        payload2 = verify_token(token2, "access")

        # jti should be unique for each token
        assert payload1["jti"] != payload2["jti"]

    def test_token_permissions_handling(self):
        """Test that permissions are properly handled in tokens."""
        user_id = "user123"
        email = "test@example.com"
        permissions = ["analyze", "batch", "admin"]

        tokens = create_token_pair(user_id, email, permissions)
        payload = verify_token(tokens["access_token"], "access")

        assert payload["permissions"] == permissions
