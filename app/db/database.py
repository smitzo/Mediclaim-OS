from pathlib import Path
from contextlib import contextmanager
from sqlalchemy import create_engine, event, inspect
from app.db.schema_v1 import metadata


class Database:
    def __init__(self, url: str, initialize: bool = True):
        self.url = url
        if url.startswith("sqlite:///"):
            Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(url, pool_pre_ping=True, connect_args={"check_same_thread": False, "timeout": 30} if url.startswith("sqlite") else {})
        if url.startswith("sqlite"):
            @event.listens_for(self.engine, "connect")
            def configure(connection, _):
                connection.execute("PRAGMA foreign_keys=ON")
                connection.execute("PRAGMA busy_timeout=30000")
                connection.execute("PRAGMA journal_mode=WAL")
        if initialize:
            metadata.create_all(self.engine)

    @contextmanager
    def transaction(self):
        with self.engine.begin() as connection:
            if self.engine.dialect.name == "sqlite":
                connection.exec_driver_sql("BEGIN IMMEDIATE")
            yield connection

    def check(self):
        from sqlalchemy import text
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            if "jobs" not in inspect(connection).get_table_names():
                raise RuntimeError("Database migrations are required.")
