"""Initial transactional record schema. schema_v1 is an immutable snapshot."""
from alembic import op
from app.db.schema_v1 import metadata
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    metadata.create_all(op.get_bind())


def downgrade():
    metadata.drop_all(op.get_bind())
