"""Tests for API key generation and validation utilities."""

import hashlib

from github_analyzer.api.utils.api_key import (
    extract_key_prefix,
    generate_api_key,
    hash_api_key,
    hash_api_key_with_salt,
    validate_api_key_format,
    verify_api_key,
    verify_api_key_with_salt,
)


class TestAPIKeyGeneration:
    """Test API key generation functionality."""

    def test_generate_api_key_format(self):
        """Test that generated API keys have the correct format."""
        api_key, key_prefix, api_key_hash, salt = generate_api_key()

        # Check format
        assert api_key.startswith("gha_")
        assert len(api_key) == 36  # "gha_" (4) + prefix (10) + "_" (1) + secret (21)
        assert validate_api_key_format(api_key)

        # Check that it has the right structure
        parts = api_key.split("_")
        assert len(parts) == 3
        assert parts[0] == "gha"
        assert len(parts[1]) == 10  # prefix
        assert len(parts[2]) == 21  # secret

        # Check prefix matches
        assert key_prefix == parts[1]

        # Check hash format
        assert api_key_hash is not None
        assert len(api_key_hash) == 64  # SHA-256 hex digest

        # Check salt format
        assert salt is not None
        assert len(salt) == 32  # 16 bytes hex = 32 chars

    def test_generate_api_key_uniqueness(self):
        """Test that generated API keys are unique."""
        keys = set()
        prefixes = set()
        hashes = set()
        salts = set()

        # Generate 100 keys and ensure they're all unique
        for _ in range(100):
            api_key, key_prefix, api_key_hash, salt = generate_api_key()
            keys.add(api_key)
            prefixes.add(key_prefix)
            hashes.add(api_key_hash)
            salts.add(salt)

        assert len(keys) == 100
        assert len(prefixes) == 100  # Prefixes must be unique
        assert len(hashes) == 100
        assert len(salts) == 100

    def test_generate_api_key_returns_different_values(self):
        """Test that key and hash are different."""
        api_key, key_prefix, api_key_hash, salt = generate_api_key()
        assert api_key != api_key_hash
        assert api_key != salt
        assert api_key_hash != salt
        assert key_prefix != api_key_hash
        assert key_prefix in api_key  # Prefix should be part of the key


class TestAPIKeyPrefixExtraction:
    """Test API key prefix extraction functionality."""

    def test_extract_key_prefix_valid(self):
        """Test extracting prefix from valid API keys."""
        test_cases = [
            ("gha_1234567890_123456789012345678901", "1234567890"),
            ("gha_abcdef1234_abcdefabcdefabcdefabc", "abcdef1234"),
            ("gha_0987654321_098765432109876543210", "0987654321"),
        ]

        for api_key, expected_prefix in test_cases:
            assert extract_key_prefix(api_key) == expected_prefix

    def test_extract_key_prefix_invalid(self):
        """Test extracting prefix from invalid API keys."""
        invalid_keys = [
            "invalid_key",
            "gha_notenoughparts",
            "wrongprefix_test_secret",
            "",
            "gha_",
        ]

        for api_key in invalid_keys:
            assert extract_key_prefix(api_key) == ""


class TestAPIKeyHashing:
    """Test API key hashing functionality."""

    def test_hash_api_key_with_salt_consistency(self):
        """Test that hashing with the same salt produces the same result."""
        api_key = "gha_1234567890_123456789012345678901"
        salt = "abcdef1234567890abcdef1234567890"

        hash1 = hash_api_key_with_salt(api_key, salt)
        hash2 = hash_api_key_with_salt(api_key, salt)

        # Should be the same when using the same salt
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex digest

    def test_hash_api_key_consistency(self):
        """Test that hashing the same key produces different results due to random salt."""
        api_key = "gha_1234567890_123456789012345678901"

        hash1 = hash_api_key(api_key)
        hash2 = hash_api_key(api_key)

        # Should be different due to different salts
        assert hash1 != hash2

        # But both should be valid format
        assert ":" in hash1
        assert ":" in hash2

    def test_hash_api_key_different_keys(self):
        """Test that different keys produce different hashes."""
        key1 = "gha_1234567890_123456789012345678901"
        key2 = "gha_0987654321_098765432109876543210"

        hash1 = hash_api_key(key1)
        hash2 = hash_api_key(key2)

        assert hash1 != hash2

    def test_hash_api_key_length(self):
        """Test that hash has correct format."""
        api_key = "gha_1234567890_123456789012345678901"
        api_key_hash = hash_api_key(api_key)

        # Check format salt:hash
        assert ":" in api_key_hash
        salt, hash_part = api_key_hash.split(":", 1)
        assert len(salt) == 32  # 16 bytes hex
        assert len(hash_part) == 64  # SHA-256 hex digest


