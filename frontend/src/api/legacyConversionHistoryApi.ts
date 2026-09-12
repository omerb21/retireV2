import { buildApiUrl } from "./apiBase";
export interface LegacyRevision { revision_id: string; created_at: string; input_amount: string | null; coefficient: { coefficient: string }; manifest: null | { display_result: string | null } }
export interface LegacySubject { subject_id: string; current_revision: LegacyRevision | null }
async function read<T>(clientId: number, suffix: string): Promise<T> {
  const response = await fetch(buildApiUrl(`/clients/${clientId}/m06/subjects${suffix}`));
  if (!response.ok) throw new Error("לא ניתן לטעון את ארכיון ההמרות");
  return response.json() as Promise<T>;
}
export const listLegacyConversions = (clientId: number) => read<LegacySubject[]>(clientId, "");
export const legacyConversionHistory = (clientId: number, id: string) => read<LegacyRevision[]>(clientId, `/${encodeURIComponent(id)}/history`);
