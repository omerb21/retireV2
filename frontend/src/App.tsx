import { Link, useLocation } from "react-router-dom";

import { AppRoutes } from "./routes/AppRoutes";
import { AuthenticationGate } from "./components/AuthenticationGate";

const navLinks = [
  { path: "/clients", label: "לקוחות" },
  { path: "/fixation/input", label: "נתוני קיבוע זכויות" },
  { path: "/fixation/result", label: "תוצאת חישוב" },
  { path: "/fixation/history", label: "היסטוריית חישובים" },
  { path: "/fixation/runs/placeholder", label: "פרטי הרצה" }
];

function AppFrame() {
  const { pathname } = useLocation();
  if (/^\/clients\/[1-9][0-9]*\/workspace\/?$/.test(pathname)) {
    // New, owner-reviewed workspace owns its own navigation and hierarchy.
    // Keep the legacy application shell unchanged on all other routes.
    return <AppRoutes />;
  }
  return <div dir="rtl" lang="he">
    <h1>מערכת תכנון פרישה</h1>
    <nav aria-label="ניווט ראשי">
      <ul>
        {navLinks.map(({ path, label }) => (
          <li key={path}><Link to={path}>{label}</Link></li>
        ))}
      </ul>
    </nav>
    <AppRoutes />
  </div>;
}

function App() {
  return <AuthenticationGate><AppFrame /></AuthenticationGate>;
}

export default App;
