from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.m09_scenario_subject import (
    M09ScenarioAdjustment,
    M09ScenarioSubject,
    M09ScenarioSubjectSeal,
    M09SubjectMonthlyResult,
    M09SubjectRun,
    SUBJECT_FAMILY,
    SUBJECT_VERSION,
)
from app.schemas.m10_comparison import M10ComparisonRequest, M10ComparisonResponse
from app.services.m09_cashflow_service import (
    DOMAIN_CONTRACT_VERSION,
    ENGINE_VERSION,
    RESULT_SCHEMA_VERSION,
    _digest,
    _error,
    _month_range,
)
from app.services.m09_scenario_subject_service import (
    SUBJECT_ENGINE_VERSION,
    SUBJECT_RESULT_SCHEMA_VERSION,
    _manifest_integrity_reasons,
    _semantic_component_evidence,
    _stored_factual_material,
    _subject_integrity_payload,
    subject_currentness,
    subject_eligibility,
)


COMPARISON_CONTRACT_VERSION = "m10-scenario-comparison-v2"
PAIR_ADMISSION_CONTRACT = "m10-pair-admission-v2"
COMPARISON_RESULT_SCHEMA = "m10-comparison-result-v2"
COMPARISON_FINGERPRINT_SCHEMA = "m10-comparison-fingerprint-v2"
SNAPSHOT_SCHEMA_VERSION = "m09-subject-upstream-snapshot-v1"
INVENTORY_SCHEMA_VERSION = "m09-resolved-component-inventory-v1"
M06_HANDOFF_CONTRACT = "m06-to-m09-monthly-amount-v1"

SHA256 = re.compile(r"^[0-9a-f]{64}$")
MONEY = re.compile(r"^-?(0|[1-9][0-9]{0,17})\.[0-9]{2}$")
DELTA = re.compile(r"^-?(0|[1-9][0-9]{0,18})\.[0-9]{2}$")
DELTA_LIMIT = Decimal("1999999999999999999.98")
METRICS = ("gross_inflow_total", "gross_outflow_total", "period_net")
SUPPORTED_DOMAINS = ("recurring_income", "recurring_expense", "m06_monthly_pension")
PUBLIC_BLOCKERS = (
    "comparison_run_unavailable",
    "comparison_same_subject",
    "comparison_pair_role_invalid",
    "comparison_scenario_contract_mismatch",
    "comparison_horizon_mismatch",
    "comparison_factual_baseline_material_mismatch",
    "comparison_component_domain_contract_mismatch",
    "comparison_engine_version_mismatch",
    "comparison_result_schema_version_mismatch",
    "comparison_factual_upstream_version_mismatch",
    "comparison_run_not_current",
    "comparison_run_not_eligible",
    "comparison_fingerprint_invalid",
    "comparison_semantically_identical_manifest",
    "comparison_month_alignment_mismatch",
    "comparison_numeric_domain_invalid",
)


def _block(code: str, message: str, status: int = 409):
    raise _error(code, message, status)


def _run(db: Session, client_id: int, run_id: str) -> M09SubjectRun:
    row = db.scalar(
        select(M09SubjectRun).where(
            M09SubjectRun.client_id == client_id,
            M09SubjectRun.run_id == run_id,
        )
    )
    if row is None:
        _block("comparison_run_unavailable", "comparison run is unavailable", 404)
    return row


def _subject(db: Session, run: M09SubjectRun) -> M09ScenarioSubject:
    row = db.scalar(
        select(M09ScenarioSubject).where(
            M09ScenarioSubject.client_id == run.client_id,
            M09ScenarioSubject.scenario_subject_id == run.scenario_subject_id,
        )
    )
    if row is None:
        _block("comparison_pair_role_invalid", "comparison subject role is invalid")
    return row


def _rows(db: Session, run: M09SubjectRun) -> list[M09SubjectMonthlyResult]:
    # This is the accepted M09 persisted read order used by PKG-014.
    return list(
        db.scalars(
            select(M09SubjectMonthlyResult)
            .where(
                M09SubjectMonthlyResult.client_id == run.client_id,
                M09SubjectMonthlyResult.scenario_subject_id == run.scenario_subject_id,
                M09SubjectMonthlyResult.run_id == run.run_id,
            )
            .order_by(M09SubjectMonthlyResult.month)
        )
    )


def _fingerprint(value: Any) -> bool:
    return isinstance(value, str) and SHA256.fullmatch(value) is not None


