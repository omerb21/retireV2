import { Link } from "react-router-dom";

import { AppRoutes } from "./routes/AppRoutes";

const navLinks = [
  { path: "/clients", label: "לקוחות" },
  { path: "/fixation/input", label: "נתוני קיבוע זכויות" },
  { path: "/fixation/result", label: "תוצאת חישוב" },
  { path: "/fixation/history", label: "היסטוריית חישובים" },
  { path: "/fixation/runs/placeholder", label: "פרטי הרצה" }
];

function App() {
  return (
    <div dir="rtl" lang="he">
      <h1>מערכת תכנון פרישה</h1>
      <nav aria-label="ניווט ראשי">
        <ul>
          {navLinks.map(({ path, label }) => (
            <li key={path}>
              <Link to={path}>{label}</Link>
            </li>
          ))}
        </ul>
      </nav>
      <AppRoutes />
    </div>
  );
}

export default App;
