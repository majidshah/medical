"""Section B security review: roles/permissions + admin authorization.

Answers the six attack questions concretely, against the real app and
real DB, not by assertion:

1. Can a normal account reach ANY admin endpoint? (must be 403, every one)
2. Can an account self-assign/escalate to admin through any endpoint/payload?
3. Does EVERY admin route explicitly call require_admin (none relying on
   plain account auth alone)?
4. Is patient data still account-scoped for an admin?
5. Is role assignment guarded (seeded/admin-only, never self-service)?
6. Are admin actions audited?
"""

import uuid

from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.security import hash_password
from app.main import app
from app.models.account import Account
from app.models.account_role import AccountRole
from app.models.audit_log import AuditLog
from app.services.roles import ADMIN_ROLE_KEY, RoleError, grant_role, has_role


async def _create_account_and_grant_twice(session: AsyncSession, email: str) -> None:
    account = Account(email=email, password_hash=hash_password("securepass123"))
    session.add(account)
    await session.flush()
    await grant_role(
        session, target_email=email, role_key=ADMIN_ROLE_KEY, granted_by_account_id=None
    )
    await grant_role(
        session, target_email=email, role_key=ADMIN_ROLE_KEY, granted_by_account_id=None
    )


def _discover_admin_routes() -> list:
    """Walk the live FastAPI route table for every route under /admin.

    This is a regression guard, not a fixed list: if someone adds a new
    admin route later and forgets require_admin, this test starts
    failing against the route table itself — not against a hand-maintained
    list that could silently drift out of sync.
    """
    routes = []
    for route in app.routes:
        if type(route).__name__ == "_IncludedRouter":
            for r in route.original_router.routes:
                path = getattr(r, "path", "")
                if path.startswith("/admin"):
                    routes.append(r)
    assert routes, "no /admin routes found — route discovery itself is broken"
    return routes


def _walk_dependencies(dependant) -> list:
    deps = []
    if dependant.call:
        deps.append(dependant.call)
    for sub in dependant.dependencies:
        deps.extend(_walk_dependencies(sub))
    return deps


class TestQuestion3EveryAdminRouteCallsTheCheck:
    """Code-level proof, not behavioral inference: inspect the actual
    dependency tree FastAPI built for each admin route.
    """

    def test_every_admin_route_has_require_admin_in_its_dependency_tree(self):
        admin_routes = _discover_admin_routes()
        assert len(admin_routes) >= 2, "expected at least /admin/roles and /admin/roles/grant"

        missing = []
        for route in admin_routes:
            deps = _walk_dependencies(route.dependant)
            if require_admin not in deps:
                missing.append((sorted(route.methods), route.path))

        assert missing == [], f"admin routes NOT guarded by require_admin: {missing}"


class TestQuestion1NormalAccountBlockedFromEveryAdminEndpoint:
    async def test_every_admin_route_returns_403_for_normal_account(
        self, client: AsyncClient, auth_tokens: dict
    ):
        headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
        admin_routes = _discover_admin_routes()

        results = []
        for route in admin_routes:
            method = next(iter(route.methods - {"HEAD", "OPTIONS"}))
            url = "/api/v1" + route.path
            if method == "GET":
                resp = await client.get(url, headers=headers)
            elif method == "POST":
                # Body content doesn't matter — require_admin must reject
                # before the handler (or its validation) ever runs.
                resp = await client.post(url, json={}, headers=headers)
            else:
                continue
            results.append((method, url, resp.status_code))

        for method, url, status_code in results:
            assert status_code == 403, f"{method} {url} returned {status_code}, expected 403"

    async def test_unauthenticated_request_is_401_not_403(self, client: AsyncClient):
        # Sanity check that require_admin layers on top of authentication
        # rather than replacing it: no token at all -> 401, not 403.
        resp = await client.get("/api/v1/admin/roles")
        assert resp.status_code == 401


