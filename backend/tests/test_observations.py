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


async def _get_type_id(client: AsyncClient, tokens: dict, key: str) -> str:
    resp = await client.get("/api/v1/observation-types", headers=_auth(tokens))
    return next(t["id"] for t in resp.json() if t["key"] == key)


class TestCreateObservation:
    async def test_create_numeric(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        sleep_id = await _get_type_id(client, auth_tokens, "sleep_duration")
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/observations",
            headers=_auth(auth_tokens),
            json={
                "observation_type_id": sleep_id,
                "effective_date": "2024-06-01",
                "value_numeric": 7.5,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert float(data["value_numeric"]) == 7.5
        assert data["unit"] == "h"

    async def test_create_coded(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        smoking_id = await _get_type_id(client, auth_tokens, "smoking_status")
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/observations",
            headers=_auth(auth_tokens),
            json={
                "observation_type_id": smoking_id,
                "effective_date": "2024-06-01",
                "value_code": "never",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["value_code"] == "never"

    async def test_wrong_value_column_for_type(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        sleep_id = await _get_type_id(client, auth_tokens, "sleep_duration")
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/observations",
            headers=_auth(auth_tokens),
            json={
                "observation_type_id": sleep_id,
                "effective_date": "2024-06-01",
                "value_text": "seven hours",
            },
        )
        assert resp.status_code == 422

    async def test_no_value_set_rejected(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        sleep_id = await _get_type_id(client, auth_tokens, "sleep_duration")
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/observations",
            headers=_auth(auth_tokens),
            json={
                "observation_type_id": sleep_id,
                "effective_date": "2024-06-01",
            },
        )
        assert resp.status_code == 422

    async def test_multiple_values_rejected(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        sleep_id = await _get_type_id(client, auth_tokens, "sleep_duration")
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/observations",
            headers=_auth(auth_tokens),
            json={
                "observation_type_id": sleep_id,
                "effective_date": "2024-06-01",
                "value_numeric": 7,
                "value_text": "also text",
            },
        )
        assert resp.status_code == 422

    async def test_create_on_soft_deleted_patient_rejected(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        sleep_id = await _get_type_id(client, auth_tokens, "sleep_duration")
        await client.delete(f"/api/v1/patients/{patient['id']}", headers=_auth(auth_tokens))
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/observations",
            headers=_auth(auth_tokens),
            json={
                "observation_type_id": sleep_id,
                "effective_date": "2024-06-01",
                "value_numeric": 7,
            },
        )
        assert resp.status_code == 404


class TestListObservations:
    async def test_list_paginated(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        sleep_id = await _get_type_id(client, auth_tokens, "sleep_duration")
        pid = patient["id"]
        for i in range(3):
            await client.post(
                f"/api/v1/patients/{pid}/observations",
                headers=_auth(auth_tokens),
                json={
                    "observation_type_id": sleep_id,
                    "effective_date": f"2024-06-0{i + 1}",
                    "value_numeric": 6 + i,
                },
            )
        resp = await client.get(
            f"/api/v1/patients/{pid}/observations",
            headers=_auth(auth_tokens),
            params={"limit": 2},
        )
        assert resp.json()["total"] == 3
        assert len(resp.json()["items"]) == 2

    async def test_list_filter_by_type(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        sleep_id = await _get_type_id(client, auth_tokens, "sleep_duration")
        smoking_id = await _get_type_id(client, auth_tokens, "smoking_status")
        pid = patient["id"]
        await client.post(
            f"/api/v1/patients/{pid}/observations",
            headers=_auth(auth_tokens),
            json={
                "observation_type_id": sleep_id,
                "effective_date": "2024-06-01",
                "value_numeric": 7,
            },
        )
        await client.post(
            f"/api/v1/patients/{pid}/observations",
            headers=_auth(auth_tokens),
            json={
                "observation_type_id": smoking_id,
                "effective_date": "2024-06-01",
                "value_code": "never",
            },
        )
        resp = await client.get(
            f"/api/v1/patients/{pid}/observations",
            headers=_auth(auth_tokens),
            params={"type": "sleep_duration"},
        )
        assert resp.json()["total"] == 1

    async def test_list_filter_by_date_range(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        sleep_id = await _get_type_id(client, auth_tokens, "sleep_duration")
        pid = patient["id"]
        for d in ["2024-01-01", "2024-06-01", "2024-12-01"]:
            await client.post(
                f"/api/v1/patients/{pid}/observations",
                headers=_auth(auth_tokens),
                json={
                    "observation_type_id": sleep_id,
                    "effective_date": d,
                    "value_numeric": 7,
                },
            )
        resp = await client.get(
            f"/api/v1/patients/{pid}/observations",
            headers=_auth(auth_tokens),
            params={"from": "2024-05-01", "to": "2024-07-01"},
        )
        assert resp.json()["total"] == 1


class TestGetObservation:
    async def test_get_nonexistent_404(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        resp = await client.get(
            f"/api/v1/patients/{patient['id']}/observations/{uuid.uuid4()}",
            headers=_auth(auth_tokens),
        )
        assert resp.status_code == 404


class TestUpdateObservation:
    async def test_update_value(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        sleep_id = await _get_type_id(client, auth_tokens, "sleep_duration")
        create_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/observations",
            headers=_auth(auth_tokens),
            json={
                "observation_type_id": sleep_id,
                "effective_date": "2024-06-01",
                "value_numeric": 7,
            },
        )
        oid = create_resp.json()["id"]
        patch_resp = await client.patch(
            f"/api/v1/patients/{patient['id']}/observations/{oid}",
            headers=_auth(auth_tokens),
            json={"value_numeric": 8.5},
        )
        assert patch_resp.status_code == 200
        assert float(patch_resp.json()["value_numeric"]) == 8.5

    async def test_patch_cannot_change_patient_id(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        sleep_id = await _get_type_id(client, auth_tokens, "sleep_duration")
        create_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/observations",
            headers=_auth(auth_tokens),
            json={
                "observation_type_id": sleep_id,
                "effective_date": "2024-06-01",
                "value_numeric": 7,
            },
        )
        oid = create_resp.json()["id"]
        patch_resp = await client.patch(
            f"/api/v1/patients/{patient['id']}/observations/{oid}",
            headers=_auth(auth_tokens),
            json={"patient_id": str(uuid.uuid4())},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["patient_id"] == patient["id"]


class TestSoftDelete:
    async def test_soft_delete_excludes_from_list_get_trend(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        sleep_id = await _get_type_id(client, auth_tokens, "sleep_duration")
        pid = patient["id"]
        create_resp = await client.post(
            f"/api/v1/patients/{pid}/observations",
            headers=_auth(auth_tokens),
            json={
                "observation_type_id": sleep_id,
                "effective_date": "2024-06-01",
                "value_numeric": 7,
            },
        )
        oid = create_resp.json()["id"]
        await client.delete(
            f"/api/v1/patients/{pid}/observations/{oid}", headers=_auth(auth_tokens)
        )
        assert (
            await client.get(
                f"/api/v1/patients/{pid}/observations/{oid}", headers=_auth(auth_tokens)
            )
        ).status_code == 404
        list_resp = await client.get(
            f"/api/v1/patients/{pid}/observations", headers=_auth(auth_tokens)
        )
        assert list_resp.json()["total"] == 0
        trend_resp = await client.get(
            f"/api/v1/patients/{pid}/observations/trend",
            headers=_auth(auth_tokens),
            params={"type": "sleep_duration"},
        )
        assert trend_resp.status_code == 200
        assert len(trend_resp.json()["points"]) == 0


class TestTrend:
    async def test_trend_numeric_ascending(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        sleep_id = await _get_type_id(client, auth_tokens, "sleep_duration")
        pid = patient["id"]
        for d, v in [("2024-01-01", 6), ("2024-03-01", 7), ("2024-06-01", 8)]:
            await client.post(
                f"/api/v1/patients/{pid}/observations",
                headers=_auth(auth_tokens),
                json={
                    "observation_type_id": sleep_id,
                    "effective_date": d,
                    "value_numeric": v,
                },
            )
        resp = await client.get(
            f"/api/v1/patients/{pid}/observations/trend",
            headers=_auth(auth_tokens),
            params={"type": "sleep_duration"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["chartable"] is True
        assert data["observation_type_key"] == "sleep_duration"
        assert len(data["points"]) == 3
        dates = [p["effective_date"] for p in data["points"]]
        assert dates == sorted(dates)
        assert data["points"][0]["value"] == 6
        assert data["points"][2]["value"] == 8

    async def test_trend_coded_not_chartable(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        smoking_id = await _get_type_id(client, auth_tokens, "smoking_status")
        pid = patient["id"]
        await client.post(
            f"/api/v1/patients/{pid}/observations",
            headers=_auth(auth_tokens),
            json={
                "observation_type_id": smoking_id,
                "effective_date": "2024-06-01",
                "value_code": "current",
            },
        )
        resp = await client.get(
            f"/api/v1/patients/{pid}/observations/trend",
            headers=_auth(auth_tokens),
            params={"type": "smoking_status"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["chartable"] is False
        assert data["points"][0]["value"] == "current"

    async def test_trend_empty_returns_empty(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        resp = await client.get(
            f"/api/v1/patients/{patient['id']}/observations/trend",
            headers=_auth(auth_tokens),
            params={"type": "sleep_duration"},
        )
        assert resp.status_code == 200
        assert resp.json()["points"] == []

    async def test_trend_with_date_range(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        sleep_id = await _get_type_id(client, auth_tokens, "sleep_duration")
        pid = patient["id"]
        for d in ["2024-01-01", "2024-06-01", "2024-12-01"]:
            await client.post(
                f"/api/v1/patients/{pid}/observations",
                headers=_auth(auth_tokens),
                json={
                    "observation_type_id": sleep_id,
                    "effective_date": d,
                    "value_numeric": 7,
                },
            )
        resp = await client.get(
            f"/api/v1/patients/{pid}/observations/trend",
            headers=_auth(auth_tokens),
            params={"type": "sleep_duration", "from": "2024-05-01", "to": "2024-07-01"},
        )
        assert len(resp.json()["points"]) == 1


class TestObservationFHIR:
    async def test_fhir_numeric_valid_r4(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        sleep_id = await _get_type_id(client, auth_tokens, "sleep_duration")
        create_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/observations",
            headers=_auth(auth_tokens),
            json={
                "observation_type_id": sleep_id,
                "effective_date": "2024-06-01",
                "value_numeric": 7.5,
            },
        )
        oid = create_resp.json()["id"]
        resp = await client.get(
            f"/api/v1/patients/{patient['id']}/observations/{oid}/fhir",
            headers=_auth(auth_tokens),
        )
        assert resp.status_code == 200
        fhir = resp.json()
        assert fhir["resourceType"] == "Observation"
        assert fhir["subject"]["reference"] == f"Patient/{patient['id']}"
        assert fhir["code"]["text"] == "Sleep Duration"
        assert fhir["code"]["coding"][0]["code"] == "93832-4"
        assert float(fhir["valueQuantity"]["value"]) == 7.5
        assert fhir["status"] == "final"

        from fhir.resources.observation import Observation

        Observation(**fhir)

    async def test_fhir_coded_valid_r4(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        smoking_id = await _get_type_id(client, auth_tokens, "smoking_status")
        create_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/observations",
            headers=_auth(auth_tokens),
            json={
                "observation_type_id": smoking_id,
                "effective_date": "2024-06-01",
                "value_code": "never",
            },
        )
        oid = create_resp.json()["id"]
        resp = await client.get(
            f"/api/v1/patients/{patient['id']}/observations/{oid}/fhir",
            headers=_auth(auth_tokens),
        )
        fhir = resp.json()
        assert fhir["valueCodeableConcept"]["text"] == "never"

        from fhir.resources.observation import Observation

        Observation(**fhir)


class TestObservationScoping:
    async def test_account_b_cannot_create(self, client: AsyncClient, auth_tokens):
        patient_a = await _create_patient(client, auth_tokens)
        sleep_id = await _get_type_id(client, auth_tokens, "sleep_duration")
        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        resp = await client.post(
            f"/api/v1/patients/{patient_a['id']}/observations",
            headers=_auth(tokens_b),
            json={
                "observation_type_id": sleep_id,
                "effective_date": "2024-06-01",
                "value_numeric": 7,
            },
        )
        assert resp.status_code == 404

    async def test_account_b_cannot_list(self, client: AsyncClient, auth_tokens):
        patient_a = await _create_patient(client, auth_tokens)
        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        resp = await client.get(
            f"/api/v1/patients/{patient_a['id']}/observations",
            headers=_auth(tokens_b),
        )
        assert resp.status_code == 404

    async def test_account_b_cannot_trend(self, client: AsyncClient, auth_tokens):
        patient_a = await _create_patient(client, auth_tokens)
        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        resp = await client.get(
            f"/api/v1/patients/{patient_a['id']}/observations/trend",
            headers=_auth(tokens_b),
            params={"type": "sleep_duration"},
        )
        assert resp.status_code == 404


class TestObservationTypes:
    async def test_observation_types_list(self, client: AsyncClient, auth_tokens):
        resp = await client.get("/api/v1/observation-types", headers=_auth(auth_tokens))
        assert resp.status_code == 200
        types = resp.json()
        assert len(types) == 5
        keys = {t["key"] for t in types}
        assert keys == {"smoking_status", "alcohol_use", "exercise", "sleep_duration", "other"}
