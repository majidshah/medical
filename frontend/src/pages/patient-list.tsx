import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { fetchPatients } from "@/api/patients";
import { Card } from "@/components/ui/card";

export function PatientListPage() {
  const { t } = useTranslation();
  const { data, isLoading, error } = useQuery({
    queryKey: ["patients"],
    queryFn: fetchPatients,
  });

  if (isLoading) {
    return <p className="text-muted text-center py-12">{t("common.loading")}</p>;
  }
  if (error) {
    return <p className="text-amber text-center py-12">{t("common.error")}</p>;
  }

  const patients = data?.items || [];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-serif text-2xl text-ink">{t("patients.title")}</h1>
      </div>

      {patients.length === 0 ? (
        <Card className="text-center py-12">
          <p className="text-muted text-lg mb-2">{t("patients.empty")}</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {patients.map((p) => (
            <Link key={p.id} to={`/patients/${p.id}`}>
              <Card className="hover:border-teal/40 transition-colors cursor-pointer">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="font-serif text-lg text-ink">
                      {p.full_name}
                    </h2>
                    <p className="text-base text-muted">
                      {t("patients.medical_id")}: {p.medical_id}
                    </p>
                  </div>
                  <span className="text-base text-muted capitalize">
                    {p.relationship_to_account}
                  </span>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