class TestQuestion2NoSelfEscalationPath:
    async def test_normal_account_cannot_grant_itself_admin(
        self,
        client: AsyncClient,
        auth_tokens: dict,
        registered_user: dict,
        db_session: AsyncSession,
    ):
        headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
        resp = await client.post(
            "/api/v1/admin/roles/grant",
            json={"email": "test@example.com", "role_key": "admin"},
            headers=headers,
        )
        assert resp.status_code == 403

        is_now_admin = await has_role(db_session, uuid.UUID(registered_user["id"]), ADMIN_ROLE_KEY)
        assert is_now_admin is False

    async def test_normal_account_cannot_grant_admin_to_someone_else(
        self, client: AsyncClient, auth_tokens: dict, db_session: AsyncSession
    ):
        headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
        # Register a second, unrelated victim account.
        await client.post(
            "/api/v1/auth/register",
            json={"email": "victim@example.com", "password": "securepass123"},
        )
        resp = await client.post(
            "/api/v1/admin/roles/grant",
            json={"email": "victim@example.com", "role_key": "admin"},
            headers=headers,
        )
        assert resp.status_code == 403

        victim_id = (
            await db_session.execute(
                text("SELECT id FROM accounts WHERE email='victim@example.com'")
            )
        ).scalar_one()
        assert await has_role(db_session, victim_id, ADMIN_ROLE_KEY) is False

    async def test_registration_payload_cannot_smuggle_a_role(self, client: AsyncClient):
        # Extra fields a client might try injecting at signup time must be
        # silently ignored by Pydantic, not interpreted as a role grant.
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "sneaky@example.com",
                "password": "securepass123",
                "role": "admin",
                "is_admin": True,
                "roles": ["admin"],
            },
        )
        assert resp.status_code == 201
        assert resp.json()["roles"] == []

    async def test_response_after_register_and_login_shows_no_roles(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "plain@example.com", "password": "securepass123"},
        )
        login = await client.post(
            "/api/v1/auth/login", json={"email": "plain@example.com", "password": "securepass123"}
        )
        me = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {login.json()['access_token']}"}
        )
        assert me.status_code == 200
        assert me.json()["roles"] == []


class TestQuestion4PatientDataStaysAccountScopedForAdmin:
    async def test_admin_only_sees_their_own_patients(
        self, client: AsyncClient, auth_tokens: dict, admin_auth_tokens: dict
    ):
        normal_headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
        admin_headers = {"Authorization": f"Bearer {admin_auth_tokens['access_token']}"}

        normal_patient = await client.post(
            "/api/v1/patients",
            json={
                "full_name": "Normal Account Patient",
                "gender": "male",
                "relationship_to_account": "self",
                "cnic": "11111-1111111-1",
            },
            headers=normal_headers,
        )
        assert normal_patient.status_code == 201

        admin_patient = await client.post(
            "/api/v1/patients",
            json={
                "full_name": "Admin Account Patient",
                "gender": "female",
                "relationship_to_account": "self",
                "cnic": "22222-2222222-2",
            },
            headers=admin_headers,
        )
        assert admin_patient.status_code == 201

        admin_list = await client.get("/api/v1/patients", headers=admin_headers)
        assert admin_list.status_code == 200
        admin_patient_names = {p["full_name"] for p in admin_list.json()["items"]}
        assert admin_patient_names == {"Admin Account Patient"}

    async def test_admin_cannot_read_another_accounts_patient_by_id(
        self, client: AsyncClient, auth_tokens: dict, admin_auth_tokens: dict
    ):
        normal_headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
        admin_headers = {"Authorization": f"Bearer {admin_auth_tokens['access_token']}"}

        normal_patient = await client.post(
            "/api/v1/patients",
            json={
                "full_name": "Cross Account Target",
                "gender": "male",
                "relationship_to_account": "self",
                "cnic": "33333-3333333-3",
            },
            headers=normal_headers,
        )
        assert normal_patient.status_code == 201
        patient_id = normal_patient.json()["id"]

        # Being admin must not unlock another account's patient record.
        admin_get = await client.get(f"/api/v1/patients/{patient_id}", headers=admin_headers)
        assert admin_get.status_code == 404

        admin_summary = await client.get(
            f"/api/v1/patients/{patient_id}/summary", headers=admin_headers
        )
        assert admin_summary.status_code == 404


