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


async def _get_test_id(client: AsyncClient, tokens: dict, q: str) -> str:
    resp = await client.get("/api/v1/lab-catalogue", headers=_auth(tokens), params={"q": q})
    return resp.json()["items"][0]["id"]


class TestSummaryPopulated:
    async def test_summary_all_sections(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        pid = patient["id"]
        h = _auth(auth_tokens)

        await client.post(
            f"/api/v1/patients/{pid}/conditions",
            headers=h,
            json={"display_name": "Hypertension", "clinical_status": "active"},
        )
        await client.post(
            f"/api/v1/patients/{pid}/conditions",
            headers=h,
            json={"display_name": "Resolved Cold", "clinical_status": "resolved"},
        )

        await client.post(
            f"/api/v1/patients/{pid}/medications",
            headers=h,
            json={"display_name": "Metformin", "status": "active"},
        )
        await client.post(
            f"/api/v1/patients/{pid}/medications",
            headers=h,
            json={"display_name": "Old Med", "status": "stopped"},
        )

        await client.post(
            f"/api/v1/patients/{pid}/allergies",
            headers=h,
            json={
                "display_name": "Peanuts",
                "category": "food",
                "clinical_status": "active",
            },
        )
        await client.post(
            f"/api/v1/patients/{pid}/allergies",
            headers=h,
            json={
                "display_name": "Resolved Allergy",
                "category": "food",
                "clinical_status": "resolved",
            },
        )

        test_id = await _get_test_id(client, auth_tokens, "Fasting Blood Glucose")
        report_resp = await client.post(
            f"/api/v1/patients/{pid}/reports",
            headers=h,
            json={"category": "lab", "report_date": "2024-06-01"},
        )
        rid = report_resp.json()["id"]
        await client.post(
            f"/api/v1/patients/{pid}/reports/{rid}/results",
            headers=h,
            json={
                "test_id": test_id,
                "display_name": "FBG",
                "value_numeric": 92,
                "effective_date": "2024-06-01",
            },
        )

        resp = await client.get(f"/api/v1/patients/{pid}/summary", headers=h)
        assert resp.status_code == 200
        data = resp.json()

        assert data["patient"]["id"] == pid
        assert data["patient"]["full_name"] == "Test Patient"

        assert len(data["active_conditions"]) == 1
        assert data["active_conditions"][0]["display_name"] == "Hypertension"

        assert len(data["current_medications"]) == 1
        assert data["current_medications"][0]["display_name"] == "Metformin"

        assert len(data["allergies"]) == 1
        assert data["allergies"][0]["display_name"] == "Peanuts"

        assert len(data["recent_results"]) == 1
        assert data["recent_results"][0]["normality_status"] == "in_range"

        assert data["counts"]["conditions"] >= 1
        assert data["counts"]["medications"] >= 1
        assert data["counts"]["allergies"] >= 1


class TestSummaryEmpty:
    async def test_empty_patient(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        resp = await client.get(
            f"/api/v1/patients/{patient['id']}/summary",
            headers=_auth(auth_tokens),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["active_conditions"] == []
        assert data["current_medications"] == []
        assert data["allergies"] == []
        assert data["recent_results"] == []
        assert data["counts"]["conditions"] == 0
        assert data["counts"]["medications"] == 0


class TestSummaryRecentResults:
    async def test_recent_results_bounded(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        pid = patient["id"]
        h = _auth(auth_tokens)
        test_id = await _get_test_id(client, auth_tokens, "Fasting Blood Glucose")

        for i in range(15):
            report_resp = await client.post(
                f"/api/v1/patients/{pid}/reports",
                headers=h,
                json={"category": "lab", "report_date": f"2024-{(i % 12) + 1:02d}-01"},
            )
            rid = report_resp.json()["id"]
            await client.post(
                f"/api/v1/patients/{pid}/reports/{rid}/results",
                headers=h,
                json={
                    "test_id": test_id,
                    "display_name": "FBG",
                    "value_numeric": 80 + i,
                    "effective_date": f"2024-{(i % 12) + 1:02d}-01",
                },
            )

        resp = await client.get(
            f"/api/v1/patients/{pid}/summary",
            headers=h,
            params={"recent_results": 5},
        )
        assert resp.status_code == 200
        results = resp.json()["recent_results"]
        assert len(results) == 5
        dates = [r["effective_date"] for r in results]
        assert dates == sorted(dates, reverse=True)

    async def test_recent_results_include_normality(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        pid = patient["id"]
        h = _auth(auth_tokens)
        test_id = await _get_test_id(client, auth_tokens, "Fasting Blood Glucose")

        report_resp = await client.post(
            f"/api/v1/patients/{pid}/reports",
            headers=h,
            json={"category": "lab", "report_date": "2024-06-01"},
        )
        rid = report_resp.json()["id"]
        await client.post(
            f"/api/v1/patients/{pid}/reports/{rid}/results",
            headers=h,
            json={
                "test_id": test_id,
                "display_name": "FBG",
                "value_numeric": 150,
                "effective_date": "2024-06-01",
            },
        )

        resp = await client.get(f"/api/v1/patients/{pid}/summary", headers=h)
        r = resp.json()["recent_results"][0]
        assert r["normality_status"] == "above_high"


class TestSummarySoftDelete:
    async def test_soft_deleted_excluded(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        pid = patient["id"]
        h = _auth(auth_tokens)

        cond_resp = await client.post(
            f"/api/v1/patients/{pid}/conditions",
            headers=h,
            json={"display_name": "To Delete", "clinical_status": "active"},
        )
        await client.delete(
            f"/api/v1/patients/{pid}/conditions/{cond_resp.json()['id']}", headers=h
        )

        resp = await client.get(f"/api/v1/patients/{pid}/summary", headers=h)
        assert resp.json()["active_conditions"] == []


class TestSummaryScoping:
    async def test_cross_account_404(self, client: AsyncClient, auth_tokens):
        patient_a = await _create_patient(client, auth_tokens)
        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        resp = await client.get(
            f"/api/v1/patients/{patient_a['id']}/summary",
            headers=_auth(tokens_b),
        )
        assert resp.status_code == 404