def _check_subject_integrity(
    db: Session, subject: M09ScenarioSubject, run: M09SubjectRun
) -> None:
    if (
        not _fingerprint(subject.calculation_semantic_fingerprint)
        or not _fingerprint(subject.integrity_fingerprint)
        or _digest(_subject_integrity_payload(subject)) != subject.integrity_fingerprint
    ):
        _block("comparison_fingerprint_invalid", "subject fingerprint is invalid")

    if (
        not _fingerprint(run.adjustment_manifest_fingerprint)
        or _manifest_integrity_reasons(db, subject)
        or run.adjustment_manifest_fingerprint != subject.adjustment_manifest_fingerprint
        or not isinstance(run.adjustment_manifest, dict)
        or run.adjustment_manifest != subject.adjustment_manifest
    ):
        _block("comparison_fingerprint_invalid", "adjustment manifest fingerprint is invalid")


def _check_run_integrity(
    db: Session,
    subject: M09ScenarioSubject,
    run: M09SubjectRun,
    rows: list[M09SubjectMonthlyResult],
) -> None:
    if not _fingerprint(run.semantic_result_fingerprint) or not _fingerprint(
        run.result_integrity_fingerprint
    ):
        _block("comparison_fingerprint_invalid", "result fingerprint is invalid")

    _check_subject_integrity(db, subject, run)

    if (
        not isinstance(run.factual_inventory, dict)
        or not _fingerprint(run.factual_inventory_fingerprint)
        or _digest(run.factual_inventory) != run.factual_inventory_fingerprint
        or not _fingerprint(run.factual_baseline_material_fingerprint)
        or _stored_factual_material(run) != run.factual_baseline_material_fingerprint
    ):
        _block("comparison_fingerprint_invalid", "factual inventory fingerprint is invalid")

    if not isinstance(run.upstream_snapshot, dict):
        _block("comparison_fingerprint_invalid", "upstream snapshot fingerprint is invalid")
    snapshot = {k: v for k, v in run.upstream_snapshot.items() if k != "snapshot_fingerprint"}
    if (
        not _fingerprint(run.upstream_snapshot_fingerprint)
        or _digest(snapshot) != run.upstream_snapshot_fingerprint
        or run.upstream_snapshot.get("snapshot_fingerprint")
        != run.upstream_snapshot_fingerprint
    ):
        _block("comparison_fingerprint_invalid", "upstream snapshot fingerprint is invalid")

    expected_months = _month_range(run.start_month, run.end_month)
    membership_valid = [row.month for row in rows] == expected_months
    if not isinstance(run.range_totals, dict) or set(run.range_totals) != set(METRICS):
        _block("comparison_fingerprint_invalid", "persisted range totals are invalid")
    for row in rows:
        payload = {
            "month": row.month,
            "component_evidence": row.component_evidence,
            "gross_inflow_total": format(row.gross_inflow_total, ".2f"),
            "gross_outflow_total": format(row.gross_outflow_total, ".2f"),
            "period_net": format(row.period_net, ".2f"),
        }
        if not _fingerprint(row.result_fingerprint) or _digest(payload) != row.result_fingerprint:
            _block("comparison_fingerprint_invalid", "persisted monthly result is invalid")
    # PKG-014 currentness owns missing, extra, duplicate, and incomplete month
    # membership. Integrity still verifies every row that is present. Aggregate
    # bindings are evaluated only for a complete canonical set so a pure
    # membership defect reaches predicates 19/20 instead of being remapped.
    if membership_valid:
        semantic = _digest(
            {
                "result_schema_version": SUBJECT_RESULT_SCHEMA_VERSION,
                "scenario_family": run.scenario_family,
                "scenario_contract_version": run.scenario_contract_version,
                "months": [
                    {
                        "month": row.month,
                        "component_evidence": _semantic_component_evidence(row.component_evidence),
                        "gross_inflow_total": format(row.gross_inflow_total, ".2f"),
                        "gross_outflow_total": format(row.gross_outflow_total, ".2f"),
                        "period_net": format(row.period_net, ".2f"),
                    }
                    for row in rows
                ],
                "range_totals": run.range_totals,
            }
        )
        integrity = _digest(
            {
                "semantic_result_fingerprint": run.semantic_result_fingerprint,
                "upstream_snapshot_fingerprint": run.upstream_snapshot_fingerprint,
                "factual_baseline_material_fingerprint": run.factual_baseline_material_fingerprint,
                "monthly_result_fingerprints": [row.result_fingerprint for row in rows],
                "range_totals": run.range_totals,
            }
        )
        if semantic != run.semantic_result_fingerprint or integrity != run.result_integrity_fingerprint:
            _block("comparison_fingerprint_invalid", "persisted result binding is invalid")


