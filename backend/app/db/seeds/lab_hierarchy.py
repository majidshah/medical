"""Department -> Panel -> Test hierarchy for the lab catalogue.

Single source of truth for which existing lab_test_catalogue.key belongs
to which department/panel. Used by:
- the Alembic migration that creates lab_departments/lab_panels and
  backfills department_id/panel_id onto the pre-existing catalogue rows
- tests/conftest.py, so the test DB's catalogue seed mirrors the real
  hierarchy instead of silently drifting from it

This module only covers the BACKFILL of tests that existed before the
hierarchy did (the 8 pre-existing rows + the 41 IDC-seeded rows). Future
catalogue rows created through the admin UI (Section C) are assigned a
department/panel directly at creation time and don't go through this
module.

'imaging' is not one of the four departments named in the catalogue-admin
spec (Chemistry/Hematology/Special Chemistry/Endocrinology) — it's added
here so the pre-existing chest_xray row (category='imaging') has a valid,
non-NULL department_id to backfill into, since department_id is NOT NULL
on every catalogue row regardless of category.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PanelSeed:
    key: str
    name: str
    test_keys: list[str]


@dataclass
class DepartmentSeed:
    key: str
    name: str
    panels: list[PanelSeed] = field(default_factory=list)
    standalone_test_keys: list[str] = field(default_factory=list)


DEPARTMENTS: list[DepartmentSeed] = [
    DepartmentSeed(
        key="chemistry",
        name="Chemistry",
        panels=[
            PanelSeed(
                "lft",
                "Liver Function Tests (LFT)",
                [
                    "alt_s_g_p_t",
                    "ast_s_g_o_t",
                    "total_bilirubin",
                    "alkaline_phosphatase",
                    "gamma_gt_ggt",
                    "total_protein",
                    "albumin",
                    "globulin",
                ],
            ),
            PanelSeed(
                "rft",
                "Renal Function Tests (RFT)",
                ["blood_urea", "blood_urea_nitrogen", "serum_creatinine", "uric_acid"],
            ),
            PanelSeed(
                "lipid_profile",
                "Lipid Profile",
                [
                    "total_cholesterol",
                    "hdl_cholesterol",
                    "ldl_cholesterol",
                    "triglycerides",
                    "cholesterol_hdl_ratio",
                    "apolipoprotein_b",
                ],
            ),
            PanelSeed("diabetes", "Diabetes", ["fasting_blood_glucose", "hba1c"]),
        ],
        standalone_test_keys=[
            "urine_creatinine",
            "urine_microalbumin",
            "urobilinogen",
            "urinalysis",
        ],
    ),
    DepartmentSeed(
        key="hematology",
        name="Hematology",
        panels=[
            PanelSeed(
                "cbc",
                "Complete Blood Count (CBC)",
                [
                    "cbc_hemoglobin",
                    "hematocrit",
                    "mch",
                    "mchc",
                    "rdw_cv",
                    "neutrophils",
                    "lymphocytes",
                    "monocytes",
                    "eosinophils",
                ],
            ),
            PanelSeed(
                "iron_studies",
                "Iron Studies",
                [
                    "iron_serum",
                    "total_iron_binding_capacity_tibc",
                    "ferritin",
                    "transferrin_saturation",
                ],
            ),
        ],
    ),
    DepartmentSeed(
        key="special_chemistry",
        name="Special Chemistry",
        standalone_test_keys=[
            "serum_copper",
            "zinc_level",
            "ceruloplasmin_serum",
            "vitamin_b12",
            "vitamin_d_25_oh",
            "high_sensitive_crp_hscrp",
            "homocysteine",
            "lipoprotein_a",
        ],
    ),
    DepartmentSeed(
        key="endocrinology",
        name="Endocrinology",
        panels=[
            PanelSeed("thyroid_profile", "Thyroid Profile", ["t3_free", "t4_free", "tsh"]),
        ],
    ),
    DepartmentSeed(
        key="imaging",
        name="Imaging",
        standalone_test_keys=["chest_xray"],
    ),
]


def test_key_to_department_panel() -> dict[str, tuple[str, str | None]]:
    """Map every catalogue test key to (department_key, panel_key | None)."""
    mapping: dict[str, tuple[str, str | None]] = {}
    for dept in DEPARTMENTS:
        for panel in dept.panels:
            for test_key in panel.test_keys:
                mapping[test_key] = (dept.key, panel.key)
        for test_key in dept.standalone_test_keys:
            mapping[test_key] = (dept.key, None)
    return mapping