class TestAPIKeyValidation:
    """Test API key format validation."""

    def test_validate_api_key_format_valid(self):
        """Test validation of valid API keys."""
        # Generate some valid keys
        for _ in range(5):
            api_key, _, _, _ = generate_api_key()
            assert validate_api_key_format(api_key) is True

        # Also test some manual valid formats
        valid_keys = [
            "gha_1234567890_123456789012345678901",  # Valid format
            "gha_abcdef1234_abcdefabcdefabcdefabc",  # Valid hex
            "gha_0123456789_012345678901234567890",  # Another valid
        ]

        for key in valid_keys:
            assert validate_api_key_format(key) is True

    def test_validate_api_key_format_invalid_prefix(self):
        """Test validation rejects keys without correct prefix."""
        invalid_keys = [
            "12345678901234567890123456789012",  # No prefix
            "api_1234567890_123456789012345678901",  # Wrong prefix
            "GHA_1234567890_123456789012345678901",  # Wrong case
            "gha1234567890_123456789012345678901",  # No underscore after gha
            "gha_",  # Incomplete
        ]

        for key in invalid_keys:
            assert validate_api_key_format(key) is False

    def test_validate_api_key_format_invalid_length(self):
        """Test validation rejects keys with wrong length."""
        invalid_keys = [
            "gha_123_456",  # Too short
            "gha_1234567890_12345678901234567890123",  # Too long secret
            "gha_123_123456789012345678901",  # Too short prefix
            "gha_12345678901_123456789012345678901",  # Too long prefix
            "gha_1234567890123456789012345678901",  # No separator
        ]

        for key in invalid_keys:
            assert validate_api_key_format(key) is False

    def test_validate_api_key_format_invalid_characters(self):
        """Test validation rejects keys with invalid characters."""
        invalid_keys = [
            "gha_12345678!0_123456789012345678901",  # Special char in prefix
            "gha_1234567890_12345678901234567890!",  # Special char in secret
            "gha_1234567890_12345678901234567890 ",  # Space
            "gha_123456789$_123456789012345678901",  # Dollar sign
            "gha_123456789@_123456789012345678901",  # At symbol
            "gha_123456789g_123456789012345678901",  # Non-hex letter 'g'
            "gha_ABCDEF1234_123456789012345678901",  # Uppercase letters
        ]

        for key in invalid_keys:
            assert validate_api_key_format(key) is False


class TestAPIKeyVerification:
    """Test API key verification functionality."""

    def test_verify_api_key_with_salt_valid(self):
        """Test verification of valid API key with separate salt."""
        # Generate a key
        api_key, key_prefix, api_key_hash, salt = generate_api_key()

        # Verify it
        assert verify_api_key_with_salt(api_key, api_key_hash, salt) is True

    def test_verify_api_key_valid(self):
        """Test verification of valid API key (legacy format)."""
        # Generate a key with correct format
        api_key = "gha_1234567890_123456789012345678901"  # Exactly 36 chars
        api_key_hash = hash_api_key(api_key)

        # Verify it
        assert verify_api_key(api_key, api_key_hash) is True

    def test_verify_api_key_invalid_key(self):
        """Test verification fails with wrong key."""
        # Generate a key
        api_key, key_prefix, api_key_hash, salt = generate_api_key()

        # Try to verify with wrong key
        wrong_key = "gha_1111111111_111111111111111111111"
        assert verify_api_key_with_salt(wrong_key, api_key_hash, salt) is False

    def test_verify_api_key_invalid_format(self):
        """Test verification fails with invalid format."""
        # Generate a key
        _, _, api_key_hash, salt = generate_api_key()

        # Try to verify with invalid format
        invalid_key = "invalid_key"
        assert verify_api_key_with_salt(invalid_key, api_key_hash, salt) is False

    def test_verify_api_key_timing_safe(self):
        """Test that verification uses timing-safe comparison."""
        # This is implicitly tested by using secrets.compare_digest
        # Just ensure it works correctly
        api_key = "gha_1234567890_123456789012345678901"
        correct_hash = hash_api_key(api_key)

        # Create a wrong hash with the same salt but different key
        salt = correct_hash.split(":", 1)[0]
        wrong_key = "gha_1111111111_111111111111111111111"
        wrong_key_with_salt = f"{salt}:{wrong_key}".encode("utf-8")
        wrong_hash_value = hashlib.sha256(wrong_key_with_salt).hexdigest()
        wrong_hash = f"{salt}:{wrong_hash_value}"

        assert verify_api_key(api_key, correct_hash) is True
        assert verify_api_key(api_key, wrong_hash) is False
