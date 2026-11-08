"""Package 2: admitted Stage 6 producers bound to one unified scenario snapshot.

Read-only internal service. No API, mutation, tax or net calculation.
The approved package-1 V1 envelope remains intact; this is a separately
versioned extension with nonbinding financial estimates only.
"""
from __future__ import annotations

from copy import deepcopy
import hmac

from app.services.scenario_input_manifest_service import _fingerprint
from app.services.scenario_snapshot_candidate_service import (
    ScenarioSnapshotError, build_manifest_candidate_snapshot,
)
from app.services.scenario_unified_result_service import (
    _assemble, FINANCIAL_DOMAINS, CONTRACT as BASE_CONTRACT,
)
from app.services.scenario_financial_evidence_service import (
    collect_scenario_financial_evidence,
)
from app.services.scenario_capital_projection_service import (
    build_scenario_capital_projection,
)
from app.services.scenario_stage6_single_pension_estimate_service import (
    _aggregate_extension, _valid_sealed_result,
    AGGREGATE_CONTRACT,
)
from app.services.scenario_stage6_monthly_cashflow_service import (
    _cashflow_extension, validate_monthly_cashflow_result,
    CONTRACT as CASHFLOW_CONTRACT,
)

CONTRACT = "UNIFIED_RETIREMENT_SCENARIO_ENGINE_BINDINGS_V1"
SEVERANCE_PLANNING_CONTRACT = "SEVERANCE_SCENARIO_PLANNING_BINDING_V1"
INERT_DOMAINS = {
    "capital": "CAPITAL_PROJECTION_IS_CLIENT_SCOPED_NOT_SCENARIO_ADMITTED",
    "severance": "SEVERANCE_SCENARIO_ADMISSION_NOT_DEFINED",
    "fixation_tax": "FIXATION_ELIGIBILITY_AND_SCENARIO_TAX_ADMISSION_REQUIRED",
    "scenario_comparison": "FULL_COMPARISON_OUT_OF_SCOPE_PACKAGE_2",
}
HASH = set("0123456789abcdef")


def _bound_domain(*, state: str, result=None, fingerprint=None,
                  blockers=(), producer=None):
    return {
        "state": state,
        "result": deepcopy(result),
        "result_fingerprint": fingerprint,
        "producer_contract": producer,
        "professional_authority": False,
        "blockers": sorted(set(blockers)),
    }


