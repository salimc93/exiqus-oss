"""Tests for ConsentService functionality."""

import json
from datetime import datetime, timezone

import pytest

from github_analyzer.api.services.consent_service import (
    CURRENT_CONSENT_VERSION,
    ConsentService,
)
from github_analyzer.database.models import SubscriptionPlan, User


class TestConsentService:
    """Test ConsentService functionality."""

    @pytest.fixture
    def free_user(self):
        """Create a free tier user."""
        return User(
            user_id="test-free-user",
            email="free@test.com",
            full_name="Free User",
            subscription_plan=SubscriptionPlan.FREE,
            privacy_preferences=None,
            consent_version_accepted=None,
            consent_notice_dismissed_at=None,
        )

    @pytest.fixture
    def pro_user(self):
        """Create a professional tier user."""
        return User(
            user_id="test-pro-user",
            email="pro@test.com",
            full_name="Pro User",
            subscription_plan=SubscriptionPlan.PROFESSIONAL,
            privacy_preferences=None,
            consent_version_accepted=None,
            consent_notice_dismissed_at=None,
        )

    @pytest.fixture
    def enterprise_user(self):
        """Create an enterprise tier user."""
        return User(
            user_id="test-enterprise-user",
            email="enterprise@test.com",
            full_name="Enterprise User",
            subscription_plan=SubscriptionPlan.ENTERPRISE,
            privacy_preferences=json.dumps(
                {"training_usage": True, "anonymized": True}
            ),
            consent_version_accepted=CURRENT_CONSENT_VERSION,
            consent_notice_dismissed_at=datetime.now(timezone.utc),
        )

    def test_get_user_consent_free_tier_defaults(self, free_user):
        """Test that free tier users get correct default consent settings."""
        consent = ConsentService.get_user_consent(free_user)

        assert consent["training_usage"] is True  # Opt-in by default
        assert consent["anonymized"] is True
        assert consent["retention_period"] == "2_years"
        assert consent["third_party_sharing"] is False
        assert consent["tier"] == "FREE"
        assert consent["consent_version"] == CURRENT_CONSENT_VERSION

    def test_get_user_consent_pro_tier_defaults(self, pro_user):
        """Test that professional tier users get privacy-first defaults."""
        consent = ConsentService.get_user_consent(pro_user)

        assert consent["training_usage"] is False  # Opt-out by default
        assert consent["anonymized"] is False
        assert consent["retention_period"] == "5_years"
        assert consent["third_party_sharing"] is False
        assert consent["tier"] == "PROFESSIONAL"

    def test_get_user_consent_with_preferences(self, enterprise_user):
        """Test that user preferences override tier defaults."""
        consent = ConsentService.get_user_consent(enterprise_user)

        # User opted in to training despite enterprise defaults
        assert consent["training_usage"] is True
        assert consent["anonymized"] is True
        assert consent["tier"] == "ENTERPRISE"

    def test_should_show_consent_notice_free_tier(self, free_user):
        """Test consent notice visibility for free tier."""
        should_show = ConsentService.should_show_consent_notice(free_user)
        assert should_show is True  # Should show notice to new free users

    def test_should_show_consent_notice_dismissed(self, enterprise_user):
        """Test consent notice not shown when already dismissed."""
        should_show = ConsentService.should_show_consent_notice(enterprise_user)
        assert should_show is False

    def test_get_consent_notice_free_tier(self):
        """Test consent notice message for free tier."""
        notice = ConsentService.get_consent_notice(SubscriptionPlan.FREE)
        assert "anonymized analysis data helps improve" in notice
        assert "opt-out anytime" in notice

    def test_get_consent_notice_pro_tier(self):
        """Test consent notice message for professional tier."""
        notice = ConsentService.get_consent_notice(SubscriptionPlan.PROFESSIONAL)
        assert "private by default" in notice
        assert "choose to contribute" in notice

    def test_validate_consent_update_free_tier(self, free_user):
        """Test that free tier users can only update limited fields."""
        updates = {
            "training_usage": False,
            "analysis_storage": False,  # Should be filtered out
            "retention_period": "1_year",  # Should be filtered out
        }

        validated = ConsentService.validate_consent_update(free_user, updates)

        assert "training_usage" in validated
        assert validated["training_usage"] is False
        assert "analysis_storage" not in validated
        assert "retention_period" not in validated

    def test_validate_consent_update_pro_tier(self, pro_user):
        """Test that pro tier users can update all fields."""
        updates = {
            "training_usage": True,
            "anonymized": True,
            "retention_period": "3_years",
        }

        validated = ConsentService.validate_consent_update(pro_user, updates)

        assert validated == updates  # All updates allowed

    def test_create_consent_snapshot(self, free_user):
        """Test consent snapshot creation."""
        snapshot = ConsentService.create_consent_snapshot(free_user)

        assert snapshot["user_id"] == free_user.user_id
        assert "snapshot_date" in snapshot
        assert snapshot["training_usage"] is True
        assert snapshot["tier"] == "FREE"

    def test_should_allow_training_opt_in(self):
        """Test training allowance with opt-in consent."""
        consent = {
            "training_usage": True,
            "anonymized": True,
        }

        assert ConsentService.should_allow_training(consent) is True

    def test_should_allow_training_opt_out(self):
        """Test training not allowed with opt-out."""
        consent = {
            "training_usage": False,
            "anonymized": True,
        }

        assert ConsentService.should_allow_training(consent) is False

    def test_should_allow_training_not_anonymized(self):
        """Test training not allowed without anonymization."""
        consent = {
            "training_usage": True,
            "anonymized": False,
        }

        assert ConsentService.should_allow_training(consent) is False

    def test_get_retention_days_standard(self, free_user):
        """Test standard retention period calculation."""
        days = ConsentService.get_retention_days(free_user)
        assert days == 730  # 2 years

    def test_get_retention_days_custom(self):
        """Test custom retention period for enterprise."""
        enterprise_user = User(
            user_id="test-custom",
            email="custom@test.com",
            full_name="Custom User",
            subscription_plan=SubscriptionPlan.ENTERPRISE,
            privacy_preferences=json.dumps(
                {
                    "retention_period": "custom",
                    "custom_retention_days": 180,
                }
            ),
        )

        days = ConsentService.get_retention_days(enterprise_user)
        assert days == 180

    def test_get_retention_days_indefinite(self):
        """Test indefinite retention period."""
        user = User(
            user_id="test-indefinite",
            email="indefinite@test.com",
            full_name="Indefinite User",
            subscription_plan=SubscriptionPlan.ENTERPRISE,
            privacy_preferences=json.dumps({"retention_period": "indefinite"}),
        )

        days = ConsentService.get_retention_days(user)
        assert days == 36500  # ~100 years
