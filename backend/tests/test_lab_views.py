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


async def _create_report_with_result(
    client: AsyncClient,
    tokens: dict,
    pid: str,
    test_id: str | None,
    display_name: str,
    value_numeric: float | None = None,
    value_text: str | None = None,
    effective_date: str = "2024-06-01",
    unit: str | None = None,
):
    report_resp = await client.post(
        f"/api/v1/patients/{pid}/reports",
        headers=_auth(tokens),
        json={"category": "lab", "report_date": effective_date},
    )
    rid = report_resp.json()["id"]
    body = {
        "display_name": display_name,
        "effective_date": effective_date,
    }
    if test_id:
        body["test_id"] = test_id
    if value_numeric is not None:
        body["value_numeric"] = value_numeric
    if value_text is not None:
        body["value_text"] = value_text
    if unit:
        body["unit"] = unit
    result_resp = await client.post(
        f"/api/v1/patients/{pid}/reports/{rid}/results",
        headers=_auth(tokens),
        json=body,
    )
    return report_resp.json(), result_resp.json()


class TestEnrichedReportDetail:
    async def test_report_detail_with_normality(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        pid = patient["id"]
        test_id = await _get_test_id(client, auth_tokens, "Fasting Blood Glucose")
        report, result = await _create_report_with_result(
            client, auth_tokens, pid, test_id, "FBG", value_numeric=92
        )
        resp = await client.get(
            f"/api/v1/patients/{pid}/reports/{report['id']}",
            headers=_auth(auth_tokens),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 1
        r = data["results"][0]
        assert "normality" in r
        assert r["normality"]["status"] == "in_range"
        assert r["normality"]["range_low"] is not None

    async def test_report_detail_out_of_range(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        pid = patient["id"]
        test_id = await _get_test_id(client, auth_tokens, "Fasting Blood Glucose")
        report, result = await _create_report_with_result(
            client, auth_tokens, pid, test_id, "FBG", value_numeric=150
        )
        resp = await client.get(
            f"/api/v1/patients/{pid}/reports/{report['id']}",
            headers=_auth(auth_tokens),
        )
        r = resp.json()["results"][0]
        assert r["normality"]["status"] == "above_high"

    async def test_report_detail_includes_file_ref(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        pid = patient["id"]
        upload_resp = await client.post(
            f"/api/v1/patients/{pid}/files",
            headers=_auth(auth_tokens),
            files={"file": ("report.pdf", b"%PDF-1.4", "application/pdf")},
        )
        file_id = upload_resp.json()["id"]
        report_resp = await client.post(
            f"/api/v1/patients/{pid}/reports",
            headers=_auth(auth_tokens),
            json={"category": "lab", "report_date": "2024-06-01", "file_id": file_id},
        )
        resp = await client.get(
            f"/api/v1/patients/{pid}/reports/{report_resp.json()['id']}",
            headers=_auth(auth_tokens),
        )
        assert resp.json()["file_ref"] is not None
        assert resp.json()["file_ref"]["id"] == file_id


class TestTimeline:
    async def test_timeline_newest_first(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        pid = patient["id"]
        for d in ["2024-01-01", "2024-06-01", "2024-12-01"]:
            await client.post(
                f"/api/v1/patients/{pid}/reports",
                headers=_auth(auth_tokens),
                json={"category": "lab", "report_date": d},
            )
        resp = await client.get(f"/api/v1/patients/{pid}/timeline", headers=_auth(auth_tokens))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        dates = [e["report_date"] for e in data["items"]]
        assert dates == sorted(dates, reverse=True)

    async def test_timeline_filter_by_category(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        pid = patient["id"]
        await client.post(
            f"/api/v1/patients/{pid}/reports",
            headers=_auth(auth_tokens),
            json={"category": "lab", "report_date": "2024-06-01"},
        )
        await client.post(
            f"/api/v1/patients/{pid}/reports",
            headers=_auth(auth_tokens),
            json={"category": "imaging", "report_date": "2024-06-01"},
        )
        resp = await client.get(
            f"/api/v1/patients/{pid}/timeline",
            headers=_auth(auth_tokens),
            params={"category": "lab"},
        )
        assert resp.json()["total"] == 1

    async def test_timeline_out_of_range_flag(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        pid = patient["id"]
        test_id = await _get_test_id(client, auth_tokens, "Fasting Blood Glucose")
        await _create_report_with_result(
            client, auth_tokens, pid, test_id, "FBG", value_numeric=150
        )
        resp = await client.get(f"/api/v1/patients/{pid}/timeline", headers=_auth(auth_tokens))
        assert resp.json()["items"][0]["has_out_of_range"] is True

    async def test_timeline_paginated(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        pid = patient["id"]
        for i in range(3):
            await client.post(
                f"/api/v1/patients/{pid}/reports",
                headers=_auth(auth_tokens),
                json={"category": "lab", "report_date": f"2024-0{i + 1}-01"},
            )
        resp = await client.get(
            f"/api/v1/patients/{pid}/timeline",
            headers=_auth(auth_tokens),
            params={"limit": 2},
        )
        assert resp.json()["total"] == 3
        assert len(resp.json()["items"]) == 2

    async def test_timeline_scoping(self, client: AsyncClient, auth_tokens):
        patient_a = await _create_patient(client, auth_tokens)
        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        resp = await client.get(
            f"/api/v1/patients/{patient_a['id']}/timeline",
            headers=_auth(tokens_b),
        )
        assert resp.status_code == 404


class TestNormality:
    async def test_normality_in_range(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        pid = patient["id"]
        test_id = await _get_test_id(client, auth_tokens, "Fasting Blood Glucose")
        _, result = await _create_report_with_result(
            client, auth_tokens, pid, test_id, "FBG", value_numeric=85
        )
        resp = await client.get(
            f"/api/v1/patients/{pid}/results/{result['id']}/normality",
            headers=_auth(auth_tokens),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_range"
        assert resp.json()["range_low"] is not None

    async def test_normality_unit_mismatch(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        pid = patient["id"]
        test_id = await _get_test_id(client, auth_tokens, "Fasting Blood Glucose")
        _, result = await _create_report_with_result(
            client, auth_tokens, pid, test_id, "FBG", value_numeric=5.5, unit="mmol/L"
        )
        resp = await client.get(
            f"/api/v1/patients/{pid}/results/{result['id']}/normality",
            headers=_auth(auth_tokens),
        )
        assert resp.json()["status"] == "unknown"
        assert "Unit mismatch" in resp.json()["reason"]

    async def test_normality_scoping(self, client: AsyncClient, auth_tokens):
        patient_a = await _create_patient(client, auth_tokens)
        pid = patient_a["id"]
        test_id = await _get_test_id(client, auth_tokens, "Fasting Blood Glucose")
        _, result = await _create_report_with_result(
            client, auth_tokens, pid, test_id, "FBG", value_numeric=85
        )
        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        resp = await client.get(
            f"/api/v1/patients/{pid}/results/{result['id']}/normality",
            headers=_auth(tokens_b),
        )
        assert resp.status_code == 404


class TestLabTrend:
    async def test_trend_ascending_with_normality(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        pid = patient["id"]
        test_id = await _get_test_id(client, auth_tokens, "Fasting Blood Glucose")
        for d, v in [("2024-01-01", 85), ("2024-06-01", 105), ("2024-12-01", 92)]:
            await _create_report_with_result(
                client, auth_tokens, pid, test_id, "FBG", value_numeric=v, effective_date=d
            )
        resp = await client.get(
            f"/api/v1/patients/{pid}/lab-trend",
            headers=_auth(auth_tokens),
            params={"test": "fasting_blood_glucose"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["chartable"] is True
        assert data["test_key"] == "fasting_blood_glucose"
        assert len(data["points"]) == 3
        dates = [p["effective_date"] for p in data["points"]]
        assert dates == sorted(dates)
        assert data["points"][0]["normality_status"] == "in_range"
        assert data["points"][1]["normality_status"] == "above_high"
        assert data["range_low"] is not None
        assert data["range_high"] is not None

    async def test_trend_empty_returns_empty(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        resp = await client.get(
            f"/api/v1/patients/{patient['id']}/lab-trend",
            headers=_auth(auth_tokens),
            params={"test": "fasting_blood_glucose"},
        )
        assert resp.status_code == 200
        assert resp.json()["points"] == []

    async def test_trend_scoping(self, client: AsyncClient, auth_tokens):
        patient_a = await _create_patient(client, auth_tokens)
        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        resp = await client.get(
            f"/api/v1/patients/{patient_a['id']}/lab-trend",
            headers=_auth(tokens_b),
            params={"test": "fasting_blood_glucose"},
        )
        assert resp.status_code == 404

    async def test_trend_with_date_range(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        pid = patient["id"]
        test_id = await _get_test_id(client, auth_tokens, "Fasting Blood Glucose")
        for d in ["2024-01-01", "2024-06-01", "2024-12-01"]:
            await _create_report_with_result(
                client, auth_tokens, pid, test_id, "FBG", value_numeric=90, effective_date=d
            )
        resp = await client.get(
            f"/api/v1/patients/{pid}/lab-trend",
            headers=_auth(auth_tokens),
            params={"test": "fasting_blood_glucose", "from": "2024-05-01", "to": "2024-07-01"},
        )
        assert len(resp.json()["points"]) == 1
