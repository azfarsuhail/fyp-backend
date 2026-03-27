"""
Alembic Environment Configuration
----------------------------------
Connects Alembic to the same Neon DB engine used by the app,
and imports all models so autogenerate can detect schema changes.
"""

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Load .env so DATABASE_URL is available ────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

# ── Alembic Config object ────────────────────────────────────────────────────
config = context.config

# Override sqlalchemy.url with the env variable
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL", ""))

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Import ALL models so Alembic can detect them ─────────────────────────────
from app.core.config import Base
from app.models.user import User          # noqa: F401
from app.models.image import Image        # noqa: F401
from app.models.report import Report      # noqa: F401
from app.models.library import ExerciseVideo  # noqa: F401

target_metadata = Base.metadata


# ── Offline migrations (generate SQL without DB connection) ──────────────────
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online migrations (connect to Neon DB and apply) ─────────────────────────
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
