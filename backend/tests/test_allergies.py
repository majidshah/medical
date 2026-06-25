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


_ALLERGY_BASE = {
    "display_name": "Peanuts",
    "category": "food",
}


class TestCreateAllergy:
    async def test_create_display_name_only(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/allergies",
            headers=_auth(auth_tokens),
            json=_ALLERGY_BASE,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["display_name"] == "Peanuts"
        assert data["code"] is None
        assert data["clinical_status"] == "active"
        assert data["category"] == "food"

    async def test_create_with_snomed_code(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/allergies",
            headers=_auth(auth_tokens),
            json={**_ALLERGY_BASE, "code": "91935009", "code_system": "http://snomed.info/sct"},
        )
        assert resp.status_code == 201
        assert resp.json()["code"] == "91935009"

    async def test_invalid_category_rejected(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/allergies",
            headers=_auth(auth_tokens),
            json={**_ALLERGY_BASE, "category": "invalid"},
        )
        assert resp.status_code == 422

    async def test_invalid_criticality_rejected(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/allergies",
            headers=_auth(auth_tokens),
            json={**_ALLERGY_BASE, "criticality": "extreme"},
        )
        assert resp.status_code == 422

    async def test_create_on_soft_deleted_patient_rejected(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        await client.delete(f"/api/v1/patients/{patient['id']}", headers=_auth(auth_tokens))
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/allergies",
            headers=_auth(auth_tokens),
            json=_ALLERGY_BASE,
        )
        assert resp.status_code == 404


class TestListAllergies:
    async def test_list_paginated(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        pid = patient["id"]
        for name in ["Peanuts", "Shellfish", "Dust"]:
            await client.post(
                f"/api/v1/patients/{pid}/allergies",
                headers=_auth(auth_tokens),
                json={"display_name": name, "category": "food"},
            )
        resp = await client.get(
            f"/api/v1/patients/{pid}/allergies",
            headers=_auth(auth_tokens),
            params={"limit": 2},
        )
        assert resp.json()["total"] == 3
        assert len(resp.json()["items"]) == 2


class TestGetAllergy:
    async def test_get_nonexistent_404(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        resp = await client.get(
            f"/api/v1/patients/{patient['id']}/allergies/{uuid.uuid4()}",
            headers=_auth(auth_tokens),
        )
        assert resp.status_code == 404


class TestUpdateAllergy:
    async def test_update_status_to_resolved(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        create_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/allergies",
            headers=_auth(auth_tokens),
            json=_ALLERGY_BASE,
        )
        aid = create_resp.json()["id"]
        patch_resp = await client.patch(
            f"/api/v1/patients/{patient['id']}/allergies/{aid}",
            headers=_auth(auth_tokens),
            json={"clinical_status": "resolved"},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["clinical_status"] == "resolved"

    async def test_patch_cannot_change_patient_id(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        create_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/allergies",
            headers=_auth(auth_tokens),
            json=_ALLERGY_BASE,
        )
        aid = create_resp.json()["id"]
        patch_resp = await client.patch(
            f"/api/v1/patients/{patient['id']}/allergies/{aid}",
            headers=_auth(auth_tokens),
            json={"patient_id": str(uuid.uuid4())},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["patient_id"] == patient["id"]


class TestSoftDeleteAllergy:
    async def test_soft_delete(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        create_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/allergies",
            headers=_auth(auth_tokens),
            json=_ALLERGY_BASE,
        )
        aid = create_resp.json()["id"]
        del_resp = await client.delete(
            f"/api/v1/patients/{patient['id']}/allergies/{aid}",
            headers=_auth(auth_tokens),
        )
        assert del_resp.status_code == 204
        get_resp = await client.get(
            f"/api/v1/patients/{patient['id']}/allergies/{aid}",
            headers=_auth(auth_tokens),
        )
        assert get_resp.status_code == 404


class TestAllergyFHIR:
    async def test_fhir_valid_r4(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        create_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/allergies",
            headers=_auth(auth_tokens),
            json={
                **_ALLERGY_BASE,
                "code": "91935009",
                "criticality": "high",
                "reaction": "Anaphylaxis",
                "severity": "severe",
            },
        )
        aid = create_resp.json()["id"]
        resp = await client.get(
            f"/api/v1/patients/{patient['id']}/allergies/{aid}/fhir",
            headers=_auth(auth_tokens),
        )
        assert resp.status_code == 200
        fhir = resp.json()
        assert fhir["resourceType"] == "AllergyIntolerance"
        assert fhir["patient"]["reference"] == f"Patient/{patient['id']}"
        assert fhir["code"]["text"] == "Peanuts"
        assert fhir["code"]["coding"][0]["code"] == "91935009"
        assert fhir["category"] == ["food"]
        assert fhir["criticality"] == "high"

        from fhir.resources.allergyintolerance import AllergyIntolerance

        AllergyIntolerance(**fhir)


class TestAllergyScoping:
    async def test_account_b_cannot_create(self, client: AsyncClient, auth_tokens):
        patient_a = await _create_patient(client, auth_tokens)
        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        resp = await client.post(
            f"/api/v1/patients/{patient_a['id']}/allergies",
            headers=_auth(tokens_b),
            json=_ALLERGY_BASE,
        )
        assert resp.status_code == 404

    async def test_account_b_cannot_list(self, client: AsyncClient, auth_tokens):
        patient_a = await _create_patient(client, auth_tokens)
        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        resp = await client.get(
            f"/api/v1/patients/{patient_a['id']}/allergies",
            headers=_auth(tokens_b),
        )
        assert resp.status_code == 404

    async def test_account_b_cannot_get(self, client: AsyncClient, auth_tokens):
        patient_a = await _create_patient(client, auth_tokens)
        create_resp = await client.post(
            f"/api/v1/patients/{patient_a['id']}/allergies",
            headers=_auth(auth_tokens),
            json=_ALLERGY_BASE,
        )
        aid = create_resp.json()["id"]
        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        resp = await client.get(
            f"/api/v1/patients/{patient_a['id']}/allergies/{aid}",
            headers=_auth(tokens_b),
        )
        assert resp.status_code == 404