def _pension(db, pair, base):
    identity = base["identity"]
    client_id, scenario_id, version = (
        identity["client_id"], identity["scenario_id"], identity["scenario_version"],
    )
    if base["blockers"]:
        return _bound_domain(
            state="BLOCKED", blockers=["UNIFIED_BASE_NOT_CURRENT"],
            producer=AGGREGATE_CONTRACT,
        )
    aggregate = _aggregate_extension(
        client_id=client_id, scenario_id=scenario_id,
    )(db, pair)
    if (aggregate.get("schema_version") != AGGREGATE_CONTRACT
            or aggregate.get("client_id") != client_id
            or aggregate.get("scenario_id") != scenario_id
            or aggregate.get("scenario_version") != version
            or aggregate.get("execution_allowed") is not False):
        return _bound_domain(state="BLOCKED", blockers=["PENSION_AGGREGATE_IDENTITY_INVALID"],
                             producer=AGGREGATE_CONTRACT)
    preimage = {k: v for k, v in aggregate.items() if k != "aggregate_fingerprint"}
    expected = _fingerprint({
        "contract_version": "STAGE6_PENSION_DECISION_AGGREGATE_FINGERPRINT_V1",
        "result": preimage,
    })
    if (not isinstance(aggregate.get("aggregate_fingerprint"), str)
            or not hmac.compare_digest(expected, aggregate["aggregate_fingerprint"])):
        return _bound_domain(state="BLOCKED", blockers=["PENSION_AGGREGATE_FINGERPRINT_INVALID"],
                             producer=AGGREGATE_CONTRACT)
    expected_ids = sorted(
        row["decision_id"] for row in pair["manifest"]["decisions"]
        if row["action"] == "pension"
    )
    results = aggregate.get("decision_results")
    if (not isinstance(results, list)
            or sorted(row.get("decision_id") for row in results
                      if isinstance(row, dict)) != expected_ids
            or len(results) != len(expected_ids)
            or any(not _valid_sealed_result(
                row, client_id=client_id, scenario_id=scenario_id,
                decision_id=row["decision_id"],
            ) for row in results)):
        return _bound_domain(state="BLOCKED", blockers=["PENSION_DECISION_RESULT_INVALID"],
                             producer=AGGREGATE_CONTRACT)
    if any(row.get("scenario_version") not in (version, None) for row in results):
        return _bound_domain(state="BLOCKED", blockers=["PENSION_DECISION_VERSION_INVALID"],
                             producer=AGGREGATE_CONTRACT)
    ready = aggregate.get("aggregation_state") == "COMPLETE"
    if (not ready or not results or
            any(row["result_state"] != "RESULT_READY" for row in results) or
            not isinstance(aggregate.get("monthly_pension_gross_total_ils"), str) or
            not isinstance(aggregate.get("comparison_basis"), dict) or
            aggregate["comparison_basis"].get("retirement_target_date")
            != base["reference_dates"]["retirement_target_date"]):
        return _bound_domain(
            state="BLOCKED", blockers=aggregate.get("blockers") or
            ["PENSION_AGGREGATE_NOT_ADMITTED"], producer=AGGREGATE_CONTRACT,
        )
    # Stage 6 calls this a nonbinding estimate. Never promote it into a
    # guaranteed pension, insurer quote or taxation authority.
    return _bound_domain(
        state="NONBINDING_ESTIMATE", result=aggregate,
        fingerprint=aggregate["aggregate_fingerprint"],
        producer=AGGREGATE_CONTRACT,
    )


def _cashflow(db, pair, base, start_month, end_month):
    identity = base["identity"]
    client_id, scenario_id, version = (
        identity["client_id"], identity["scenario_id"], identity["scenario_version"],
    )
    if base["blockers"]:
        return _bound_domain(
            state="BLOCKED", blockers=["UNIFIED_BASE_NOT_CURRENT"],
            producer=CASHFLOW_CONTRACT,
        )
    result = _cashflow_extension(
        client_id=client_id, scenario_id=scenario_id,
        start_month=start_month, end_month=end_month,
    )(db, pair)
    if (not validate_monthly_cashflow_result(
            result, client_id=client_id, scenario_id=scenario_id,
            scenario_version=version, start_month=start_month, end_month=end_month,
        ) or result.get("manifest_fingerprint") != base["manifest_fingerprint"]):
        return _bound_domain(
            state="BLOCKED", blockers=["CASHFLOW_CONTRACT_INVALID"],
            producer=CASHFLOW_CONTRACT,
        )
    if result["cashflow_state"] != "COMPLETE":
        return _bound_domain(
            state="BLOCKED", blockers=result["blocker_codes"] or
            ["CASHFLOW_INCOMPLETE"], producer=CASHFLOW_CONTRACT,
        )
    if any(row["cashflow_state"] != "COMPLETE" or
           row["gross_income_total_ils"] is None
           for row in result["monthly_rows"]):
        return _bound_domain(state="BLOCKED", blockers=["CASHFLOW_MONTH_INCOMPLETE"],
                             producer=CASHFLOW_CONTRACT)
    # The canonical Stage 6 producer already deduplicates source identities
    # and reconciles pension/recurring-income contributions. Never resummate.
    return _bound_domain(
        state="NONBINDING_GROSS", result=result,
        fingerprint=result["cashflow_fingerprint"],
        producer=CASHFLOW_CONTRACT,
    )


