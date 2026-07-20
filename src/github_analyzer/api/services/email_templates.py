# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Email templates for transactional emails.

Provides HTML and text templates for various email types.
"""

from typing import Optional


def verification_email_template(
    user_name: str, verification_link: str, expires_in_hours: int = 24
) -> tuple[str, str]:
    """
    Generate email verification template.

    Returns:
        tuple: (html_content, text_content)
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Verify Your Email - Exiqus</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                background-color: #f5f5f5;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 600px;
                margin: 40px auto;
                background-color: #ffffff;
                padding: 0;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 40px 30px;
                text-align: center;
                border-radius: 8px 8px 0 0;
            }}
            .header h1 {{
                margin: 0;
                font-size: 28px;
                font-weight: 600;
            }}
            .content {{
                padding: 40px 30px;
            }}
            .button {{
                display: inline-block;
                padding: 14px 32px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                text-decoration: none;
                border-radius: 6px;
                font-weight: 600;
                margin: 20px 0;
            }}
            .button:hover {{
                opacity: 0.9;
            }}
            .footer {{
                padding: 20px 30px;
                text-align: center;
                color: #666;
                font-size: 14px;
                border-top: 1px solid #eee;
            }}
            .warning {{
                background-color: #fff3cd;
                border: 1px solid #ffeaa7;
                color: #856404;
                padding: 12px;
                border-radius: 4px;
                margin: 20px 0;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <img src="{logo_url}" alt="Exiqus Logo" style="height: 60px; width: auto; margin-bottom: 15px; opacity: 0.9;" />
                <h1 style="font-size: 32px; letter-spacing: 1px; margin-bottom: 10px;">EXIQUS</h1>
                <p style="margin: 0; font-size: 18px; opacity: 0.9;">Verify Your Email Address</p>
            </div>
            <div class="content">
                <p>Hi {user_name},</p>

                <p>Thanks for signing up for Exiqus! Please verify your email address to activate your account and start assessing developer candidates through their GitHub portfolios and pull requests.</p>

                <div style="text-align: center;">
                    <a href="{verification_link}" class="button">Verify Email Address</a>
                </div>

                <div class="warning">
                    ⏰ This link will expire in {expires_in_hours} hours for security reasons.
                </div>

                <p>If you didn't create an account with Exiqus, please ignore this email.</p>

                <p>Having trouble with the button? Copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #667eea;">{verification_link}</p>
            </div>
            <div class="footer">
                <p>© 2025 Exiqus. All rights reserved.</p>
                <p>AI-Powered Developer Assessment Platform</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_content = """
Welcome to Exiqus!

Hi {user_name},

Thanks for signing up for Exiqus! Please verify your email address to activate your account and start assessing developer candidates through their GitHub portfolios and pull requests.

Verify your email by clicking this link:
{verification_link}

This link will expire in {expires_in_hours} hours for security reasons.

If you didn't create an account with Exiqus, please ignore this email.

Best regards,
The Exiqus Team

© 2025 Exiqus. All rights reserved.
    """

    import os

    logo_url = os.getenv("FRONTEND_URL", "http://localhost:3000") + "/exiqus-logo.png"

    return html_content.format(
        user_name=user_name,
        verification_link=verification_link,
        expires_in_hours=expires_in_hours,
        logo_url=logo_url,
    ), text_content.format(
        user_name=user_name,
        verification_link=verification_link,
        expires_in_hours=expires_in_hours,
    )


def welcome_email_template(
    user_name: str, frontend_url: Optional[str] = None
) -> tuple[str, str]:
    """
    Generate welcome email template (sent after verification).

    Returns:
        tuple: (html_content, text_content)
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Welcome to Exiqus!</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                background-color: #f5f5f5;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 600px;
                margin: 40px auto;
                background-color: #ffffff;
                padding: 0;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 40px 30px;
                text-align: center;
                border-radius: 8px 8px 0 0;
            }}
            .header h1 {{
                margin: 0;
                font-size: 28px;
                font-weight: 600;
            }}
            .content {{
                padding: 40px 30px;
            }}
            .feature {{
                margin: 20px 0;
                padding: 15px;
                background-color: #f8f9fa;
                border-radius: 6px;
            }}
            .button {{
                display: inline-block;
                padding: 14px 32px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                text-decoration: none;
                border-radius: 6px;
                font-weight: 600;
                margin: 20px 0;
            }}
            .footer {{
                padding: 20px 30px;
                text-align: center;
                color: #666;
                font-size: 14px;
                border-top: 1px solid #eee;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <img src="{logo_url}" alt="Exiqus Logo" style="height: 60px; width: auto; margin-bottom: 15px; opacity: 0.9;" />
                <h1 style="font-size: 32px; letter-spacing: 1px; margin-bottom: 10px;">EXIQUS</h1>
                <p style="margin: 0; font-size: 18px; opacity: 0.9;">Welcome to Your AI-Powered Developer Assessment Platform</p>
            </div>
            <div class="content">
                <p>Hi {user_name},</p>

                <p>Your email has been verified! You're all set to start using Exiqus for evidence-based developer hiring.</p>

                <h3>Here's what you can do now:</h3>

                <div class="feature">
                    <strong>👤 Assess Candidates</strong><br>
                    Enter a GitHub username to analyse complete developer portfolios, PR contributions, and repository deep dives—all in one comprehensive candidate assessment.
                </div>

                <div class="feature">
                    <strong>📊 Context-Aware Insights</strong><br>
                    Tailor assessments for your hiring context: Startup, Enterprise, Agency, or Open Source—and select the role level (Junior, Mid, or Senior).
                </div>

                <div class="feature">
                    <strong>🎯 Evidence Over Guesswork</strong><br>
                    Get factual, objective insights grounded in real code and observable work patterns. No scores, no grades—just facts about real work.
                </div>

                <div style="text-align: center;">
                    <a href="{frontend_url}/dashboard" class="button">Go to Dashboard</a>
                </div>

                <p>Want to learn more about our approach? Check out <a href="{frontend_url}/methodology">our methodology</a> or discover <a href="{frontend_url}/why">why teams choose Exiqus</a>.</p>

                <p>Need help? <a href="{frontend_url}/contact">Contact our support team</a> anytime.</p>
            </div>
            <div class="footer">
                <p>© 2025 Exiqus. All rights reserved.</p>
                <p>AI-Powered Developer Assessment Platform</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_content = """
Welcome to Exiqus!

Hi {user_name},

Your email has been verified! You're all set to start using Exiqus for evidence-based developer hiring.

Here's what you can do now:

👤 Assess Candidates
Enter a GitHub username to analyse complete developer portfolios, PR contributions, and repository deep dives—all in one comprehensive candidate assessment.

📊 Context-Aware Insights
Tailor assessments for your hiring context: Startup, Enterprise, Agency, or Open Source—and select the role level (Junior, Mid, or Senior).

🎯 Evidence Over Guesswork
Get factual, objective insights grounded in real code and observable work patterns. No scores, no grades—just facts about real work.

Get started: {frontend_url}/dashboard

Want to learn more? Check out our methodology at {frontend_url}/methodology or discover why teams choose Exiqus at {frontend_url}/why.

Need help? Contact our support team at {frontend_url}/contact.

Best regards,
The Exiqus Team

© 2025 Exiqus. All rights reserved.
    """

    import os

    if not frontend_url:
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

    logo_url = f"{frontend_url}/exiqus-logo.png"

    return html_content.format(
        user_name=user_name, frontend_url=frontend_url, logo_url=logo_url
    ), text_content.format(user_name=user_name, frontend_url=frontend_url)


def resend_verification_email_template(
    user_name: str, verification_link: str, expires_in_hours: int = 24
) -> tuple[str, str]:
    """
    Generate resend verification email template.

    Returns:
        tuple: (html_content, text_content)
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>New Verification Link - Exiqus</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                background-color: #f5f5f5;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 600px;
                margin: 40px auto;
                background-color: #ffffff;
                padding: 0;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 40px 30px;
                text-align: center;
                border-radius: 8px 8px 0 0;
            }}
            .content {{
                padding: 40px 30px;
            }}
            .button {{
                display: inline-block;
                padding: 14px 32px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                text-decoration: none;
                border-radius: 6px;
                font-weight: 600;
                margin: 20px 0;
            }}
            .warning {{
                background-color: #fff3cd;
                border: 1px solid #ffeaa7;
                color: #856404;
                padding: 12px;
                border-radius: 4px;
                margin: 20px 0;
                font-size: 14px;
            }}
            .footer {{
                padding: 20px 30px;
                text-align: center;
                color: #666;
                font-size: 14px;
                border-top: 1px solid #eee;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <img src="{logo_url}" alt="Exiqus Logo" style="height: 60px; width: auto; margin-bottom: 15px; opacity: 0.9;" />
                <h1 style="font-size: 32px; letter-spacing: 1px; margin-bottom: 10px;">EXIQUS</h1>
                <p style="margin: 0; font-size: 18px; opacity: 0.9;">New Verification Link</p>
            </div>
            <div class="content">
                <p>Hi {user_name},</p>

                <p>You requested a new email verification link. Here it is!</p>

                <div style="text-align: center;">
                    <a href="{verification_link}" class="button">Verify Email Address</a>
                </div>

                <div class="warning">
                    ⏰ This link will expire in {expires_in_hours} hours. Your previous verification links have been invalidated.
                </div>

                <p>If you didn't request this, please ignore this email.</p>

                <p>Having trouble? Copy and paste this link:</p>
                <p style="word-break: break-all; color: #667eea;">{verification_link}</p>
            </div>
            <div class="footer">
                <p>© 2025 Exiqus. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_content = """
New Verification Link - Exiqus

Hi {user_name},

You requested a new email verification link. Here it is!

Verify your email by clicking this link:
{verification_link}

This link will expire in {expires_in_hours} hours. Your previous verification links have been invalidated.

If you didn't request this, please ignore this email.

Best regards,
The Exiqus Team

© 2025 Exiqus. All rights reserved.
    """

    import os

    logo_url = os.getenv("FRONTEND_URL", "http://localhost:3000") + "/exiqus-logo.png"

    return html_content.format(
        user_name=user_name,
        verification_link=verification_link,
        expires_in_hours=expires_in_hours,
        logo_url=logo_url,
    ), text_content.format(
        user_name=user_name,
        verification_link=verification_link,
        expires_in_hours=expires_in_hours,
    )
