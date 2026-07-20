# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Email validation service with disposable email detection.

Uses disposable-email-domains package for up-to-date detection.
"""

import re
from typing import Tuple

import disposable_email_domains


class EmailValidator:
    """Service for comprehensive email validation including disposable detection."""

    @staticmethod
    def is_disposable(email: str) -> bool:
        """
        Check if an email address is from a disposable email provider.

        Args:
            email: Email address to check

        Returns:
            True if email is disposable, False otherwise
        """
        if not email or "@" not in email:
            return False

        # Extract domain from email
        domain = email.lower().split("@")[-1]

        # Check against the disposable domains list
        return domain in disposable_email_domains.blocklist

    @staticmethod
    def validate_email_format(email: str) -> bool:
        """
        Validate basic email format.

        Args:
            email: Email address to validate

        Returns:
            True if format is valid, False otherwise
        """
        if not email or "@" not in email:
            return False

        # Basic email format validation
        email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

        return bool(email_pattern.match(email))

    @staticmethod
    def validate_email(email: str, allow_disposable: bool = False) -> Tuple[bool, str]:
        """
        Validate email address with optional disposable email blocking.

        Allows both personal (Gmail, Outlook, Yahoo, etc.) and business emails.
        Only blocks temporary/disposable email services.

        Args:
            email: Email address to validate
            allow_disposable: Whether to allow disposable emails (default False)

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not email:
            return False, "Email address is required"

        # Check format
        if not EmailValidator.validate_email_format(email):
            return False, "Invalid email format"

        # Check if disposable (unless explicitly allowed)
        # This ONLY blocks temp emails - personal & business emails are fine
        if not allow_disposable and EmailValidator.is_disposable(email):
            return False, (
                "Temporary or disposable email addresses are not allowed. "
                "Please use a permanent email address. "
                "Personal emails (Gmail, Yahoo, Outlook, etc.) and business emails are welcome."
            )

        return True, ""

    @staticmethod
    def get_domain(email: str) -> str:
        """
        Extract domain from email address.

        Args:
            email: Email address

        Returns:
            Domain part of email or empty string
        """
        if not email or "@" not in email:
            return ""

        return email.lower().split("@")[-1]

    @staticmethod
    def is_business_email(email: str) -> bool:
        """
        Check if email appears to be a business/corporate email.

        Args:
            email: Email address to check

        Returns:
            True if likely business email, False if personal provider
        """
        personal_providers = {
            "gmail.com",
            "yahoo.com",
            "outlook.com",
            "hotmail.com",
            "aol.com",
            "icloud.com",
            "mail.com",
            "protonmail.com",
            "yandex.com",
            "mail.ru",
        }

        domain = EmailValidator.get_domain(email)
        return (
            domain not in personal_providers
            and domain not in disposable_email_domains.blocklist
        )

    @staticmethod
    def is_legitimate_email(email: str) -> bool:
        """
        Check if email is legitimate (not disposable).
        Accepts both personal (Gmail, Yahoo, etc.) and business emails.

        Args:
            email: Email address to check

        Returns:
            True if email is legitimate (personal or business), False if disposable
        """
        is_valid, _ = EmailValidator.validate_email(email, allow_disposable=False)
        return is_valid
