"""Section C review: admin CRUD for departments/panels/tests/ranges/labs.

Answers the review questions concretely:
1. Are admin-catalogue endpoints behind require_admin (covered generically
   by test_admin_security.py's route-table walk — this file adds the
   behavioral checks: a normal account is rejected on representative
   admin-catalogue routes too).
2. Can an admin do full CRUD on departments, panels, tests, ranges, labs?
3. Does the ranges endpoint accept ANY applies_to value, including 'female'?
4. Are admin-catalogue writes audited?
"""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.lab_department import LabDepartment


def _headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


class TestNormalAccountBlockedFromCatalogueEndpoints:
    async def test_normal_account_cannot_create_department(
        self, client: AsyncClient, auth_tokens: dict
    ):
        resp = await client.post(
            "/api/v1/admin/departments",
            json={"key": "sneaky", "name": "Sneaky Dept"},
            headers=_headers(auth_tokens),
        )
        assert resp.status_code == 403

    async def test_normal_account_cannot_list_departments(
        self, client: AsyncClient, auth_tokens: dict
    ):
        resp = await client.get("/api/v1/admin/departments", headers=_headers(auth_tokens))
        assert resp.status_code == 403


class TestDepartmentCrud:
    async def test_create_list_update_deactivate(
        self, client: AsyncClient, admin_auth_tokens: dict
    ):
        h = _headers(admin_auth_tokens)

        create = await client.post(
            "/api/v1/admin/departments",
            json={"key": "radiology", "name": "Radiology", "display_order": 5},
            headers=h,
        )
        assert create.status_code == 201
        dept = create.json()
        assert dept["is_active"] is True

        listed = await client.get("/api/v1/admin/departments", headers=h)
        assert listed.status_code == 200
        assert any(d["id"] == dept["id"] for d in listed.json())

        updated = await client.patch(
            f"/api/v1/admin/departments/{dept['id']}",
            json={"name": "Radiology & Imaging"},
            headers=h,
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == "Radiology & Imaging"

        deactivated = await client.delete(f"/api/v1/admin/departments/{dept['id']}", headers=h)
        assert deactivated.status_code == 200
        assert deactivated.json()["is_active"] is False

        # Deactivated departments still appear in the admin list (reversible).
        listed_after = await client.get("/api/v1/admin/departments", headers=h)
        dept_after = next(d for d in listed_after.json() if d["id"] == dept["id"])
        assert dept_after["is_active"] is False

    async def test_duplicate_key_is_conflict(self, client: AsyncClient, admin_auth_tokens: dict):
        h = _headers(admin_auth_tokens)
        body = {"key": "dup_dept", "name": "Dup Dept"}
        first = await client.post("/api/v1/admin/departments", json=body, headers=h)
        assert first.status_code == 201
        second = await client.post("/api/v1/admin/departments", json=body, headers=h)
        assert second.status_code == 409


class TestPanelCrud:
    async def test_create_panel_requires_existing_department(
        self, client: AsyncClient, admin_auth_tokens: dict
    ):
        h = _headers(admin_auth_tokens)
        resp = await client.post(
            "/api/v1/admin/panels",
            json={
                "department_id": "00000000-0000-0000-0000-000000000000",
                "key": "orphan",
                "name": "Orphan Panel",
            },
            headers=h,
        )
        assert resp.status_code == 404

    async def test_full_crud(self, client: AsyncClient, admin_auth_tokens: dict):
        h = _headers(admin_auth_tokens)
        dept = (
            await client.post(
                "/api/v1/admin/departments",
                json={"key": "panel_dept", "name": "Panel Dept"},
                headers=h,
            )
        ).json()

        create = await client.post(
            "/api/v1/admin/panels",
            json={"department_id": dept["id"], "key": "lft", "name": "Liver Function"},
            headers=h,
        )
        assert create.status_code == 201
        panel = create.json()

        listed = await client.get(f"/api/v1/admin/panels?department_id={dept['id']}", headers=h)
        assert listed.status_code == 200
        assert [p["id"] for p in listed.json()] == [panel["id"]]

        updated = await client.patch(
            f"/api/v1/admin/panels/{panel['id']}", json={"display_order": 9}, headers=h
        )
        assert updated.status_code == 200
        assert updated.json()["display_order"] == 9

        deactivated = await client.delete(f"/api/v1/admin/panels/{panel['id']}", headers=h)
        assert deactivated.status_code == 200
        assert deactivated.json()["is_active"] is False


class TestTestCrud:
    async def test_panel_must_belong_to_department(
        self, client: AsyncClient, admin_auth_tokens: dict
    ):
        h = _headers(admin_auth_tokens)
        dept_a = (
            await client.post(
                "/api/v1/admin/departments", json={"key": "dept_a", "name": "Dept A"}, headers=h
            )
        ).json()
        dept_b = (
            await client.post(
                "/api/v1/admin/departments", json={"key": "dept_b", "name": "Dept B"}, headers=h
            )
        ).json()
        panel_b = (
            await client.post(
                "/api/v1/admin/panels",
                json={"department_id": dept_b["id"], "key": "panel_b", "name": "Panel B"},
                headers=h,
            )
        ).json()

        resp = await client.post(
            "/api/v1/admin/tests",
            json={
                "key": "cross_dept_test",
                "display_name": "Cross Dept Test",
                "department_id": dept_a["id"],
                "panel_id": panel_b["id"],
                "category": "lab",
            },
            headers=h,
        )
        assert resp.status_code == 422

    async def test_full_crud(self, client: AsyncClient, admin_auth_tokens: dict):
        h = _headers(admin_auth_tokens)
        dept = (
            await client.post(
                "/api/v1/admin/departments",
                json={"key": "test_dept", "name": "Test Dept"},
                headers=h,
            )
        ).json()

        create = await client.post(
            "/api/v1/admin/tests",
            json={
                "key": "new_analyte",
                "display_name": "New Analyte",
                "department_id": dept["id"],
                "category": "lab",
                "specimen": "blood",
                "default_unit": "mg/dL",
            },
            headers=h,
        )
        assert create.status_code == 201
        test = create.json()
        assert test["is_active"] is True

        listed = await client.get(f"/api/v1/admin/tests?department_id={dept['id']}", headers=h)
        assert [t["id"] for t in listed.json()] == [test["id"]]

        updated = await client.patch(
            f"/api/v1/admin/tests/{test['id']}",
            json={"display_name": "New Analyte (revised)"},
            headers=h,
        )
        assert updated.status_code == 200
        assert updated.json()["display_name"] == "New Analyte (revised)"

        deactivated = await client.delete(f"/api/v1/admin/tests/{test['id']}", headers=h)
        assert deactivated.status_code == 200
        assert deactivated.json()["is_active"] is False


class TestRangeCrudAndFemaleApplesTo:
    async def test_admin_can_add_a_female_range(
        self, client: AsyncClient, admin_auth_tokens: dict, db_session: AsyncSession
    ):
        """The whole point of Section C: an admin must be able to add a
        reference range with applies_to='female' through the UI/API —
        this is how female ranges get into the catalogue at all, since
        the IDC seed only carried 'general'/'male'/unspecified rows.
        """
        h = _headers(admin_auth_tokens)
        dept = (
            await client.post(
                "/api/v1/admin/departments",
                json={"key": "female_range_dept", "name": "Female Range Dept"},
                headers=h,
            )
        ).json()
        test = (
            await client.post(
                "/api/v1/admin/tests",
                json={
                    "key": "iron_studies_ferritin",
                    "display_name": "Ferritin",
                    "department_id": dept["id"],
                    "category": "lab",
                },
                headers=h,
            )
        ).json()

        resp = await client.post(
            "/api/v1/admin/ranges",
            json={
                "test_id": test["id"],
                "applies_to": "female",
                "low": 11,
                "high": 307,
                "unit": "ng/mL",
                "needs_clinical_review": False,
            },
            headers=h,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["applies_to"] == "female"

        listed = await client.get(f"/api/v1/admin/tests/{test['id']}/ranges", headers=h)
        assert listed.status_code == 200
        assert any(r["applies_to"] == "female" for r in listed.json())

    async def test_range_accepts_arbitrary_applies_to_cohort(
        self, client: AsyncClient, admin_auth_tokens: dict
    ):
        # Not an enum: any cohort string is accepted (CLAUDE.md rule).
        h = _headers(admin_auth_tokens)
        dept = (
            await client.post(
                "/api/v1/admin/departments",
                json={"key": "cohort_dept", "name": "Cohort Dept"},
                headers=h,
            )
        ).json()
        test = (
            await client.post(
                "/api/v1/admin/tests",
                json={
                    "key": "pediatric_test",
                    "display_name": "Pediatric Test",
                    "department_id": dept["id"],
                    "category": "lab",
                },
                headers=h,
            )
        ).json()

        resp = await client.post(
            "/api/v1/admin/ranges",
            json={
                "test_id": test["id"],
                "applies_to": "pediatric_0_5y",
                "unit": "unit",
            },
            headers=h,
        )
        assert resp.status_code == 201
        assert resp.json()["applies_to"] == "pediatric_0_5y"

    async def test_full_crud_with_lab_attribution(
        self, client: AsyncClient, admin_auth_tokens: dict
    ):
        h = _headers(admin_auth_tokens)
        dept = (
            await client.post(
                "/api/v1/admin/departments",
                json={"key": "range_dept", "name": "Range Dept"},
                headers=h,
            )
        ).json()
        test = (
            await client.post(
                "/api/v1/admin/tests",
                json={
                    "key": "range_test",
                    "display_name": "Range Test",
                    "department_id": dept["id"],
                    "category": "lab",
                },
                headers=h,
            )
        ).json()
        lab = (
            await client.post(
                "/api/v1/admin/labs", json={"key": "chughtai", "name": "Chughtai Lab"}, headers=h
            )
        ).json()

        create = await client.post(
            "/api/v1/admin/ranges",
            json={
                "test_id": test["id"],
                "applies_to": "general",
                "low": 1,
                "high": 2,
                "unit": "u",
                "lab_id": lab["id"],
            },
            headers=h,
        )
        assert create.status_code == 201
        range_ = create.json()
        assert range_["lab_id"] == lab["id"]

        updated = await client.patch(
            f"/api/v1/admin/ranges/{range_['id']}", json={"high": 3}, headers=h
        )
        assert updated.status_code == 200
        assert updated.json()["high"] == 3

        deleted = await client.delete(f"/api/v1/admin/ranges/{range_['id']}", headers=h)
        assert deleted.status_code == 204

        listed = await client.get(f"/api/v1/admin/tests/{test['id']}/ranges", headers=h)
        assert listed.json() == []


class TestLabCrud:
    async def test_full_crud(self, client: AsyncClient, admin_auth_tokens: dict):
        h = _headers(admin_auth_tokens)
        create = await client.post(
            "/api/v1/admin/labs",
            json={"key": "shaukat_khanum", "name": "Shaukat Khanum"},
            headers=h,
        )
        assert create.status_code == 201
        lab = create.json()

        listed = await client.get("/api/v1/admin/labs", headers=h)
        assert any(item["id"] == lab["id"] for item in listed.json())

        updated = await client.patch(
            f"/api/v1/admin/labs/{lab['id']}", json={"name": "Shaukat Khanum Memorial"}, headers=h
        )
        assert updated.json()["name"] == "Shaukat Khanum Memorial"

        deactivated = await client.delete(f"/api/v1/admin/labs/{lab['id']}", headers=h)
        assert deactivated.json()["is_active"] is False


class TestCatalogueWritesAreAudited:
    async def test_department_create_and_update_are_audited(
        self, client: AsyncClient, admin_auth_tokens: dict, db_session: AsyncSession
    ):
        h = _headers(admin_auth_tokens)
        create = await client.post(
            "/api/v1/admin/departments",
            json={"key": "audited_dept", "name": "Audited Dept"},
            headers=h,
        )
        dept_id = create.json()["id"]

        await client.patch(
            f"/api/v1/admin/departments/{dept_id}", json={"name": "Audited Dept Renamed"}, headers=h
        )
        await client.delete(f"/api/v1/admin/departments/{dept_id}", headers=h)

        entries = (
            (
                await db_session.execute(
                    select(AuditLog)
                    .where(AuditLog.detail.like(f"%department_id={dept_id}%"))
                    .order_by(AuditLog.created_at)
                )
            )
            .scalars()
            .all()
        )
        assert len(entries) == 3
        assert [e.event_type for e in entries] == [
            "admin.department_created",
            "admin.department_updated",
            "admin.department_updated",
        ]

    async def test_range_create_update_delete_are_audited(
        self, client: AsyncClient, admin_auth_tokens: dict, db_session: AsyncSession
    ):
        h = _headers(admin_auth_tokens)
        dept = (
            await client.post(
                "/api/v1/admin/departments",
                json={"key": "audit_range_dept", "name": "Audit Range Dept"},
                headers=h,
            )
        ).json()
        test = (
            await client.post(
                "/api/v1/admin/tests",
                json={
                    "key": "audit_range_test",
                    "display_name": "Audit Range Test",
                    "department_id": dept["id"],
                    "category": "lab",
                },
                headers=h,
            )
        ).json()
        range_ = (
            await client.post(
                "/api/v1/admin/ranges",
                json={"test_id": test["id"], "applies_to": "female", "unit": "u", "high": 5},
                headers=h,
            )
        ).json()
        await client.patch(f"/api/v1/admin/ranges/{range_['id']}", json={"high": 6}, headers=h)
        await client.delete(f"/api/v1/admin/ranges/{range_['id']}", headers=h)

        entries = (
            (
                await db_session.execute(
                    select(AuditLog).where(AuditLog.detail.like(f"%range_id={range_['id']}%"))
                )
            )
            .scalars()
            .all()
        )
        assert {e.event_type for e in entries} == {
            "admin.range_created",
            "admin.range_updated",
            "admin.range_deleted",
        }

    async def test_audit_entries_have_no_pii(
        self, client: AsyncClient, admin_auth_tokens: dict, db_session: AsyncSession
    ):
        h = _headers(admin_auth_tokens)
        resp = await client.post(
            "/api/v1/admin/labs", json={"key": "no_pii_lab", "name": "No PII Lab"}, headers=h
        )
        lab_id = resp.json()["id"]
        entry = (
            await db_session.execute(
                select(AuditLog).where(AuditLog.detail.like(f"%lab_id={lab_id}%"))
            )
        ).scalar_one()
        assert "@" not in entry.detail


class TestUniqueDepartmentSeeded:
    async def test_seeded_departments_are_visible_to_admin(
        self, client: AsyncClient, admin_auth_tokens: dict, db_session: AsyncSession
    ):
        # Sanity: the Section A seeded hierarchy is manageable through
        # these same admin endpoints, not a parallel dataset.
        seeded = (await db_session.execute(select(LabDepartment))).scalars().all()
        h = _headers(admin_auth_tokens)
        listed = await client.get("/api/v1/admin/departments", headers=h)
        listed_ids = {d["id"] for d in listed.json()}
        assert {str(d.id) for d in seeded}.issubset(listed_ids)