def _upstream_versions(run: M09SubjectRun) -> list[dict[str, Any]]:
    domains = run.factual_inventory.get("domains")
    if not isinstance(domains, list):
        _block("comparison_factual_upstream_version_mismatch", "factual upstream versions are malformed")
    output: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for domain in domains:
        if not isinstance(domain, dict) or not isinstance(domain.get("domain_identity"), str) or not isinstance(domain.get("candidates"), list):
            _block("comparison_factual_upstream_version_mismatch", "factual upstream versions are malformed")
        domain_id = domain["domain_identity"]
        if domain_id not in SUPPORTED_DOMAINS:
            _block("comparison_factual_upstream_version_mismatch", "factual upstream domain is unsupported")
        for candidate in domain["candidates"]:
            if not isinstance(candidate, dict) or not isinstance(candidate.get("included"), bool):
                _block("comparison_factual_upstream_version_mismatch", "factual upstream versions are malformed")
            if candidate["included"] is not True:
                continue
            required = ("candidate_identity", "source_identity", "source_version", "source_fingerprint")
            if any(not isinstance(candidate.get(key), str) for key in required) or not _fingerprint(candidate["source_fingerprint"]):
                _block("comparison_factual_upstream_version_mismatch", "factual upstream versions are malformed")
            key = (domain_id, candidate["candidate_identity"])
            if key in seen:
                _block("comparison_factual_upstream_version_mismatch", "factual upstream versions contain duplicate identities")
            seen.add(key)
            handoffs: list[str] = []
            if domain_id == "m06_monthly_pension":
                components = candidate.get("components")
                if not isinstance(components, list) or not components:
                    _block("comparison_factual_upstream_version_mismatch", "M06 handoff evidence is missing")
                for component in components:
                    if not isinstance(component, dict):
                        _block("comparison_factual_upstream_version_mismatch", "M06 component evidence is malformed")
                    provenance = component.get("provenance")
                    if not isinstance(provenance, dict):
                        _block("comparison_factual_upstream_version_mismatch", "M06 component provenance is malformed")
                    if provenance.get("handoff_contract_version") != M06_HANDOFF_CONTRACT:
                        _block("comparison_factual_upstream_version_mismatch", "M06 handoff evidence is unsupported")
                handoffs = [M06_HANDOFF_CONTRACT]
            output.append(
                {
                    "domain_identity": domain_id,
                    "candidate_identity": candidate["candidate_identity"],
                    "source_identity": candidate["source_identity"],
                    "source_version": candidate["source_version"],
                    "source_fingerprint": candidate["source_fingerprint"],
                    "handoff_contract_versions": handoffs,
                }
            )
    return output


def _money(value: Any, *, delta: bool = False) -> tuple[Decimal, str]:
    if isinstance(value, bool) or not isinstance(value, (Decimal, str)):
        _block("comparison_numeric_domain_invalid", "persisted monetary value is invalid")
    pattern = DELTA if delta else MONEY
    if isinstance(value, Decimal):
        number = value
        if not number.is_finite() or number.as_tuple().exponent != -2:
            _block("comparison_numeric_domain_invalid", "persisted monetary value is invalid")
    else:
        if pattern.fullmatch(value) is None:
            _block("comparison_numeric_domain_invalid", "persisted monetary value is invalid")
        try:
            number = Decimal(value)
        except InvalidOperation:
            _block("comparison_numeric_domain_invalid", "persisted monetary value is invalid")
    if not number.is_finite() or (delta and abs(number) > DELTA_LIMIT):
        _block("comparison_numeric_domain_invalid", "persisted monetary value is outside the comparison domain")
    canonical = "0.00" if number == 0 else format(number, ".2f")
    if pattern.fullmatch(canonical) is None:
        _block("comparison_numeric_domain_invalid", "persisted monetary value is not canonical")
    return number, canonical


def _assert_month_alignment(
    reference_months: list[str],
    compared_months: list[str],
    expected_months: list[str],
) -> None:
    """Fail closed on the defensive pair-level canonical sequence invariant."""
    if (
        reference_months != expected_months
        or compared_months != expected_months
        or reference_months != compared_months
    ):
        _block("comparison_month_alignment_mismatch", "persisted month sequences do not align")


