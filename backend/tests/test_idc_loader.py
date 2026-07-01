"""Tests for the IDC lab catalogue seed CSV parser — no DB required.

Locks in the three resolved flags from the seed review:
1. loinc_code stays unset for every IDC row (no invented LOINC codes).
2. Male-only ranges are seeded as-is, with no synthesized female range,
   and select_range() must NOT apply a male range to a female patient.
3. Vitamin D (25-OH) carries the standard sufficiency band, not the
   "<20" deficiency cutoff, and is flagged needs_clinical_review.
"""

from app.db.seeds.idc_loader import KNOWN_OVERLAPS, parse_idc_csv, slugify
from app.services.normality import evaluate, select_range


class TestSlugify:
    def test_simple_name(self):
        assert slugify("Albumin") == "albumin"

    def test_name_with_parens_and_dots(self):
        assert slugify("AST (S.G.O.T.)") == "ast_s_g_o_t"

    def test_collapses_repeated_separators(self):
        assert slugify("Total Iron Binding Capacity (TIBC)") == "total_iron_binding_capacity_tibc"


class TestParseIdcCsv:
    def test_parses_expected_row_count(self):
        parsed = parse_idc_csv()
        # 46 source rows minus 5 known overlaps with the existing catalogue.
        assert len(parsed.catalogue_rows) == 46 - len(KNOWN_OVERLAPS)
        assert len(parsed.range_rows) == len(parsed.catalogue_rows)

    def test_skips_known_overlapping_tests(self):
        parsed = parse_idc_csv()
        skipped_names = {name for name, _ in parsed.skipped_existing}
        assert skipped_names == set(KNOWN_OVERLAPS.keys())
        catalogue_keys = {row.key for row in parsed.catalogue_rows}
        for existing_key in KNOWN_OVERLAPS.values():
            assert existing_key not in catalogue_keys

    def test_no_duplicate_keys(self):
        parsed = parse_idc_csv()
        keys = [row.key for row in parsed.catalogue_rows]
        assert len(keys) == len(set(keys))

    def test_loinc_is_never_set_by_loader(self):
        # The loader doesn't even have a loinc field on CatalogueRow —
        # this test documents that omission is deliberate, not an oversight.
        parsed = parse_idc_csv()
        assert not hasattr(parsed.catalogue_rows[0], "loinc_code")

    def test_male_only_ranges_have_no_synthesized_female_counterpart(self):
        parsed = parse_idc_csv()
        male_keys = {r.test_key for r in parsed.range_rows if r.applies_to == "male"}
        female_keys = {r.test_key for r in parsed.range_rows if r.applies_to == "female"}
        assert male_keys, "expected at least one male-only range from the IDC seed"
        assert female_keys == set()
        assert "ferritin" in male_keys
        assert "hematocrit" in male_keys
        assert "iron_serum" in male_keys
        assert "uric_acid" in male_keys

    def test_vitamin_d_uses_sufficiency_band_not_deficiency_cutoff(self):
        parsed = parse_idc_csv()
        vd = next(r for r in parsed.range_rows if r.test_key == "vitamin_d_25_oh")
        assert vd.low == 30.0
        assert vd.high == 100.0
        assert vd.needs_clinical_review is True

    def test_only_vitamin_d_is_flagged_for_review(self):
        parsed = parse_idc_csv()
        flagged = [r.test_key for r in parsed.range_rows if r.needs_clinical_review]
        assert flagged == ["vitamin_d_25_oh"]

    def test_blank_low_or_high_parses_to_none(self):
        parsed = parse_idc_csv()
        # Cholesterol/HDL Ratio is "< 4.97" — no lower bound in source.
        ratio = next(r for r in parsed.range_rows if r.test_key == "cholesterol_hdl_ratio")
        assert ratio.low is None
        assert ratio.high == 4.97


class TestMaleOnlyRangeDoesNotLeakToFemalePatient:
    """End-to-end through select_range + evaluate, using real IDC seed data."""

    def _ferritin_ranges(self) -> list[dict]:
        parsed = parse_idc_csv()
        return [
            {
                "applies_to": r.applies_to,
                "low": r.low,
                "high": r.high,
                "unit": r.unit,
            }
            for r in parsed.range_rows
            if r.test_key == "ferritin"
        ]

    def test_male_patient_gets_the_male_range(self):
        ranges = self._ferritin_ranges()
        chosen = select_range(ranges, "male")
        assert chosen is not None
        assert chosen["applies_to"] == "male"
        assert chosen["low"] == 22.0

    def test_female_patient_does_not_get_male_range(self):
        ranges = self._ferritin_ranges()
        chosen = select_range(ranges, "female")
        # No 'general' fallback exists for ferritin in the IDC seed, so a
        # female patient must get None, not the male range.
        assert chosen is None

    def test_female_patient_normality_is_unknown_not_in_range(self):
        ranges = self._ferritin_ranges()
        chosen = select_range(ranges, "female")
        result = evaluate(
            value_numeric=50,
            value_text=None,
            result_unit="ng/mL",
            range_low=chosen["low"] if chosen else None,
            range_high=chosen["high"] if chosen else None,
            range_unit=chosen["unit"] if chosen else None,
        )
        assert result.status == "unknown"
