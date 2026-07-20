"""
Tests for registration endpoint rate limiting to prevent abuse.

This module tests that account creation is properly rate-limited to prevent:
- Mass account creation from a single IP
- Bot registration attacks
- Email harvesting attempts
"""

from unittest.mock import patch

import pytest
from fastapi import status


@pytest.mark.asyncio
async def test_registration_hourly_rate_limit(async_client, test_db):
    """Test that registration is limited to 5 per hour per IP."""
    # Mock email service to avoid sending real emails
    with patch(
        "github_analyzer.api.services.email_service.EmailService.send_email"
    ) as mock_send:
        mock_send.return_value = True

        # Attempt to register 5 accounts (should all succeed)
        for i in range(5):
            response = await async_client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"test{i}@example.com",
                    "password": "SecurePass123!",
                    "full_name": f"Test User {i}",
                },
            )
            assert response.status_code == status.HTTP_201_CREATED, (
                f"Registration {i + 1} should succeed, got {response.status_code}: {response.json()}"
            )

        # 6th attempt should be rate limited
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "test6@example.com",
                "password": "SecurePass123!",
                "full_name": "Test User 6",
            },
        )
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        data = response.json()
        assert data["detail"]["error"] == "Rate limit exceeded"
        assert "5 per hour" in data["detail"]["message"], (
            "Should mention hourly limit in error message"
        )
        assert data["detail"]["limit"] == 5
        assert data["detail"]["endpoint"] == "registration"
        assert "Retry-After" in response.headers
        assert response.headers["Retry-After"] == "3600"


@pytest.mark.asyncio
async def test_registration_abuse_scenario(async_client, test_db):
    """
    Test realistic abuse scenario: attacker trying to create many accounts rapidly.

    This simulates a bot attempting to:
    1. Create 10 accounts in quick succession
    2. Verify that only 5 succeed (hourly limit)
    3. Verify appropriate error messages
    """
    with patch(
        "github_analyzer.api.services.email_service.EmailService.send_email"
    ) as mock_send:
        mock_send.return_value = True

        successful_registrations = 0
        rate_limited_count = 0

        # Attempt to rapidly create 10 accounts from same IP
        for i in range(10):
            response = await async_client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"bot_account_{i}@example.com",
                    "password": "BotPass123!",
                    "full_name": f"Bot Account {i}",
                },
            )

            if response.status_code == status.HTTP_201_CREATED:
                successful_registrations += 1
            elif response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                rate_limited_count += 1
                # Verify error details
                data = response.json()
                assert data["detail"]["error"] == "Rate limit exceeded"
                assert "prevent abuse" in data["detail"]["message"]

        # Verify rate limiting worked
        assert successful_registrations == 5, (
            f"Expected 5 successful registrations, got {successful_registrations}"
        )
        assert rate_limited_count == 5, (
            f"Expected 5 rate-limited attempts, got {rate_limited_count}"
        )

        print("\n✓ Abuse scenario test passed:")
        print(f"  - Successful registrations: {successful_registrations}/10")
        print(f"  - Rate limited requests: {rate_limited_count}/10")
        print("  - Hourly rate limit (5) successfully prevented mass account creation")


@pytest.mark.asyncio
async def test_registration_error_details(async_client, test_db):
    """Test that rate limit error provides helpful information to legitimate users."""
    with patch(
        "github_analyzer.api.services.email_service.EmailService.send_email"
    ) as mock_send:
        mock_send.return_value = True

        # Hit the rate limit
        for i in range(6):
            response = await async_client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"error_test{i}@example.com",
                    "password": "SecurePass123!",
                    "full_name": f"Error Test {i}",
                },
            )

        # Check last response (rate limited)
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        data = response.json()

        # Verify all required error fields are present
        assert "detail" in data
        detail = data["detail"]

        assert "error" in detail, "Should have error field"
        assert "message" in detail, "Should have human-readable message"
        assert "current_usage" in detail, "Should show current usage"
        assert "limit" in detail, "Should show the limit"
        assert "reset_in_seconds" in detail, "Should show when limit resets"
        assert "endpoint" in detail, "Should identify endpoint"

        # Verify message is helpful
        assert "prevent abuse" in detail["message"].lower(), (
            "Should explain why limit exists"
        )
        assert str(detail["limit"]) in detail["message"], (
            "Should mention the actual limit"
        )

        # Verify Retry-After header
        assert "Retry-After" in response.headers, "Should have Retry-After header"