def _metric(reference: Any, compared: Any) -> dict[str, str]:
    reference_number, reference_text = _money(reference)
    compared_number, compared_text = _money(compared)
    delta_number = compared_number - reference_number
    _, delta_text = _money(delta_number, delta=True)
    relation = (
        "equal"
        if delta_number == 0
        else "compared_greater_than_reference"
        if delta_number > 0
        else "compared_lower_than_reference"
    )
    return {
        "reference_value": reference_text,
        "compared_value": compared_text,
        "delta": delta_text,
        "relation": relation,
    }


def _run_evidence(run: M09SubjectRun, subject: M09ScenarioSubject) -> dict[str, str]:
    return {
        "run_id": run.run_id,
        "scenario_subject_id": run.scenario_subject_id,
        "subject_type": subject.subject_type,
        "calculation_semantic_fingerprint": subject.calculation_semantic_fingerprint,
        "integrity_fingerprint": subject.integrity_fingerprint,
        "adjustment_manifest_fingerprint": run.adjustment_manifest_fingerprint,
        "factual_inventory_fingerprint": run.factual_inventory_fingerprint,
        "upstream_snapshot_fingerprint": run.upstream_snapshot_fingerprint,
        "semantic_result_fingerprint": run.semantic_result_fingerprint,
        "result_integrity_fingerprint": run.result_integrity_fingerprint,
    }


