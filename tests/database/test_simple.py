"""
Simple test for database operations to validate setup.

This module provides a minimal test to ensure database models and operations work.
"""

import pytest

# datetime imports removed - not needed for this test
from github_analyzer.database.operations import UserOperations


@pytest.mark.asyncio
async def test_database_connection(test_db):
    """Test basic database connection and user creation."""
    # Test operations
    async with test_db() as session:
        try:
            # Create user
            user = await UserOperations.create_user(
                session,
                email="test@example.com",
                password="secure_password123",
                full_name="Test User",
                company="Test Corp",
            )

            # Verify user creation
            assert user.user_id.startswith("usr_")
            assert user.email == "test@example.com"
            assert user.full_name == "Test User"
            assert user.company == "Test Corp"
            assert user.is_active is True
            assert user.is_verified is False
            assert user.usage_quota == 100
            assert user.usage_count == 0
            assert user.password_hash != "secure_password123"  # Should be hashed

            # Test user lookup
            found_user = await UserOperations.get_user_by_email(
                session, "test@example.com"
            )
            assert found_user is not None
            assert found_user.user_id == user.user_id

            # Test authentication
            auth_user = await UserOperations.authenticate_user(
                session, "test@example.com", "secure_password123"
            )
            assert auth_user is not None
            assert auth_user.user_id == user.user_id

            # Test wrong password
            wrong_auth = await UserOperations.authenticate_user(
                session, "test@example.com", "wrong_password"
            )
            assert wrong_auth is None

            await session.commit()

        except Exception:
            await session.rollback()
            raise


@pytest.mark.asyncio
async def test_duplicate_email_error(test_db):
    """Test that duplicate emails are handled correctly."""
    # Test operations
    async with test_db() as session:
        try:
            # Create first user
            user1 = await UserOperations.create_user(
                session,
                email="duplicate@example.com",
                password="password1",
                full_name="First User",
            )
            assert user1 is not None

            # Try to create second user with same email
            with pytest.raises(ValueError, match="Email address already registered"):
                await UserOperations.create_user(
                    session,
                    email="duplicate@example.com",
                    password="password2",
                    full_name="Second User",
                )

            await session.commit()

        except Exception:
            await session.rollback()
            raise
