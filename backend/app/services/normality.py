"""Normality evaluation — pure logic, no DB.

Computes whether a numeric lab result is in-range, below, or above the
reference range. Returns 'unknown' when: no range exists, result is
non-numeric, or units don't match (no guessed conversions).

Range boundaries are INCLUSIVE: value == low or value == high is in_range.

Depends on 8a reference ranges being clinically correct. Ranges remain
flagged for clinical review; normality output is only as trustworthy as
the seeded ranges.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class NormalityResult:
    status: str  # in_range | below_low | above_high | unknown
    range_low: float | None = None
    range_high: float | None = None
    range_unit: str | None = None
    range_applies_to: str | None = None
    reason: str | None = None


def evaluate(
    *,
    value_numeric: float | None,
    value_text: str | None,
    result_unit: str | None,
    range_low: float | None,
    range_high: float | None,
    range_unit: str | None,
    range_applies_to: str | None = None,
) -> NormalityResult:
    if value_numeric is None:
        return NormalityResult(status="unknown", reason="Non-numeric result")

    if range_low is None and range_high is None:
        return NormalityResult(status="unknown", reason="No reference range available")

    if range_unit and result_unit and range_unit != result_unit:
        return NormalityResult(
            status="unknown",
            range_low=range_low,
            range_high=range_high,
            range_unit=range_unit,
            range_applies_to=range_applies_to,
            reason=f"Unit mismatch: result '{result_unit}' vs range '{range_unit}'",
        )

    if range_low is not None and value_numeric < range_low:
        return NormalityResult(
            status="below_low",
            range_low=range_low,
            range_high=range_high,
            range_unit=range_unit,
            range_applies_to=range_applies_to,
        )

    if range_high is not None and value_numeric > range_high:
        return NormalityResult(
            status="above_high",
            range_low=range_low,
            range_high=range_high,
            range_unit=range_unit,
            range_applies_to=range_applies_to,
        )

    return NormalityResult(
        status="in_range",
        range_low=range_low,
        range_high=range_high,
        range_unit=range_unit,
        range_applies_to=range_applies_to,
    )


def select_range(
    ranges: list[dict],
    patient_gender: str | None = None,
) -> dict | None:
    """Pick the best matching reference range for this patient context.

    Resolution order:
    1. Match patient gender (male/female) if available.
    2. Fall back to 'general'.
    3. If nothing matches, return None.
    """
    by_applies = {r["applies_to"]: r for r in ranges}

    if patient_gender and patient_gender in by_applies:
        return by_applies[patient_gender]

    if "general" in by_applies:
        return by_applies["general"]

    return None
