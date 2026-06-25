import asyncio
import uuid

from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str, password: str) -> dict:
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()


def _auth(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


class TestCreatePatientCNIC:
    async def test_create_with_cnic(self, client: AsyncClient, auth_tokens):
        resp = await client.post(
            "/api/v1/patients",
            headers=_auth(auth_tokens),
            json={
                "full_name": "Ali Khan",
                "gender": "male",
                "relationship_to_account": "self",
                "cnic": "42201-1234567-8",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["medical_id"] == "42201-1234567-8"
        assert data["has_cnic"] is True
        assert data["full_name"] == "Ali Khan"

    async def test_cnic_normalized_without_dashes(self, client: AsyncClient, auth_tokens):
        resp = await client.post(
            "/api/v1/patients",
            headers=_auth(auth_tokens),
            json={
                "full_name": "Sara Ahmed",
                "gender": "female",
                "relationship_to_account": "self",
                "cnic": "4220112345678",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["medical_id"] == "42201-1234567-8"

    async def test_duplicate_cnic_rejected(self, client: AsyncClient, auth_tokens):
        await client.post(
            "/api/v1/patients",
            headers=_auth(auth_tokens),
            json={
                "full_name": "Ali Khan",
                "gender": "male",
                "relationship_to_account": "self",
                "cnic": "42201-1234567-8",
            },
        )
        tokens2 = await _register_and_login(client, "other@example.com", "securepass123")
        resp = await client.post(
            "/api/v1/patients",
            headers=_auth(tokens2),
            json={
                "full_name": "Different Person",
                "gender": "male",
                "relationship_to_account": "self",
                "cnic": "42201-1234567-8",
            },
        )
        assert resp.status_code == 409

    async def test_malformed_cnic_rejected(self, client: AsyncClient, auth_tokens):
        resp = await client.post(
            "/api/v1/patients",
            headers=_auth(auth_tokens),
            json={
                "full_name": "Bad CNIC",
                "gender": "male",
                "relationship_to_account": "self",
                "cnic": "1234",
            },
        )
        assert resp.status_code == 422

    async def test_neither_cnic_nor_guardian_rejected(self, client: AsyncClient, auth_tokens):
        resp = await client.post(
            "/api/v1/patients",
            headers=_auth(auth_tokens),
            json={
                "full_name": "No ID",
                "gender": "male",
                "relationship_to_account": "self",
            },
        )
        assert resp.status_code == 422


class TestCreateDependent:
    async def test_create_dependent(self, client: AsyncClient, auth_tokens):
        guardian_resp = await client.post(
            "/api/v1/patients",
            headers=_auth(auth_tokens),
            json={
                "full_name": "Guardian",
                "gender": "male",
                "relationship_to_account": "self",
                "cnic": "42201-1234567-8",
            },
        )
        guardian_id = guardian_resp.json()["id"]
        dep_resp = await client.post(
            "/api/v1/patients",
            headers=_auth(auth_tokens),
            json={
                "full_name": "Child One",
                "gender": "female",
                "relationship_to_account": "child",
                "guardian_patient_id": guardian_id,
            },
        )
        assert dep_resp.status_code == 201
        data = dep_resp.json()
        assert data["medical_id"] == "42201-1234567-8-D1"
        assert data["has_cnic"] is False
        assert data["guardian_patient_id"] == guardian_id

    async def test_second_dependent_gets_d2(self, client: AsyncClient, auth_tokens):
        guardian_resp = await client.post(
            "/api/v1/patients",
            headers=_auth(auth_tokens),
            json={
                "full_name": "Guardian",
                "gender": "male",
                "relationship_to_account": "self",
                "cnic": "42201-1234567-8",
            },
        )
        guardian_id = guardian_resp.json()["id"]
        await client.post(
            "/api/v1/patients",
            headers=_auth(auth_tokens),
            json={
                "full_name": "Child One",
                "gender": "female",
                "relationship_to_account": "child",
                "guardian_patient_id": guardian_id,
            },
        )
        dep2 = await client.post(
            "/api/v1/patients",
            headers=_auth(auth_tokens),
            json={
                "full_name": "Child Two",
                "gender": "male",
                "relationship_to_account": "child",
                "guardian_patient_id": guardian_id,
            },
        )
        assert dep2.status_code == 201
        assert dep2.json()["medical_id"] == "42201-1234567-8-D2"

    async def test_guardian_from_other_account_rejected(self, client: AsyncClient, auth_tokens):
        guardian_resp = await client.post(
            "/api/v1/patients",
            headers=_auth(auth_tokens),
            json={
                "full_name": "Guardian",
                "gender": "male",
                "relationship_to_account": "self",
                "cnic": "42201-1234567-8",
            },
        )
        guardian_id = guardian_resp.json()["id"]
        tokens2 = await _register_and_login(client, "other@example.com", "securepass123")
        resp = await client.post(
            "/api/v1/patients",
            headers=_auth(tokens2),
            json={
                "full_name": "Sneaky Child",
                "gender": "male",
                "relationship_to_account": "child",
                "guardian_patient_id": guardian_id,
            },
        )
        assert resp.status_code == 404

    async def test_concurrent_dependents_no_collision(self, client: AsyncClient, auth_tokens):
        guardian_resp = await client.post(
            "/api/v1/patients",
            headers=_auth(auth_tokens),
            json={
                "full_name": "Guardian",
                "gender": "male",
                "relationship_to_account": "self",
                "cnic": "55555-5555555-5",
            },
        )
        guardian_id = guardian_resp.json()["id"]

        async def create_dep(name: str):
            return await client.post(
                "/api/v1/patients",
                headers=_auth(auth_tokens),
                json={
                    "full_name": name,
                    "gender": "male",
                    "relationship_to_account": "child",
                    "guardian_patient_id": guardian_id,
                },
            )

        results = await asyncio.gather(
            create_dep("Dep A"), create_dep("Dep B"), create_dep("Dep C")
        )
        statuses = [r.status_code for r in results]
        assert all(s == 201 for s in statuses), f"Some creates failed: {statuses}"
        medical_ids = {r.json()["medical_id"] for r in results}
        assert len(medical_ids) == 3
        assert medical_ids == {
            "55555-5555555-5-D1",
            "55555-5555555-5-D2",
            "55555-5555555-5-D3",
        }


class TestScoping:
    async def test_cannot_get_other_accounts_patient(self, client: AsyncClient, auth_tokens):
        resp = await client.post(
            "/api/v1/patients",
            headers=_auth(auth_tokens),
            json={
                "full_name": "Account A Patient",
                "gender": "male",
                "relationship_to_account": "self",
                "cnic": "42201-1234567-8",
            },
        )
        patient_id = resp.json()["id"]

        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        get_resp = await client.get(f"/api/v1/patients/{patient_id}", headers=_auth(tokens_b))
        assert get_resp.status_code == 404

    async def test_cannot_patch_other_accounts_patient(self, client: AsyncClient, auth_tokens):
        resp = await client.post(
            "/api/v1/patients",
            headers=_auth(auth_tokens),
            json={
                "full_name": "Account A Patient",
                "gender": "male",
                "relationship_to_account": "self",
                "cnic": "42201-1234567-8",
            },
        )
        patient_id = resp.json()["id"]

        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        patch_resp = await client.patch(
            f"/api/v1/patients/{patient_id}",
            headers=_auth(tokens_b),
            json={"full_name": "Hacked"},
        )
        assert patch_resp.status_code == 404

    async def test_cannot_delete_other_accounts_patient(self, client: AsyncClient, auth_tokens):
        resp = await client.post(
            "/api/v1/patients",
            headers=_auth(auth_tokens),
            json={
                "full_name": "Account A Patient",
                "gender": "male",
                "relationship_to_account": "self",
                "cnic": "42201-1234567-8",
            },
        )
        patient_id = resp.json()["id"]

        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        del_resp = await client.delete(f"/api/v1/patients/{patient_id}", headers=_auth(tokens_b))
        assert del_resp.status_code == 404

    async def test_list_only_own_patients(self, client: AsyncClient, auth_tokens):
        await client.post(
            "/api/v1/patients",
            headers=_auth(auth_tokens),
            json={
                "full_name": "Account A Patient",
                "gender": "male",
                "relationship_to_account": "self",
                "cnic": "42201-1234567-8",
            },
        )
        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        await client.post(
            "/api/v1/patients",
            headers=_auth(tokens_b),
            json={
                "full_name": "Account B Patient",
                "gender": "female",
                "relationship_to_account": "self",
                "cnic": "11111-1111111-1",
            },
        )
        list_a = await client.get("/api/v1/patients", headers=_auth(auth_tokens))
        assert list_a.status_code == 200
        data_a = list_a.json()
        assert data_a["total"] == 1
        assert data_a["items"][0]["full_name"] == "Account A Patient"

        list_b = await client.get("/api/v1/patients", headers=_auth(tokens_b))
        assert list_b.json()["total"] == 1
        assert list_b.json()["items"][0]["full_name"] == "Account B Patient"

    async def test_search_scoped_to_account(self, client: AsyncClient, auth_tokens):
        await client.post(
            "/api/v1/patients",
            headers=_auth(auth_tokens),
            json={
                "full_name": "Owner",
                "gender": "male",
                "relationship_to_account": "self",
                "cnic": "42201-1234567-8",
            },
        )
        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        resp = await client.get(
            "/api/v1/patients/search",
            headers=_auth(tokens_b),
            params={"medical_id": "42201-1234567-8"},
        )
        assert resp.status_code == 404


class TestListAndSoftDelete:
    async def test_list_paginated(self, client: AsyncClient, auth_tokens):
        for i in range(3):
            cnic = f"{10000 + i}-0000000-0"
            await client.post(
                "/api/v1/patients",
                headers=_auth(auth_tokens),
                json={
                    "full_name": f"Patient {i}",
                    "gender": "male",
                    "relationship_to_account": "self",
                    "cnic": cnic,
                },
            )
        resp = await client.get(
            "/api/v1/patients",
            headers=_auth(auth_tokens),
            params={"limit": 2, "offset": 0},
        )
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2

    async def test_soft_delete(self, client: AsyncClient, auth_tokens):
        resp = await client.post(
            "/api/v1/patients",
            headers=_auth(auth_tokens),
            json={
                "full_name": "To Delete",
                "gender": "male",
                "relationship_to_account": "self",
                "cnic": "42201-1234567-8",
            },
        )
        patient_id = resp.json()["id"]
        del_resp = await client.delete(f"/api/v1/patients/{patient_id}", headers=_auth(auth_tokens))
        assert del_resp.status_code == 204

        get_resp = await client.get(f"/api/v1/patients/{patient_id}", headers=_auth(auth_tokens))
        assert get_resp.status_code == 404

        list_resp = await client.get("/api/v1/patients", headers=_auth(auth_tokens))
        assert list_resp.json()["total"] == 0


class TestUpdatePatient:
    async def test_update_name(self, client: AsyncClient, auth_tokens):
        resp = await client.post(
            "/api/v1/patients",
            headers=_auth(auth_tokens),
            json={
                "full_name": "Old Name",
                "gender": "male",
                "relationship_to_account": "self",
                "cnic": "42201-1234567-8",
            },
        )
        patient_id = resp.json()["id"]
        patch_resp = await client.patch(
            f"/api/v1/patients/{patient_id}",
            headers=_auth(auth_tokens),
            json={"full_name": "New Name"},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["full_name"] == "New Name"

    async def test_update_nonexistent_returns_404(self, client: AsyncClient, auth_tokens):
        fake_id = str(uuid.uuid4())
        resp = await client.patch(
            f"/api/v1/patients/{fake_id}",
            headers=_auth(auth_tokens),
            json={"full_name": "Ghost"},
        )
        assert resp.status_code == 404
