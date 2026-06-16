import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, insert, select
from sqlalchemy.exc import IntegrityError
from app.db.database import Database
from app.db.schema_v1 import tenants, users, memberships


def test_migration_and_rollback(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    config = Config("alembic.ini")
    url = f"sqlite:///{tmp_path}/migrate.db"
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    db = Database(url, initialize=False)
    db.check()
    assert "enqueue_outbox" in inspect(db.engine).get_table_names()
    command.downgrade(config, "base")
    assert "jobs" not in inspect(db.engine).get_table_names()


def test_failed_transaction_rolls_back(tmp_path):
    db = Database(f"sqlite:///{tmp_path}/test.db")
    with pytest.raises(IntegrityError), db.engine.begin() as connection:
        connection.execute(insert(tenants).values(id="a", name="Synthetic"))
        connection.execute(insert(memberships).values(tenant_id="a", username="missing", role="administrator"))
    with db.engine.connect() as connection:
        assert connection.execute(select(tenants)).first() is None
