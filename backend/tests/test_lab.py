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


class TestCatalogue:
    async def test_list_catalogue(self, client: AsyncClient, auth_tokens):
        resp = await client.get("/api/v1/lab-catalogue", headers=_auth(auth_tokens))
        assert resp.status_code == 200
        assert resp.json()["total"] >= 8

    async def test_list_filter_by_category(self, client: AsyncClient, auth_tokens):
        resp = await client.get(
            "/api/v1/lab-catalogue", headers=_auth(auth_tokens), params={"category": "imaging"}
        )
        assert resp.status_code == 200
        assert all(t["category"] == "imaging" for t in resp.json()["items"])

    async def test_list_search_by_name(self, client: AsyncClient, auth_tokens):
        resp = await client.get(
            "/api/v1/lab-catalogue", headers=_auth(auth_tokens), params={"q": "glucose"}
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    async def test_detail_with_ranges(self, client: AsyncClient, auth_tokens):
        list_resp = await client.get(
            "/api/v1/lab-catalogue", headers=_auth(auth_tokens), params={"q": "Hemoglobin"}
        )
        test_id = list_resp.json()["items"][0]["id"]
        resp = await client.get(f"/api/v1/lab-catalogue/{test_id}", headers=_auth(auth_tokens))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["reference_ranges"]) >= 2
        applies = {r["applies_to"] for r in data["reference_ranges"]}
        assert "male" in applies
        assert "female" in applies


