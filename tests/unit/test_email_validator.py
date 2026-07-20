"""
Tests for email validation service.
"""

from src.github_analyzer.api.services.email_validator import EmailValidator


class TestEmailValidator:
    """Test email validation functionality."""

    def test_legitimate_personal_emails(self):
        """Test that personal emails from legitimate providers are accepted."""
        valid_emails = [
            "user@gmail.com",
            "person@yahoo.com",
            "contact@outlook.com",
            "test@hotmail.com",
            "user@icloud.com",
            "person@aol.com",
            "test@protonmail.com",
        ]

        for email in valid_emails:
            is_valid, error = EmailValidator.validate_email(email)
            assert is_valid is True, f"Failed for {email}: {error}"
            assert error == ""

    def test_legitimate_business_emails(self):
        """Test that business/corporate emails are accepted."""
        valid_emails = [
            "john@company.com",
            "admin@example.com",
            "contact@startup.io",
            "hr@bigcorp.org",
            "support@enterprise.net",
        ]

        for email in valid_emails:
            is_valid, error = EmailValidator.validate_email(email)
            assert is_valid is True, f"Failed for {email}: {error}"
            assert error == ""

    def test_disposable_emails_blocked(self):
        """Test that disposable/temporary emails are blocked."""
        disposable_emails = [
            "test@guerrillamail.com",
            "user@10minutemail.com",
            "temp@mailinator.com",
            "quick@yopmail.com",
            "test@temp-mail.org",
            "user@throwawaymail.com",  # Changed from throwaway.email
            "person@trashmail.com",
            "test@guerrillamail.net",
            "user@sharklasers.com",
            "test@spam4.me",
            "user@maildrop.cc",
            "test@tempemail.com",  # mozmail wasn't in list, using another temp service
        ]

        for email in disposable_emails:
            is_valid, error = EmailValidator.validate_email(email)
            assert is_valid is False, f"Should have blocked {email}"
            assert "Temporary or disposable email" in error
            assert (
                "Personal emails" in error
            )  # Check message mentions personal emails are ok

    def test_invalid_email_format(self):
        """Test that invalid email formats are rejected."""
        invalid_emails = [
            "notanemail",
            "missing@domain",
            "@nodomain.com",
            "no-at-sign.com",
            "spaces in@email.com",
            "",
            None,
        ]

        for email in invalid_emails:
            if email is not None:
                is_valid, error = EmailValidator.validate_email(email)
                assert is_valid is False
                assert error != ""

    def test_is_disposable_method(self):
        """Test the is_disposable method directly."""
        # Disposable domains
        assert EmailValidator.is_disposable("test@guerrillamail.com") is True
        assert EmailValidator.is_disposable("user@10minutemail.com") is True
        assert EmailValidator.is_disposable("temp@mailinator.com") is True

        # Legitimate domains
        assert EmailValidator.is_disposable("user@gmail.com") is False
        assert EmailValidator.is_disposable("admin@company.com") is False
        assert EmailValidator.is_disposable("test@outlook.com") is False

    def test_is_business_email(self):
        """Test business email detection."""
        # Business emails
        assert EmailValidator.is_business_email("admin@company.com") is True
        assert EmailValidator.is_business_email("hr@startup.io") is True
        assert EmailValidator.is_business_email("contact@enterprise.org") is True

        # Personal emails
        assert EmailValidator.is_business_email("user@gmail.com") is False
        assert EmailValidator.is_business_email("test@yahoo.com") is False
        assert EmailValidator.is_business_email("person@outlook.com") is False

        # Disposable emails (should not be considered business)
        assert EmailValidator.is_business_email("test@guerrillamail.com") is False

    def test_is_legitimate_email(self):
        """Test legitimate email check."""
        # Legitimate emails (both personal and business)
        assert EmailValidator.is_legitimate_email("user@gmail.com") is True
        assert EmailValidator.is_legitimate_email("admin@company.com") is True
        assert EmailValidator.is_legitimate_email("test@outlook.com") is True

        # Disposable emails
        assert EmailValidator.is_legitimate_email("test@guerrillamail.com") is False
        assert EmailValidator.is_legitimate_email("user@temp-mail.org") is False

    def test_get_domain(self):
        """Test domain extraction."""
        assert EmailValidator.get_domain("user@gmail.com") == "gmail.com"
        assert EmailValidator.get_domain("admin@company.org") == "company.org"
        assert (
            EmailValidator.get_domain("Test@GMAIL.COM") == "gmail.com"
        )  # Case insensitive
        assert EmailValidator.get_domain("notanemail") == ""
        assert EmailValidator.get_domain("") == ""

    def test_allow_disposable_flag(self):
        """Test that allow_disposable flag works."""
        disposable_email = "test@guerrillamail.com"

        # Default - disposable blocked
        is_valid, error = EmailValidator.validate_email(disposable_email)
        assert is_valid is False

        # Allow disposable
        is_valid, error = EmailValidator.validate_email(
            disposable_email, allow_disposable=True
        )
        assert is_valid is True
        assert error == ""
