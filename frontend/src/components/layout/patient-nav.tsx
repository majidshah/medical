import { useTranslation } from "react-i18next";
import { Link, useLocation } from "react-router-dom";

interface PatientNavProps {
  patientId: string;
}

export function PatientNav({ patientId }: PatientNavProps) {
  const { t } = useTranslation();
  const { pathname } = useLocation();

  const links = [
    { to: `/patients/${patientId}`, label: t("summary.title"), exact: true },
    { to: `/patients/${patientId}/conditions`, label: t("conditions.title") },
    { to: `/patients/${patientId}/allergies`, label: t("allergies.title") },
    { to: `/patients/${patientId}/medications`, label: t("medications.title") },
    {
      to: `/patients/${patientId}/immunizations`,
      label: t("immunizations.title"),
    },
    {
      to: `/patients/${patientId}/family-history`,
      label: t("family_history.title"),
    },
    {
      to: `/patients/${patientId}/lifestyle`,
      label: t("lifestyle.title"),
    },
    {
      to: `/patients/${patientId}/reports`,
      label: t("lab.title"),
    },
  ];

  return (
    <nav className="flex gap-1 mb-6 overflow-x-auto border-b border-muted/20 pb-2">
      {links.map((l) => {
        const active = l.exact
          ? pathname === l.to
          : pathname.startsWith(l.to);
        return (
          <Link
            key={l.to}
            to={l.to}
            className={`px-3 py-1.5 rounded text-base whitespace-nowrap transition-colors ${
              active
                ? "bg-teal-50 text-teal font-medium"
                : "text-muted hover:text-ink"
            }`}
          >
            {l.label}
          </Link>
        );
      })}
    </nav>
  );
}