class TestFileUpload:
    async def test_upload_png(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/files",
            headers=_auth(auth_tokens),
            files={"file": ("report.png", b"\x89PNG\r\n\x1a\nfakedata", "image/png")},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["original_filename"] == "report.png"
        assert data["content_type"] == "image/png"
        assert data["size_bytes"] > 0

    async def test_upload_pdf(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/files",
            headers=_auth(auth_tokens),
            files={"file": ("report.pdf", b"%PDF-1.4 fakedata", "application/pdf")},
        )
        assert resp.status_code == 201

    async def test_upload_disallowed_type(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/files",
            headers=_auth(auth_tokens),
            files={"file": ("script.exe", b"MZ...", "application/x-executable")},
        )
        assert resp.status_code == 422

    async def test_path_traversal_safe(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/files",
            headers=_auth(auth_tokens),
            files={"file": ("../../etc/passwd", b"\x89PNG\r\n\x1a\nfake", "image/png")},
        )
        assert resp.status_code == 201
        assert resp.json()["original_filename"] == "passwd"

    async def test_upload_on_soft_deleted_patient(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        await client.delete(f"/api/v1/patients/{patient['id']}", headers=_auth(auth_tokens))
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/files",
            headers=_auth(auth_tokens),
            files={"file": ("img.png", b"\x89PNG\r\n\x1a\n", "image/png")},
        )
        assert resp.status_code == 404


class TestFileDownload:
    async def test_download_own_file(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        content = b"\x89PNG\r\n\x1a\ntestcontent"
        upload_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/files",
            headers=_auth(auth_tokens),
            files={"file": ("test.png", content, "image/png")},
        )
        file_id = upload_resp.json()["id"]
        resp = await client.get(
            f"/api/v1/patients/{patient['id']}/files/{file_id}",
            headers=_auth(auth_tokens),
        )
        assert resp.status_code == 200
        assert resp.content == content

    async def test_download_cross_account_404(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        upload_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/files",
            headers=_auth(auth_tokens),
            files={"file": ("test.png", b"\x89PNGdata", "image/png")},
        )
        file_id = upload_resp.json()["id"]
        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        resp = await client.get(
            f"/api/v1/patients/{patient['id']}/files/{file_id}",
            headers=_auth(tokens_b),
        )
        assert resp.status_code == 404

    async def test_download_unknown_404(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        resp = await client.get(
            f"/api/v1/patients/{patient['id']}/files/{uuid.uuid4()}",
            headers=_auth(auth_tokens),
        )
        assert resp.status_code == 404


class TestFileDelete:
    async def test_soft_delete_file(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        upload_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/files",
            headers=_auth(auth_tokens),
            files={"file": ("test.png", b"\x89PNGdata", "image/png")},
        )
        file_id = upload_resp.json()["id"]
        del_resp = await client.delete(
            f"/api/v1/patients/{patient['id']}/files/{file_id}",
            headers=_auth(auth_tokens),
        )
        assert del_resp.status_code == 204
        get_resp = await client.get(
            f"/api/v1/patients/{patient['id']}/files/{file_id}",
            headers=_auth(auth_tokens),
        )
        assert get_resp.status_code == 404


class TestReports:
    async def test_create_report_no_file(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/reports",
            headers=_auth(auth_tokens),
            json={"category": "lab", "report_date": "2024-06-01", "lab_name": "City Lab"},
        )
        assert resp.status_code == 201
        assert resp.json()["category"] == "lab"
        assert resp.json()["file_id"] is None

    async def test_create_report_with_file(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        upload_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/files",
            headers=_auth(auth_tokens),
            files={"file": ("report.pdf", b"%PDF-1.4", "application/pdf")},
        )
        file_id = upload_resp.json()["id"]
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/reports",
            headers=_auth(auth_tokens),
            json={
                "category": "lab",
                "report_date": "2024-06-01",
                "file_id": file_id,
            },
        )
        assert resp.status_code == 201
        assert resp.json()["file_id"] == file_id

    async def test_list_reports_paginated(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        pid = patient["id"]
        for i in range(3):
            await client.post(
                f"/api/v1/patients/{pid}/reports",
                headers=_auth(auth_tokens),
                json={"category": "lab", "report_date": f"2024-0{i + 1}-01"},
            )
        resp = await client.get(
            f"/api/v1/patients/{pid}/reports",
            headers=_auth(auth_tokens),
            params={"limit": 2},
        )
        assert resp.json()["total"] == 3
        assert len(resp.json()["items"]) == 2

    async def test_report_detail_with_results(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        report_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/reports",
            headers=_auth(auth_tokens),
            json={"category": "lab", "report_date": "2024-06-01"},
        )
        rid = report_resp.json()["id"]
        await client.post(
            f"/api/v1/patients/{patient['id']}/reports/{rid}/results",
            headers=_auth(auth_tokens),
            json={
                "display_name": "Glucose",
                "value_numeric": 95,
                "effective_date": "2024-06-01",
            },
        )
        resp = await client.get(
            f"/api/v1/patients/{patient['id']}/reports/{rid}",
            headers=_auth(auth_tokens),
        )
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 1

    async def test_report_soft_delete_cascades_results(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        report_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/reports",
            headers=_auth(auth_tokens),
            json={"category": "lab", "report_date": "2024-06-01"},
        )
        rid = report_resp.json()["id"]
        result_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/reports/{rid}/results",
            headers=_auth(auth_tokens),
            json={
                "display_name": "Test",
                "value_numeric": 1,
                "effective_date": "2024-06-01",
            },
        )
        res_id = result_resp.json()["id"]
        await client.delete(
            f"/api/v1/patients/{patient['id']}/reports/{rid}",
            headers=_auth(auth_tokens),
        )
        get_result = await client.get(
            f"/api/v1/patients/{patient['id']}/results/{res_id}",
            headers=_auth(auth_tokens),
        )
        assert get_result.status_code == 404


class TestResults:
    async def test_create_from_catalogue(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        cat_resp = await client.get(
            "/api/v1/lab-catalogue",
            headers=_auth(auth_tokens),
            params={"q": "Fasting Blood Glucose"},
        )
        test_id = cat_resp.json()["items"][0]["id"]
        report_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/reports",
            headers=_auth(auth_tokens),
            json={"category": "lab", "report_date": "2024-06-01"},
        )
        rid = report_resp.json()["id"]
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/reports/{rid}/results",
            headers=_auth(auth_tokens),
            json={
                "test_id": test_id,
                "display_name": "Fasting Blood Glucose",
                "value_numeric": 92,
                "effective_date": "2024-06-01",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["test_id"] == test_id
        assert data["loinc_code"] == "1558-6"
        assert data["unit"] == "mg/dL"

    async def test_create_free_text_result(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        report_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/reports",
            headers=_auth(auth_tokens),
            json={"category": "lab", "report_date": "2024-06-01"},
        )
        rid = report_resp.json()["id"]
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/reports/{rid}/results",
            headers=_auth(auth_tokens),
            json={
                "display_name": "Custom Test",
                "value_text": "Positive",
                "effective_date": "2024-06-01",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["test_id"] is None
        assert resp.json()["value_text"] == "Positive"

    async def test_value_integrity_rejected(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        report_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/reports",
            headers=_auth(auth_tokens),
            json={"category": "lab", "report_date": "2024-06-01"},
        )
        rid = report_resp.json()["id"]
        resp = await client.post(
            f"/api/v1/patients/{patient['id']}/reports/{rid}/results",
            headers=_auth(auth_tokens),
            json={
                "display_name": "Test",
                "value_numeric": 5,
                "value_text": "also text",
                "effective_date": "2024-06-01",
            },
        )
        assert resp.status_code == 422

    async def test_multiple_results_per_report(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        report_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/reports",
            headers=_auth(auth_tokens),
            json={"category": "lab", "report_date": "2024-06-01"},
        )
        rid = report_resp.json()["id"]
        for name in ["Test A", "Test B"]:
            await client.post(
                f"/api/v1/patients/{patient['id']}/reports/{rid}/results",
                headers=_auth(auth_tokens),
                json={
                    "display_name": name,
                    "value_numeric": 1,
                    "effective_date": "2024-06-01",
                },
            )
        resp = await client.get(
            f"/api/v1/patients/{patient['id']}/reports/{rid}/results",
            headers=_auth(auth_tokens),
        )
        assert resp.json()["total"] == 2


class TestResultFHIR:
    async def test_fhir_valid_r4(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        report_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/reports",
            headers=_auth(auth_tokens),
            json={"category": "lab", "report_date": "2024-06-01"},
        )
        rid = report_resp.json()["id"]
        cat_resp = await client.get(
            "/api/v1/lab-catalogue",
            headers=_auth(auth_tokens),
            params={"q": "Fasting Blood Glucose"},
        )
        test_id = cat_resp.json()["items"][0]["id"]
        result_resp = await client.post(
            f"/api/v1/patients/{patient['id']}/reports/{rid}/results",
            headers=_auth(auth_tokens),
            json={
                "test_id": test_id,
                "display_name": "Fasting Blood Glucose",
                "value_numeric": 95,
                "effective_date": "2024-06-01",
            },
        )
        res_id = result_resp.json()["id"]
        resp = await client.get(
            f"/api/v1/patients/{patient['id']}/results/{res_id}/fhir",
            headers=_auth(auth_tokens),
        )
        assert resp.status_code == 200
        fhir = resp.json()
        assert fhir["resourceType"] == "Observation"
        assert fhir["category"][0]["coding"][0]["code"] == "laboratory"
        assert fhir["code"]["coding"][0]["code"] == "1558-6"

        from fhir.resources.observation import Observation

        Observation(**fhir)


class TestLabScoping:
    async def test_cross_account_report_404(self, client: AsyncClient, auth_tokens):
        patient_a = await _create_patient(client, auth_tokens)
        report_resp = await client.post(
            f"/api/v1/patients/{patient_a['id']}/reports",
            headers=_auth(auth_tokens),
            json={"category": "lab", "report_date": "2024-06-01"},
        )
        rid = report_resp.json()["id"]
        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        resp = await client.get(
            f"/api/v1/patients/{patient_a['id']}/reports/{rid}",
            headers=_auth(tokens_b),
        )
        assert resp.status_code == 404

    async def test_cross_account_result_404(self, client: AsyncClient, auth_tokens):
        patient_a = await _create_patient(client, auth_tokens)
        report_resp = await client.post(
            f"/api/v1/patients/{patient_a['id']}/reports",
            headers=_auth(auth_tokens),
            json={"category": "lab", "report_date": "2024-06-01"},
        )
        rid = report_resp.json()["id"]
        result_resp = await client.post(
            f"/api/v1/patients/{patient_a['id']}/reports/{rid}/results",
            headers=_auth(auth_tokens),
            json={
                "display_name": "Private",
                "value_numeric": 1,
                "effective_date": "2024-06-01",
            },
        )
        res_id = result_resp.json()["id"]
        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        resp = await client.get(
            f"/api/v1/patients/{patient_a['id']}/results/{res_id}",
            headers=_auth(tokens_b),
        )
        assert resp.status_code == 404

    async def test_cross_account_file_download_404(self, client: AsyncClient, auth_tokens):
        patient_a = await _create_patient(client, auth_tokens)
        upload_resp = await client.post(
            f"/api/v1/patients/{patient_a['id']}/files",
            headers=_auth(auth_tokens),
            files={"file": ("test.png", b"\x89PNGdata", "image/png")},
        )
        file_id = upload_resp.json()["id"]
        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        resp = await client.get(
            f"/api/v1/patients/{patient_a['id']}/files/{file_id}",
            headers=_auth(tokens_b),
        )
        assert resp.status_code == 404
