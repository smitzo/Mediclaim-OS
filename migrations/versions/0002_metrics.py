from alembic import op
import sqlalchemy as sa
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("http_metrics", sa.Column("key", sa.String(256), primary_key=True), sa.Column("count", sa.Integer(), nullable=False), sa.Column("latency_ms", sa.Float(), nullable=False))


def downgrade(): op.drop_table("http_metrics")
