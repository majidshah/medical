import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { ApiError } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/lib/auth-context";

export function RegisterPage() {
  const { t } = useTranslation();
  const { register } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (password.length < 8) {
      setError(t("register.password"));
      return;
    }
    setLoading(true);
    try {
      await register(email, password);
      navigate("/patients");
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError(t("register.error_duplicate"));
      } else {
        setError(t("common.error"));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-page flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <h1 className="text-xl text-ink font-medium text-center mb-8">
          {t("register.title")}
        </h1>
        <form onSubmit={handleSubmit} className="bg-surface rounded-theme border border-border-light p-6">
          <Input
            label={t("register.email")}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
          <Input
            label={t("register.password")}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            autoComplete="new-password"
          />
          {error && (
            <p className="mb-4 text-base text-status-warning" role="alert">
              {error}
            </p>
          )}
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? t("common.loading") : t("register.submit")}
          </Button>
          <p className="mt-4 text-center text-base text-muted">
            {t("register.has_account")}{" "}
            <Link to="/login" className="text-accent hover:underline">
              {t("register.login_link")}
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
