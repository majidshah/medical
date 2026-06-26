import { useTranslation } from "react-i18next";
import { Link, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "@/lib/auth-context";

export function AppShell() {
  const { t } = useTranslation();
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-paper">
      <header className="bg-surface border-b border-muted/20 px-6 py-3">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <Link to="/patients" className="font-serif text-xl text-teal font-bold">
            {t("app_name")}
          </Link>
          <nav className="flex items-center gap-4">
            <Link
              to="/patients"
              className="text-base text-ink hover:text-teal"
            >
              {t("nav.patients")}
            </Link>
            <button
              onClick={handleLogout}
              className="text-base text-muted hover:text-ink"
            >
              {t("nav.logout")}
            </button>
          </nav>
        </div>
      </header>
      <main className="max-w-4xl mx-auto px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
}
