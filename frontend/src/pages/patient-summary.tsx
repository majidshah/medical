import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { fetchPatientSummary } from "@/api/patients";
import { Card } from "@/components/ui/card";
import { NormalityBadge } from "@/components/ui/normality-badge";

export function PatientSummaryPage() {
  const { t } = useTranslation();
  const { patientId } = useParams<{ patientId: string }>();
  const { data, isLoading, error } = useQuery({
    queryKey: ["patient-summary", patientId],
    queryFn: () => fetchPatientSummary(patientId!),
    enabled: !!patientId,
  });

  if (isLoading) {
    return <p className="text-muted text-center py-12">{t("common.loading")}</p>;
  }
  if (error || !data) {
    return <p className="text-amber text-center py-12">{t("common.error")}</p>;
  }

  const { patient, active_conditions, current_medications, allergies, recent_results, counts } = data;

  return (
    <div>
      <div className="mb-8">
        <h1 className="font-serif text-2xl text-ink">{patient.full_name}</h1>
        <p className="text-base text-muted">
          {patient.medical_id} &middot; {patient.gender} &middot;{" "}
          {patient.date_of_birth || ""}
        </p>
      </div>

      <div className="space-y-6">
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-serif text-xl text-ink">
              {t("summary.conditions")}
              {counts.conditions > 0 && (
                <span className="ml-2 text-base text-muted font-sans">
                  ({counts.conditions})
                </span>
              )}
            </h2>
            <Link
              to={`/patients/${patientId}/conditions`}
              className="text-base text-teal hover:underline"
            >
              {t("summary.view_all")}
            </Link>
          </div>
          {active_conditions.length > 0 ? (
            <ul className="space-y-2">
              {active_conditions.map((c) => (
                <li key={c.id} className="flex items-center justify-between">
                  <span className="text-base">{c.display_name}</span>
                  <span className="text-base text-muted capitalize">
                    {c.clinical_status}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-muted text-base">{t("summary.none_recorded")}</p>
          )}
        </Card>

        <Card>
          <h2 className="font-serif text-xl text-ink mb-4">
            {t("summary.medications")}
            {counts.medications > 0 && (
              <span className="ml-2 text-base text-muted font-sans">
                ({counts.medications})
              </span>
            )}
          </h2>
          {current_medications.length > 0 ? (
            <ul className="space-y-2">
              {current_medications.map((m) => (
                <li key={m.id} className="flex items-center justify-between">
                  <div>
                    <span className="text-base">{m.display_name}</span>
                    {m.dosage && (
                      <span className="ml-2 text-base text-muted">
                        {m.dosage}
                      </span>
                    )}
                  </div>
                  {m.frequency && (
                    <span className="text-base text-muted">{m.frequency}</span>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-muted text-base">{t("summary.none_recorded")}</p>
          )}
        </Card>

        <Card className="border-amber/30">
          <h2 className="font-serif text-xl text-ink mb-4">
            {t("summary.allergies")}
            {counts.allergies > 0 && (
              <span className="ml-2 text-base text-muted font-sans">
                ({counts.allergies})
              </span>
            )}
          </h2>
          {allergies.length > 0 ? (
            <ul className="space-y-2">
              {allergies.map((a) => (
                <li key={a.id} className="flex items-center justify-between">
                  <div>
                    <span className="text-base font-medium">{a.display_name}</span>
                    <span className="ml-2 text-base text-muted capitalize">
                      {a.category}
                    </span>
                  </div>
                  {a.criticality && (
                    <span className="text-base text-amber font-medium capitalize">
                      {a.criticality}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-muted text-base">{t("summary.no_allergies")}</p>
          )}
        </Card>

        <Card>
          <h2 className="font-serif text-xl text-ink mb-4">
            {t("summary.recent_results")}
            {counts.reports > 0 && (
              <span className="ml-2 text-base text-muted font-sans">
                ({counts.reports} {t("summary.reports_count")})
              </span>
            )}
          </h2>
          {recent_results.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-base">
                <thead>
                  <tr className="border-b border-muted/20 text-left">
                    <th className="pb-2 font-medium">{t("summary.table_test")}</th>
                    <th className="pb-2 font-medium">{t("summary.table_value")}</th>
                    <th className="pb-2 font-medium">{t("summary.table_date")}</th>
                    <th className="pb-2 font-medium">{t("summary.table_status")}</th>
                  </tr>
                </thead>
                <tbody>
                  {recent_results.map((r) => (
                    <tr key={r.id} className="border-b border-muted/10">
                      <td className="py-2">{r.display_name}</td>
                      <td className="py-2 font-sans tabular-nums">
                        {r.value_numeric ?? r.value_text ?? ""}{" "}
                        {r.unit && (
                          <span className="text-muted">{r.unit}</span>
                        )}
                      </td>
                      <td className="py-2 text-muted">{r.effective_date}</td>
                      <td className="py-2">
                        <NormalityBadge status={r.normality_status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-muted text-base">{t("summary.none_recorded")}</p>
          )}
        </Card>
      </div>
    </div>
  );
}
