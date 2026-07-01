"""add lab departments and panels hierarchy

Revision ID: ac9ca50336fc
Revises: ea4260e45547
Create Date: 2026-06-30 06:10:58.842890
"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.db.seeds.lab_hierarchy import DEPARTMENTS, test_key_to_department_panel


revision: str = 'ac9ca50336fc'
down_revision: Union[str, None] = 'ea4260e45547'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'lab_departments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('key', sa.Text(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key'),
    )

    op.create_table(
        'lab_panels',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('department_id', sa.UUID(), nullable=False),
        sa.Column('key', sa.Text(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['department_id'], ['lab_departments.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('department_id', 'key', name='uq_lab_panels_department_id_key'),
        sa.UniqueConstraint('department_id', 'id', name='uq_lab_panels_department_id_id'),
    )
    op.create_index(op.f('ix_lab_panels_department_id'), 'lab_panels', ['department_id'], unique=False)

    op.add_column('lab_test_catalogue', sa.Column('department_id', sa.UUID(), nullable=True))
    op.add_column('lab_test_catalogue', sa.Column('panel_id', sa.UUID(), nullable=True))
    op.create_index(
        op.f('ix_lab_test_catalogue_department_id'), 'lab_test_catalogue', ['department_id'], unique=False
    )
    op.create_index(
        op.f('ix_lab_test_catalogue_panel_id'), 'lab_test_catalogue', ['panel_id'], unique=False
    )
    op.create_foreign_key(
        'fk_lab_test_catalogue_department_id', 'lab_test_catalogue', 'lab_departments',
        ['department_id'], ['id'],
    )
    # Composite FK: a test's panel must belong to the test's own
    # department. Postgres skips a multi-column FK check when ANY
    # referencing column is NULL, so this is a no-op for standalone
    # tests (panel_id IS NULL) and fully enforced once a panel is set.
    op.create_foreign_key(
        'fk_lab_test_catalogue_panel_matches_department', 'lab_test_catalogue', 'lab_panels',
        ['department_id', 'panel_id'], ['department_id', 'id'],
    )

    # Seed the hierarchy and backfill every pre-existing catalogue row
    # (the 8 original tests + the 41 IDC-seeded tests) into it. See
    # app/db/seeds/lab_hierarchy.py for the mapping — single source of
    # truth shared with tests/conftest.py.
    conn = op.get_bind()

    dept_table = sa.table(
        "lab_departments",
        sa.column("id", sa.UUID), sa.column("key", sa.Text), sa.column("name", sa.Text),
        sa.column("display_order", sa.Integer), sa.column("is_active", sa.Boolean),
    )
    panel_table = sa.table(
        "lab_panels",
        sa.column("id", sa.UUID), sa.column("department_id", sa.UUID),
        sa.column("key", sa.Text), sa.column("name", sa.Text),
        sa.column("display_order", sa.Integer), sa.column("is_active", sa.Boolean),
    )

    dept_ids: dict[str, uuid.UUID] = {}
    panel_ids: dict[tuple[str, str], uuid.UUID] = {}

    for dept_order, dept in enumerate(DEPARTMENTS):
        did = uuid.uuid4()
        dept_ids[dept.key] = did
        conn.execute(
            dept_table.insert().values(
                id=did, key=dept.key, name=dept.name, display_order=dept_order, is_active=True
            )
        )
        for panel_order, panel in enumerate(dept.panels):
            pid = uuid.uuid4()
            panel_ids[(dept.key, panel.key)] = pid
            conn.execute(
                panel_table.insert().values(
                    id=pid, department_id=did, key=panel.key, name=panel.name,
                    display_order=panel_order, is_active=True,
                )
            )

    unmapped: list[str] = []
    for test_key, (dept_key, panel_key) in test_key_to_department_panel().items():
        did = dept_ids[dept_key]
        pid = panel_ids[(dept_key, panel_key)] if panel_key else None
        result = conn.execute(
            sa.text("UPDATE lab_test_catalogue SET department_id = :did, panel_id = :pid WHERE key = :key"),
            {"did": str(did), "pid": str(pid) if pid else None, "key": test_key},
        )
        if result.rowcount == 0:
            unmapped.append(test_key)

    if unmapped:
        raise RuntimeError(
            f"lab_hierarchy mapping references catalogue keys that don't exist: {unmapped}"
        )

    remaining = conn.execute(
        sa.text("SELECT key FROM lab_test_catalogue WHERE department_id IS NULL")
    ).fetchall()
    if remaining:
        raise RuntimeError(
            f"catalogue rows left without a department after backfill: {[r[0] for r in remaining]}"
        )

    op.alter_column('lab_test_catalogue', 'department_id', nullable=False)


def downgrade() -> None:
    op.drop_constraint(
        'fk_lab_test_catalogue_panel_matches_department', 'lab_test_catalogue', type_='foreignkey'
    )
    op.drop_constraint('fk_lab_test_catalogue_department_id', 'lab_test_catalogue', type_='foreignkey')
    op.drop_index(op.f('ix_lab_test_catalogue_panel_id'), table_name='lab_test_catalogue')
    op.drop_index(op.f('ix_lab_test_catalogue_department_id'), table_name='lab_test_catalogue')
    op.drop_column('lab_test_catalogue', 'panel_id')
    op.drop_column('lab_test_catalogue', 'department_id')

    op.drop_index(op.f('ix_lab_panels_department_id'), table_name='lab_panels')
    op.drop_table('lab_panels')
    op.drop_table('lab_departments')
