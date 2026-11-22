"""Explicit source-specific Stage 6 price comparison decisions.

No indexation, conversion, pension qualification or automatic approval occurs.
CRTISBA remains the sole authority for recurring incomes; this narrow
extension covers scenario-decision pensions which CRTISBA cannot represent.
"""
from __future__ import annotations

from datetime import date
from uuid import uuid4
from urllib.parse import quote

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.scenario_draft import ScenarioDraft
from app.models.scenario_pension_price_basis import ScenarioPensionPriceBasis
from app.services.planning_input_service import fingerprint
from app.services.scenario_draft_service import DraftError
from app.services.scenario_stage6_monthly_cashflow_service import build_scenario_monthly_cashflow
from app.services import retirement_monthly_income_target_service as target_service


DECISION_BASIS = "NOMINAL_AT_RETIREMENT_TARGET_DATE"
UNKNOWN_BASIS = "UNKNOWN"


def current_rows(db: Session, client_id: int, scenario_ids: tuple[str, ...]) -> dict[str, dict]:
    """Read latest revision per exact scenario and decision in the owner's snapshot."""
    if not scenario_ids:
        return {}
    rows = db.scalars(select(ScenarioPensionPriceBasis).where(
        ScenarioPensionPriceBasis.client_id == client_id,
        ScenarioPensionPriceBasis.scenario_id.in_(scenario_ids),
    ).order_by(ScenarioPensionPriceBasis.revision.desc())).all()
    result = {}
    for row in rows:
        source_id = ("scenario-decision:" + quote(row.scenario_id, safe="")
                     + ":" + quote(row.decision_id, safe=""))
        if source_id not in result:
            result[source_id] = {
                "source_id": source_id,
                "scenario_id": row.scenario_id,
                "decision_id": row.decision_id,
                "scenario_version": row.scenario_version,
                "source_fingerprint": row.source_fingerprint,
                "target_fingerprint": row.target_fingerprint,
                "target_date": row.target_date.isoformat(),
                "price_basis": row.price_basis,
                "revision": row.revision,
                "record_fingerprint": row.record_fingerprint,
                "provenance": "EXPLICIT_PROFESSIONAL",
            }
    return result


def evaluate_decision(row: dict | None, source: dict, *, client_id: int,
                      scenario_id: str, scenario_version: int,
                      target_fingerprint: str, target_date: str) -> str:
    """Never infer comparability from a source's nominal amount or PTE factor."""
    if row is None:
        return "MISSING"
    if (row.get("source_id") != source.get("source_id")
        or row.get("scenario_id") != scenario_id
        or row.get("decision_id") != source.get("decision_id")
        or row.get("scenario_version") != scenario_version
        or row.get("source_fingerprint") != source.get("authority_fingerprint")
        or row.get("target_fingerprint") != target_fingerprint
        or row.get("target_date") != target_date):
        return "STALE"
    if row.get("price_basis") != DECISION_BASIS:
        return "UNRESOLVED"
    preimage = {key: row[key] for key in (
        "source_id", "scenario_id", "decision_id", "scenario_version",
        "source_fingerprint", "target_fingerprint", "target_date", "price_basis", "revision",
    )}
    if row.get("record_fingerprint") != fingerprint({"contract": "S6_PRICE_BASIS_V1", **preimage}):
        return "INVALID"
    if source.get("source_kind") != "CALCULATED_PENSION" or source.get("source_state") != "READY":
        return "INVALID"
    return "CURRENT"


def save_explicit_decision(factory, *, client_id: int, scenario_id: str, decision_id: str,
                           expected_scenario_version: int, expected_source_fingerprint: str,
                           expected_target_fingerprint: str, expected_target_date: str,
                           expected_revision: int, price_basis: str, actor: str) -> dict:
    if price_basis not in {DECISION_BASIS, UNKNOWN_BASIS} or not actor or len(actor) > 128:
        raise DraftError("S6_PRICE_BASIS_REQUEST_INVALID", 422)
    if len(expected_source_fingerprint) != 64 or len(expected_target_fingerprint) != 64:
        raise DraftError("S6_PRICE_BASIS_REQUEST_INVALID", 422)
    try:
        target_date = date.fromisoformat(expected_target_date)
    except ValueError:
        raise DraftError("S6_PRICE_BASIS_REQUEST_INVALID", 422) from None
    with factory.begin() as db:
        scenario = db.scalar(select(ScenarioDraft).where(
            ScenarioDraft.client_id == client_id, ScenarioDraft.scenario_id == scenario_id,
        ).with_for_update())
        if scenario is None:
            raise DraftError("SCENARIO_NOT_FOUND", 404)
        if scenario.status != "draft" or scenario.version != expected_scenario_version:
            raise DraftError("S6_PRICE_BASIS_SCENARIO_STALE", 409)
        # Factor admission writers use this same ScenarioDraft row lock.
        cf = build_scenario_monthly_cashflow(
            factory, client_id=client_id, scenario_id=scenario_id,
            start_month=expected_target_date[:7], end_month=expected_target_date[:7],
        )
        with factory() as target_db:
            if target_db.get_bind().dialect.name != "postgresql":
                raise DraftError("S6_PRICE_BASIS_REQUIRES_POSTGRESQL", 503)
            target_db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
            target_result = target_service.assess_in_snapshot(target_db, client_id)
        if (not target_result.get("target_ready")
            or target_result.get("retirement_target_date") != expected_target_date
            or target_result.get("target_result_fingerprint") != expected_target_fingerprint):
            raise DraftError("S6_PRICE_BASIS_TARGET_STALE", 409)
        source_id = ("scenario-decision:" + quote(scenario_id, safe="")
                     + ":" + quote(decision_id, safe=""))
        source = next((item for item in cf["sources"] if item["source_id"] == source_id), None)
        if (not source or source.get("source_kind") != "CALCULATED_PENSION"
            or source.get("source_state") != "READY"
            or source.get("authority_fingerprint") != expected_source_fingerprint):
            raise DraftError("S6_PRICE_BASIS_SOURCE_STALE", 409)
        previous = current_rows(db, client_id, (scenario_id,)).get(source_id)
        revision = previous["revision"] if previous else 0
        if revision != expected_revision:
            raise DraftError("S6_PRICE_BASIS_REVISION_CONFLICT", 409)
        preimage = dict(
            source_id=source_id, scenario_id=scenario_id, decision_id=decision_id,
            scenario_version=expected_scenario_version,
            source_fingerprint=expected_source_fingerprint,
            target_fingerprint=expected_target_fingerprint,
            target_date=expected_target_date, price_basis=price_basis, revision=revision + 1,
        )
        row = ScenarioPensionPriceBasis(
            id=uuid4().hex, client_id=client_id, scenario_id=scenario_id,
            decision_id=decision_id, scenario_version=expected_scenario_version,
            revision=revision + 1, source_fingerprint=expected_source_fingerprint,
            target_fingerprint=expected_target_fingerprint, target_date=target_date,
            price_basis=price_basis, actor_id=actor,
            record_fingerprint=fingerprint({"contract": "S6_PRICE_BASIS_V1", **preimage}),
        )
        db.add(row)
        return {**preimage, "record_fingerprint": row.record_fingerprint,
                "provenance": "EXPLICIT_PROFESSIONAL"}
