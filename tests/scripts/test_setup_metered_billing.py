"""
Test suite for metered billing setup script.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.setup_metered_billing import setup_metered_billing


@pytest.mark.asyncio
async def test_setup_metered_billing_success():
    """Test successful setup of metered billing."""
    with patch("scripts.setup_metered_billing.StripeClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.is_configured = True

        # Use AsyncMock for the async method
        mock_client.create_metered_billing_prices = AsyncMock(
            return_value={
                "professional": "price_prof_overage",
                "enterprise": "price_ent_overage",
            }
        )
        mock_client_class.return_value = mock_client

        result = await setup_metered_billing()

        assert result is True
        # Verify the async method was properly awaited
        mock_client.create_metered_billing_prices.assert_awaited_once()


@pytest.mark.asyncio
async def test_setup_metered_billing_not_configured():
    """Test setup when Stripe is not configured."""
    with patch("scripts.setup_metered_billing.StripeClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.is_configured = False
        mock_client_class.return_value = mock_client

        result = await setup_metered_billing()

        assert result is False
        mock_client.create_metered_billing_prices.assert_not_called()


@pytest.mark.asyncio
async def test_setup_metered_billing_error():
    """Test setup with error handling."""
    with patch("scripts.setup_metered_billing.StripeClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.is_configured = True

        # Use AsyncMock with side_effect for exception
        mock_client.create_metered_billing_prices = AsyncMock(
            side_effect=Exception("API error")
        )
        mock_client_class.return_value = mock_client

        result = await setup_metered_billing()

        assert result is False
        # Verify the async method was attempted
        mock_client.create_metered_billing_prices.assert_awaited_once()
