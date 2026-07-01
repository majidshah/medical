"""Pure parsing/normalization for the IDC lab catalogue seed CSV.

No DB access here — the Alembic migration imports this module to get
normalized rows, then does the actual inserts. Kept separate so the
parsing logic (slugify, range parsing, dedupe-against-existing-keys) is
unit-testable without a database.

Decisions baked in here (resolved with the product owner, do not
change without re-confirming):
- loinc_code is always None for IDC rows. We do not have a confidently
  verified LOINC mapping for this source; inventing one would be worse
  than leaving it null. LOINC enrichment is a deferred, separate task.
- 'applies_to: male' rows are seeded as-is with no synthesized female
  counterpart. app.services.normality.select_range() already falls
  back from gender match -> 'general' -> unknown, so a female patient
  against a male-only range correctly resolves to normality 'unknown'
  rather than silently applying the male range.
- Vitamin D (25-OH) ships with the standard sufficiency band
  (30-100 ng/mL), NOT the "<20 deficiency cutoff" that appeared in the
  source report. That row also gets needs_clinical_review=True.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

SEED_CSV_PATH = Path(__file__).parent / "idc_lab_catalogue_seed.csv"

# Test names that already exist in the catalogue (seeded by migration
# eef39c9e1f7c) under a different display name / key for the same
# real-world analyte. Seeding these again under a new key would create
# a second catalogue entry for the same test and, worse, a conflicting
# reference range for the same (test, applies_to) pair under whichever
# entry a user happens to pick. Merging IDC ranges into the existing
# entries is a deliberate decision deferred to a follow-up — surfaced
# explicitly via `skipped_existing` rather than guessed at here.
KNOWN_OVERLAPS = {
    "Cholesterol (Total)": "total_cholesterol",
    "Creatinine (Serum)": "serum_creatinine",
    "Glucose (Fasting)": "fasting_blood_glucose",
    "Haemoglobin": "cbc_hemoglobin",
    "HbA1c": "hba1c",
}

VITAMIN_D_TEST_NAME = "Vitamin D (25-OH)"


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug


def _parse_float(raw: str) -> float | None:
    raw = raw.strip()
    return float(raw) if raw else None


@dataclass
class CatalogueRow:
    key: str
    display_name: str
    default_unit: str | None
    specimen: str | None


@dataclass
class RangeRow:
    test_key: str
    applies_to: str
    low: float | None
    high: float | None
    unit: str
    notes: str | None
    needs_clinical_review: bool


@dataclass
class ParsedSeed:
    catalogue_rows: list[CatalogueRow]
    range_rows: list[RangeRow]
    skipped_existing: list[tuple[str, str]]  # (csv test_name, existing catalogue key)


def _infer_specimen(test_name: str) -> str:
    name = test_name.lower()
    return "urine" if "urine" in name or "urobilinogen" in name else "blood"


def _build_notes(range_raw: str, review_note: str) -> str | None:
    parts = [p for p in (range_raw.strip(), review_note.strip()) if p]
    return " — ".join(parts) if parts else None


def parse_idc_csv(path: Path = SEED_CSV_PATH) -> ParsedSeed:
    catalogue_rows: list[CatalogueRow] = []
    range_rows: list[RangeRow] = []
    skipped_existing: list[tuple[str, str]] = []

    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            test_name = row["test_name"].strip()

            if test_name in KNOWN_OVERLAPS:
                skipped_existing.append((test_name, KNOWN_OVERLAPS[test_name]))
                continue

            key = slugify(test_name)
            unit = row["unit"].strip() or None
            catalogue_rows.append(
                CatalogueRow(
                    key=key,
                    display_name=test_name,
                    default_unit=unit,
                    specimen=_infer_specimen(test_name),
                )
            )

            needs_review = test_name == VITAMIN_D_TEST_NAME
            range_rows.append(
                RangeRow(
                    test_key=key,
                    applies_to=row["applies_to"].strip() or "general",
                    low=_parse_float(row["range_low"]),
                    high=_parse_float(row["range_high"]),
                    unit=unit or "",
                    notes=_build_notes(row["range_raw"], row["review_note"]),
                    needs_clinical_review=needs_review,
                )
            )

    return ParsedSeed(
        catalogue_rows=catalogue_rows,
        range_rows=range_rows,
        skipped_existing=skipped_existing,
    )
