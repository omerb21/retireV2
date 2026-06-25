import { Navigate, Route, Routes } from "react-router-dom";
import { ActualCapitalizationsScreen } from "../pages/ActualCapitalizationsScreen";
import { CalculationResultScreen } from "../pages/CalculationResultScreen";
import { CreateClientScreen } from "../pages/CreateClientScreen";
import { ClientDetailScreen } from "../pages/ClientDetailScreen";
import { ClientListScreen } from "../pages/ClientListScreen";
import { EmploymentHistoryScreen } from "../pages/EmploymentHistoryScreen";
import { FixationWorkspaceScreen } from "../pages/FixationWorkspaceScreen";
import { FixationInputScreen } from "../pages/FixationInputScreen";
import { GrantsScreen } from "../pages/GrantsScreen";
import { RunDetailScreen } from "../pages/RunDetailScreen";
import { RunHistoryScreen } from "../pages/RunHistoryScreen";

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/clients" replace />} />
      <Route path="/clients" element={<ClientListScreen />} />
      <Route path="/clients/new" element={<CreateClientScreen />} />
      <Route path="/clients/:clientId" element={<ClientDetailScreen />} />
      <Route path="/clients/:clientId/employment-history" element={<EmploymentHistoryScreen />} />
      <Route path="/clients/:clientId/grants" element={<GrantsScreen />} />
      <Route path="/clients/:clientId/actual-capitalizations" element={<ActualCapitalizationsScreen />} />
      <Route path="/clients/:clientId/fixation/workspace" element={<FixationWorkspaceScreen />} />
      <Route path="/clients/:clientId/fixation/input" element={<FixationInputScreen />} />
      <Route path="/clients/:clientId/fixation/result" element={<CalculationResultScreen />} />
      <Route path="/clients/:clientId/fixation/history" element={<RunHistoryScreen />} />
      <Route path="/clients/:clientId/fixation/runs/:runId" element={<RunDetailScreen />} />
      <Route path="/fixation/input" element={<FixationInputScreen />} />
      <Route path="/fixation/result" element={<CalculationResultScreen />} />
      <Route path="/fixation/history" element={<RunHistoryScreen />} />
      <Route path="/fixation/runs/:runId" element={<RunDetailScreen />} />
    </Routes>
  );
}
