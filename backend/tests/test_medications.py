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


_MED_BASE = {"display_name": "Metformin"}


class TestCreateMedication:
    async def test_create_display_name_only(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/medications",
            headers=_auth(auth_tokens),
            json=_MED_BASE,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["display_name"] == "Metformin"
        assert data["code"] is None
        assert data["status"] == "active"

    async def test_create_with_code(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/medications",
            headers=_auth(auth_tokens),
            json={
                **_MED_BASE,
                "code": "860975",
                "code_system": "http://www.nlm.nih.gov/research/umls/rxnorm",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["code"] == "860975"

    async def test_invalid_status_rejected(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/medications",
            headers=_auth(auth_tokens),
            json={**_MED_BASE, "status": "invalid"},
        )
        assert resp.status_code == 422

    async def test_create_on_soft_deleted_patient_rejected(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        await client.delete(f"/api/v1/patients/{patient['id']}", headers=_auth(auth_tokens))
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/medications",
            headers=_auth(auth_tokens),
            json=_MED_BASE,
        )
        assert resp.status_code == 404


class TestListMedications:
    async def test_list_paginated(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        pid = patient["id"]
        for name in ["Med A", "Med B", "Med C"]:
            await client.post(
                f"/api/v1/patients/{pid}/medications",
                headers=_auth(auth_tokens),
                json={"display_name": name},
            )
        resp = await client.get(
            f"/api/v1/patients/{pid}/medications",
            headers=_auth(auth_tokens),
            params={"limit": 2},
        )
        assert resp.json()["total"] == 3
        assert len(resp.json()["items"]) == 2


class TestGetMedication:
    async def test_get_nonexistent_404(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        resp = await client.get(
            f"/api/v1/patients/{patient['id']}/medications/{uuid.uuid4()}",
            headers=_auth(auth_tokens),
        )
        assert resp.status_code == 404


class TestUpdateMedication:
    async def test_update_status_to_stopped(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        create_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/medications",
            headers=_auth(auth_tokens),
            json={**_MED_BASE, "start_date": "2024-01-01"},
        )
        mid = create_resp.json()["id"]
        patch_resp = await client.patch(
            f"/api/v1/patients/{patient['id']}/medications/{mid}",
            headers=_auth(auth_tokens),
            json={"status": "stopped", "end_date": "2024-06-15"},
        )
        assert patch_resp.status_code == 200
        data = patch_resp.json()
        assert data["status"] == "stopped"
        assert data["end_date"] == "2024-06-15"

    async def test_patch_cannot_change_account_id(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        create_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/medications",
            headers=_auth(auth_tokens),
            json=_MED_BASE,
        )
        mid = create_resp.json()["id"]
        original = create_resp.json()["account_id"]
        patch_resp = await client.patch(
            f"/api/v1/patients/{patient['id']}/medications/{mid}",
            headers=_auth(auth_tokens),
            json={"account_id": str(uuid.uuid4())},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["account_id"] == original


class TestSoftDeleteMedication:
    async def test_soft_delete(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        create_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/medications",
            headers=_auth(auth_tokens),
            json=_MED_BASE,
        )
        mid = create_resp.json()["id"]
        del_resp = await client.delete(
            f"/api/v1/patients/{patient['id']}/medications/{mid}",
            headers=_auth(auth_tokens),
        )
        assert del_resp.status_code == 204
        get_resp = await client.get(
            f"/api/v1/patients/{patient['id']}/medications/{mid}",
            headers=_auth(auth_tokens),
        )
        assert get_resp.status_code == 404


class TestMedicationFHIR:
    async def test_fhir_valid_r4(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        create_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/medications",
            headers=_auth(auth_tokens),
            json={
                **_MED_BASE,
                "code": "860975",
                "dosage": "500 mg",
                "frequency": "twice daily",
                "route": "oral",
                "start_date": "2024-01-01",
            },
        )
        mid = create_resp.json()["id"]
        resp = await client.get(
            f"/api/v1/patients/{patient['id']}/medications/{mid}/fhir",
            headers=_auth(auth_tokens),
        )
        assert resp.status_code == 200
        fhir = resp.json()
        assert fhir["resourceType"] == "MedicationStatement"
        assert fhir["subject"]["reference"] == f"Patient/{patient['id']}"
        assert fhir["medication"]["concept"]["text"] == "Metformin"
        assert fhir["status"] == "active"
        assert "dosage" in fhir

        from fhir.resources.medicationstatement import MedicationStatement

        MedicationStatement(**fhir)


class TestMedicationScoping:
    async def test_account_b_cannot_create(self, client: AsyncClient, auth_tokens):
        patient_a = await _create_patient(client, auth_tokens)
        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        resp = await client.post(
            f"/api/v1/patients/{patient_a['id']}/medications",
            headers=_auth(tokens_b),
            json=_MED_BASE,
        )
        assert resp.status_code == 404

    async def test_account_b_cannot_list(self, client: AsyncClient, auth_tokens):
        patient_a = await _create_patient(client, auth_tokens)
        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        resp = await client.get(
            f"/api/v1/patients/{patient_a['id']}/medications",
            headers=_auth(tokens_b),
        )
        assert resp.status_code == 404

    async def test_account_b_cannot_get(self, client: AsyncClient, auth_tokens):
        patient_a = await _create_patient(client, auth_tokens)
        create_resp = await client.post(
            f"/api/v1/patients/{patient_a['id']}/medications",
            headers=_auth(auth_tokens),
            json=_MED_BASE,
        )
        mid = create_resp.json()["id"]
        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        resp = await client.get(
            f"/api/v1/patients/{patient_a['id']}/medications/{mid}",
            headers=_auth(tokens_b),
        )
        assert resp.status_code == 404
