"""
Alembic environment configuration
"""
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys
from dotenv import load_dotenv

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Загружаем переменные окружения
load_dotenv()

# Импортируем модели и Base
from database.connection import Base
from database.models import Ticket, Log  # noqa

# this is the Alembic Config object
config = context.config

# Интерпретируем файл конфигурации для логирования
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# URL базы данных из переменных окружения
database_url = os.getenv(
    "DATABASE_URL",
    "postgresql://support_user:support_password@localhost:5432/support_db"
)
config.set_main_option("sqlalchemy.url", database_url)

# target_metadata для 'autogenerate'
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
