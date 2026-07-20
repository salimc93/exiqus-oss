# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Admin CLI commands for GitHub Analyzer.

This module provides administrative commands for managing users,
setting custom limits, and monitoring system health.
"""

import typer

from ...database.connection import get_sync_db_session
from ...database.models import SubscriptionPlan, User
from ...utils.logging import get_logger

logger = get_logger(__name__)

# Create admin command group
admin = typer.Typer(help="Administrative commands for user and system management")


@admin.command()
def set_repo_limit(
    email: str = typer.Argument(..., help="User email address"),
    limit_mb: int = typer.Argument(..., help="Size limit in MB (1-10240)"),
    force: bool = typer.Option(
        False, "--force", "-", help="Force update even for non-enterprise users"
    ),
) -> None:
    """
    Set custom repository size limit for a user.

    This command allows administrators to set custom repository size limits
    for users, typically used for enterprise customers who need to analyze
    larger repositories.

    Examples:
        # Set 5GB limit for enterprise customer
        python -m github_analyzer.cli admin set-repo-limit enterprise@company.com 5120

        # Force set limit for non-enterprise user (not recommended)
        python -m github_analyzer.cli admin set-repo-limit user@company.com 2048 --force
    """
    # Validate limit range
    if limit_mb < 1 or limit_mb > 10240:
        typer.echo(
            "❌ Error: Size limit must be between 1 and 10240 MB (10GB)", err=True
        )
        raise typer.Exit(1)

    try:
        # Get database session
        with get_sync_db_session() as db:
            # Find user by email
            user = db.query(User).filter(User.email == email).first()
            if not user:
                typer.echo(f"❌ Error: User {email} not found", err=True)
                raise typer.Exit(1)

            # Check if user is enterprise (recommended but not enforced)
            if user.subscription_plan != SubscriptionPlan.ENTERPRISE and not force:
                typer.echo(
                    f"⚠️  Warning: User {email} has {user.subscription_plan.value} plan.",
                    err=True,
                )
                typer.echo("Custom limits are intended for Enterprise users.", err=True)
                typer.echo("Use --force to override this check.", err=True)
                raise typer.Exit(1)

            # Store old limit for logging
            old_limit = user.custom_repo_size_limit_mb

            # Update custom limit
            user.custom_repo_size_limit_mb = limit_mb
            db.commit()

            # Success output
            typer.echo(f"✅ Updated repo size limit for {email}")
            typer.echo(f"   Email: {user.email}")
            typer.echo(f"   Plan: {user.subscription_plan.value}")
            typer.echo(f"   Old limit: {old_limit or 'plan default'}")
            typer.echo(f"   New limit: {limit_mb}MB")

            # Log the action
            logger.info(
                f"CLI: Updated repo size limit for {email} from "
                f"{old_limit or 'plan default'} to {limit_mb}MB"
            )

    except Exception as e:
        typer.echo(f"❌ Failed to update repo size limit: {str(e)}", err=True)
        logger.error(f"Failed to update repo size limit for {email}: {e}")
        raise typer.Exit(1)


@admin.command()
def get_repo_limit(
    email: str = typer.Argument(..., help="User email address"),
) -> None:
    """
    Get current repository size limit for a user.

    Shows both the effective limit and the source (plan or custom).
    """
    try:
        with get_sync_db_session() as db:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                typer.echo(f"❌ Error: User {email} not found", err=True)
                raise typer.Exit(1)

            # Calculate effective limit
            if user.custom_repo_size_limit_mb is not None:
                effective_limit = user.custom_repo_size_limit_mb
                source = "custom"
            else:
                plan_limits = {
                    SubscriptionPlan.FREE: 50,
                    SubscriptionPlan.BASIC: 100,
                    SubscriptionPlan.PROFESSIONAL: 500,
                    SubscriptionPlan.ENTERPRISE: 1000,
                }
                effective_limit = plan_limits.get(user.subscription_plan, 50)
                source = "plan"

            # Display information
            typer.echo(f"📊 Repository size limit for {email}")
            typer.echo(f"   Plan: {user.subscription_plan.value}")
            typer.echo(f"   Effective limit: {effective_limit}MB")
            typer.echo(f"   Source: {source}")
            if user.custom_repo_size_limit_mb is not None:
                typer.echo(f"   Custom limit: {user.custom_repo_size_limit_mb}MB")

    except Exception as e:
        typer.echo(f"❌ Failed to get repo size limit: {str(e)}", err=True)
        raise typer.Exit(1)


@admin.command()
def list_custom_limits() -> None:
    """
    List all users with custom repository size limits.
    """
    try:
        with get_sync_db_session() as db:
            users_with_custom_limits = (
                db.query(User)
                .filter(User.custom_repo_size_limit_mb.isnot(None))
                .order_by(User.custom_repo_size_limit_mb.desc())
                .all()
            )

            if not users_with_custom_limits:
                typer.echo("📋 No users have custom repository size limits set.")
                return

            typer.echo(
                f"📋 Users with custom repository size limits ({len(users_with_custom_limits)}):"
            )
            typer.echo()

            for user in users_with_custom_limits:
                typer.echo(f"   {user.email}")
                typer.echo(f"     Plan: {user.subscription_plan.value}")
                typer.echo(f"     Custom limit: {user.custom_repo_size_limit_mb}MB")
                typer.echo()

    except Exception as e:
        typer.echo(f"❌ Failed to list custom limits: {str(e)}", err=True)
        raise typer.Exit(1)


@admin.command()
def clear_repo_limit(
    email: str = typer.Argument(..., help="User email address"),
    confirm: bool = typer.Option(
        False, "--confirm", help="Confirm the action without prompting"
    ),
) -> None:
    """
    Clear custom repository size limit for a user (revert to plan default).
    """
    try:
        with get_sync_db_session() as db:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                typer.echo(f"❌ Error: User {email} not found", err=True)
                raise typer.Exit(1)

            if user.custom_repo_size_limit_mb is None:
                typer.echo(f"ℹ️  User {email} does not have a custom limit set.")
                return

            # Confirm action
            if not confirm:
                current_limit = user.custom_repo_size_limit_mb
                plan_limits = {
                    SubscriptionPlan.FREE: 50,
                    SubscriptionPlan.BASIC: 100,
                    SubscriptionPlan.PROFESSIONAL: 500,
                    SubscriptionPlan.ENTERPRISE: 1000,
                }
                plan_limit = plan_limits.get(user.subscription_plan, 50)

                typer.echo(f"⚠️  About to clear custom limit for {email}")
                typer.echo(f"   Current limit: {current_limit}MB (custom)")
                typer.echo(f"   Will revert to: {plan_limit}MB (plan default)")

                if not typer.confirm("Continue?"):
                    typer.echo("❌ Operation cancelled.")
                    return

            # Clear custom limit
            old_limit = user.custom_repo_size_limit_mb
            user.custom_repo_size_limit_mb = None
            db.commit()

            typer.echo(f"✅ Cleared custom repo size limit for {email}")
            typer.echo(f"   Removed limit: {old_limit}MB")
            typer.echo(f"   Now using plan default for {user.subscription_plan.value}")

            # Log the action
            logger.info(
                f"CLI: Cleared custom repo size limit for {email} (was {old_limit}MB)"
            )

    except Exception as e:
        typer.echo(f"❌ Failed to clear repo size limit: {str(e)}", err=True)
        raise typer.Exit(1)


# Additional utility commands for admin use
@admin.command()
def user_info(
    email: str = typer.Argument(..., help="User email address"),
) -> None:
    """
    Display comprehensive information about a user.
    """
    try:
        with get_sync_db_session() as db:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                typer.echo(f"❌ Error: User {email} not found", err=True)
                raise typer.Exit(1)

            # Calculate effective repo limit
            if user.custom_repo_size_limit_mb is not None:
                repo_limit = f"{user.custom_repo_size_limit_mb}MB (custom)"
            else:
                plan_limits = {
                    SubscriptionPlan.FREE: 50,
                    SubscriptionPlan.BASIC: 100,
                    SubscriptionPlan.PROFESSIONAL: 500,
                    SubscriptionPlan.ENTERPRISE: 1000,
                }
                plan_limit = plan_limits.get(user.subscription_plan, 50)
                repo_limit = f"{plan_limit}MB (plan default)"

            # Display user information
            typer.echo(f"👤 User Information: {email}")
            typer.echo(f"   User ID: {user.user_id}")
            typer.echo(f"   Full Name: {user.full_name}")
            typer.echo(f"   Company: {user.company or 'Not specified'}")
            typer.echo(f"   Plan: {user.subscription_plan.value}")
            typer.echo(f"   Status: {user.subscription_status.value}")
            typer.echo(f"   Active: {'Yes' if user.is_active else 'No'}")
            typer.echo(f"   Verified: {'Yes' if user.is_verified else 'No'}")
            typer.echo(f"   Repo Size Limit: {repo_limit}")
            typer.echo(f"   Usage: {user.usage_count}/{user.usage_quota} this month")
            typer.echo(
                f"   Created: {user.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )

    except Exception as e:
        typer.echo(f"❌ Failed to get user info: {str(e)}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    admin()
