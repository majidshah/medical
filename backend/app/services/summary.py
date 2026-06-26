import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.allergy import Allergy
from app.models.condition import Condition
from app.models.family_history import FamilyHistory
from app.models.immunization import Immunization
from app.models.lab_result import LabResult
from app.models.medication import Medication
from app.models.report import Report
from app.services.audit import log_event
from app.services.lab import compute_normality_for_result
from app.services.patient import get_patient_for_account


async def get_summary(
    session: AsyncSession,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
    recent_results_limit: int = 10,
) -> dict:
    patient = await get_patient_for_account(session, patient_id, account_id)
    if patient is None:
        return None

    patient_data = {
        "id": patient.id,
        "medical_id": patient.medical_id,
        "full_name": patient.full_name,
        "date_of_birth": patient.date_of_birth,
        "gender": patient.gender,
        "relationship_to_account": patient.relationship_to_account,
    }

    scope = {"patient_id": patient_id, "account_id": account_id}

    conditions_result = await session.execute(
        select(Condition).where(
            Condition.patient_id == scope["patient_id"],
            Condition.account_id == scope["account_id"],
            Condition.is_active.is_(True),
            Condition.clinical_status.in_(["active", "recurrence", "relapse"]),
        )
    )
    active_conditions = [
        {
            "id": c.id,
            "display_name": c.display_name,
            "code": c.code,
            "clinical_status": c.clinical_status,
            "onset_date": c.onset_date,
        }
        for c in conditions_result.scalars().all()
    ]

    meds_result = await session.execute(
        select(Medication).where(
            Medication.patient_id == scope["patient_id"],
            Medication.account_id == scope["account_id"],
            Medication.is_active.is_(True),
            Medication.status == "active",
        )
    )
    current_medications = [
        {
            "id": m.id,
            "display_name": m.display_name,
            "dosage": m.dosage,
            "frequency": m.frequency,
            "status": m.status,
            "start_date": m.start_date,
        }
        for m in meds_result.scalars().all()
    ]

    allergies_result = await session.execute(
        select(Allergy).where(
            Allergy.patient_id == scope["patient_id"],
            Allergy.account_id == scope["account_id"],
            Allergy.is_active.is_(True),
            Allergy.clinical_status == "active",
        )
    )
    allergy_list = [
        {
            "id": a.id,
            "display_name": a.display_name,
            "category": a.category,
            "criticality": a.criticality,
            "severity": a.severity,
            "reaction": a.reaction,
        }
        for a in allergies_result.scalars().all()
    ]

    results_query = (
        select(LabResult)
        .where(
            LabResult.patient_id == scope["patient_id"],
            LabResult.account_id == scope["account_id"],
            LabResult.is_active.is_(True),
        )
        .order_by(LabResult.effective_date.desc())
        .limit(recent_results_limit)
    )
    results_result = await session.execute(results_query)
    recent_results = []
    for r in results_result.scalars().all():
        n = await compute_normality_for_result(session, r, patient.gender)
        recent_results.append(
            {
                "id": r.id,
                "report_id": r.report_id,
                "display_name": r.display_name,
                "value_numeric": float(r.value_numeric) if r.value_numeric is not None else None,
                "value_text": r.value_text,
                "unit": r.unit,
                "effective_date": r.effective_date,
                "normality_status": n.status,
            }
        )

    count_filters = lambda model: [  # noqa: E731
        model.patient_id == scope["patient_id"],
        model.account_id == scope["account_id"],
        model.is_active.is_(True),
    ]

    counts = {}
    for name, model in [
        ("conditions", Condition),
        ("medications", Medication),
        ("allergies", Allergy),
        ("immunizations", Immunization),
        ("family_history", FamilyHistory),
        ("reports", Report),
    ]:
        result = await session.execute(
            select(func.count()).select_from(model).where(*count_filters(model))
        )
        counts[name] = result.scalar_one()

    await log_event(
        session,
        "summary_viewed",
        account_id=account_id,
        detail=f"patient_id={patient_id}",
    )
    await session.commit()

    return {
        "patient": patient_data,
        "active_conditions": active_conditions,
        "current_medications": current_medications,
        "allergies": allergy_list,
        "recent_results": recent_results,
        "counts": counts,
    }
