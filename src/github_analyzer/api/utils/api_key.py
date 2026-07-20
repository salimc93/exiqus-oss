# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""API key generation and validation utilities."""

import hashlib
import secrets
from typing import Tuple


def generate_api_key() -> Tuple[str, str, str, str]:
    """
    Generate a new API key with prefix, hash, and salt.

    Returns:
        Tuple[str, str, str, str]: (api_key, key_prefix, api_key_hash, salt)
        The api_key should be shown to the user once.
        The key_prefix, api_key_hash and salt should be stored in the database.

    API key format: gha_prefix123_secretpart456789012
    Total length: 36 chars (4 + 10 + 1 + 21)
    """
    # Generate a unique prefix for O(1) lookups (10 chars)
    # Use token_hex to avoid underscores in the output
    prefix = secrets.token_hex(5)[:10]  # 5 bytes = 10 hex chars

    # Generate the secret part (21 chars)
    # Use a combination to ensure exactly 21 chars without underscores
    secret = secrets.token_hex(11)[:21]  # 11 bytes = 22 hex chars, take 21

    # Combine into full API key
    api_key = f"gha_{prefix}_{secret}"

    # Generate a unique salt for this key
    salt = secrets.token_hex(16)  # 16 bytes = 128 bits of randomness

    # Hash the API key with the salt
    api_key_hash = hash_api_key_with_salt(api_key, salt)

    return api_key, prefix, api_key_hash, salt


def hash_api_key_with_salt(api_key: str, salt: str) -> str:
    """
    Hash an API key with a specific salt.

    Args:
        api_key: The plain text API key
        salt: The salt to use for hashing

    Returns:
        str: The hashed API key
    """
    # Use SHA-256 with the provided salt
    key_with_salt = f"{salt}:{api_key}".encode("utf-8")
    return hashlib.sha256(key_with_salt).hexdigest()


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for secure storage (legacy function for backwards compatibility).

    Args:
        api_key: The plain text API key

    Returns:
        str: The hashed API key with salt prefix (format: "salt:hash")
    """
    # Generate a random salt for this specific hash
    salt = secrets.token_hex(16)  # 16 bytes = 128 bits of randomness
    hash_value = hash_api_key_with_salt(api_key, salt)

    # Return salt and hash together for backwards compatibility
    return f"{salt}:{hash_value}"


def extract_key_prefix(api_key: str) -> str:
    """
    Extract the prefix from an API key for database lookup.

    Args:
        api_key: The full API key (format: gha_prefix123_secretpart)

    Returns:
        str: The prefix part or empty string if invalid format
    """
    if not api_key.startswith("gha_"):
        return ""

    # Split by underscore and get the prefix part
    parts = api_key.split("_", 2)
    # Must have exactly 3 parts: gha_prefix_secret
    if len(parts) == 3:
        return parts[1]  # Return the prefix

    return ""


def validate_api_key_format(api_key: str) -> bool:
    """
    Validate the format of an API key.

    Args:
        api_key: The API key to validate

    Returns:
        bool: True if the format is valid
    """
    # Check if it starts with "gha_" and has the right length
    if not api_key.startswith("gha_"):
        return False

    # Total length should be "gha_" (4) + prefix (10) + "_" (1) + secret (21) = 36
    if len(api_key) != 36:
        return False

    # Check format: gha_prefix_secret
    parts = api_key.split("_", 2)
    if len(parts) != 3:
        return False

    # Validate each part length
    if len(parts[1]) != 10 or len(parts[2]) != 21:
        return False

    # Check that all parts contain only valid hex characters (lowercase)
    valid_chars = set("abcdef0123456789")

    for part in [parts[1], parts[2]]:
        if not set(part).issubset(valid_chars):
            return False

    return True


def verify_api_key_with_salt(api_key: str, stored_hash: str, salt: str) -> bool:
    """
    Verify an API key against its stored hash using a separate salt.

    Args:
        api_key: The plain text API key provided by the user
        stored_hash: The hash stored in the database
        salt: The salt stored in the database

    Returns:
        bool: True if the API key is valid
    """
    if not validate_api_key_format(api_key):
        return False

    # Hash the provided key with the same salt
    provided_hash = hash_api_key_with_salt(api_key, salt)

    # Use timing-safe comparison
    return secrets.compare_digest(provided_hash, stored_hash)


def verify_api_key(api_key: str, stored_hash: str) -> bool:
    """
    Verify an API key against its stored hash (legacy function for backwards compatibility).

    Args:
        api_key: The plain text API key provided by the user
        stored_hash: The hash stored in the database (format: "salt:hash")

    Returns:
        bool: True if the API key is valid
    """
    if not validate_api_key_format(api_key):
        return False

    # Extract salt and hash from stored value
    try:
        salt, expected_hash = stored_hash.split(":", 1)
    except ValueError:
        # Invalid stored hash format
        return False

    # Use the new function with extracted salt
    return verify_api_key_with_salt(api_key, expected_hash, salt)
