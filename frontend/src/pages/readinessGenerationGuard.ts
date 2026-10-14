export const generationPolicy = {
  isCurrent(active: number, current: number): boolean {
    return active === current;
  },
  workspaceKey(clientId: number): number | string {
    return clientId;
  },
};
