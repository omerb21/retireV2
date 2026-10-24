import type { ScenarioDraft } from "../api/scenarioDraftsApi";
import type { PensionProduct } from "../api/pensionProductsApi";

export interface ScenarioDraftSummary {
  scenarioId: string;
  name: string;
  status: ScenarioDraft["status"];
  decisionCount: number;
  pensionCents: bigint;
  capitalCents: bigint;
  missingSources: number;
  overAllocatedSources: number;
  invalidAmounts: number;
  staleDecisions: number;
}
function cents(value: string): bigint | null {
  if (!/^(?:0|[1-9][0-9]*)(?:\.[0-9]{1,2})?$/.test(value)) return null;
  const [whole, fraction = ""] = value.split(".");
  return BigInt(whole) * 100n + BigInt(fraction.padEnd(2, "0"));
}
export function formatScenarioCents(value: bigint): string {
  return (value < 0n ? "-" : "") + (value < 0n ? -value : value) / 100n + "." +
    ((value < 0n ? -value : value) % 100n).toString().padStart(2, "0");
}
export function summarizeScenarioDraft(draft: ScenarioDraft, products: PensionProduct[]): ScenarioDraftSummary {
  const sources = new Map<string, bigint>();
  for (const product of products) {
    for (const component of product.conversion_components ?? []) {
      const parsed = cents(component.balance);
      if (parsed !== null) sources.set(JSON.stringify([product.product_id, component.component_id, component.component_code]), parsed);
    }
  }
  const allocated = new Map<string, bigint>();
  let pensionCents = 0n, capitalCents = 0n, missingSources = 0, invalidAmounts = 0, staleDecisions = 0;
  for (const decision of draft.decisions) {
    const key = JSON.stringify([decision.source_product_id, decision.source_component_id, decision.component_code]);
    const amount = cents(decision.amount);
    if (amount === null || amount <= 0n) { invalidAmounts++; continue; }
    if (decision.action === "pension") pensionCents += amount;
    else capitalCents += amount;
    if (!sources.has(key)) missingSources++;
    allocated.set(key, (allocated.get(key) ?? 0n) + amount);
    if (decision.validation_state === "needs_revalidation") staleDecisions++;
  }
  const overAllocatedSources = [...allocated].filter(([key, amount]) => {
    const balance = sources.get(key);
    return balance !== undefined && amount > balance;
  }).length;
  return {
    scenarioId: draft.scenario_id, name: draft.name, status: draft.status,
    decisionCount: draft.decisions.length, pensionCents, capitalCents,
    missingSources, overAllocatedSources, invalidAmounts, staleDecisions,
  };
}
