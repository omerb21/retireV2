import { Link } from "react-router-dom";

import { AppRoutes } from "./routes/AppRoutes";

const navLinks = [
  { path: "/fixation/input", label: "Input Screen" },
  { path: "/fixation/result", label: "Result Screen" },
  { path: "/fixation/history", label: "History Screen" },
  { path: "/fixation/runs/placeholder", label: "Run Detail Screen" }
];

function App() {
  return (
    <div>
      <h1>Retirement Planning V2 - Frontend Shell</h1>
      <nav>
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
