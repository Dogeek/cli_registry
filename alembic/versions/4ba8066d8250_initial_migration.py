"""Initial migration

Revision ID: 4ba8066d8250
Revises:
Create Date: 2022-07-28 10:03:23.010187

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4ba8066d8250'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'plugins',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(255), nullable=False),
    )

    op.create_table(
        'versions',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('upload_date', sa.DateTime, nullable=False),
        sa.Column('version', sa.String(20), nullable=False),
        sa.Column('plugin_id', sa.Integer, sa.ForeignKey('plugins.id')),
    )

    op.create_table(
        'maintainers',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('ssh_key', sa.String(400), nullable=False)
    )

    op.create_table(
        'plugins_maintainers_association',
        sa.Column("plugin_id", sa.Integer, sa.ForeignKey("plugins.id"), primary_key=True),
        sa.Column("maintainer_id", sa.Integer, sa.ForeignKey("maintainers.id"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table('plugins_maintainers_association')
    op.drop_table('plugins')
    op.drop_table('maintainers')
    op.drop_table('versions')