def _severance_planning_domain(base, evidence):
    """Non-monetary projection of saved severance choices from this snapshot.

    The canonical severance evidence adapter has already called read_choices
    inside the same database Session. Do not reopen a transaction or aggregate
    these amounts with pension, capital or historical grant amounts.
    """
    identity = base["identity"]
    expected = {key: identity[key] for key in (
        "client_id", "scenario_id", "scenario_version",
    )}
    if (any(evidence.get(key) != val for key, val in expected.items())
            or evidence.get("domain") != "severance"
            or evidence.get("authority_state") != "FACTUAL_EVIDENCE_ONLY"):
        raise ScenarioSnapshotError("SEVERANCE_EVIDENCE_IDENTITY_INVALID")
    choices = evidence.get("facts", {}).get("scenario_planning_choices")
    if (not isinstance(choices, dict)
            or any(choices.get(key) != val for key, val in expected.items())
            or choices.get("authority_state") != "DRAFT_ONLY"
            or choices.get("execution_allowed") is not False
            or not isinstance(choices.get("choices"), list)):
        raise ScenarioSnapshotError("SEVERANCE_PLANNING_IDENTITY_INVALID")
    rows = []
    seen = set()
    blockers = {"SEVERANCE_PLANNING_NOT_PROFESSIONALLY_ADMITTED",
                *evidence["blockers"]}
    allowed_states = {
        "DRAFT_ONLY", "BLOCKED_SOURCE_STALE", "BLOCKED_SCENARIO_VERSION_STALE",
        "BLOCKED_SOURCE_MISSING_OR_FOREIGN", "BLOCKED_COMPONENT_OVERALLOCATED",
        "BLOCKED_GRANT_COMPONENT_OVERLAP_UNRECONCILED",
        "BLOCKED_SCENARIO_NOT_ACTIVE",
    }
    for item in choices["choices"]:
        if (not isinstance(item, dict)
                or item.get("client_id") != expected["client_id"]
                or item.get("scenario_id") != expected["scenario_id"]
                or item.get("current_scenario_version") != expected["scenario_version"]
                or item.get("source_kind") not in {"grant", "pension_component"}
                or item.get("state") not in allowed_states
                or item.get("execution_allowed") is not False
                or item.get("professional_authority") is not False
                or any(item.get(field) is not None for field in (
                    "actual_paid_amount_ils", "future_payable_amount_ils",
                    "exempt_amount_ils", "net_amount_ils",
                ))):
            raise ScenarioSnapshotError("SEVERANCE_PLANNING_CHOICE_INVALID")
        key = (item["source_kind"], item.get("source_id"))
        if not isinstance(key[1], str) or not key[1] or key in seen:
            raise ScenarioSnapshotError("SEVERANCE_PLANNING_SOURCE_DUPLICATE")
        seen.add(key)
        choice_blockers = ["SEVERANCE_PLANNING_NOT_PROFESSIONALLY_ADMITTED"]
        if item["state"] != "DRAFT_ONLY":
            choice_blockers.append(item["state"])
            blockers.add(item["state"])
        if "SEVERANCE_GRANT_COMPONENT_OVERLAP_UNRECONCILED" in evidence["blockers"]:
            choice_blockers.append("SEVERANCE_GRANT_COMPONENT_OVERLAP_UNRECONCILED")
        rows.append({
            "source_kind": item["source_kind"],
            "source_id": item["source_id"],
            "choice": item["choice"],
            "planned_amount_ils": item["planned_amount_ils"],
            "source_fingerprint": item["source_fingerprint"],
            "saved_from_scenario_version": item["saved_from_scenario_version"],
            "state": item["state"],
            "blockers": sorted(set(choice_blockers)),
            "execution_allowed": False,
            "professional_authority": False,
            "actual_payment_ils": None,
            "tax_exemption_ils": None,
            "tax_due_ils": None,
            "net_cashflow_ils": None,
            "withdrawable_capital_ils": None,
        })
    # Sorting also makes equivalent source selection ordering deterministic.
    rows.sort(key=lambda item: (item["source_kind"], item["source_id"]))
    planning = {
        "contract": SEVERANCE_PLANNING_CONTRACT,
        **expected,
        "choices": rows,
        "blockers": sorted(blockers),
        "evidence_fingerprint": evidence["evidence_fingerprint"],
        "execution_allowed": False,
        "professional_authority": False,
        "approved_withdrawal_ils": None,
        "actual_grants_paid_ils": None,
        "approved_continuity": None,
        "exempt_amount_ils": None,
        "tax_due_ils": None,
        "net_cashflow_ils": None,
        "withdrawable_capital_ils": None,
    }
    planning["planning_fingerprint"] = _fingerprint(planning)
    domain = _bound_domain(
        state="BLOCKED", blockers=blockers,
        producer=SEVERANCE_PLANNING_CONTRACT,
    )
    # Contract extension: positive planning evidence is NOT a financial result.
    # Preserve the approved blocked-domain shape and its null result fingerprint.
    domain["planning"] = planning
    return domain