def compare_runs(
    db: Session, client_id: int, request: M10ComparisonRequest
) -> M10ComparisonResponse:
    # Predicates 1-2: client-scoped, reference first, with no global probe.
    reference = _run(db, client_id, request.reference_run_id)
    compared = _run(db, client_id, request.compared_run_id)
    reference_subject = _subject(db, reference)
    compared_subject = _subject(db, compared)

    if reference.scenario_subject_id == compared.scenario_subject_id:
        _block("comparison_same_subject", "comparison subjects must be distinct")

    seal = db.scalar(
        select(M09ScenarioSubjectSeal).where(
            M09ScenarioSubjectSeal.client_id == client_id,
            M09ScenarioSubjectSeal.scenario_subject_id == compared_subject.scenario_subject_id,
        )
    )
    adjustment_count = db.scalar(
        select(M09ScenarioAdjustment)
        .where(
            M09ScenarioAdjustment.client_id == client_id,
            M09ScenarioAdjustment.scenario_subject_id == compared_subject.scenario_subject_id,
        )
        .limit(1)
    )
    if (
        reference_subject.subject_type != "baseline"
        or compared_subject.subject_type != "adjusted"
        or seal is None
        or seal.adjustment_count < 1
        or adjustment_count is None
    ):
        _block("comparison_pair_role_invalid", "comparison run roles are invalid")

    if (
        reference.scenario_family != SUBJECT_FAMILY
        or compared.scenario_family != SUBJECT_FAMILY
        or reference.scenario_contract_version != SUBJECT_VERSION
        or compared.scenario_contract_version != SUBJECT_VERSION
    ):
        _block("comparison_scenario_contract_mismatch", "scenario contract is unsupported or unequal")
    if (reference.start_month, reference.end_month) != (compared.start_month, compared.end_month):
        _block("comparison_horizon_mismatch", "comparison horizons differ")

    reference_rows = _rows(db, reference)
    compared_rows = _rows(db, compared)
    _check_run_integrity(db, reference_subject, reference, reference_rows)
    _check_run_integrity(db, compared_subject, compared, compared_rows)

    reference_currentness = subject_currentness(
        db, client_id, reference.scenario_subject_id, reference.run_id
    )
    if (
        reference_currentness.assessment_contract_version
        != "m09-subject-currentness-v1"
        or not reference_currentness.is_current
    ):
        _block("comparison_run_not_current", "reference run is not current")
    compared_currentness = subject_currentness(
        db, client_id, compared.scenario_subject_id, compared.run_id
    )
    if (
        compared_currentness.assessment_contract_version
        != "m09-subject-currentness-v1"
        or not compared_currentness.is_current
    ):
        _block("comparison_run_not_current", "compared run is not current")
    reference_eligibility = subject_eligibility(
        db, client_id, reference.scenario_subject_id, reference.run_id
    )
    if (
        reference_eligibility.eligibility_contract_version
        != "m09-to-m10-eligibility-v2"
        or not reference_eligibility.eligible_for_m10
    ):
        _block("comparison_run_not_eligible", "reference run is not eligible")
    compared_eligibility = subject_eligibility(
        db, client_id, compared.scenario_subject_id, compared.run_id
    )
    if (
        compared_eligibility.eligibility_contract_version
        != "m09-to-m10-eligibility-v2"
        or not compared_eligibility.eligible_for_m10
    ):
        _block("comparison_run_not_eligible", "compared run is not eligible")

    if reference.factual_baseline_material_fingerprint != compared.factual_baseline_material_fingerprint:
        _block("comparison_factual_baseline_material_mismatch", "factual baseline material differs")
    if (
        reference.component_domain_contract_version != DOMAIN_CONTRACT_VERSION
        or compared.component_domain_contract_version != DOMAIN_CONTRACT_VERSION
    ):
        _block("comparison_component_domain_contract_mismatch", "component-domain contract differs or is unsupported")
    for run in (reference, compared):
        if run.upstream_snapshot.get("engine_version") != SUBJECT_ENGINE_VERSION or ENGINE_VERSION != "m09-aggregation-v1":
            _block("comparison_engine_version_mismatch", "engine version differs or is unsupported")
        if (
            RESULT_SCHEMA_VERSION != "m09-result-v1"
            or run.upstream_snapshot.get("result_schema_version") != SUBJECT_RESULT_SCHEMA_VERSION
            or run.upstream_snapshot.get("snapshot_schema_version") != SNAPSHOT_SCHEMA_VERSION
            or run.factual_inventory.get("inventory_schema_version") != INVENTORY_SCHEMA_VERSION
        ):
            _block("comparison_result_schema_version_mismatch", "result or dependency schema differs or is unsupported")
    reference_upstream = _upstream_versions(reference)
    compared_upstream = _upstream_versions(compared)
    if reference_upstream != compared_upstream:
        _block("comparison_factual_upstream_version_mismatch", "factual upstream versions differ")
    if reference_subject.calculation_semantic_fingerprint == compared_subject.calculation_semantic_fingerprint:
        _block("comparison_semantically_identical_manifest", "adjustment manifests are semantically identical")

    reference_months = [row.month for row in reference_rows]
    compared_months = [row.month for row in compared_rows]
    expected = _month_range(reference.start_month, reference.end_month)
    _assert_month_alignment(reference_months, compared_months, expected)

    monthly = []
    for reference_row, compared_row in zip(reference_rows, compared_rows, strict=True):
        monthly.append(
            {
                "month": reference_row.month,
                **{
                    metric: _metric(getattr(reference_row, metric), getattr(compared_row, metric))
                    for metric in METRICS
                },
            }
        )
    range_totals = {
        metric: _metric(reference.range_totals[metric], compared.range_totals[metric])
        for metric in METRICS
    }
    material: dict[str, Any] = {
        "comparison_contract_version": COMPARISON_CONTRACT_VERSION,
        "pair_admission_contract": PAIR_ADMISSION_CONTRACT,
        "comparison_result_schema": COMPARISON_RESULT_SCHEMA,
        "comparison_fingerprint_schema": COMPARISON_FINGERPRINT_SCHEMA,
        "delta_direction": "compared_minus_reference",
        "client_id": client_id,
        "scenario_family": SUBJECT_FAMILY,
        "scenario_contract_version": SUBJECT_VERSION,
        "horizon": {"start_month": reference.start_month, "end_month": reference.end_month},
        "factual_baseline_material_fingerprint": reference.factual_baseline_material_fingerprint,
        "component_domain_contract_version": DOMAIN_CONTRACT_VERSION,
        "versions": {
            "factual_engine_version": ENGINE_VERSION,
            "factual_result_schema_version": RESULT_SCHEMA_VERSION,
            "subject_engine_version": SUBJECT_ENGINE_VERSION,
            "subject_result_schema_version": SUBJECT_RESULT_SCHEMA_VERSION,
            "upstream_snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
            "factual_inventory_schema_version": INVENTORY_SCHEMA_VERSION,
            "factual_upstream_versions": reference_upstream,
        },
        "reference_run": _run_evidence(reference, reference_subject),
        "compared_run": _run_evidence(compared, compared_subject),
        "monthly_comparisons": monthly,
        "range_totals": range_totals,
    }
    response = {**material, "comparison_fingerprint": _digest(material)}
    return M10ComparisonResponse.model_validate(response)
