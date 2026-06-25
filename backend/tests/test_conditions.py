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


class TestCreateCondition:
    async def test_create_with_display_name_only(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/conditions",
            headers=_auth(auth_tokens),
            json={"display_name": "Hypertension"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["display_name"] == "Hypertension"
        assert data["code"] is None
        assert data["clinical_status"] == "active"
        assert data["patient_id"] == patient["id"]

    async def test_create_with_snomed_code(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/conditions",
            headers=_auth(auth_tokens),
            json={
                "display_name": "Type 2 Diabetes",
                "code": "44054006",
                "code_system": "http://snomed.info/sct",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["code"] == "44054006"
        assert data["code_system"] == "http://snomed.info/sct"
        assert data["display_name"] == "Type 2 Diabetes"

    async def test_create_on_soft_deleted_patient_rejected(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        await client.delete(f"/api/v1/patients/{patient['id']}", headers=_auth(auth_tokens))
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/conditions",
            headers=_auth(auth_tokens),
            json={"display_name": "Should Fail"},
        )
        assert resp.status_code == 404


class TestListConditions:
    async def test_list_paginated(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        pid = patient["id"]
        for name in ["Cond A", "Cond B", "Cond C"]:
            await client.post(
                f"/api/v1/patients/{pid}/conditions",
                headers=_auth(auth_tokens),
                json={"display_name": name},
            )
        resp = await client.get(
            f"/api/v1/patients/{pid}/conditions",
            headers=_auth(auth_tokens),
            params={"limit": 2, "offset": 0},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2

    async def test_list_only_active(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        pid = patient["id"]
        await client.post(
            f"/api/v1/patients/{pid}/conditions",
            headers=_auth(auth_tokens),
            json={"display_name": "Active"},
        )
        r2 = await client.post(
            f"/api/v1/patients/{pid}/conditions",
            headers=_auth(auth_tokens),
            json={"display_name": "To Delete"},
        )
        await client.delete(
            f"/api/v1/patients/{pid}/conditions/{r2.json()['id']}",
            headers=_auth(auth_tokens),
        )
        resp = await client.get(f"/api/v1/patients/{pid}/conditions", headers=_auth(auth_tokens))
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["display_name"] == "Active"


class TestGetCondition:
    async def test_get_one(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        create_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/conditions",
            headers=_auth(auth_tokens),
            json={"display_name": "Asthma", "code": "195967001"},
        )
        cid = create_resp.json()["id"]
        resp = await client.get(
            f"/api/v1/patients/{patient['id']}/conditions/{cid}",
            headers=_auth(auth_tokens),
        )
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Asthma"

    async def test_get_nonexistent_returns_404(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        resp = await client.get(
            f"/api/v1/patients/{patient['id']}/conditions/{uuid.uuid4()}",
            headers=_auth(auth_tokens),
        )
        assert resp.status_code == 404


class TestUpdateCondition:
    async def test_update_clinical_status_to_resolved(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        create_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/conditions",
            headers=_auth(auth_tokens),
            json={"display_name": "Pneumonia", "onset_date": "2024-01-15"},
        )
        cid = create_resp.json()["id"]
        patch_resp = await client.patch(
            f"/api/v1/patients/{patient['id']}/conditions/{cid}",
            headers=_auth(auth_tokens),
            json={"clinical_status": "resolved", "abatement_date": "2024-02-20"},
        )
        assert patch_resp.status_code == 200
        data = patch_resp.json()
        assert data["clinical_status"] == "resolved"
        assert data["abatement_date"] == "2024-02-20"

    async def test_patch_cannot_change_patient_id(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        create_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/conditions",
            headers=_auth(auth_tokens),
            json={"display_name": "Test"},
        )
        cid = create_resp.json()["id"]
        patch_resp = await client.patch(
            f"/api/v1/patients/{patient['id']}/conditions/{cid}",
            headers=_auth(auth_tokens),
            json={"patient_id": str(uuid.uuid4())},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["patient_id"] == patient["id"]

    async def test_patch_cannot_change_account_id(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        create_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/conditions",
            headers=_auth(auth_tokens),
            json={"display_name": "Test"},
        )
        cid = create_resp.json()["id"]
        original_account_id = create_resp.json()["account_id"]
        patch_resp = await client.patch(
            f"/api/v1/patients/{patient['id']}/conditions/{cid}",
            headers=_auth(auth_tokens),
            json={"account_id": str(uuid.uuid4())},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["account_id"] == original_account_id


class TestSoftDelete:
    async def test_soft_delete_excludes_from_list_and_get(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        create_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/conditions",
            headers=_auth(auth_tokens),
            json={"display_name": "To Delete"},
        )
        cid = create_resp.json()["id"]
        del_resp = await client.delete(
            f"/api/v1/patients/{patient['id']}/conditions/{cid}",
            headers=_auth(auth_tokens),
        )
        assert del_resp.status_code == 204

        get_resp = await client.get(
            f"/api/v1/patients/{patient['id']}/conditions/{cid}",
            headers=_auth(auth_tokens),
        )
        assert get_resp.status_code == 404

        list_resp = await client.get(
            f"/api/v1/patients/{patient['id']}/conditions",
            headers=_auth(auth_tokens),
        )
        assert list_resp.json()["total"] == 0


class TestFHIREndpoint:
    async def test_fhir_returns_valid_r4(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        create_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/conditions",
            headers=_auth(auth_tokens),
            json={
                "display_name": "Hypertension",
                "code": "38341003",
                "onset_date": "2023-06-01",
                "notes": "Controlled with medication",
            },
        )
        cid = create_resp.json()["id"]
        resp = await client.get(
            f"/api/v1/patients/{patient['id']}/conditions/{cid}/fhir",
            headers=_auth(auth_tokens),
        )
        assert resp.status_code == 200
        fhir = resp.json()
        assert fhir["resourceType"] == "Condition"
        assert fhir["id"] == cid
        assert fhir["subject"]["reference"] == f"Patient/{patient['id']}"
        assert fhir["clinicalStatus"]["coding"][0]["code"] == "active"
        assert fhir["code"]["text"] == "Hypertension"
        assert fhir["code"]["coding"][0]["code"] == "38341003"
        assert fhir["code"]["coding"][0]["system"] == "http://snomed.info/sct"
        assert fhir["onsetDateTime"] == "2023-06-01"
        assert fhir["note"][0]["text"] == "Controlled with medication"

    async def test_fhir_without_code_has_no_coding(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        create_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/conditions",
            headers=_auth(auth_tokens),
            json={"display_name": "Back pain"},
        )
        cid = create_resp.json()["id"]
        resp = await client.get(
            f"/api/v1/patients/{patient['id']}/conditions/{cid}/fhir",
            headers=_auth(auth_tokens),
        )
        fhir = resp.json()
        assert fhir["code"]["text"] == "Back pain"
        assert "coding" not in fhir["code"]


class TestScoping:
    async def test_account_b_cannot_create_on_account_a_patient(
        self, client: AsyncClient, auth_tokens
    ):
        patient_a = await _create_patient(client, auth_tokens)
        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        resp = await client.post(
            f"/api/v1/patients/{patient_a['id']}/conditions",
            headers=_auth(tokens_b),
            json={"display_name": "Sneaky"},
        )
        assert resp.status_code == 404

    async def test_account_b_cannot_list_account_a_conditions(
        self, client: AsyncClient, auth_tokens
    ):
        patient_a = await _create_patient(client, auth_tokens)
        await client.post(
            f"/api/v1/patients/{patient_a['id']}/conditions",
            headers=_auth(auth_tokens),
            json={"display_name": "Private"},
        )
        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        resp = await client.get(
            f"/api/v1/patients/{patient_a['id']}/conditions",
            headers=_auth(tokens_b),
        )
        assert resp.status_code == 404

    async def test_account_b_cannot_get_account_a_condition(self, client: AsyncClient, auth_tokens):
        patient_a = await _create_patient(client, auth_tokens)
        create_resp = await client.post(
            f"/api/v1/patients/{patient_a['id']}/conditions",
            headers=_auth(auth_tokens),
            json={"display_name": "Private"},
        )
        cid = create_resp.json()["id"]
        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        resp = await client.get(
            f"/api/v1/patients/{patient_a['id']}/conditions/{cid}",
            headers=_auth(tokens_b),
        )
        assert resp.status_code == 404

    async def test_account_b_cannot_update_account_a_condition(
        self, client: AsyncClient, auth_tokens
    ):
        patient_a = await _create_patient(client, auth_tokens)
        create_resp = await client.post(
            f"/api/v1/patients/{patient_a['id']}/conditions",
            headers=_auth(auth_tokens),
            json={"display_name": "Private"},
        )
        cid = create_resp.json()["id"]
        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        resp = await client.patch(
            f"/api/v1/patients/{patient_a['id']}/conditions/{cid}",
            headers=_auth(tokens_b),
            json={"display_name": "Hacked"},
        )
        assert resp.status_code == 404

    async def test_account_b_cannot_delete_account_a_condition(
        self, client: AsyncClient, auth_tokens
    ):
        patient_a = await _create_patient(client, auth_tokens)
        create_resp = await client.post(
            f"/api/v1/patients/{patient_a['id']}/conditions",
            headers=_auth(auth_tokens),
            json={"display_name": "Private"},
        )
        cid = create_resp.json()["id"]
        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        resp = await client.delete(
            f"/api/v1/patients/{patient_a['id']}/conditions/{cid}",
            headers=_auth(tokens_b),
        )
        assert resp.status_code == 404
