import { useLocation, useParams } from "react-router-dom";
import { ActualCapitalizationsSection } from "./ActualCapitalizationsSection";

/** Legacy route stays live and delegates to the same editor used in workspace step 3. */
export function ActualCapitalizationsScreen() {
  const { clientId } = useParams<{ clientId: string }>();
  const location = useLocation();
  const parsedClientId = Number(clientId);
  const clientName = typeof location.state === "object" && location.state !== null && "clientName" in location.state && typeof location.state.clientName === "string" ? location.state.clientName : null;
  return <ActualCapitalizationsSection key={parsedClientId} parsedClientId={parsedClientId} clientName={clientName} />;
}
