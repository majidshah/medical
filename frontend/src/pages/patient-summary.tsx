import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { fetchPatientSummary } from "@/api/patients";
import { Card } from "@/components/ui/card";
import { DataTable } from "@/components/ui/data-table";
import { NormalityBadge } from "@/components/ui/normality-badge";
import { PageHeader } from "@/components/ui/page-header";
import { StatCard } from "@/components/ui/stat-card";
import { PatientNav } from "@/components/layout/patient-nav";
import { formatDate } from "@/lib/format";

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
    return <p className="text-status-warning text-center py-12">{t("common.error")}</p>;
  }

  const { patient, active_conditions, current_medications, allergies, recent_results, counts } = data;

  return (
    <div>
      <PatientNav patientId={patientId!} />
      <PageHeader
        title={patient.full_name}
        subtitle={`${patient.medical_id} · ${patient.gender} · ${patient.date_of_birth || ""}`}
      />

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
        <StatCard label={t("summary.conditions")} value={counts.conditions} icon="♥" tint="accent" />
        <StatCard label={t("summary.medications")} value={counts.medications} icon="℞" tint="neutral" />
        <StatCard label={t("summary.allergies")} value={counts.allergies} icon="⚠" tint={counts.allergies > 0 ? "warning" : "neutral"} />
        <StatCard label={t("summary.recent_results")} value={counts.reports} icon="🔬" tint="neutral" />
      </div>

      <div className="space-y-6">
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg text-ink font-medium">{t("summary.conditions")}</h2>
            <Link to={`/patients/${patientId}/conditions`} className="text-sm text-accent hover:underline">
              {t("summary.view_all")}
            </Link>
          </div>
          {active_conditions.length > 0 ? (
            <ul className="space-y-2">
              {active_conditions.map((c) => (
                <li key={c.id} className="flex items-center justify-between">
                  <span className="text-base">{c.display_name}</span>
                  <span className="text-sm text-muted capitalize">{c.clinical_status}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-muted text-base">{t("summary.none_recorded")}</p>
          )}
        </Card>

        <Card>
          <h2 className="text-lg text-ink font-medium mb-4">{t("summary.medications")}</h2>
          {current_medications.length > 0 ? (
            <ul className="space-y-2">
              {current_medications.map((m) => (
                <li key={m.id} className="flex items-center justify-between">
                  <div>
                    <span className="text-base">{m.display_name}</span>
                    {m.dosage && <span className="ml-2 text-sm text-muted">{m.dosage}</span>}
                  </div>
                  {m.frequency && <span className="text-sm text-muted">{m.frequency}</span>}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-muted text-base">{t("summary.none_recorded")}</p>
          )}
        </Card>

        <Card className="border-status-warning/30">
          <h2 className="text-lg text-ink font-medium mb-4">{t("summary.allergies")}</h2>
          {allergies.length > 0 ? (
            <ul className="space-y-2">
              {allergies.map((a) => (
                <li key={a.id} className="flex items-center justify-between">
                  <div>
                    <span className="text-base font-medium">{a.display_name}</span>
                    <span className="ml-2 text-sm text-muted capitalize">{a.category}</span>
                  </div>
                  {a.criticality && (
                    <span className="text-sm text-status-warning font-medium capitalize">
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
          <h2 className="text-lg text-ink font-medium mb-4">{t("summary.recent_results")}</h2>
          <DataTable
            columns={[
              { key: "test", header: t("summary.table_test"), render: (r) => <span className="text-base">{r.display_name}</span> },
              { key: "value", header: t("summary.table_value"), render: (r) => (
                <span className="font-sans tabular-nums">
                  {r.value_numeric ?? r.value_text ?? ""}{" "}
                  {r.unit && <span className="text-muted">{r.unit}</span>}
                </span>
              ), className: "font-sans tabular-nums" },
              { key: "date", header: t("summary.table_date"), render: (r) => <span className="text-muted">{formatDate(r.effective_date)}</span> },
              { key: "status", header: t("summary.table_status"), render: (r) => <NormalityBadge status={r.normality_status} /> },
            ]}
            data={recent_results}
            getKey={(r) => r.id}
            emptyMessage={t("summary.none_recorded")}
          />
        </Card>
      </div>
    </div>
  );
}
