"""add roles and account_roles for admin authorization

Revision ID: e88b6036ee63
Revises: ac9ca50336fc
Create Date: 2026-06-30 06:58:56.931401
"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e88b6036ee63'
down_revision: Union[str, None] = 'ac9ca50336fc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'roles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('key', sa.Text(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key'),
    )

    op.create_table(
        'account_roles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('account_id', sa.UUID(), nullable=False),
        sa.Column('role_id', sa.UUID(), nullable=False),
        sa.Column('granted_by_account_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id']),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id']),
        sa.ForeignKeyConstraint(['granted_by_account_id'], ['accounts.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('account_id', 'role_id', name='uq_account_roles_account_role'),
    )
    op.create_index(op.f('ix_account_roles_account_id'), 'account_roles', ['account_id'], unique=False)
    op.create_index(op.f('ix_account_roles_role_id'), 'account_roles', ['role_id'], unique=False)

    # Seed exactly the 'admin' role. No account is granted it here — the
    # first admin must be created via scripts/grant_admin.py, run directly
    # by a human against the DB. There is deliberately no migration-time
    # or application-time auto-grant of admin to anyone.
    roles_table = sa.table(
        "roles",
        sa.column("id", sa.UUID), sa.column("key", sa.Text),
        sa.column("name", sa.Text),
    )
    op.bulk_insert(roles_table, [
        {"id": str(uuid.uuid4()), "key": "admin", "name": "Administrator"},
    ])


def downgrade() -> None:
    op.drop_index(op.f('ix_account_roles_role_id'), table_name='account_roles')
    op.drop_index(op.f('ix_account_roles_account_id'), table_name='account_roles')
    op.drop_table('account_roles')
    op.drop_table('roles')
