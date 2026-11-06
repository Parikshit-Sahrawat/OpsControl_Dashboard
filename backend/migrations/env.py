from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.db.session import Base
from app.models import entities
from app.core.config import settings
import app.security.models
import app.worker.remote_models
import app.telemetry.models
import app.unified.models
import app.unified.pentaho_models
import app.registry.models
import app.data_pipelines.models
import app.etl_bindings.models
import app.native_incidents.models
import app.services.rule_models

config = context.config
# Use the same environment-configured database as FastAPI, not an outdated localhost URL.
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_migrations_offline():
    # Offline SQL cannot inspect/lock protected rows. Do not emit an unsafe
    # rollback script that would bypass the online populated-data guard.
    from app.db.etl_rollback import downgrade_plan

    try:
        start = context.get_starting_revision_argument()
        target = context.get_revision_argument()
    except KeyError:
        start = target = None
    if start and downgrade_plan(config, start, target):
        raise RuntimeError(
            "Offline ETL downgrade SQL is unsupported; run guarded online preflight against an isolated restored database"
        )
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, compare_type=True
        )
        with context.begin_transaction():
            from app.db.etl_rollback import protect_downgrade

            try:
                target = context.get_revision_argument()
            except KeyError:
                pass  # schema checks/autogeneration have no migration destination
            else:
                protect_downgrade(
                    connection,
                    config,
                    context.get_context().get_current_heads(),
                    target,
                )
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
