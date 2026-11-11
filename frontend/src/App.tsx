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
  if (workspace) {
    // Specialist legacy routes keep the same visual workspace frame and
    // client identity. They are not separate primary workflows.
    return <main dir="rtl" lang="he" className="professional-workspace">
      <header className="professional-workspace__header">
        <div><strong>בן־צבי · סביבת תכנון פרישה</strong>
          <p>תיק פעיל: מזהה תיק {clientMatch![1]} · כלי מקצועי מתקדם</p>
        </div>
        <NavLink to="/clients">החלפת לקוח</NavLink>
      </header>
      <nav className="professional-workspace__steps" aria-label="שלבי תיק הלקוח">
        <NavLink to={workspace + "?step=client"}>1. לקוח ותיק</NavLink>
        <NavLink to={workspace + "?step=portfolio"}>2. תיק פנסיוני</NavLink>
        <NavLink to={workspace + "?step=supplement"}>3. נתונים משלימים</NavLink>
        <NavLink to={workspace + "?step=scenario"}>4. תכנון תרחישים</NavLink>
        <NavLink to={workspace + "?step=results"}>5. תוצאות והשוואה</NavLink>
      </nav>
      <div className="professional-workspace__body">
        <p role="status" className="professional-workspace__boundary">
          כלי מקצועי משני. הנתונים והפעולות משויכים לתיק הלקוח הפעיל.
        </p>
        <AppRoutes />
      </div>
    </main>;
  }
  return (
    <div className="app-shell" dir="rtl" lang="he">
      <header className="app-shell__header">
        <h1>מערכת תכנון פרישה</h1>
        <nav className="app-shell__nav" aria-label="ניווט ראשי">
          {navLinks.map(({ path, label }) => (
            <NavLink key={path} to={path}>{label}</NavLink>
          ))}
        </nav>
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
