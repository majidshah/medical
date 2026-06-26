import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/layout/app-shell";
import { AuthProvider } from "@/lib/auth-context";
import { ProtectedRoute } from "@/lib/protected-route";
import { LoginPage } from "@/pages/login";
import { PatientListPage } from "@/pages/patient-list";
import { PatientSummaryPage } from "@/pages/patient-summary";
import { RegisterPage } from "@/pages/register";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false, refetchOnWindowFocus: false },
  },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route element={<ProtectedRoute />}>
              <Route element={<AppShell />}>
                <Route path="/patients" element={<PatientListPage />} />
                <Route
                  path="/patients/:patientId"
                  element={<PatientSummaryPage />}
                />
              </Route>
            </Route>
            <Route path="*" element={<Navigate to="/patients" replace />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
