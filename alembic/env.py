"""Alembic environment configuration for Exiqus GitHub Analyzer."""

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, pool

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import your models
from src.github_analyzer.database.connection import Base  # noqa: E402
from src.github_analyzer.database.models import (  # noqa: E402, F401
    AnalysisResult,
    APIKey,
    APIUsageOverage,
    AuditLog,
    BatchAnalysis,
    BillingUsageRecord,
    ContactMessage,
    EmailVerificationToken,
    Invoice,
    PasswordResetToken,
    Payment,
    PRAnalysisRecord,
    PRAnalysisResult,
    SystemMetric,
    TokenBlacklist,
    UsageRecord,
    User,
    UserActivity,
    WebhookEvent,
)
from src.github_analyzer.database.models_portfolio import (  # noqa: E402, F401
    CandidateAssessment,
    PortfolioAnalysis,
)

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


# Get database URL from environment or config
def get_database_url():
    """Get database URL from environment variable or config file."""
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        # Railway and some other services use postgresql:// but SQLAlchemy needs postgresql+psycopg2://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        return database_url

    # Fallback to config file
    return config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = create_engine(
        configuration["sqlalchemy.url"],
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
