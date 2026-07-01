import { useTranslation } from "react-i18next";
import { Link, useLocation } from "react-router-dom";

export function AdminNav() {
  const { t } = useTranslation();
  const { pathname } = useLocation();

  const links = [
    { to: "/admin/departments", label: t("admin.departments.title") },
    { to: "/admin/panels", label: t("admin.panels.title") },
    { to: "/admin/tests", label: t("admin.tests.title") },
    { to: "/admin/labs", label: t("admin.labs.title") },
  ];

  return (
    <nav className="flex gap-1 mb-6 overflow-x-auto border-b border-border-light pb-2">
      {links.map((l) => {
        const active = pathname.startsWith(l.to);
        return (
          <Link
            key={l.to}
            to={l.to}
            className={`px-3 py-1.5 rounded text-base whitespace-nowrap transition-colors ${
              active ? "bg-accent-50 text-accent font-medium" : "text-muted hover:text-ink"
            }`}
          >
            {l.label}
          </Link>
        );
      })}
    </nav>
  );
}
