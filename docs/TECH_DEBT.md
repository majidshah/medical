# Tech Debt

Items to address before or at the specified milestone. Each entry names the
affected code, what needs to change, and when.

---

## ~~FHIR mappings: replace hand-built dicts with fhir.resources validation~~ RESOLVED

**Resolved in slice 5.** All FHIR mappers (`condition.py`, `allergy.py`,
`medication.py`, `immunization.py`, `family_history.py`, `observation.py`)
now construct resources via `fhir.resources` models with schema validation.
Confirmed clean for the FHIR Bundle export in slice 10.
