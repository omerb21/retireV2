"""M12-P1 read-only draft projection of existing facts, not a calculator or authority."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.client import Client
from app.models.pension_product import PensionProduct
from app.models.retirement_facts import CapitalAsset, RecurringIncome, RecurringExpense, PlannerAssumption
from app.models.missing_data_item import MissingDataItem
from app.models.scenario_draft import ScenarioDraft, ScenarioDraftDecision
from app.models.m11_preferred_scenario import M11PreferredScenarioRevision
from app.services.scenario_draft_service import DraftError


def _value(value):
    """JSON-safe, preserving missingness: None is never cast to zero."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return format(value, "f")
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def build(db: Session, client_id: int) -> dict:
    client = db.get(Client, client_id)
    if client is None:
        raise DraftError("CLIENT_NOT_FOUND", 404)
    products = list(db.scalars(select(PensionProduct).where(PensionProduct.client_id == client_id)
                               .order_by(PensionProduct.product_name, PensionProduct.product_id)))
    assets = list(db.scalars(select(CapitalAsset).where(
        CapitalAsset.client_id == client_id, CapitalAsset.lifecycle_status == "current"
    ).order_by(CapitalAsset.id)))
    incomes = list(db.scalars(select(RecurringIncome).where(
        RecurringIncome.client_id == client_id, RecurringIncome.lifecycle_status == "current"
    ).order_by(RecurringIncome.id)))
    expenses = list(db.scalars(select(RecurringExpense).where(
        RecurringExpense.client_id == client_id, RecurringExpense.lifecycle_status == "current"
    ).order_by(RecurringExpense.id)))
    assumptions = list(db.scalars(select(PlannerAssumption).where(
        PlannerAssumption.client_id == client_id, PlannerAssumption.lifecycle_status == "current"
    ).order_by(PlannerAssumption.id)))
    missing = list(db.scalars(select(MissingDataItem).where(
        MissingDataItem.client_id == client_id, (MissingDataItem.advisory_status.is_(None) | (MissingDataItem.advisory_status != "resolved"))
    ).order_by(MissingDataItem.created_at)))
    scenarios = list(db.scalars(select(ScenarioDraft).where(
        ScenarioDraft.client_id == client_id, ScenarioDraft.status != "archived"
    ).order_by(ScenarioDraft.created_at, ScenarioDraft.scenario_id)))
    scenario_ids = [row.scenario_id for row in scenarios]
    decisions = list(db.scalars(select(ScenarioDraftDecision).where(
        ScenarioDraftDecision.scenario_id.in_(scenario_ids)
    ))) if scenario_ids else []
    decisions_by_scenario = {sid: [] for sid in scenario_ids}
    for decision in decisions:
        decisions_by_scenario[decision.scenario_id].append({
            "component": decision.component_code,
            "action": decision.action,
            "declared_amount": _value(decision.amount),
            "effective_date": _value(decision.effective_date),
            "validation_state": decision.validation_state,
            "qualified_calculation": False,
        })
    history = db.scalar(select(M11PreferredScenarioRevision).where(
        M11PreferredScenarioRevision.client_id == client_id
    ).order_by(M11PreferredScenarioRevision.revision.desc()).limit(1))
    selected = next((s for s in scenarios if history and s.scenario_id == history.scenario_id), None)
    outdated = bool(history and (
        selected is None or selected.version != history.scenario_version
        or selected.status != "draft"
    ))
    warnings = [
        "טיוטת תכנון בלבד. בחירת החלופה אינה מאשרת חישובים.",
        "אין שיוך מאומת לחלופה של ריצות M09/M10 או תוצאות Stage 6. לא מוצגים תזרימים או תחזיות מחושבות.",
    ]
    if not history:
        warnings.append("לא נשמרה חלופה מועדפת ב-M11.")
    elif outdated:
        warnings.append("החלופה המועדפת השתנתה, דורשת אימות מחדש או אינה פעילה.")
    if not products and not assets:
        warnings.append("לא קיימים בתיק מוצרים פנסיוניים או נכסי הון להצגה.")
    for scenario in scenarios:
        if scenario.status == "needs_revalidation":
            warnings.append("חלופה '" + scenario.name + "' דורשת אימות מחדש.")
        if any(d["validation_state"] != "unverified" for d in decisions_by_scenario[scenario.scenario_id]):
            warnings.append("קיימות החלטות בחלופות שדורשות בדיקה מחדש.")
    return {
        "document_kind": "M12_FIRST_STAGE_DRAFT",
        "draft": True,
        "client": {
            "name": client.display_name,
            "birth_date": _value(client.birth_date),
            "employment_status": client.employment_status,
            "planned_retirement_date": _value(client.planned_retirement_date),
            "planned_retirement_age": client.planned_retirement_age,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pension_products": [{
            "name": p.product_name, "type": p.product_type,
            "provider": p.provider_name,
            "reported_total": _value(p.reported_product_total),
            "statement_date": _value(p.statement_date),
            "verification": "דיווח מקור, אינו אישור חישוב",
        } for p in products],
        "capital_assets": [{
            "name": a.asset_description, "category": a.asset_category,
            "value": _value(a.known_value_amount),
            "value_date": _value(a.value_as_of_date),
            "verification": a.verification_state,
        } for a in assets],
        "incomes": [{
            "name": i.description, "amount": _value(i.amount),
            "frequency": i.frequency, "amount_basis": i.amount_basis,
            "verification": i.verification_state,
        } for i in incomes],
        "expenses": [{
            "name": e.description, "amount": _value(e.amount),
            "frequency": e.frequency, "verification": e.verification_state,
        } for e in expenses],
        "scenarios": [{
            "name": s.name, "version": s.version, "status": s.status,
            "preferred": bool(history and history.scenario_id == s.scenario_id),
            "decisions": sorted(decisions_by_scenario[s.scenario_id],
                                key=lambda d: (d["component"], d["effective_date"], d["action"])),
        } for s in scenarios],
        "preferred": ({
            "name": selected.name if selected else "החלופה אינה פעילה",
            "version_at_selection": history.scenario_version,
            "rationale": history.rationale,
            "saved_at": _value(history.saved_at),
            "outdated": outdated,
        } if history else None),
        "assumptions": [{"title": a.title, "value": a.assumption_value_text,
                         "rationale": a.rationale} for a in assumptions],
        "missing_information": [{"label": m.missing_item_label,
                                 "status": m.missing_status} for m in missing],
        "warnings": warnings,
        "cashflow_results": None,
        "calculation_traceability": "not_established",
    }
