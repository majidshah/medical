# Tech Debt

Items to address before or at the specified milestone. Each entry names the
affected code, what needs to change, and when.

---

## FHIR mappings: replace hand-built dicts with fhir.resources validation

**Where:** `backend/app/fhir/condition.py` (and every future `fhir/*.py` mapper)

**Current state:** FHIR R4 resources are built as plain Python dicts. The output
is structurally correct for the fields used today, but nothing validates that the
dict conforms to the FHIR R4 schema. A misspelled field or wrong structure would
pass silently.

**Required change:** Install the `fhir.resources` library (Pydantic-based) and
construct FHIR resources through its models (e.g.
`fhir.resources.condition.Condition`) so every mapping is schema-validated at
build time. Convert `fhir/condition.py` first as the template, then apply the
same pattern to all subsequent mappers.

**Deadline:** Before or at slice 7 (FHIR JSON bundle export), where invalid
resources would corrupt exported bundles. Acceptable to defer until then since
single-resource endpoints are tested and correct today.

**Reference:** ARCHITECTURE.md §2 recommends `fhir.resources` as the validation
mechanism.
