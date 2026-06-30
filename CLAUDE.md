# CLAUDE.md — MedVault

This file is read at the start of every Claude Code session. It defines what we are
building, the conventions to follow, and the rules that must not be broken. Treat it
as authoritative. If a request conflicts with this file, raise the conflict before acting.

---

## 1. What we are building

MedVault is a patient-centred personal health record (PHR) platform for the Pakistani
market. Patients and families store, manage, and derive insight from their complete
health profile in one secure place.

- Phase 1: web application (this is what we build now).
- Phase 2 (later): React Native mobile apps consuming the same REST API. Do not build
  mobile now, but never make a backend decision that would block it.

All health data is modelled on **HL7 FHIR R4**. This is a hard requirement, not a
preference. Coding systems: LOINC for lab tests, SNOMED CT for conditions and allergies,
Pakistan EPI schedule for immunizations.

---

## 2. Tech stack (fixed for MVP — do not substitute without asking)

- Backend: Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), Alembic for
  migrations, Uvicorn.
- Database: PostgreSQL 16.
- Frontend: React (Vite), TypeScript, with i18n scaffolding from day one (English now,
  Urdu later — never hardcode user-facing strings).
- Auth: JWT access + refresh tokens.
- Tests: pytest (backend), Vitest + React Testing Library (frontend).
- Lint/format: ruff + black (backend), eslint + prettier (frontend).

If you believe a library choice is wrong, say so and propose an alternative — do not
silently swap it.

---

## 3. Repository structure

This is a monorepo. Maintain this layout:

```
/backend        FastAPI service
  /app
    /api        routers (versioned: /api/v1/...)
    /core       config, security, settings (env-driven)
    /models     SQLAlchemy ORM models
    /schemas    Pydantic request/response models
    /fhir       FHIR R4 mapping layer (ORM <-> FHIR resources)
    /services   business logic (thin routers, fat services)
    /db         session, base, migrations entrypoint
  /alembic      migration scripts
  /tests
/frontend       React + Vite + TS
  /src
    /api        typed API client (generated from OpenAPI where possible)
    /components
    /pages
    /i18n       translation files (en/ now, ur/ later)
    /lib
  /tests
/infra          IaC, deployment configs, Dockerfiles (added at deploy phase)
/docs           architecture notes, ADRs, this brief's companion spec
```

---

## 4. Architectural rules

- **REST, versioned, stateless.** All endpoints under `/api/v1`. The frontend and the
  future mobile app are independent clients of this API. Never couple the API to one
  client.
- **FHIR is the data model.** Each clinical entity maps to a FHIR R4 resource (see the
  spec for the table). Store data in normalized Postgres tables, but the API exposes and
  exports FHIR-shaped resources. Keep a dedicated `/fhir` mapping layer — do not scatter
  FHIR logic through routers.
- **Thin routers, fat services.** Routers validate and delegate. Business logic lives in
  `/services`. This keeps logic testable and reusable by future clients.
- **Async all the way.** Async SQLAlchemy, async endpoints. Do not mix sync DB calls into
  the request path.
- **Config via environment variables only.** No secrets, connection strings, or hosts in
  code. Read everything through `core/config.py` (pydantic-settings). This is what makes
  containerization and multi-environment deploys painless later.
- **Multi-tenant by account.** Every patient profile belongs to an account. Every query
  that returns patient data MUST be scoped to the authenticated account. There is no
  endpoint that returns another account's data. Treat a missing scope filter as a bug.

---

## 5. Reference data & roles

### Reference data is admin-configurable by design

Lab reference data — departments, panels, tests, reference ranges, and lab sources — is
modelled as EDITABLE DATA (normal tables, never enums or hardcoded values), designed to be
managed by an admin. Specifically:
- Departments → Panels → Tests is a data hierarchy (panel optional; one test per header).
- Reference ranges are keyed by `applies_to` (the model accepts ANY value:
  general/male/female/pediatric/pregnancy/…), stored as data rows, not hardcoded.
- Each reference range carries a `lab` attribution (e.g. IDC), so per-lab ranges are
  supported as data.
- Reference ranges that are not clinically validated carry `needs_clinical_review = true`
  and a `source`; the UI shows an indicative-ranges disclaimer.

Build reference-data models to support admin editing. Never fabricate clinical reference
values (ranges, LOINC codes) — store null/leave unflagged rather than invent, and flag for
review.

