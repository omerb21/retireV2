import { Navigate, Route, Routes } from "react-router-dom";
import { ActualCapitalizationsScreen } from "../pages/ActualCapitalizationsScreen";
import { CalculationResultScreen } from "../pages/CalculationResultScreen";
import { ClientDetailScreen } from "../pages/ClientDetailScreen";
import { ClientListScreen } from "../pages/ClientListScreen";
import { EmploymentHistoryScreen } from "../pages/EmploymentHistoryScreen";
import { FixationInputScreen } from "../pages/FixationInputScreen";
import { GrantsScreen } from "../pages/GrantsScreen";
import { RunDetailScreen } from "../pages/RunDetailScreen";
import { RunHistoryScreen } from "../pages/RunHistoryScreen";

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/clients" replace />} />
      <Route path="/clients" element={<ClientListScreen />} />
      <Route path="/clients/:clientId" element={<ClientDetailScreen />} />
      <Route path="/clients/:clientId/employment-history" element={<EmploymentHistoryScreen />} />
      <Route path="/clients/:clientId/grants" element={<GrantsScreen />} />
      <Route path="/clients/:clientId/actual-capitalizations" element={<ActualCapitalizationsScreen />} />
      <Route path="/fixation/input" element={<FixationInputScreen />} />
      <Route path="/fixation/result" element={<CalculationResultScreen />} />
      <Route path="/fixation/history" element={<RunHistoryScreen />} />
      <Route path="/fixation/runs/:runId" element={<RunDetailScreen />} />
    </Routes>
  );
}
