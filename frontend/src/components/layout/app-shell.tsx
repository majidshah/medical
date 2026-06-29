import { useTranslation } from "react-i18next";
import { Link, Outlet, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { fetchPatients } from "@/api/patients";
import { useAuth } from "@/lib/auth-context";
import { useTheme } from "@/lib/theme-context";

export function AppShell() {
  const { t } = useTranslation();
  const { logout } = useAuth();
  const navigate = useNavigate();
  const { patientId } = useParams<{ patientId: string }>();
  const theme = useTheme();

  const { data: patientsData } = useQuery({
    queryKey: ["patients"],
    queryFn: fetchPatients,
  });
  const patients = patientsData?.items || [];

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const navItems = patientId
    ? [
        { to: `/patients/${patientId}`, label: t("summary.title"), icon: "📊", exact: true },
        { to: `/patients/${patientId}/conditions`, label: t("conditions.title"), icon: "🩺" },
        { to: `/patients/${patientId}/allergies`, label: t("allergies.title"), icon: "⚠" },
        { to: `/patients/${patientId}/medications`, label: t("medications.title"), icon: "💊" },
        { to: `/patients/${patientId}/immunizations`, label: t("immunizations.title"), icon: "💉" },
        { to: `/patients/${patientId}/family-history`, label: t("family_history.title"), icon: "👪" },
        { to: `/patients/${patientId}/lifestyle`, label: t("lifestyle.title"), icon: "🏃" },
        { to: `/patients/${patientId}/reports`, label: t("lab.title"), icon: "🔬" },
      ]
    : [];

  return (
    <div className="flex min-h-screen bg-page">
      <aside className="w-64 bg-sidebar text-on-sidebar flex flex-col shrink-0">
        <div className="p-4">
          <Link to="/patients" className="font-serif text-lg font-medium text-on-sidebar hover:opacity-80">
            {t("app_name")}
          </Link>
        </div>

        <div className="px-3 mb-2">
          <select
            value={patientId || ""}
            onChange={(e) => {
              if (e.target.value) navigate(`/patients/${e.target.value}`);
              else navigate("/patients");
            }}
            className="w-full px-2 py-1.5 rounded-theme bg-white/10 text-on-sidebar text-base border border-white/20"
          >
            <option value="">{t("patients.title")}</option>
            {patients.map((p) => (
              <option key={p.id} value={p.id}>{p.full_name}</option>
            ))}
          </select>
        </div>

        <nav className="flex-1 px-2 overflow-y-auto">
          {patientId && navItems.map((item) => {
            const active = item.exact
              ? location.pathname === item.to
              : location.pathname.startsWith(item.to);
            return (
              <Link
                key={item.to}
                to={item.to}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-theme text-base mb-0.5 transition-colors ${
                  active
                    ? "bg-accent text-on-accent font-medium"
                    : "text-on-sidebar/80 hover:bg-white/10"
                }`}
              >
                <span className="text-sm" aria-hidden="true">{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="p-3 border-t border-white/10 space-y-2">
          <div className="flex gap-1">
            {(["light", "dark"] as const).map((m) => (
              <button
                key={m}
                onClick={() => theme.setMode(m)}
                className={`flex-1 px-2 py-1 rounded-theme text-xs ${
                  theme.mode === m ? "bg-accent text-on-accent" : "text-on-sidebar/60 hover:bg-white/10"
                }`}
              >
                {m === "light" ? "☀" : "🌙"} {t(`theme.${m}`)}
              </button>
            ))}
          </div>
          <div className="flex gap-1">
            {(["teal", "blue", "rose"] as const).map((a) => (
              <button
                key={a}
                onClick={() => theme.setAccent(a)}
                className={`flex-1 px-2 py-1 rounded-theme text-xs capitalize ${
                  theme.accent === a ? "bg-accent text-on-accent" : "text-on-sidebar/60 hover:bg-white/10"
                }`}
              >
                {t(`theme.${a}`)}
              </button>
            ))}
          </div>
          <div className="flex gap-1">
            {(["comfortable", "compact"] as const).map((d) => (
              <button
                key={d}
                onClick={() => theme.setDensity(d)}
                className={`flex-1 px-2 py-1 rounded-theme text-xs ${
                  theme.density === d ? "bg-accent text-on-accent" : "text-on-sidebar/60 hover:bg-white/10"
                }`}
              >
                {t(`theme.${d}`)}
              </button>
            ))}
          </div>
          <button
            onClick={handleLogout}
            className="w-full text-left px-3 py-1.5 rounded-theme text-base text-on-sidebar/60 hover:bg-white/10"
          >
            {t("nav.logout")}
          </button>
        </div>
      </aside>

      <main className="flex-1 p-8 overflow-y-auto">
        <div className="max-w-4xl">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
