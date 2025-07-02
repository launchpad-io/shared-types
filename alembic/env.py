import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# Add your project to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

# Now import your models' Base
from app.db.base import Base

# Import ALL your models here so Alembic can see them
from app.models.user import PlatformUser
from app.models.creator import Creator, CreatorBadge

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# THIS IS THE IMPORTANT LINE - Set target_metadata
target_metadata = Base.metadata

# Get the custom version table name from alembic.ini
version_table = config.get_main_option("version_table", "alembic_version_shared_types")

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table=version_table,  # ADD THIS LINE
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            version_table=version_table,  # ADD THIS LINE
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()