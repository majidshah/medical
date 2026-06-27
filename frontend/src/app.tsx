import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/layout/app-shell";
import { AuthProvider } from "@/lib/auth-context";
import { ProtectedRoute } from "@/lib/protected-route";
import { ThemeProvider } from "@/lib/theme-context";
import { AllergiesPage } from "@/pages/allergies";
import { ConditionsPage } from "@/pages/conditions";
import { FamilyHistoryPage } from "@/pages/family-history";
import { ImmunizationsPage } from "@/pages/immunizations";
import { LabReportsPage } from "@/pages/lab-reports";
import { LifestylePage } from "@/pages/lifestyle";
import { LoginPage } from "@/pages/login";
import { MedicationsPage } from "@/pages/medications";
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
        <ThemeProvider>
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
                <Route
                  path="/patients/:patientId/conditions"
                  element={<ConditionsPage />}
                />
                <Route
                  path="/patients/:patientId/allergies"
                  element={<AllergiesPage />}
                />
                <Route
                  path="/patients/:patientId/medications"
                  element={<MedicationsPage />}
                />
                <Route
                  path="/patients/:patientId/immunizations"
                  element={<ImmunizationsPage />}
                />
                <Route
                  path="/patients/:patientId/family-history"
                  element={<FamilyHistoryPage />}
                />
                <Route
                  path="/patients/:patientId/lifestyle"
                  element={<LifestylePage />}
                />
                <Route
                  path="/patients/:patientId/reports"
                  element={<LabReportsPage />}
                />
              </Route>
            </Route>
            <Route path="*" element={<Navigate to="/patients" replace />} />
          </Routes>
        </AuthProvider>
        </ThemeProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
