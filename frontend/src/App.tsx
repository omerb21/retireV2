import { AppRoutes } from "./routes/AppRoutes";
import { AuthenticationGate } from "./components/AuthenticationGate";
import { ProfessionalAppShell } from "./components/ProfessionalAppShell";

function App() {
  return (
    <AuthenticationGate>
      <ProfessionalAppShell>
        <AppRoutes />
      </ProfessionalAppShell>
    </AuthenticationGate>
  );
}

export default App;
