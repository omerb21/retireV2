import { NavLink, useLocation } from "react-router-dom";

import { AppRoutes } from "./routes/AppRoutes";
import { AuthenticationGate } from "./components/AuthenticationGate";

const navLinks = [
  { path: "/clients", label: "לקוחות" }
];

function AppFrame() {
  const { pathname } = useLocation();
  if (/^\/clients\/[1-9][0-9]*\/workspace\/?$/.test(pathname)) {
    // The dedicated workspace maintains its own navigation and presentation.
    return <AppRoutes />;
  }
  const clientMatch = /^\/clients\/([1-9][0-9]*)(?:\/|$)/.exec(pathname);
  const workspace = clientMatch ? `/clients/${clientMatch[1]}/workspace` : null;
  return (
    <div className="app-shell" dir="rtl" lang="he">
      <header className="app-shell__header">
        <h1>מערכת תכנון פרישה</h1>
        <nav className="app-shell__nav" aria-label="ניווט ראשי">
          {navLinks.map(({ path, label }) => (
            <NavLink key={path} to={path}>{label}</NavLink>
          ))}
        </nav>
        {workspace && <nav aria-label="שלבי תיק הלקוח" className="app-shell__client-steps">
          <NavLink to={workspace + "?step=client"}>פרטי תיק</NavLink>
          <NavLink to={workspace + "?step=portfolio"}>מסלקה ותיק פנסיוני</NavLink>
          <NavLink to={workspace + "?step=supplement"}>נתונים משלימים</NavLink>
          <NavLink to={workspace + "?step=scenario"}>תכנון חלופות</NavLink>
          <NavLink to={workspace + "?step=results"}>תוצאות והשוואה</NavLink>
          <span role="status">כלי מקצועי משני בתיק הלקוח הפעיל</span>
        </nav>}
      </header>
      <main className="app-shell__main">
        <AppRoutes />
      </main>
    </div>
  );
}

function App() {
  return <AuthenticationGate><AppFrame /></AuthenticationGate>;
}

export default App;