def _assemble_bound(db, pair, client_id, scenario_id, *, start_month, end_month):
    base = _assemble(db, pair, client_id, scenario_id)
    if (base["schema_version"] != BASE_CONTRACT or
            base["identity"]["client_id"] != client_id or
            base["identity"]["scenario_id"] != scenario_id):
        raise ScenarioSnapshotError("UNIFIED_ENGINE_BASE_IDENTITY_INVALID")
    domains = {}
    for name in FINANCIAL_DOMAINS:
        if name in INERT_DOMAINS:
            domains[name] = _bound_domain(
                state="BLOCKED", blockers=[INERT_DOMAINS[name]],
            )
    # Scenario-scoped factual sources may be shown independently of payment,
    # withdrawal, tax, and government approval. They never create a positive
    # financial domain result or gain permission to execute source conversions.
    financial_evidence = collect_scenario_financial_evidence(db, base)
    domains["capital"] = build_scenario_capital_projection(
        db, base, financial_evidence,
    )
    domains["severance"] = _severance_planning_domain(
        base, financial_evidence["severance"],
    )
    domains["pension_gross"] = _pension(db, pair, base)
    if (start_month is None and end_month is None):
        domains["monthly_cashflow"] = _bound_domain(
            state="NOT_REQUESTED", blockers=["CASHFLOW_HORIZON_NOT_SUPPLIED"],
            producer=CASHFLOW_CONTRACT,
        )
    elif isinstance(start_month, str) and isinstance(end_month, str):
        domains["monthly_cashflow"] = _cashflow(
            db, pair, base, start_month, end_month,
        )
    else:
        raise ValueError("UNIFIED_CASHFLOW_HORIZON_INVALID")
    payload = {
        "schema_version": CONTRACT,
        "base": base,
        "identity": deepcopy(base["identity"]),
        "domain_results": {k: domains[k] for k in FINANCIAL_DOMAINS},
        "financial_evidence": financial_evidence,
        "net_income": _bound_domain(
            state="BLOCKED", blockers=["NET_TAX_EXECUTION_NOT_AUTHORIZED"],
        ),
        "execution_allowed": False,
        "professional_authority": False,
    }
    payload["result_fingerprint"] = _fingerprint(payload)
    return payload


def build_unified_scenario_engine_bindings(
    factory, *, client_id: int, scenario_id: str,
    start_month: str | None = None, end_month: str | None = None,
) -> dict:
    """One real PostgreSQL read-only snapshot; no archived engine invocation."""
    if (start_month is None) != (end_month is None):
        raise ValueError("UNIFIED_CASHFLOW_HORIZON_INVALID")
    if start_month is not None:
        from app.services.scenario_stage6_monthly_cashflow_service import _months
        _months(start_month, end_month)
    return build_manifest_candidate_snapshot(
        factory, client_id=client_id, scenario_id=scenario_id,
        _snapshot_extension=lambda db, pair: _assemble_bound(
            db, pair, client_id, scenario_id,
            start_month=start_month, end_month=end_month,
        ),
    )
