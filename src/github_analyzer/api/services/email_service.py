# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Email service for sending transactional emails.

This module provides email sending functionality with support for
multiple backends (console for development, Resend for production).
"""

import os
from abc import ABC, abstractmethod
from typing import Optional

from ...utils.config import get_config
from ...utils.logging import get_logger

logger = get_logger(__name__)
config = get_config()


class EmailBackend(ABC):
    """Abstract base class for email backends."""

    @abstractmethod
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        from_email: Optional[str] = None,
    ) -> bool:
        """Send an email."""
        pass


class ConsoleEmailBackend(EmailBackend):
    """Email backend that prints to console (for development)."""

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        from_email: Optional[str] = None,
    ) -> bool:
        """Print email to console instead of sending."""
        from_email = from_email or os.getenv("EMAIL_FROM", "noreply@example.com")

        logger.info("=" * 80)
        logger.info("EMAIL (Console Backend)")
        logger.info("=" * 80)
        logger.info(f"From: {from_email}")
        logger.info(f"To: {to_email}")
        logger.info(f"Subject: {subject}")
        logger.info("-" * 80)
        if text_content:
            logger.info("Text Content:")
            logger.info(text_content)
            logger.info("-" * 80)
        logger.info("HTML Content:")
        logger.info(html_content)
        logger.info("=" * 80)

        # Also print to stdout for visibility
        print("\n" + "=" * 80)
        print("EMAIL (Console Backend)")
        print("=" * 80)
        print(f"From: {from_email}")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print("-" * 80)
        if text_content:
            print("Text Content:")
            print(text_content)
            print("-" * 80)
        print("HTML Content Preview:")
        # Extract just the text content from HTML for readability
        import re

        text_preview = re.sub("<[^<]+?>", "", html_content)
        print(text_preview[:500] + "..." if len(text_preview) > 500 else text_preview)
        print("=" * 80 + "\n")

        return True


class ResendEmailBackend(EmailBackend):
    """Email backend using Resend API."""

    def __init__(self) -> None:
        self.api_key = os.getenv("RESEND_API_KEY")
        if not self.api_key:
            logger.warning("RESEND_API_KEY not set, emails will not be sent")

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        from_email: Optional[str] = None,
    ) -> bool:
        """Send email via Resend API."""
        if not self.api_key:
            logger.error("Cannot send email: RESEND_API_KEY not configured")
            return False

        try:
            # Import resend only when needed
            import resend

            resend.api_key = self.api_key

            # Prepare email data
            email_data = {
                "from": from_email
                or os.getenv("EMAIL_FROM", "Exiqus <noreply@example.com>"),
                "to": [to_email],
                "subject": subject,
                "html": html_content,
            }

            if text_content:
                email_data["text"] = text_content

            # Send email - cast response to dict
            response = resend.Emails.send(email_data)  # type: ignore[arg-type]

            if response.get("id"):
                logger.info(
                    f"Email sent successfully to {to_email} (ID: {response['id']})"
                )
                return True
            else:
                logger.error(f"Failed to send email: {response}")
                return False

        except ImportError:
            logger.error(
                "Resend library not installed. Install with: pip install resend"
            )
            return False
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False


class EmailService:
    """Main email service that delegates to appropriate backend."""

    def __init__(self) -> None:
        # Determine which backend to use
        email_backend = os.getenv("EMAIL_BACKEND", "console")

        self.backend: EmailBackend
        if email_backend == "resend":
            self.backend = ResendEmailBackend()
        else:
            self.backend = ConsoleEmailBackend()

        logger.info(f"Using email backend: {self.backend.__class__.__name__}")

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        from_email: Optional[str] = None,
    ) -> bool:
        """Send email via configured backend."""
        return await self.backend.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            from_email=from_email,
        )

    async def send_password_reset_email(
        self, to_email: str, reset_url: str, user_name: Optional[str] = None
    ) -> bool:
        """Send password reset email."""
        subject = "Reset Your Exiqus Password"

        # Prepare greeting
        greeting = f"Hi {user_name}," if user_name else "Hi,"

        # Create email content with inline styles for Gmail compatibility
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 20px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333333; background-color: #f5f5f5;">
            <table role="presentation" style="width: 100%; max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <tr>
                    <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 30px; text-align: center;">
                        <h1 style="margin: 0; font-size: 32px; font-weight: 700; color: #ffffff; letter-spacing: 1px;">EXIQUS</h1>
                        <p style="margin: 8px 0 0 0; font-size: 14px; color: #ffffff; opacity: 0.95;">AI-Powered Developer Assessment Platform</p>
                    </td>
                </tr>
                <tr>
                    <td style="padding: 40px 30px; background-color: #f9fafb;">
                        <h2 style="margin: 0 0 20px 0; font-size: 24px; font-weight: 600; color: #1f2937;">Password Reset Request</h2>
                        <p style="margin: 0 0 16px 0; font-size: 16px; color: #374151;">{greeting}</p>
                        <p style="margin: 0 0 24px 0; font-size: 16px; color: #374151;">You requested to reset your password. Click the button below to create a new password:</p>
                        <table role="presentation" style="width: 100%; margin: 24px 0;">
                            <tr>
                                <td style="text-align: center;">
                                    <a href="{reset_url}" style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff; font-size: 16px; font-weight: 600; text-decoration: none; padding: 14px 32px; border-radius: 6px; box-shadow: 0 2px 4px rgba(102,126,234,0.4);">Reset Password</a>
                                </td>
                            </tr>
                        </table>
                        <p style="margin: 24px 0 8px 0; font-size: 14px; color: #6b7280;">Or copy and paste this link into your browser:</p>
                        <p style="margin: 0 0 24px 0; font-size: 13px; color: #667eea; word-break: break-all; background-color: #eff6ff; padding: 12px; border-radius: 6px; border-left: 3px solid #667eea;">{reset_url}</p>
                        <p style="margin: 0 0 16px 0; font-size: 15px; font-weight: 600; color: #dc2626;">⏱️ This link will expire in 1 hour for security reasons.</p>
                        <p style="margin: 0; font-size: 14px; color: #6b7280;">If you didn't request this password reset, please ignore this email. Your password won't be changed.</p>
                    </td>
                </tr>
                <tr>
                    <td style="padding: 30px; text-align: center; background-color: #ffffff; border-top: 1px solid #e5e7eb;">
                        <p style="margin: 0 0 8px 0; font-size: 13px; color: #9ca3af;">© 2025 Exiqus. All rights reserved.</p>
                        <p style="margin: 0; font-size: 13px; color: #9ca3af;">This is an automated email, please do not reply.</p>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """

        text_content = f"""
        Password Reset Request

        {greeting}

        You requested to reset your password. Visit this link to create a new password:

        {reset_url}

        This link will expire in 1 hour for security reasons.

        If you didn't request this password reset, please ignore this email. Your password won't be changed.

        © 2025 Exiqus. All rights reserved.
        """

        return await self.backend.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    async def send_welcome_email(self, to_email: str, user_name: str) -> bool:
        """Send welcome email to new users."""
        subject = "Welcome to Exiqus!"

        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: #f9fafb;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
                .feature {{
                    margin: 15px 0;
                    padding-left: 25px;
                }}
                .button {{
                    display: inline-block;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 12px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Welcome to EXIQUS!</h1>
            </div>
            <div class="content">
                <h2>Hi {user_name},</h2>
                <p>Welcome to Exiqus - The Insight Engine for Developer Hiring!</p>
                <p>You now have access to evidence-driven candidate intelligence from real code, not performance tests.</p>
                <p>With your free account, you can:</p>
                <ul>
                    <li class="feature">🔍 Gain insights into up to 10 developer candidates per month</li>
                    <li class="feature">🧠 Analyze real GitHub contributions and repositories</li>
                    <li class="feature">💡 Make confident, evidence-based hiring decisions</li>
                </ul>
                <div style="text-align: center;">
                    <a href="{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/dashboard" class="button">Start Getting Insights</a>
                </div>
                <p>Need more candidate insights? Check out our <a href="{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/pricing">pricing plans</a>.</p>
                <p style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 14px;">
                    <strong>AI-powered insight. Human-driven judgment.</strong>
                </p>
            </div>
        </body>
        </html>
        """

        text_content = """
        Welcome to Exiqus - The Insight Engine for Developer Hiring!

        Hi {user_name},

        You now have access to evidence-driven candidate intelligence from real code, not performance tests.

        With your free account, you can:
        - Gain insights into up to 10 developer candidates per month
        - Analyze real GitHub contributions and repositories
        - Make confident, evidence-based hiring decisions

        Start Getting Insights: {os.getenv('FRONTEND_URL', 'http://localhost:3000')}/dashboard

        Need more candidate insights? Check out our pricing plans.

        AI-powered insight. Human-driven judgment.
        """

        return await self.backend.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )


# Global email service instance
email_service = EmailService()
