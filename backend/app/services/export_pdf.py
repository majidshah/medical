"""PDF health summary export using reportlab."""

import io
import uuid
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.summary import get_summary


async def generate_pdf(
    session: AsyncSession,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
) -> bytes | None:
    data = await get_summary(session, patient_id, account_id, recent_results_limit=20)
    if data is None:
        return None

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title2", parent=styles["Title"], fontSize=16, spaceAfter=6)
    heading_style = ParagraphStyle("H2", parent=styles["Heading2"], spaceAfter=4)
    normal = styles["Normal"]
    small = ParagraphStyle("Small", parent=normal, fontSize=8, textColor=colors.grey)

    elements = []

    p = data["patient"]
    elements.append(Paragraph("MedVault — Health Summary", title_style))
    raw_dob = p["date_of_birth"]
    dob = raw_dob.isoformat() if isinstance(raw_dob, date) else (raw_dob or "N/A")
    elements.append(
        Paragraph(
            f"<b>{p['full_name']}</b> &nbsp;|&nbsp; Medical ID: {p['medical_id']} "
            f"&nbsp;|&nbsp; DOB: {dob} &nbsp;|&nbsp; Gender: {p['gender']}",
            normal,
        )
    )
    elements.append(
        Paragraph(
            f"Generated on {date.today().isoformat()} — "
            "This is a patient-generated summary, not a clinical or legal document.",
            small,
        )
    )
    elements.append(Spacer(1, 8 * mm))

    elements.append(Paragraph("Active Conditions", heading_style))
    if data["active_conditions"]:
        rows = [["Condition", "Status", "Onset"]]
        for c in data["active_conditions"]:
            rows.append([c["display_name"], c["clinical_status"], str(c.get("onset_date") or "")])
        elements.append(_table(rows))
    else:
        elements.append(Paragraph("None recorded.", normal))
    elements.append(Spacer(1, 4 * mm))

    elements.append(Paragraph("Current Medications", heading_style))
    if data["current_medications"]:
        rows = [["Medication", "Dosage", "Frequency", "Since"]]
        for m in data["current_medications"]:
            rows.append(
                [
                    m["display_name"],
                    m.get("dosage") or "",
                    m.get("frequency") or "",
                    str(m.get("start_date") or ""),
                ]
            )
        elements.append(_table(rows))
    else:
        elements.append(Paragraph("None recorded.", normal))
    elements.append(Spacer(1, 4 * mm))

    elements.append(Paragraph("Allergies", heading_style))
    if data["allergies"]:
        rows = [["Allergen", "Category", "Criticality", "Severity", "Reaction"]]
        for a in data["allergies"]:
            rows.append(
                [
                    a["display_name"],
                    a.get("category") or "",
                    a.get("criticality") or "",
                    a.get("severity") or "",
                    a.get("reaction") or "",
                ]
            )
        elements.append(_table(rows))
    else:
        elements.append(Paragraph("No known allergies recorded.", normal))
    elements.append(Spacer(1, 4 * mm))

    elements.append(Paragraph("Recent Lab Results", heading_style))
    if data["recent_results"]:
        rows = [["Test", "Value", "Unit", "Date", "Status"]]
        for r in data["recent_results"]:
            val = str(r.get("value_numeric") or r.get("value_text") or "")
            rows.append(
                [
                    r["display_name"],
                    val,
                    r.get("unit") or "",
                    str(r["effective_date"]),
                    r.get("normality_status", ""),
                ]
            )
        elements.append(_table(rows))
    else:
        elements.append(Paragraph("None recorded.", normal))

    elements.append(Spacer(1, 10 * mm))
    elements.append(
        Paragraph(
            "Disclaimer: This data is user-entered and is provided for informational "
            "and sharing purposes only. It is not a substitute for medical records "
            "maintained by a healthcare provider.",
            small,
        )
    )

    doc.build(elements)
    return buf.getvalue()


def _table(rows: list[list[str]]) -> Table:
    t = Table(rows, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e0e0e0")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    return t
