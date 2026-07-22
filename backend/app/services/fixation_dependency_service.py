from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.fixation_run import FixationRun
from app.schemas.fixation_admissibility import AdmissibleFixationInput
from app.schemas.fixation_dependency_manifest import (
    CBS_ADAPTER_CONTRACT_VERSION,
    COMPARISON_ALGORITHM_VERSION,
    FINGERPRINT_ALGORITHM_VERSION,
    FINGERPRINT_SCHEMA_VERSION,
    MANIFEST_SCHEMA_VERSION,
    CalculationContextDependencyContent,
    CalculationContextDependencyEntry,
    CapitalizationDependencyContent,
    CapitalizationDependencyEntry,
    CbsDependencyContent,
    CbsDependencyEntry,
    DependencyComparisonResponse,
    DependencyEntry,
    FixationDependencyManifest,
    FutureReserveDependencyContent,
    FutureReserveDependencyEntry,
    GrantDependencyContent,
    GrantDependencyEntry,
    M07DependencyContent,
    M07DependencyEntry,
    ParameterDependencyContent,
    ParameterDependencyEntry,
    ParameterValuesContent,
    PerDependencyComparison,
)


def _decimal(value: float | Decimal | None) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def _canonical_decimal(value: Decimal) -> str:
    if not value.is_finite():
        raise ValueError("non-finite decimals cannot be fingerprinted")
    normalized = format(value, "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return "0" if normalized in {"", "-0"} else normalized


def canonicalize_dependency_value(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="python")
    if isinstance(value, dict):
        return {
            str(key): canonicalize_dependency_value(value[key])
            for key in sorted(value, key=lambda item: str(item))
        }
    if isinstance(value, (list, tuple, set)):
        canonical_items = [canonicalize_dependency_value(item) for item in value]
        return sorted(
            canonical_items,
            key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        )
    if isinstance(value, Decimal):
        return _canonical_decimal(value)
    if isinstance(value, float):
        return _canonical_decimal(Decimal(str(value)))
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.isoformat(timespec="microseconds")
        utc_value = value.astimezone(timezone.utc)
        return utc_value.isoformat(timespec="microseconds").replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"unsupported canonical dependency value: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    return json.dumps(
        canonicalize_dependency_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def dependency_fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _entry_sort_key(entry: DependencyEntry) -> tuple[str, str]:
    return entry.dependency_type, entry.stable_identity or ""


def _entry_kwargs(content: Any, *, availability: str = "available", reasons: list[str] | None = None) -> dict:
    return {
        "availability_state": availability,
        "canonical_content": content,
        "fingerprint": dependency_fingerprint(content),
        "fingerprint_algorithm": FINGERPRINT_ALGORITHM_VERSION,
        "fingerprint_schema_version": FINGERPRINT_SCHEMA_VERSION,
        "reason_codes": sorted(reasons or []),
    }


def _unavailable_entry_kwargs(reason: str) -> dict:
    return {
        "availability_state": "unavailable",
        "canonical_content": None,
        "fingerprint": None,
        "fingerprint_algorithm": FINGERPRINT_ALGORITHM_VERSION,
        "fingerprint_schema_version": FINGERPRINT_SCHEMA_VERSION,
        "reason_codes": [reason],
    }


def _cbs_entry(grant: Any) -> CbsDependencyEntry | None:
    request = grant.cbs_request_evidence
    response = grant.cbs_response_evidence
    failure = grant.indexation_failure_evidence
    is_relevant = request is not None or response is not None or failure is not None or (
        grant.inclusion_decision == "include"
        and grant.indexation_mode
        in {"cbs_system_calculation_required", "cbs_system_calculated"}
    )
    if not is_relevant:
        return None
    if request is None or (response is None and failure is None):
        return CbsDependencyEntry(
            stable_identity=grant.grant_id,
            **_unavailable_entry_kwargs("cbs_dependency_evidence_unavailable"),
        )

    timestamp = (
        response.calculation_timestamp
        if response is not None
        else failure.calculation_timestamp if failure is not None else request.calculation_timestamp
    )
    content = CbsDependencyContent(
        grant_id=grant.grant_id,
        cpi_code=(
            grant.cpi_code
            or request.cpi_code
            or (response.cpi_code if response is not None else None)
            or (failure.cpi_code if failure is not None else None)
        ),
        endpoint=(
            response.endpoint
            if response is not None
            else failure.source_endpoint if failure is not None else request.endpoint
        ),
        request_amount=request.amount,
        resolved_base_date=request.resolved_base_date,
        base_date_source=request.base_date_source,
        target_date=request.target_date,
        raw_official_value=response.raw_to_value if response is not None else None,
        rounded_application_value=_decimal(grant.system_calculated_amount),
        response_evidence=response,
        calculation_timestamp=timestamp,
        missing_optional_fields=sorted(response.missing_optional_fields) if response is not None else [],
        failure_evidence=failure,
        adapter_contract_version=CBS_ADAPTER_CONTRACT_VERSION,
    )
    return CbsDependencyEntry(stable_identity=grant.grant_id, **_entry_kwargs(content))


def build_fixation_dependency_manifest(
    *,
    run_id: int,
    run_identity: str,
    client_id: int,
    calculation_version: str,
    input_contract_version: str,
    result_contract_version: str | None,
    context: AdmissibleFixationInput | None,
    trusted_system_evidence: bool = False,
) -> FixationDependencyManifest:
    if context is None:
        return FixationDependencyManifest(
            run_id=run_id,
            run_identity=run_identity,
            client_id=client_id,
            calculation_version=calculation_version,
            input_contract_version=input_contract_version,
            result_contract_version=result_contract_version,
            manifest_schema_version=MANIFEST_SCHEMA_VERSION,
            fingerprint_algorithm_version=FINGERPRINT_ALGORITHM_VERSION,
            context_availability="unavailable",
            context_reason_codes=["admissible_context_unavailable"],
            dependencies=[],
            manifest_fingerprint=None,
        )
    has_system_cbs_evidence = any(
        grant.indexation_mode == "cbs_system_calculated"
        or grant.system_calculated_amount is not None
        or grant.cbs_request_evidence is not None
        or grant.cbs_response_evidence is not None
        or grant.indexation_failure_evidence is not None
        for grant in context.grants
    )
    if has_system_cbs_evidence and not trusted_system_evidence:
        return FixationDependencyManifest(
            run_id=run_id,
            run_identity=run_identity,
            client_id=client_id,
            calculation_version=calculation_version,
            input_contract_version=input_contract_version,
            result_contract_version=result_contract_version,
            manifest_schema_version=MANIFEST_SCHEMA_VERSION,
            fingerprint_algorithm_version=FINGERPRINT_ALGORITHM_VERSION,
            context_availability="unavailable",
            context_reason_codes=["current_cbs_evidence_unavailable"],
            dependencies=[],
            manifest_fingerprint=None,
        )
    warnings = context.upstream_context.warnings
    sorted_warnings = (
        sorted(warnings, key=lambda warning: (warning.code, warning.message))
        if warnings is not None
        else None
    )
    m07_content = M07DependencyContent(
        profile_id=context.upstream_context.profile_id,
        state=context.upstream_context.state,
        qualification_trace_id=context.upstream_context.qualification_trace_id,
        warnings=sorted_warnings,
        review_reason=context.upstream_context.review_reason,
        reviewed_by=context.upstream_context.reviewed_by,
        review_timestamp=context.upstream_context.review_timestamp,
    )
    calculation_context_content = CalculationContextDependencyContent(
        eligibility_date=context.eligibility_date,
        eligibility_year=context.eligibility_year,
        calculation_version=calculation_version,
        input_contract_version=input_contract_version,
        result_contract_version=result_contract_version,
        manifest_schema_version=MANIFEST_SCHEMA_VERSION,
        fingerprint_algorithm_version=FINGERPRINT_ALGORITHM_VERSION,
        fingerprint_schema_version=FINGERPRINT_SCHEMA_VERSION,
        comparison_algorithm_version=COMPARISON_ALGORITHM_VERSION,
    )
    entries: list[DependencyEntry] = [
        CalculationContextDependencyEntry(
            stable_identity=None,
            **_entry_kwargs(calculation_context_content),
        ),
        M07DependencyEntry(
            stable_identity=context.upstream_context.profile_id,
            **_entry_kwargs(m07_content),
        )
    ]

    parameter_set = context.parameter_set
    parameter_content = ParameterDependencyContent(
        parameter_set_id=parameter_set.parameter_set_id,
        tax_year=parameter_set.tax_year,
        effective_from=parameter_set.effective_from,
        effective_to=parameter_set.effective_to,
        values=ParameterValuesContent(
            monthly_cap=_decimal(parameter_set.values.monthly_cap),
            exemption_percentage=_decimal(parameter_set.values.exemption_percentage),
            capital_multiplier=_decimal(parameter_set.values.capital_multiplier),
            grant_impact_multiplier=_decimal(parameter_set.values.grant_impact_multiplier),
        ),
        source_basis=parameter_set.source_basis,
        status=parameter_set.status,
        accepted_for_use=parameter_set.accepted_for_use,
        accepted_by=parameter_set.accepted_by,
        decision_timestamp=parameter_set.decision_timestamp,
    )
    entries.append(
        ParameterDependencyEntry(
            stable_identity=parameter_set.parameter_set_id,
            **_entry_kwargs(parameter_content),
        )
    )

    for grant in sorted(context.grants, key=lambda item: item.grant_id):
        cbs_entry = _cbs_entry(grant)
        grant_content = GrantDependencyContent(
            grant_id=grant.grant_id,
            client_id=grant.client_id,
            nominal_amount=_decimal(grant.nominal_amount),
            indexed_amount=_decimal(grant.indexed_amount),
            asserted_indexed_amount=_decimal(grant.asserted_indexed_amount),
            system_calculated_amount=_decimal(grant.system_calculated_amount),
            selected_calculation_amount=_decimal(grant.selected_calculation_amount),
            grant_date=grant.grant_date,
            work_start_date=grant.work_start_date,
            work_end_date=grant.work_end_date,
            inclusion_decision=grant.inclusion_decision,
            support_status=grant.support_status,
            accepted_for_use=grant.accepted_for_use,
            source_basis=grant.source_basis,
            status=grant.status,
            actor=grant.actor,
            decision_timestamp=grant.decision_timestamp,
            conflict_indicator=grant.conflict_indicator,
            accepted_value=_decimal(grant.accepted_value),
            indexation_mode=grant.indexation_mode,
            cbs_dependency_identity=grant.grant_id if cbs_entry is not None else None,
        )
        entries.append(
            GrantDependencyEntry(stable_identity=grant.grant_id, **_entry_kwargs(grant_content))
        )
        if cbs_entry is not None:
            entries.append(cbs_entry)

    for capitalization in sorted(
        context.actual_capitalizations,
        key=lambda item: item.capitalization_id,
    ):
        content = CapitalizationDependencyContent(
            capitalization_id=capitalization.capitalization_id,
            amount=_decimal(capitalization.amount),
            capitalization_date=capitalization.capitalization_date,
            recorded_meaning=capitalization.recorded_meaning,
            inclusion_decision=capitalization.inclusion_decision,
            accepted_for_use=capitalization.accepted_for_use,
            support_status=capitalization.support_status,
            source_basis=capitalization.source_basis,
            status=capitalization.status,
            actor=capitalization.actor,
            decision_timestamp=capitalization.decision_timestamp,
            conflict_indicator=capitalization.conflict_indicator,
            accepted_value=_decimal(capitalization.accepted_value),
        )
        entries.append(
            CapitalizationDependencyEntry(
                stable_identity=capitalization.capitalization_id,
                **_entry_kwargs(content),
            )
        )

    future_reserve = context.future_grant_reservation
    if future_reserve is None:
        entries.append(
            FutureReserveDependencyEntry(
                stable_identity=None,
                **_entry_kwargs(None, availability="not_applicable", reasons=["future_reserve_absent"]),
            )
        )
    else:
        future_content = FutureReserveDependencyContent(
            amount=_decimal(future_reserve.amount),
            source_basis=future_reserve.source_basis,
            status=future_reserve.status,
            accepted_for_use=future_reserve.accepted_for_use,
            actor=future_reserve.actor,
            decision_timestamp=future_reserve.decision_timestamp,
        )
        entries.append(
            FutureReserveDependencyEntry(stable_identity=None, **_entry_kwargs(future_content))
        )

    entries.sort(key=_entry_sort_key)
    fingerprint_basis = [
        {
            "dependency_type": entry.dependency_type,
            "stable_identity": entry.stable_identity,
            "availability_state": entry.availability_state,
            "fingerprint": entry.fingerprint,
            "reason_codes": entry.reason_codes,
        }
        for entry in entries
    ]
    return FixationDependencyManifest(
        run_id=run_id,
        run_identity=run_identity,
        client_id=client_id,
        calculation_version=calculation_version,
        input_contract_version=input_contract_version,
        result_contract_version=result_contract_version,
        context_availability="available",
        dependencies=entries,
        manifest_fingerprint=dependency_fingerprint(fingerprint_basis),
    )


def _changed_paths(historical: Any, current: Any, prefix: str = "") -> list[str]:
    historical = canonicalize_dependency_value(historical)
    current = canonicalize_dependency_value(current)
    if isinstance(historical, dict) and isinstance(current, dict):
        paths: list[str] = []
        for key in sorted(set(historical) | set(current)):
            path = f"{prefix}.{key}" if prefix else key
            if key not in historical or key not in current:
                paths.append(path)
            else:
                paths.extend(_changed_paths(historical[key], current[key], path))
        return paths
    return [] if historical == current else [prefix or "$entry"]


def compare_fixation_dependency_manifests(
    historical: FixationDependencyManifest,
    current: FixationDependencyManifest,
    *,
    assessment_timestamp: datetime | None = None,
    current_context_is_trusted: bool = False,
) -> DependencyComparisonResponse:
    timestamp = assessment_timestamp or datetime.now(timezone.utc)
    if historical.manifest_schema_version != current.manifest_schema_version:
        return DependencyComparisonResponse(
            run_id=historical.run_id,
            client_id=historical.client_id,
            assessment_timestamp=timestamp,
            manifest_version=historical.manifest_schema_version,
            technical_result="unknown",
            per_dependency_results=[],
            changed_dependency_types=[],
            changed_fields=[],
            historical_fingerprint=historical.manifest_fingerprint,
            current_fingerprint=current.manifest_fingerprint,
            reason_codes=["comparison_schema_incompatible"],
            unavailable_dependencies=[],
            comparison_algorithm_version=COMPARISON_ALGORITHM_VERSION,
        )
    if not current_context_is_trusted and any(
        entry.dependency_type == "cbs" and entry.availability_state == "available"
        for entry in current.dependencies
    ):
        return unavailable_comparison_response(
            run_id=historical.run_id,
            client_id=historical.client_id,
            reason_code="current_cbs_evidence_unavailable",
            historical_fingerprint=historical.manifest_fingerprint,
            manifest_version=historical.manifest_schema_version,
            assessment_timestamp=timestamp,
        )
    if historical.context_availability == "unavailable" or current.context_availability == "unavailable":
        reasons = sorted(set(historical.context_reason_codes + current.context_reason_codes))
        return DependencyComparisonResponse(
            run_id=historical.run_id,
            client_id=historical.client_id,
            assessment_timestamp=timestamp,
            manifest_version=historical.manifest_schema_version,
            technical_result="unknown",
            per_dependency_results=[],
            changed_dependency_types=[],
            changed_fields=[],
            historical_fingerprint=historical.manifest_fingerprint,
            current_fingerprint=current.manifest_fingerprint,
            reason_codes=reasons or ["dependency_context_unavailable"],
            unavailable_dependencies=[],
        )

    duplicate_keys = sorted(
        _duplicate_dependency_keys(historical.dependencies)
        | _duplicate_dependency_keys(current.dependencies),
        key=lambda key: (key[0], key[1] or ""),
    )
    if duplicate_keys:
        response = unavailable_comparison_response(
            run_id=historical.run_id,
            client_id=historical.client_id,
            reason_code="duplicate_dependency_identity",
            historical_fingerprint=historical.manifest_fingerprint,
            manifest_version=historical.manifest_schema_version,
            assessment_timestamp=timestamp,
        )
        response.current_fingerprint = current.manifest_fingerprint
        response.unavailable_dependencies = [
            f"{dependency_type}:{stable_identity or 'content-based'}"
            for dependency_type, stable_identity in duplicate_keys
        ]
        return response

    historical_entries = {
        (entry.dependency_type, entry.stable_identity): entry for entry in historical.dependencies
    }
    current_entries = {
        (entry.dependency_type, entry.stable_identity): entry for entry in current.dependencies
    }
    per_dependency: list[PerDependencyComparison] = []
    all_changed_fields: list[str] = []
    changed_types: set[str] = set()
    unavailable: list[str] = []
    unavailable_reason_codes: set[str] = set()

    for dependency_type, stable_identity in sorted(
        set(historical_entries) | set(current_entries),
        key=lambda key: (key[0], key[1] or ""),
    ):
        historical_entry = historical_entries.get((dependency_type, stable_identity))
        current_entry = current_entries.get((dependency_type, stable_identity))
        identity_label = f"{dependency_type}:{stable_identity or 'content-based'}"
        reasons: list[str] = []
        changed_fields: list[str] = []
        if historical_entry is None or current_entry is None:
            result = "changed"
            reasons = ["dependency_added" if historical_entry is None else "dependency_removed"]
            changed_fields = ["$entry"]
        elif (
            historical_entry.availability_state == "unavailable"
            or current_entry.availability_state == "unavailable"
        ):
            result = "unknown"
            reasons = sorted(set(historical_entry.reason_codes + current_entry.reason_codes))
            unavailable.append(identity_label)
            unavailable_reason_codes.update(reasons)
        elif historical_entry.fingerprint == current_entry.fingerprint:
            result = "unchanged"
        else:
            result = "changed"
            changed_fields = _changed_paths(
                historical_entry.canonical_content,
                current_entry.canonical_content,
            )

        prefixed_fields = [f"{identity_label}.{field}" for field in changed_fields]
        all_changed_fields.extend(prefixed_fields)
        if result == "changed":
            changed_types.add(dependency_type)
        per_dependency.append(
            PerDependencyComparison(
                dependency_type=dependency_type,
                stable_identity=stable_identity,
                technical_result=result,
                changed_fields=changed_fields,
                historical_fingerprint=historical_entry.fingerprint if historical_entry else None,
                current_fingerprint=current_entry.fingerprint if current_entry else None,
                reason_codes=reasons,
            )
        )

    if changed_types:
        overall = "changed"
        reason_codes = ["dependency_content_changed"]
    elif unavailable:
        overall = "unknown"
        reason_codes = sorted(unavailable_reason_codes) or ["dependency_unavailable"]
    else:
        overall = "unchanged"
        reason_codes = []

    return DependencyComparisonResponse(
        run_id=historical.run_id,
        client_id=historical.client_id,
        assessment_timestamp=timestamp,
        manifest_version=historical.manifest_schema_version,
        technical_result=overall,
        per_dependency_results=per_dependency,
        changed_dependency_types=sorted(changed_types),
        changed_fields=sorted(all_changed_fields),
        historical_fingerprint=historical.manifest_fingerprint,
        current_fingerprint=current.manifest_fingerprint,
        reason_codes=reason_codes,
        unavailable_dependencies=sorted(unavailable),
    )


def _duplicate_dependency_keys(
    entries: list[DependencyEntry],
) -> set[tuple[str, str | None]]:
    seen: set[tuple[str, str | None]] = set()
    duplicates: set[tuple[str, str | None]] = set()
    for entry in entries:
        key = (entry.dependency_type, entry.stable_identity)
        if key in seen:
            duplicates.add(key)
        seen.add(key)
    return duplicates


def get_run_with_dependency_manifest(
    *,
    client_id: int,
    run_id: int,
    db_session: Session,
) -> FixationRun | None:
    return db_session.scalar(
        select(FixationRun)
        .where(FixationRun.id == run_id, FixationRun.client_id == client_id)
        .options(selectinload(FixationRun.fixation_dependency_manifest))
    )


def parse_persisted_manifest(run: FixationRun) -> FixationDependencyManifest | None:
    record = run.fixation_dependency_manifest
    if record is None:
        return None
    try:
        return FixationDependencyManifest(**record.manifest_payload)
    except PydanticValidationError:
        return None


def unavailable_comparison_response(
    *,
    run_id: int,
    client_id: int,
    reason_code: str,
    historical_fingerprint: str | None = None,
    manifest_version: str | None = None,
    assessment_timestamp: datetime | None = None,
) -> DependencyComparisonResponse:
    return DependencyComparisonResponse(
        run_id=run_id,
        client_id=client_id,
        assessment_timestamp=assessment_timestamp or datetime.now(timezone.utc),
        manifest_version=manifest_version,
        technical_result="unknown",
        per_dependency_results=[],
        changed_dependency_types=[],
        changed_fields=[],
        historical_fingerprint=historical_fingerprint,
        current_fingerprint=None,
        reason_codes=[reason_code],
        unavailable_dependencies=[],
        comparison_algorithm_version=COMPARISON_ALGORITHM_VERSION,
    )


def current_context_admission_unavailable_reasons(
    context: AdmissibleFixationInput,
) -> list[str]:
    reasons: set[str] = set()
    if context.upstream_context.state not in {"qualified", "warning_reviewed"}:
        reasons.add("current_m07_context_not_admitted")
    parameter_set = context.parameter_set
    if not parameter_set.accepted_for_use:
        reasons.add("current_parameter_context_not_admitted")
    if parameter_set.tax_year != context.eligibility_year:
        reasons.add("current_parameter_context_not_admitted")
    if parameter_set.effective_from and context.eligibility_date < parameter_set.effective_from:
        reasons.add("current_parameter_context_not_admitted")
    if parameter_set.effective_to and context.eligibility_date > parameter_set.effective_to:
        reasons.add("current_parameter_context_not_admitted")
    if context.grants_collection_state in {"unknown", "not_collected"}:
        reasons.add("current_grant_context_not_admitted")
    if context.actual_capitalizations_collection_state in {"unknown", "not_collected"}:
        reasons.add("current_capitalization_context_not_admitted")
    if any(
        grant.inclusion_decision == "include"
        and (not grant.accepted_for_use or grant.support_status != "supported")
        for grant in context.grants
    ):
        reasons.add("current_grant_context_not_admitted")
    if any(
        item.inclusion_decision == "include"
        and (not item.accepted_for_use or item.support_status != "supported")
        for item in context.actual_capitalizations
    ):
        reasons.add("current_capitalization_context_not_admitted")
    if (
        context.future_grant_reservation is not None
        and not context.future_grant_reservation.accepted_for_use
    ):
        reasons.add("current_future_reserve_context_not_admitted")
    if context.idf is not None:
        reasons.add("current_special_handling_context_not_admitted")
    return sorted(reasons)
