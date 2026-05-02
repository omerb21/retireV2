import { Navigate, Route, Routes } from "react-router-dom";

const PlaceholderPage = ({ text }: { text: string }) => <p>{text}</p>;

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/clients" replace />} />
      <Route path="/clients" element={<PlaceholderPage text="Clients placeholder" />} />
      <Route path="/client/create" element={<PlaceholderPage text="Client create placeholder" />} />
      <Route path="/client/profile" element={<PlaceholderPage text="Client profile placeholder" />} />
      <Route path="/employment" element={<PlaceholderPage text="Employment placeholder" />} />
      <Route path="/grants" element={<PlaceholderPage text="Grants placeholder" />} />
      <Route path="/capitalizations" element={<PlaceholderPage text="Capitalizations placeholder" />} />
      <Route path="/fixation/params" element={<PlaceholderPage text="Fixation params placeholder" />} />
      <Route path="/fixation/result" element={<PlaceholderPage text="Fixation result placeholder" />} />
      <Route path="/fixation/history" element={<PlaceholderPage text="Fixation history placeholder" />} />
    </Routes>
  );
}
