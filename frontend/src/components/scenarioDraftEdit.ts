import type { DraftDecisionInput } from "../api/scenarioDraftsApi";

export function preserveEditedDecisionId(
  decision: DraftDecisionInput,
  existingId: string | null,
): DraftDecisionInput {
  return existingId ? { ...decision, decision_id: existingId } : decision;
}
