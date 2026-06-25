import uuid

from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str, password: str) -> dict:
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()


def _auth(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _create_patient(client: AsyncClient, tokens: dict, cnic: str = "42201-1234567-8"):
    resp = await client.post(
        "/api/v1/patients",
        headers=_auth(tokens),
        json={
            "full_name": "Test Patient",
            "gender": "male",
            "relationship_to_account": "self",
            "cnic": cnic,
        },
    )
    assert resp.status_code == 201
    return resp.json()


_FH_BASE = {
    "relationship": "father",
    "condition_display_name": "Type 2 Diabetes",
}


class TestCreateFamilyHistory:
    async def test_create_minimal(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/family-history",
            headers=_auth(auth_tokens),
            json=_FH_BASE,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["relationship"] == "father"
        assert data["condition_display_name"] == "Type 2 Diabetes"
        assert data["condition_code"] is None

    async def test_create_with_snomed_code(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/family-history",
            headers=_auth(auth_tokens),
            json={**_FH_BASE, "condition_code": "44054006"},
        )
        assert resp.status_code == 201
        assert resp.json()["condition_code"] == "44054006"

    async def test_invalid_relationship_rejected(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/family-history",
            headers=_auth(auth_tokens),
            json={**_FH_BASE, "relationship": "cousin"},
        )
        assert resp.status_code == 422

    async def test_create_on_soft_deleted_patient_rejected(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        await client.delete(f"/api/v1/patients/{patient['id']}", headers=_auth(auth_tokens))
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/family-history",
            headers=_auth(auth_tokens),
            json=_FH_BASE,
        )
        assert resp.status_code == 404


class TestListFamilyHistory:
    async def test_list_paginated(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        pid = patient["id"]
        for rel in ["mother", "father", "brother"]:
            await client.post(
                f"/api/v1/patients/{pid}/family-history",
                headers=_auth(auth_tokens),
                json={"relationship": rel, "condition_display_name": "Hypertension"},
            )
        resp = await client.get(
            f"/api/v1/patients/{pid}/family-history",
            headers=_auth(auth_tokens),
            params={"limit": 2},
        )
        assert resp.json()["total"] == 3
        assert len(resp.json()["items"]) == 2


class TestGetFamilyHistory:
    async def test_get_nonexistent_404(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        resp = await client.get(
            f"/api/v1/patients/{patient['id']}/family-history/{uuid.uuid4()}",
            headers=_auth(auth_tokens),
        )
        assert resp.status_code == 404


class TestUpdateFamilyHistory:
    async def test_update_onset_age(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        create_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/family-history",
            headers=_auth(auth_tokens),
            json=_FH_BASE,
        )
        fhid = create_resp.json()["id"]
        patch_resp = await client.patch(
            f"/api/v1/patients/{patient['id']}/family-history/{fhid}",
            headers=_auth(auth_tokens),
            json={"onset_age": 55, "deceased": True},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["onset_age"] == 55
        assert patch_resp.json()["deceased"] is True

    async def test_patch_cannot_change_account_id(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        create_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/family-history",
            headers=_auth(auth_tokens),
            json=_FH_BASE,
        )
        fhid = create_resp.json()["id"]
        original = create_resp.json()["account_id"]
        patch_resp = await client.patch(
            f"/api/v1/patients/{patient['id']}/family-history/{fhid}",
            headers=_auth(auth_tokens),
            json={"account_id": str(uuid.uuid4())},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["account_id"] == original


class TestSoftDeleteFamilyHistory:
    async def test_soft_delete(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        create_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/family-history",
            headers=_auth(auth_tokens),
            json=_FH_BASE,
        )
        fhid = create_resp.json()["id"]
        del_resp = await client.delete(
            f"/api/v1/patients/{patient['id']}/family-history/{fhid}",
            headers=_auth(auth_tokens),
        )
        assert del_resp.status_code == 204
        get_resp = await client.get(
            f"/api/v1/patients/{patient['id']}/family-history/{fhid}",
            headers=_auth(auth_tokens),
        )
        assert get_resp.status_code == 404


class TestFamilyHistoryFHIR:
    async def test_fhir_valid_r4(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        create_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/family-history",
            headers=_auth(auth_tokens),
            json={
                **_FH_BASE,
                "condition_code": "44054006",
                "onset_age": 50,
                "deceased": True,
            },
        )
        fhid = create_resp.json()["id"]
        resp = await client.get(
            f"/api/v1/patients/{patient['id']}/family-history/{fhid}/fhir",
            headers=_auth(auth_tokens),
        )
        assert resp.status_code == 200
        fhir = resp.json()
        assert fhir["resourceType"] == "FamilyMemberHistory"
        assert fhir["patient"]["reference"] == f"Patient/{patient['id']}"
        assert fhir["relationship"]["coding"][0]["code"] == "FTH"
        assert fhir["condition"][0]["code"]["text"] == "Type 2 Diabetes"
        assert fhir["deceasedBoolean"] is True

        from fhir.resources.familymemberhistory import FamilyMemberHistory

        FamilyMemberHistory(**fhir)


class TestFamilyHistoryScoping:
    async def test_account_b_cannot_create(self, client: AsyncClient, auth_tokens):
        patient_a = await _create_patient(client, auth_tokens)
        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        resp = await client.post(
            f"/api/v1/patients/{patient_a['id']}/family-history",
            headers=_auth(tokens_b),
            json=_FH_BASE,
        )
        assert resp.status_code == 404

    async def test_account_b_cannot_list(self, client: AsyncClient, auth_tokens):
        patient_a = await _create_patient(client, auth_tokens)
        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        resp = await client.get(
            f"/api/v1/patients/{patient_a['id']}/family-history",
            headers=_auth(tokens_b),
        )
        assert resp.status_code == 404
