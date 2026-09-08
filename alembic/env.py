import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from logging.config import fileConfig

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from sqlmodel import SQLModel
from budget_app.models import Account, Envelope, EnvelopeCategory, Ledger, Transaction

load_dotenv()

config_url = os.getenv("DATABASE_URL")

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.get_x_argument(as_dictionary=True)
file_config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if file_config.config_file_name is not None:
    fileConfig(file_config.config_file_name)

if config_url:
    file_config.set_main_option("sqlalchemy.url", config_url)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = SQLModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def render_item(type_, obj, autogen_context):
    """Prevents linter errors by rendering SQLModel AutoString as sa.String()."""
    if type_ == "type" and obj.__class__.__module__.startswith("sqlmodel"):
        return "sa.String()"
    return False


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = file_config.get_main_option("sqlalchemy.url")
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
    connectable = engine_from_config(
        file_config.get_section(file_config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            render_item=render_item,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
