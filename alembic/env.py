from sqlalchemy import engine_from_config, pool
from alembic import context
from logging.config import fileConfig
import sys, os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# import your Base here
from core.database import Base  # <- Base.metadata
from models import models       # <- import all models

config = context.config
config.set_main_option(
    "sqlalchemy.url", "postgresql+psycopg2://postgres:12345@localhost:5432/won"
)
fileConfig(config.config_file_name)
target_metadata = Base.metadata  # Alembic uses this to autogenerate

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

run_migrations_online()