class TestQuestion5RoleAssignmentIsGuarded:
    async def test_grant_role_requires_an_existing_role_key(self, db_session: AsyncSession):
        try:
            await grant_role(
                db_session,
                target_email="test@example.com",
                role_key="not_a_real_role",
                granted_by_account_id=None,
            )
            raise AssertionError("expected RoleError for unknown role_key")
        except RoleError as e:
            assert e.status_code == 404

    async def test_bootstrap_path_works_with_no_acting_account(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        # Mirrors scripts/grant_admin.py exactly: called directly, not
        # through any HTTP route, with granted_by_account_id=None.
        await client.post(
            "/api/v1/auth/register",
            json={"email": "bootstrap@example.com", "password": "securepass123"},
        )
        grant = await grant_role(
            db_session,
            target_email="bootstrap@example.com",
            role_key=ADMIN_ROLE_KEY,
            granted_by_account_id=None,
        )
        assert grant.granted_by_account_id is None
        assert await has_role(db_session, grant.account_id, ADMIN_ROLE_KEY) is True

    async def test_grant_role_is_idempotent_not_duplicating_rows(self, db_session: AsyncSession):
        await _create_account_and_grant_twice(db_session, "idempotent@example.com")
        account_id = (
            await db_session.execute(
                text("SELECT id FROM accounts WHERE email='idempotent@example.com'")
            )
        ).scalar_one()

        rows = (
            (
                await db_session.execute(
                    select(AccountRole).where(AccountRole.account_id == account_id)
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1

    async def test_existing_admin_can_grant_role_to_another_account(
        self, client: AsyncClient, admin_auth_tokens: dict, db_session: AsyncSession
    ):
        admin_headers = {"Authorization": f"Bearer {admin_auth_tokens['access_token']}"}
        await client.post(
            "/api/v1/auth/register",
            json={"email": "promoted@example.com", "password": "securepass123"},
        )
        resp = await client.post(
            "/api/v1/admin/roles/grant",
            json={"email": "promoted@example.com", "role_key": "admin"},
            headers=admin_headers,
        )
        assert resp.status_code == 201

        target_id = (
            await db_session.execute(
                text("SELECT id FROM accounts WHERE email='promoted@example.com'")
            )
        ).scalar_one()
        assert await has_role(db_session, target_id, ADMIN_ROLE_KEY) is True


class TestQuestion6AdminActionsAreAudited:
    async def test_grant_via_api_creates_audit_entry_with_no_phi(
        self, client: AsyncClient, admin_auth_tokens: dict, db_session: AsyncSession
    ):
        admin_headers = {"Authorization": f"Bearer {admin_auth_tokens['access_token']}"}
        await client.post(
            "/api/v1/auth/register",
            json={"email": "audited@example.com", "password": "securepass123"},
        )
        resp = await client.post(
            "/api/v1/admin/roles/grant",
            json={"email": "audited@example.com", "role_key": "admin"},
            headers=admin_headers,
        )
        assert resp.status_code == 201

        admin_id = (
            await db_session.execute(
                text("SELECT id FROM accounts WHERE email='admin@example.com'")
            )
        ).scalar_one()

        entries = (
            (
                await db_session.execute(
                    select(AuditLog).where(
                        AuditLog.event_type == "admin.role_granted", AuditLog.account_id == admin_id
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(entries) == 1
        entry = entries[0]
        assert "role_key=admin" in entry.detail
        assert "target_account_id=" in entry.detail
        # No email/PHI in the audit detail string — only IDs and the role key.
        assert "audited@example.com" not in entry.detail
        assert "@" not in entry.detail

    async def test_bootstrap_cli_grant_creates_audit_entry(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "cligrant@example.com", "password": "securepass123"},
        )
        await grant_role(
            db_session,
            target_email="cligrant@example.com",
            role_key=ADMIN_ROLE_KEY,
            granted_by_account_id=None,
        )

        entries = (
            (
                await db_session.execute(
                    select(AuditLog).where(
                        AuditLog.event_type == "admin.role_granted", AuditLog.account_id.is_(None)
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(entries) == 1

    async def test_idempotent_re_grant_does_not_duplicate_audit_entries(
        self, client: AsyncClient, admin_auth_tokens: dict, db_session: AsyncSession
    ):
        admin_headers = {"Authorization": f"Bearer {admin_auth_tokens['access_token']}"}
        await client.post(
            "/api/v1/auth/register",
            json={"email": "regrant@example.com", "password": "securepass123"},
        )
        for _ in range(2):
            resp = await client.post(
                "/api/v1/admin/roles/grant",
                json={"email": "regrant@example.com", "role_key": "admin"},
                headers=admin_headers,
            )
            assert resp.status_code == 201

        target_id = (
            await db_session.execute(
                text("SELECT id FROM accounts WHERE email='regrant@example.com'")
            )
        ).scalar_one()
        entries = (
            (
                await db_session.execute(
                    select(AuditLog).where(
                        AuditLog.event_type == "admin.role_granted",
                        AuditLog.detail.like(f"%{target_id}%"),
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(entries) == 1
