"""phase a retirement planning file foundation

Revision ID: 3d2f8a7b4c19
Revises: 9a6f3b8c21de
Create Date: 2026-06-24 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3d2f8a7b4c19"
down_revision: Union[str, None] = "9a6f3b8c21de"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.add_column("client_profiles", sa.Column("contact_method", sa.String(length=64), nullable=True))
        op.add_column("client_profiles", sa.Column("contact_details", sa.String(length=255), nullable=True))
        return

    with op.batch_alter_table("client_profiles") as batch_op:
        batch_op.add_column(sa.Column("contact_method", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("contact_details", sa.String(length=255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("client_profiles") as batch_op:
        batch_op.drop_column("contact_details")
        batch_op.drop_column("contact_method")
