import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "./auth-context";

export function AdminRoute() {
  const { isAdmin, rolesLoaded } = useAuth();
  if (!rolesLoaded) return null;
  if (!isAdmin) return <Navigate to="/patients" replace />;
  return <Outlet />;
}
