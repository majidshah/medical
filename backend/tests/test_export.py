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


async def _seed_clinical_data(client: AsyncClient, tokens: dict, pid: str):
    h = _auth(tokens)
    await client.post(
        f"/api/v1/patients/{pid}/conditions",
        headers=h,
        json={"display_name": "Hypertension", "code": "38341003"},
    )
    await client.post(
        f"/api/v1/patients/{pid}/allergies",
        headers=h,
        json={"display_name": "Peanuts", "category": "food", "criticality": "high"},
    )
    await client.post(
        f"/api/v1/patients/{pid}/medications",
        headers=h,
        json={"display_name": "Metformin", "dosage": "500mg"},
    )
    await client.post(
        f"/api/v1/patients/{pid}/immunizations",
        headers=h,
        json={"vaccine_display_name": "BCG", "occurrence_date": "2024-01-01"},
    )
    await client.post(
        f"/api/v1/patients/{pid}/family-history",
        headers=h,
        json={"relationship": "father", "condition_display_name": "Diabetes"},
    )

    cat_resp = await client.get(
        "/api/v1/lab-catalogue", headers=h, params={"q": "Fasting Blood Glucose"}
    )
    test_id = cat_resp.json()["items"][0]["id"]
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
            "display_name": "Fasting Blood Glucose",
            "value_numeric": 95,
            "effective_date": "2024-06-01",
        },
    )


class TestFHIRBundle:
    async def test_bundle_populated(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        pid = patient["id"]
        await _seed_clinical_data(client, auth_tokens, pid)

        resp = await client.get(f"/api/v1/patients/{pid}/export/fhir", headers=_auth(auth_tokens))
        assert resp.status_code == 200
        assert "fhir" in resp.headers["content-type"]
        bundle = resp.json()
        assert bundle["resourceType"] == "Bundle"
        assert bundle["type"] == "collection"

        types = {e["resource"]["resourceType"] for e in bundle["entry"]}
        assert "Patient" in types
        assert "Condition" in types
        assert "AllergyIntolerance" in types
        assert "MedicationStatement" in types
        assert "Immunization" in types
        assert "FamilyMemberHistory" in types
        assert "Observation" in types

    async def test_bundle_entries_have_fullurl(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        pid = patient["id"]
        await _seed_clinical_data(client, auth_tokens, pid)

        resp = await client.get(f"/api/v1/patients/{pid}/export/fhir", headers=_auth(auth_tokens))
        for entry in resp.json()["entry"]:
            assert "fullUrl" in entry
            assert entry["fullUrl"].startswith("urn:uuid:")

    async def test_bundle_patient_reference_resolves(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        pid = patient["id"]
        await _seed_clinical_data(client, auth_tokens, pid)

        resp = await client.get(f"/api/v1/patients/{pid}/export/fhir", headers=_auth(auth_tokens))
        bundle = resp.json()
        patient_entry = next(
            e for e in bundle["entry"] if e["resource"]["resourceType"] == "Patient"
        )
        patient_id_in_bundle = patient_entry["resource"]["id"]

        condition_entry = next(
            e for e in bundle["entry"] if e["resource"]["resourceType"] == "Condition"
        )
        assert f"Patient/{patient_id_in_bundle}" in str(condition_entry["resource"]["subject"])

    async def test_bundle_empty_patient(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        resp = await client.get(
            f"/api/v1/patients/{patient['id']}/export/fhir",
            headers=_auth(auth_tokens),
        )
        assert resp.status_code == 200
        bundle = resp.json()
        assert bundle["resourceType"] == "Bundle"
        assert len(bundle["entry"]) == 1
        assert bundle["entry"][0]["resource"]["resourceType"] == "Patient"

    async def test_bundle_excludes_soft_deleted(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        pid = patient["id"]
        h = _auth(auth_tokens)
        cond_resp = await client.post(
            f"/api/v1/patients/{pid}/conditions",
            headers=h,
            json={"display_name": "To Delete"},
        )
        await client.delete(
            f"/api/v1/patients/{pid}/conditions/{cond_resp.json()['id']}", headers=h
        )
        resp = await client.get(f"/api/v1/patients/{pid}/export/fhir", headers=h)
        types = [e["resource"]["resourceType"] for e in resp.json()["entry"]]
        assert "Condition" not in types

    async def test_bundle_scoping(self, client: AsyncClient, auth_tokens):
        patient_a = await _create_patient(client, auth_tokens)
        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        resp = await client.get(
            f"/api/v1/patients/{patient_a['id']}/export/fhir",
            headers=_auth(tokens_b),
        )
        assert resp.status_code == 404

    async def test_bundle_entries_validate_fhir(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        pid = patient["id"]
        await _seed_clinical_data(client, auth_tokens, pid)

        resp = await client.get(f"/api/v1/patients/{pid}/export/fhir", headers=_auth(auth_tokens))
        bundle = resp.json()
        from fhir.resources.allergyintolerance import AllergyIntolerance
        from fhir.resources.condition import Condition
        from fhir.resources.familymemberhistory import FamilyMemberHistory
        from fhir.resources.immunization import Immunization
        from fhir.resources.medicationstatement import MedicationStatement
        from fhir.resources.observation import Observation
        from fhir.resources.patient import Patient

        validators = {
            "Patient": Patient,
            "Condition": Condition,
            "AllergyIntolerance": AllergyIntolerance,
            "MedicationStatement": MedicationStatement,
            "Immunization": Immunization,
            "FamilyMemberHistory": FamilyMemberHistory,
            "Observation": Observation,
        }
        for entry in bundle["entry"]:
            rt = entry["resource"]["resourceType"]
            if rt in validators:
                validators[rt](**entry["resource"])


class TestPDFExport:
    async def test_pdf_populated(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        pid = patient["id"]
        await _seed_clinical_data(client, auth_tokens, pid)

        resp = await client.get(f"/api/v1/patients/{pid}/export/pdf", headers=_auth(auth_tokens))
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert len(resp.content) > 100
        assert resp.content[:5] == b"%PDF-"

    async def test_pdf_empty_patient(self, client: AsyncClient, auth_tokens):
        patient = await _create_patient(client, auth_tokens)
        resp = await client.get(
            f"/api/v1/patients/{patient['id']}/export/pdf",
            headers=_auth(auth_tokens),
        )
        assert resp.status_code == 200
        assert resp.content[:5] == b"%PDF-"

    async def test_pdf_scoping(self, client: AsyncClient, auth_tokens):
        patient_a = await _create_patient(client, auth_tokens)
        tokens_b = await _register_and_login(client, "b@example.com", "securepass123")
        resp = await client.get(
            f"/api/v1/patients/{patient_a['id']}/export/pdf",
            headers=_auth(tokens_b),
        )
        assert resp.status_code == 404
