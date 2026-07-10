from sqlalchemy import MetaData, Table, Column, String, Integer, Float
metadata = MetaData()
http_metrics = Table("http_metrics", metadata, Column("key", String(256), primary_key=True), Column("count", Integer, nullable=False), Column("latency_ms", Float, nullable=False))
