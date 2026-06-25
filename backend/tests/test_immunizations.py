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


_IMM_BASE = {
    "vaccine_display_name": "BCG",
    "occurrence_date": "2024-01-15",
}


class TestCreateImmunization:
    async def test_create_minimal(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/immunizations",
            headers=_auth(auth_tokens),
            json=_IMM_BASE,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["vaccine_display_name"] == "BCG"
        assert data["occurrence_date"] == "2024-01-15"
        assert data["status"] == "completed"
        assert data["epi_vaccine_id"] is None

    async def test_create_with_epi_reference(self, client: AsyncClient, auth_tokens):
        epi_resp = await client.get("/api/v1/epi-vaccines", headers=_auth(auth_tokens))
        assert epi_resp.status_code == 200
        bcg = next(v for v in epi_resp.json() if v["short_name"] == "BCG")

        patient = await _create_patient(client, auth_tokens)
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/immunizations",
            headers=_auth(auth_tokens),
            json={
                **_IMM_BASE,
                "epi_vaccine_id": bcg["id"],
                "dose_number": 1,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["epi_vaccine_id"] == bcg["id"]
        assert data["dose_number"] == 1

    async def test_create_free_text_non_epi(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/immunizations",
            headers=_auth(auth_tokens),
            json={
                "vaccine_display_name": "COVID-19 Pfizer",
                "occurrence_date": "2024-06-01",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["epi_vaccine_id"] is None
        assert resp.json()["vaccine_display_name"] == "COVID-19 Pfizer"

    async def test_invalid_status_rejected(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/immunizations",
            headers=_auth(auth_tokens),
            json={**_IMM_BASE, "status": "invalid"},
        )
        assert resp.status_code == 422

    async def test_create_on_soft_deleted_patient_rejected(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        await client.delete(f"/api/v1/patients/{patient['id']}", headers=_auth(auth_tokens))
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/immunizations",
            headers=_auth(auth_tokens),
            json=_IMM_BASE,
        )
        assert resp.status_code == 404


class TestListImmunizations:
    async def test_list_paginated(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        pid = patient["id"]
        for i in range(3):
            await client.post(
                f"/api/v1/patients/{pid}/immunizations",
                headers=_auth(auth_tokens),
                json={"vaccine_display_name": f"Vaccine {i}", "occurrence_date": "2024-01-01"},
            )
        resp = await client.get(
            f"/api/v1/patients/{pid}/immunizations",
            headers=_auth(auth_tokens),
            params={"limit": 2},
        )
        assert resp.json()["total"] == 3
        assert len(resp.json()["items"]) == 2


class TestGetImmunization:
    async def test_get_nonexistent_404(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        resp = await client.get(
            f"/api/v1/patients/{patient['id']}/immunizations/{uuid.uuid4()}",
            headers=_auth(auth_tokens),
        )
        assert resp.status_code == 404


class TestUpdateImmunization:
    async def test_update_status(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        create_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/immunizations",
            headers=_auth(auth_tokens),
            json=_IMM_BASE,
        )
        iid = create_resp.json()["id"]
        patch_resp = await client.patch(
            f"/api/v1/patients/{patient['id']}/immunizations/{iid}",
            headers=_auth(auth_tokens),
            json={"status": "entered-in-error"},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["status"] == "entered-in-error"

    async def test_patch_cannot_change_patient_id(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        create_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/immunizations",
            headers=_auth(auth_tokens),
            json=_IMM_BASE,
        )
        iid = create_resp.json()["id"]
        patch_resp = await client.patch(
            f"/api/v1/patients/{patient['id']}/immunizations/{iid}",
            headers=_auth(auth_tokens),
            json={"patient_id": str(uuid.uuid4())},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["patient_id"] == patient["id"]


class TestSoftDeleteImmunization:
    async def test_soft_delete(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        create_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/immunizations",
            headers=_auth(auth_tokens),
            json=_IMM_BASE,
        )
        iid = create_resp.json()["id"]
        del_resp = await client.delete(
            f"/api/v1/patients/{patient['id']}/immunizations/{iid}",
            headers=_auth(auth_tokens),
        )
        assert del_resp.status_code == 204
        get_resp = await client.get(
            f"/api/v1/patients/{patient['id']}/immunizations/{iid}",
            headers=_auth(auth_tokens),
        )
        assert get_resp.status_code == 404


class TestImmunizationFHIR:
    async def test_fhir_valid_r4(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        create_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/immunizations",
            headers=_auth(auth_tokens),
            json={
                **_IMM_BASE,
                "dose_number": 1,
                "lot_number": "LOT123",
                "manufacturer": "SII",
            },
        )
        iid = create_resp.json()["id"]
        resp = await client.get(
            f"/api/v1/patients/{patient['id']}/immunizations/{iid}/fhir",
            headers=_auth(auth_tokens),
        )
        assert resp.status_code == 200
        fhir = resp.json()
        assert fhir["resourceType"] == "Immunization"
        assert fhir["patient"]["reference"] == f"Patient/{patient['id']}"
        assert fhir["vaccineCode"]["text"] == "BCG"
        assert fhir["status"] == "completed"
        assert fhir["lotNumber"] == "LOT123"

        from fhir.resources.immunization import Immunization

        Immunization(**fhir)


class TestImmunizationScoping:
    async def test_account_b_cannot_create(self, client: AsyncClient, auth_tokens):
        patient_a = await _create_patient(client, auth_tokens)
        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        resp = await client.post(
            f"/api/v1/patients/{patient_a['id']}/immunizations",
            headers=_auth(tokens_b),
            json=_IMM_BASE,
        )
        assert resp.status_code == 404

    async def test_account_b_cannot_list(self, client: AsyncClient, auth_tokens):
        patient_a = await _create_patient(client, auth_tokens)
        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        resp = await client.get(
            f"/api/v1/patients/{patient_a['id']}/immunizations",
            headers=_auth(tokens_b),
        )
        assert resp.status_code == 404


class TestEPIVaccines:
    async def test_epi_vaccines_list(self, client: AsyncClient, auth_tokens):
        resp = await client.get("/api/v1/epi-vaccines", headers=_auth(auth_tokens))
        assert resp.status_code == 200
        vaccines = resp.json()
        assert len(vaccines) == 8
        names = {v["short_name"] for v in vaccines}
        assert names == {"BCG", "OPV", "Penta", "PCV", "Rota", "IPV", "Measles", "TCV"}
