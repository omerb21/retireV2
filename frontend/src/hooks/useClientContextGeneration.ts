import { useCallback, useRef } from "react";

export type ClientContextToken = {
  clientId: number | null;
  generation: number;
};

type ActiveClientContext = ClientContextToken & {
  routeKey: string;
};

export function useClientContextGeneration(clientId: number | null, routeKey: string) {
  const activeContextRef = useRef<ActiveClientContext>({
    clientId,
    routeKey,
    generation: 1,
  });

  if (
    activeContextRef.current.clientId !== clientId ||
    activeContextRef.current.routeKey !== routeKey
  ) {
    activeContextRef.current = {
      clientId,
      routeKey,
      generation: activeContextRef.current.generation + 1,
    };
  }

  const captureClientContext = useCallback(
    (): ClientContextToken => ({
      clientId: activeContextRef.current.clientId,
      generation: activeContextRef.current.generation,
    }),
    [],
  );

  const isCurrentClientContext = useCallback(
    (captured: ClientContextToken): boolean =>
      captured.clientId === activeContextRef.current.clientId &&
      captured.generation === activeContextRef.current.generation,
    [],
  );

  return { captureClientContext, isCurrentClientContext };
}
