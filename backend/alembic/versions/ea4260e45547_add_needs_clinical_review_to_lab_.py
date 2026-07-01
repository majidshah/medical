"""add needs_clinical_review to lab_reference_ranges and seed idc catalogue

Revision ID: ea4260e45547
Revises: 580c730a890f
Create Date: 2026-06-30 05:35:27.748675
"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.db.seeds.idc_loader import parse_idc_csv


revision: str = 'ea4260e45547'
down_revision: Union[str, None] = '580c730a890f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'lab_reference_ranges',
        sa.Column('needs_clinical_review', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column('lab_reference_ranges', 'needs_clinical_review', server_default=None)

    # Seed the IDC lab catalogue (backend/app/db/seeds/idc_lab_catalogue_seed.csv).
    # IMPORTANT: source ranges are from a single lab (IDC) and have NOT been
    # independently clinically reviewed beyond the three corrections noted below.
    # Do not treat as authoritative without review.
    #
    # Decisions (confirmed with product owner, see app/db/seeds/idc_loader.py):
    # - loinc_code left NULL for all IDC rows — no confidently verified LOINC
    #   mapping for this source. LOINC enrichment is a deferred separate task.
    # - 'applies_to: male' rows seeded as-is with no synthesized female range.
    #   select_range() falls back gender -> general -> unknown, so this does
    #   NOT silently apply a male range to a female patient.
    # - Vitamin D (25-OH) seeded with the standard sufficiency band
    #   (30-100 ng/mL), not the "<20" deficiency cutoff seen in the source
    #   report; flagged needs_clinical_review=True.
    # - 5 IDC test names overlap analytes already seeded by migration
    #   eef39c9e1f7c (Cholesterol Total, Creatinine, Fasting Glucose,
    #   Haemoglobin, HbA1c) and are intentionally skipped here rather than
    #   creating duplicate catalogue entries or conflicting reference ranges
    #   for the same (test, applies_to) pair. Merging the IDC ranges into
    #   those existing entries is deferred to a reviewed follow-up.
    parsed = parse_idc_csv()

    cat_table = sa.table(
        "lab_test_catalogue",
        sa.column("id", sa.UUID), sa.column("key", sa.Text),
        sa.column("display_name", sa.Text), sa.column("loinc_code", sa.Text),
        sa.column("category", sa.Text), sa.column("specimen", sa.Text),
        sa.column("default_unit", sa.Text), sa.column("is_active", sa.Boolean),
    )
    range_table = sa.table(
        "lab_reference_ranges",
        sa.column("id", sa.UUID), sa.column("test_id", sa.UUID),
        sa.column("applies_to", sa.Text), sa.column("low", sa.Numeric),
        sa.column("high", sa.Numeric), sa.column("unit", sa.Text),
        sa.column("notes", sa.Text), sa.column("needs_clinical_review", sa.Boolean),
    )

    key_to_id = {row.key: str(uuid.uuid4()) for row in parsed.catalogue_rows}

    op.bulk_insert(cat_table, [
        {
            "id": key_to_id[row.key],
            "key": row.key,
            "display_name": row.display_name,
            "loinc_code": None,
            "category": "lab",
            "specimen": row.specimen,
            "default_unit": row.default_unit,
            "is_active": True,
        }
        for row in parsed.catalogue_rows
    ])

    op.bulk_insert(range_table, [
        {
            "id": str(uuid.uuid4()),
            "test_id": key_to_id[row.test_key],
            "applies_to": row.applies_to,
            "low": row.low,
            "high": row.high,
            "unit": row.unit,
            "notes": row.notes,
            "needs_clinical_review": row.needs_clinical_review,
        }
        for row in parsed.range_rows
    ])


def downgrade() -> None:
    parsed = parse_idc_csv()
    keys = [row.key for row in parsed.catalogue_rows]

    conn = op.get_bind()
    conn.execute(
        sa.text(
            "DELETE FROM lab_reference_ranges WHERE test_id IN "
            "(SELECT id FROM lab_test_catalogue WHERE key = ANY(:keys))"
        ),
        {"keys": keys},
    )
    conn.execute(
        sa.text("DELETE FROM lab_test_catalogue WHERE key = ANY(:keys)"),
        {"keys": keys},
    )

    op.drop_column('lab_reference_ranges', 'needs_clinical_review')
