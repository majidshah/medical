"""add labs table and lab attribution on reference ranges

Revision ID: 9fefe2cf140c
Revises: e88b6036ee63
Create Date: 2026-06-30 11:06:51.688297

Adds `labs` (the diagnostic source a reference range came from, e.g. IDC)
as admin-editable reference data — not a hardcoded enum, per CLAUDE.md's
Reference data & roles rule. `lab_reference_ranges.lab_id` is nullable:
only ranges we can attribute with certainty get a lab_id; everything else
stays null rather than guessing (the eef39c9e1f7c seed predates any lab
attribution and is left unattributed).

Backfill: the IDC CSV (parsed via app.db.seeds.idc_loader.parse_idc_csv,
the same parser migration ea4260e45547 used to insert these exact rows)
is replayed to match each IDC-sourced range row by
(catalogue key, applies_to, notes) — the same fields that made the row
unique at insert time — and set its lab_id. Every row the CSV produced
must match exactly one existing range; a mismatch means the catalogue
has drifted since seeding and the migration aborts rather than silently
attributing the wrong row.
"""

import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.db.seeds.idc_loader import parse_idc_csv


revision: str = "9fefe2cf140c"
down_revision: Union[str, None] = "e88b6036ee63"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

IDC_LAB_KEY = "idc"
IDC_LAB_NAME = "IDC"


def upgrade() -> None:
    op.create_table(
        "labs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.add_column("lab_reference_ranges", sa.Column("lab_id", sa.UUID(), nullable=True))
    op.create_index(
        op.f("ix_lab_reference_ranges_lab_id"), "lab_reference_ranges", ["lab_id"], unique=False
    )
    op.create_foreign_key(
        "fk_lab_reference_ranges_lab_id", "lab_reference_ranges", "labs", ["lab_id"], ["id"]
    )

    conn = op.get_bind()

    idc_id = uuid.uuid4()
    conn.execute(
        sa.text("INSERT INTO labs (id, key, name, is_active) VALUES (:id, :key, :name, true)"),
        {"id": str(idc_id), "key": IDC_LAB_KEY, "name": IDC_LAB_NAME},
    )

    parsed = parse_idc_csv()
    unmatched: list[str] = []
    for row in parsed.range_rows:
        result = conn.execute(
            sa.text(
                """
                UPDATE lab_reference_ranges
                SET lab_id = :lab_id
                WHERE applies_to = :applies_to
                  AND notes IS NOT DISTINCT FROM :notes
                  AND test_id = (SELECT id FROM lab_test_catalogue WHERE key = :test_key)
                """
            ),
            {
                "lab_id": str(idc_id),
                "applies_to": row.applies_to,
                "notes": row.notes,
                "test_key": row.test_key,
            },
        )
        if result.rowcount != 1:
            unmatched.append(f"{row.test_key}/{row.applies_to} (matched {result.rowcount})")

    if unmatched:
        raise RuntimeError(
            f"IDC lab-attribution backfill did not cleanly match existing rows: {unmatched}"
        )


def downgrade() -> None:
    op.drop_constraint("fk_lab_reference_ranges_lab_id", "lab_reference_ranges", type_="foreignkey")
    op.drop_index(op.f("ix_lab_reference_ranges_lab_id"), table_name="lab_reference_ranges")
    op.drop_column("lab_reference_ranges", "lab_id")
    op.drop_table("labs")
