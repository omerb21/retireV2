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
import { M02PensionIntakeScreen } from "../pages/M02PensionIntakeScreen";
import { M03SourceReviewScreen } from "../pages/M03SourceReviewScreen";
import { M04ClassificationScreen } from "../pages/M04ClassificationScreen";
import { M05LedgerScreen } from "../pages/M05LedgerScreen";
import { M06ConversionScreen } from "../pages/M06ConversionScreen";
import { M09CashflowScreen } from "../pages/M09CashflowScreen";
import { M10ComparisonScreen } from "../pages/M10ComparisonScreen";

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/clients" replace />} />
      <Route path="/clients" element={<ClientListScreen />} />
      <Route path="/clients/new" element={<CreateClientScreen />} />
      <Route path="/clients/:clientId" element={<ClientDetailScreen />} />
      <Route path="/clients/:clientId/employment-history" element={<EmploymentHistoryScreen />} />
      <Route path="/clients/:clientId/pension-intake" element={<M02PensionIntakeScreen />} />
      <Route path="/clients/:clientId/source-review" element={<M03SourceReviewScreen />} />
      <Route path="/clients/:clientId/classification" element={<M04ClassificationScreen />} />
      <Route path="/clients/:clientId/pension-ledger" element={<M05LedgerScreen />} />
      <Route path="/clients/:clientId/pension-conversion" element={<M06ConversionScreen />} />
      <Route path="/clients/:clientId/monthly-cashflow" element={<M09CashflowScreen />} />
      <Route path="/clients/:clientId/scenario-comparison" element={<M10ComparisonScreen />} />
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
