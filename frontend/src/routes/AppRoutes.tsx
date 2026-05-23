import { Navigate, Route, Routes } from "react-router-dom";
import { CalculationResultScreen } from "../pages/CalculationResultScreen";
import { ClientListScreen } from "../pages/ClientListScreen";
import { FixationInputScreen } from "../pages/FixationInputScreen";
import { RunDetailScreen } from "../pages/RunDetailScreen";
import { RunHistoryScreen } from "../pages/RunHistoryScreen";

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/clients" replace />} />
      <Route path="/clients" element={<ClientListScreen />} />
      <Route path="/fixation/input" element={<FixationInputScreen />} />
      <Route path="/fixation/result" element={<CalculationResultScreen />} />
      <Route path="/fixation/history" element={<RunHistoryScreen />} />
      <Route path="/fixation/runs/:runId" element={<RunDetailScreen />} />
    </Routes>
  );
}
