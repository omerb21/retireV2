import type { PensionProduct } from "../api/pensionProductsApi";
import type { DraftDecisionInput, ScenarioDraft } from "../api/scenarioDraftsApi";
import { PORTFOLIO_COMPONENT_COLUMNS } from "./portfolioComponentColumns";

/** Strict decimal math. Never use floating-point currency or silently round. */
export function planCents(value: string | null | undefined): bigint | null {
  if (typeof value !== "string" || !/^(0|[1-9][0-9]*)(?:\.[0-9]{1,2})?$/.test(value)) return null;
  const [integer, decimal = ""] = value.split(".");
  return BigInt(integer) * 100n + BigInt(decimal.padEnd(2, "0"));
}

export function planMoney(value: bigint): string {
  const abs = value < 0n ? -value : value;
  return `${value < 0n ? "-" : ""}${abs / 100n}.${(abs % 100n).toString().padStart(2, "0")}`;
}

export interface PlanCell {
  key: string;
  productId: string;
  productName: string;
  code: string;
  label: string;
  componentId: string | null;
  balance: bigint | null;
  allocated: bigint;
  available: bigint | null;
  blocked: string | null;
}

export interface PlanRow { product: PensionProduct; cells: PlanCell[] }

export function buildPlanRows(products: PensionProduct[], decisions: ScenarioDraft["decisions"]): PlanRow[] {
  return products.map(product => ({
    product,
    cells: PORTFOLIO_COMPONENT_COLUMNS.map(([code, label]) => {
      const matches = (product.conversion_components ?? []).filter(component => component.component_code === code);
      const component = matches.length === 1 ? matches[0] : null;
      const raw = product.components?.[code] ?? component?.balance ?? null;
      const balance = raw == null ? null : planCents(raw);
      const canonBalance = component ? planCents(component.balance) : null;
      const matchingDecisions = decisions.filter(decision =>
        decision.source_product_id === product.product_id && decision.component_code === code);
      const allocatedAmounts = matchingDecisions.map(decision => planCents(decision.amount));
      const allocated = allocatedAmounts.reduce<bigint>((total, amount) => total + (amount ?? 0n), 0n);
      const blocked =
        raw != null && balance === null ? "יתרה לא תקינה"
        : raw != null && balance !== null && balance > 0n && !component ? "חסר מיפוי מקור"
        : component && (canonBalance === null || balance !== canonBalance) ? "נתוני המקור אינם תואמים"
        : matchingDecisions.some(decision => decision.validation_state === "needs_revalidation") ? "מקור דורש אימות מחדש"
        : allocatedAmounts.some(amount => amount === null) ? "סכום הקצאה לא תקין"
        : balance !== null && allocated > balance ? "הקצאת יתר בחלופה"
        : matchingDecisions.some(decision =>
            !component || decision.source_component_id !== component.component_id) ? "זהות מקור השתנתה"
        : null;
      return {
        key: `${product.product_id}|${code}`,
        productId: product.product_id,
        productName: product.product_name,
        code, label,
        componentId: component?.component_id ?? null,
        balance, allocated,
        available: balance == null || blocked ? null : balance - allocated,
        blocked,
      };
    }),
  }));
}

/** Program and column selection must fail as a unit if even one positive balance
 * cannot be mapped safely. Never present partial coverage as "whole program". */
export function selectPlanScope(rows: PlanRow[], scope: { productId?: string; code?: string }): string[] {
  const cells = rows.flatMap(row => row.cells).filter(cell =>
    (scope.productId === undefined || cell.productId === scope.productId)
    && (scope.code === undefined || cell.code === scope.code)
    && cell.balance !== null && cell.balance > 0n);
  if (cells.length === 0) throw Error("אין יתרות חיוביות בהיקף שנבחר.");
  if (cells.some(cell => cell.blocked || !cell.componentId || cell.available === null)) {
    throw Error("לא ניתן לבחור את כל ההיקף: לפחות יתרה אחת חסרה מיפוי, אינה תקינה או דורשת אימות.");
  }
  const available = cells.filter(cell => (cell.available ?? 0n) > 0n);
  if (!available.length) throw Error("כל היתרות בהיקף זה כבר הוקצו בחלופה.");
  return available.map(cell => cell.key);
}

export function buildPlanDecisions(
  rows: PlanRow[],
  selectedKeys: string[],
  action: DraftDecisionInput["action"],
  effectiveDate: string,
  singleAmount = "",
): DraftDecisionInput[] {
  const rawDate = /^\d{4}-\d{2}-\d{2}$/.test(effectiveDate)
    ? new Date(`${effectiveDate}T00:00:00Z`) : null;
  if (!rawDate || Number.isNaN(rawDate.getTime()) || rawDate.toISOString().slice(0, 10) !== effectiveDate) {
    throw Error("יש לבחור תאריך המרה תקין.");
  }
  if (action !== "pension" && action !== "capital_asset") throw Error("יעד ההמרה אינו תקין.");
  if (!selectedKeys.length || new Set(selectedKeys).size !== selectedKeys.length) {
    throw Error("יש לבחור יתרה אחת או יותר.");
  }
  const lookup = new Map(rows.flatMap(row => row.cells.map(cell => [cell.key, cell] as const)));
  if (selectedKeys.length > 500) throw Error("נבחרו יותר מדי רכיבים לחלופה אחת.");
  const exactSingle = selectedKeys.length === 1 && singleAmount !== "" ? planCents(singleAmount) : null;
  if (selectedKeys.length === 1 && singleAmount !== "" && (exactSingle === null || exactSingle <= 0n)) {
    throw Error("הסכום חייב להיות חיובי, עם עד שתי ספרות אחרי הנקודה.");
  }
  return selectedKeys.map(key => {
    const cell = lookup.get(key);
    if (!cell || !cell.componentId || cell.blocked || cell.available === null || cell.available <= 0n) {
      throw Error("לפחות אחת מהיתרות שנבחרו אינה זמינה להקצאה. יש לטעון מחדש.");
    }
    const amount = exactSingle ?? cell.available;
    if (amount <= 0n || amount > cell.available || amount > 99999999999999999999n) {
      throw Error("הסכום חורג מהיתרה הפנויה של הרכיב.");
    }
    return {
      source_product_id: cell.productId,
      source_component_id: cell.componentId,
      component_code: cell.code,
      amount: planMoney(amount), action, effective_date: effectiveDate,
    };
  });
}
