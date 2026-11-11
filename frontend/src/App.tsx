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