### Roles & authorization

MedVault has more than one privilege level. The default is an ACCOUNT (sees only its own
family's patient data, enforced via get_current_account). Above/beside it, an extensible
ROLE/PERMISSION system governs elevated capabilities (starting with ADMIN, who manages
global reference data). Rules:
- Roles/permissions are a proper extensible system (roles table + permission checks), not a
  single boolean flag — future roles (e.g. clinician/kiosk access) must fit the same model.
- Admin (and any elevated role) is a DISTINCT authorization boundary. Admin-only endpoints
  require an explicit admin permission check — never assume; never let account-level auth
  stand in for admin auth.
- Patient data remains account-scoped regardless of role. An admin manages reference data
  (departments/panels/tests/ranges/labs), NOT other accounts' patient health records, unless
  a specific, separately-designed and consented capability says otherwise.
- Elevating an account to admin is itself a privileged action (seeded/controlled, not
  self-service). Guard role assignment carefully.
- Audit elevated actions: record admin changes to reference data (who/what/when), consistent
  with the existing audit pattern; never log PHI.

---

## 6. Security & compliance (non-negotiable)

Pakistan's personal data protection law is still maturing, so we build to GDPR/HIPAA-grade
standards as the baseline. This protects users now and unblocks expansion later.

- HTTPS everywhere (enforced at deploy).
- Passwords hashed with bcrypt/argon2 — never stored or logged in plaintext.
- JWT secrets, DB credentials, and all keys come from env vars, never committed.
- **Audit logging:** record who accessed or modified which patient's data, and when.
  This is a first-class feature, not an afterthought.
- Encrypt sensitive data at rest (DB-level) and in transit.
- Never log PII or health data in application logs.
- Input validation on every endpoint via Pydantic. Never trust client input.
- Medical IDs are unique system-wide. Enforce uniqueness at the DB constraint level.

---

## 7. Workflow conventions

- **Branching:** trunk-based. `main` is protected and always deployable. Work on
  short-lived `feature/<name>` branches, open a PR, merge after CI passes.
- **Commits:** conventional commits (`feat:`, `fix:`, `chore:`, `test:`, `docs:`).
- **Every feature ships with tests.** No merge without passing tests. Aim for meaningful
  coverage of services and API contracts, not coverage theatre.
- **Migrations:** every schema change has an Alembic migration. Never edit the DB by hand.
- **Before declaring a task done:** run linters and the test suite, and confirm they pass.
- When you finish a unit of work, summarize what changed and what the human should review
  or approve — especially anything touching auth, data deletion, or access scope.

---

## 8. Hard boundaries (things the human does, not you)

- Entering real secrets/credentials/keys (you reference them by name only).
- Creating cloud accounts, buying domains, upgrading paid tiers.
- Running migrations or deploys against production (you prepare; human triggers).
- Any irreversible action (dropping tables, force-push, deleting data) — flag and wait
  for explicit confirmation.

---

## 9. MVP build order

Build in vertical slices — each slice is end-to-end (DB → API → UI → tests) and
deployable. Suggested order:

1. **Foundation:** repo scaffold, config, DB session, health-check endpoint, CI pipeline.
2. **Auth & accounts:** registration, login, JWT access/refresh, account model.
3. **Family & patients:** patient profiles under an account, Medical ID generation
   (CNIC and `{guardian_CNIC}-D{n}` for dependents), system-wide uniqueness.
4. **Health profile:** the FHIR-aligned clinical entities (conditions, allergies,
   medications, immunizations, etc.), one resource type at a time.
5. **Lab/imaging reports:** file upload + storage, manual structured entry against the
   LOINC test catalogue, report detail view, timeline, trend charts, normality colouring.
6. **Summary dashboard:** unified active conditions / medications / allergies / recent
   results for the selected patient.
7. **Export:** PDF summary and FHIR JSON bundle.

Do one slice at a time. Do not scaffold all of it at once. Finish, test, and review a
slice before starting the next.

---

## 10. Out of scope for MVP (do not build)

OCR/AI extraction, direct lab integration, doctor/kiosk one-time access, AI pre-visit
summaries, native mobile apps, Urdu translations (scaffold i18n only). These are
post-MVP. If a task drifts into these, stop and confirm.
