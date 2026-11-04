from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

import app.models  # noqa: F401 (enregistre tous les modèles dans Base.metadata)
from app.core.config import settings
from app.core.database import Base

# Configuration lue depuis alembic.ini
config = context.config

# Active les journaux (logs) définis dans alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Les tables que nos modèles décrivent : c'est le "plan" à comparer avec la base
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Mode hors ligne : écrit le SQL des migrations sans se connecter à la base."""
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Mode en ligne : se connecte à la base et applique les migrations."""
    connectable = create_engine(settings.database_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()