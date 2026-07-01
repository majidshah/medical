"""Table-driven unit tests for normality evaluation — no DB required."""

from app.services.normality import evaluate, select_range


class TestEvaluate:
    def test_in_range(self):
        r = evaluate(
            value_numeric=85,
            value_text=None,
            result_unit="mg/dL",
            range_low=70,
            range_high=100,
            range_unit="mg/dL",
        )
        assert r.status == "in_range"

    def test_at_low_boundary_inclusive(self):
        r = evaluate(
            value_numeric=70,
            value_text=None,
            result_unit="mg/dL",
            range_low=70,
            range_high=100,
            range_unit="mg/dL",
        )
        assert r.status == "in_range"

    def test_at_high_boundary_inclusive(self):
        r = evaluate(
            value_numeric=100,
            value_text=None,
            result_unit="mg/dL",
            range_low=70,
            range_high=100,
            range_unit="mg/dL",
        )
        assert r.status == "in_range"

    def test_below_low(self):
        r = evaluate(
            value_numeric=65,
            value_text=None,
            result_unit="mg/dL",
            range_low=70,
            range_high=100,
            range_unit="mg/dL",
        )
        assert r.status == "below_low"
        assert r.range_low == 70

    def test_above_high(self):
        r = evaluate(
            value_numeric=110,
            value_text=None,
            result_unit="mg/dL",
            range_low=70,
            range_high=100,
            range_unit="mg/dL",
        )
        assert r.status == "above_high"
        assert r.range_high == 100

    def test_no_range(self):
        r = evaluate(
            value_numeric=85,
            value_text=None,
            result_unit="mg/dL",
            range_low=None,
            range_high=None,
            range_unit=None,
        )
        assert r.status == "unknown"
        assert "No reference range" in r.reason

    def test_non_numeric(self):
        r = evaluate(
            value_numeric=None,
            value_text="Positive",
            result_unit=None,
            range_low=70,
            range_high=100,
            range_unit="mg/dL",
        )
        assert r.status == "unknown"
        assert "Non-numeric" in r.reason

    def test_unit_mismatch(self):
        r = evaluate(
            value_numeric=5.5,
            value_text=None,
            result_unit="mmol/L",
            range_low=70,
            range_high=100,
            range_unit="mg/dL",
        )
        assert r.status == "unknown"
        assert "Unit mismatch" in r.reason

    def test_one_sided_range_high_only(self):
        r = evaluate(
            value_numeric=180,
            value_text=None,
            result_unit="mg/dL",
            range_low=None,
            range_high=200,
            range_unit="mg/dL",
        )
        assert r.status == "in_range"

    def test_one_sided_range_above_high(self):
        r = evaluate(
            value_numeric=250,
            value_text=None,
            result_unit="mg/dL",
            range_low=None,
            range_high=200,
            range_unit="mg/dL",
        )
        assert r.status == "above_high"

    def test_one_sided_range_low_only_in_range(self):
        # e.g. HDL Cholesterol: "> 60" desirable, no upper bound.
        r = evaluate(
            value_numeric=65,
            value_text=None,
            result_unit="mg/dL",
            range_low=60,
            range_high=None,
            range_unit="mg/dL",
        )
        assert r.status == "in_range"

    def test_one_sided_range_low_only_at_boundary(self):
        r = evaluate(
            value_numeric=60,
            value_text=None,
            result_unit="mg/dL",
            range_low=60,
            range_high=None,
            range_unit="mg/dL",
        )
        assert r.status == "in_range"

    def test_one_sided_range_below_low(self):
        r = evaluate(
            value_numeric=45,
            value_text=None,
            result_unit="mg/dL",
            range_low=60,
            range_high=None,
            range_unit="mg/dL",
        )
        assert r.status == "below_low"


class TestSelectRange:
    def test_gender_match(self):
        ranges = [
            {"applies_to": "male", "low": 13.5, "high": 17.5, "unit": "g/dL"},
            {"applies_to": "female", "low": 12.0, "high": 15.5, "unit": "g/dL"},
            {"applies_to": "general", "low": 12.0, "high": 17.5, "unit": "g/dL"},
        ]
        r = select_range(ranges, "male")
        assert r["applies_to"] == "male"

    def test_fallback_to_general(self):
        ranges = [
            {"applies_to": "male", "low": 13.5, "high": 17.5, "unit": "g/dL"},
            {"applies_to": "general", "low": 12.0, "high": 17.5, "unit": "g/dL"},
        ]
        r = select_range(ranges, "unknown")
        assert r["applies_to"] == "general"

    def test_no_gender_uses_general(self):
        ranges = [
            {"applies_to": "general", "low": 70, "high": 100, "unit": "mg/dL"},
        ]
        r = select_range(ranges, None)
        assert r["applies_to"] == "general"

    def test_no_match_returns_none(self):
        ranges = [
            {"applies_to": "male", "low": 13.5, "high": 17.5, "unit": "g/dL"},
        ]
        r = select_range(ranges, "female")
        assert r is None
