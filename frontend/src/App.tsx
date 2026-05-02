import { Link } from "react-router-dom";

import { AppRoutes } from "./routes/AppRoutes";

const navLinks = [
  "/clients",
  "/client/create",
  "/client/profile",
  "/employment",
  "/grants",
  "/capitalizations",
  "/fixation/params",
  "/fixation/result",
  "/fixation/history"
];

function App() {
  return (
    <div>
      <h1>Retirement Planning V2 - Frontend Shell</h1>
      <nav>
        <ul>
          {navLinks.map((path) => (
            <li key={path}>
              <Link to={path}>{path}</Link>
            </li>
          ))}
        </ul>
      </nav>
      <AppRoutes />
    </div>
  );
}

export default App;
