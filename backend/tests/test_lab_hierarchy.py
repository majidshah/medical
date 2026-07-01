"""Tests for the Department -> Panel -> Test lab catalogue hierarchy.

Covers Section A of the catalogue-admin spec: hierarchy + cross-table
constraint, seed re-filing onto the hierarchy, existing lab_results
still resolving through it, and applies_to remaining free-form.

Note: tests/conftest.py only seeds the 8 original catalogue rows (not
the full 49-row real catalogue), so these tests use those 8 keys —
fasting_blood_glucose, hba1c, cbc_hemoglobin, serum_creatinine,
total_cholesterol, tsh, urinalysis, chest_xray.
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seeds import lab_hierarchy
from app.db.seeds.lab_hierarchy import DEPARTMENTS
from app.models import LabReferenceRange


async def _get_department_id(session: AsyncSession, key: str) -> uuid.UUID:
    row = (
        await session.execute(text("SELECT id FROM lab_departments WHERE key = :k"), {"k": key})
    ).first()
    assert row is not None, f"department {key!r} not seeded"
    return row[0]


async def _get_panel_id(session: AsyncSession, department_key: str, panel_key: str) -> uuid.UUID:
    row = (
        await session.execute(
            text(
                "SELECT p.id FROM lab_panels p JOIN lab_departments d ON d.id = p.department_id "
                "WHERE d.key = :dk AND p.key = :pk"
            ),
            {"dk": department_key, "pk": panel_key},
        )
    ).first()
    assert row is not None, f"panel {department_key}/{panel_key} not seeded"
    return row[0]


class TestHierarchySeeded:
    async def test_all_five_departments_present(self, db_session: AsyncSession):
        rows = (await db_session.execute(text("SELECT key FROM lab_departments"))).all()
        keys = {r[0] for r in rows}
        assert keys == {"chemistry", "hematology", "special_chemistry", "endocrinology", "imaging"}

    async def test_panel_count_matches_mapping(self, db_session: AsyncSession):
        expected_panel_count = sum(len(d.panels) for d in DEPARTMENTS)
        actual = (await db_session.execute(text("SELECT count(*) FROM lab_panels"))).scalar_one()
        assert actual == expected_panel_count

    async def test_every_seeded_test_has_a_department(self, db_session: AsyncSession):
        rows = (
            await db_session.execute(
                text("SELECT key FROM lab_test_catalogue WHERE department_id IS NULL")
            )
        ).all()
        assert rows == []

    async def test_seed_re_filed_to_correct_department_and_panel(self, db_session: AsyncSession):
        # Spot-check against the shared mapping (not just counts), using
        # only the 8 keys conftest actually seeds for tests.
        mapping = lab_hierarchy.test_key_to_department_panel()
        for test_key in (
            "fasting_blood_glucose",
            "cbc_hemoglobin",
            "tsh",
            "chest_xray",
            "urinalysis",
        ):
            expected_dept_key, expected_panel_key = mapping[test_key]
            row = (
                await db_session.execute(
                    text(
                        "SELECT d.key, p.key FROM lab_test_catalogue t "
                        "JOIN lab_departments d ON d.id = t.department_id "
                        "LEFT JOIN lab_panels p ON p.id = t.panel_id "
                        "WHERE t.key = :key"
                    ),
                    {"key": test_key},
                )
            ).first()
            assert row is not None
            actual_dept_key, actual_panel_key = row
            assert actual_dept_key == expected_dept_key
            assert actual_panel_key == expected_panel_key


class TestPanelMustMatchDepartment:
    async def test_panel_from_different_department_rejected(self, db_session: AsyncSession):
        # serum_creatinine is seeded under chemistry/rft; hematology/cbc
        # is a real panel in a different department.
        chemistry_id = await _get_department_id(db_session, "chemistry")
        hematology_cbc_panel_id = await _get_panel_id(db_session, "hematology", "cbc")

        with pytest.raises(IntegrityError):
            await db_session.execute(
                text(
                    "UPDATE lab_test_catalogue SET department_id = :did, panel_id = :pid "
                    "WHERE key = 'serum_creatinine'"
                ),
                {"did": str(chemistry_id), "pid": str(hematology_cbc_panel_id)},
            )
            await db_session.flush()
        await db_session.rollback()

    async def test_panel_from_same_department_accepted(self, db_session: AsyncSession):
        chemistry_id = await _get_department_id(db_session, "chemistry")
        lft_panel_id = await _get_panel_id(db_session, "chemistry", "lft")

        await db_session.execute(
            text(
                "UPDATE lab_test_catalogue SET department_id = :did, panel_id = :pid "
                "WHERE key = 'serum_creatinine'"
            ),
            {"did": str(chemistry_id), "pid": str(lft_panel_id)},
        )
        await db_session.flush()
        await db_session.rollback()  # don't actually mutate seed data for other tests

    async def test_standalone_test_with_no_panel_is_allowed(self, db_session: AsyncSession):
        # panel_id IS NULL must not trip the composite FK, even when the
        # department is also being changed to one with real panels.
        hematology_id = await _get_department_id(db_session, "hematology")
        await db_session.execute(
            text(
                "UPDATE lab_test_catalogue SET department_id = :did, panel_id = NULL "
                "WHERE key = 'serum_creatinine'"
            ),
            {"did": str(hematology_id)},
        )
        await db_session.flush()
        await db_session.rollback()


class TestApplesToFreeForm:
    async def test_arbitrary_cohort_value_accepted(self, db_session: AsyncSession):
        test_row = (
            await db_session.execute(text("SELECT id FROM lab_test_catalogue WHERE key = 'tsh'"))
        ).first()
        assert test_row is not None

        db_session.add(
            LabReferenceRange(
                id=uuid.uuid4(),
                test_id=test_row[0],
                applies_to="pregnancy",
                low=0.1,
                high=2.5,
                unit="mIU/L",
            )
        )
        await db_session.flush()
        await db_session.rollback()


class TestExistingLabResultsStillResolve:
    async def test_lab_result_joins_to_hierarchy_through_test_id(
        self, client, auth_tokens, db_session: AsyncSession
    ):
        # Create a patient + report + result through the real API (as
        # existing slice-8 tests do), then confirm the result's test_id
        # still resolves all the way through to a department via the
        # new hierarchy columns.
        headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
        patient_resp = await client.post(
            "/api/v1/patients",
            json={
                "full_name": "Hierarchy Test Patient",
                "gender": "male",
                "relationship_to_account": "self",
                "cnic": "12345-1234567-1",
            },
            headers=headers,
        )
        assert patient_resp.status_code == 201
        patient_id = patient_resp.json()["id"]

        report_resp = await client.post(
            f"/api/v1/patients/{patient_id}/reports",
            json={"category": "lab", "report_date": "2026-01-01"},
            headers=headers,
        )
        assert report_resp.status_code == 201
        report_id = report_resp.json()["id"]

        catalogue_resp = await client.get(
            "/api/v1/lab-catalogue", params={"q": "Fasting Blood Glucose"}, headers=headers
        )
        assert catalogue_resp.status_code == 200
        test_id = catalogue_resp.json()["items"][0]["id"]

        result_resp = await client.post(
            f"/api/v1/patients/{patient_id}/reports/{report_id}/results",
            json={
                "test_id": test_id,
                "display_name": "Fasting Blood Glucose",
                "value_numeric": 95,
                "unit": "mg/dL",
                "effective_date": "2026-01-01",
            },
            headers=headers,
        )
        assert result_resp.status_code == 201

        row = (
            await db_session.execute(
                text(
                    "SELECT d.key FROM lab_results r "
                    "JOIN lab_test_catalogue t ON t.id = r.test_id "
                    "JOIN lab_departments d ON d.id = t.department_id "
                    "WHERE r.id = :rid"
                ),
                {"rid": result_resp.json()["id"]},
            )
        ).first()
        assert row is not None
        assert row[0] == "chemistry"
