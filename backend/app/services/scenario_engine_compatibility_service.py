"""SC-03B exact, non-executing compatibility map for accepted engines.

Structural callable compatibility is reported separately from professional
admission, permission and tax. This module never invokes a financial engine.
"""
from __future__ import annotations

from collections.abc import Mapping
from inspect import Parameter, signature

from sqlalchemy.orm import Session

from app.services import capital_projection_execution_service as capital
from app.services import pension_target_date_execution_service as pension
from app.services import retirement_monthly_income_gap_service as gap
from app.services.scenario_input_manifest_service import (
    ManifestValidationError, validate_inert_manifest,
)


ENGINE_CONTRACTS = {
    "pension_target_date": {
        "callable": pension.execute_from_planning_result,
        "callable_path": (
            "app.services.pension_target_date_execution_service."
            "execute_from_planning_result"
        ),
        "parameters": (
            "planning_result", "source_id",
            "supplied_planning_calculation_input_fingerprint",
            "supplied_monthly_basis_semantic_fingerprint",
            "supplied_monthly_basis_source_fingerprint",
            "supplied_temporal_semantic_fingerprint",
            "supplied_temporal_source_fingerprint",
        ),
        "parameter_kinds": (
            "POSITIONAL_OR_KEYWORD", "POSITIONAL_OR_KEYWORD",
            "KEYWORD_ONLY", "KEYWORD_ONLY", "KEYWORD_ONLY", "KEYWORD_ONLY",
            "KEYWORD_ONLY",
        ),
        "scenario_adapter_requirements": (
            "verified_scenario_planning_result", "verified_pension_source_identity",
            "verified_monthly_basis_authority", "verified_temporal_authority",
        ),
    },
    "capital_projection": {
        "callable": capital.execute,
        "callable_path": "app.services.capital_projection_execution_service.execute",
        "parameters": ("client_id", "plan", "authority"),
        "parameter_kinds": (
            "POSITIONAL_OR_KEYWORD", "POSITIONAL_OR_KEYWORD",
            "POSITIONAL_OR_KEYWORD",
        ),
        "scenario_adapter_requirements": (
            "verified_scenario_plan", "verified_capital_projection_basis_authority",
            "complete_capital_source_coverage",
        ),
    },
    "monthly_income_gap": {
        "callable": gap.assess,
        "callable_path": "app.services.retirement_monthly_income_gap_service.assess",
        "parameters": ("db", "request"),
        "parameter_kinds": ("POSITIONAL_OR_KEYWORD", "POSITIONAL_OR_KEYWORD"),
        "scenario_adapter_requirements": (
            "fresh_rmiga_session", "verified_scenario_planning_fingerprint",
            "verified_retirement_target_date",
        ),
    },
}


def _actual_parameter_contract(engine: str) -> tuple[tuple[str, str, bool], ...]:
    parameters = signature(ENGINE_CONTRACTS[engine]["callable"]).parameters.values()
    return tuple(
        (item.name, item.kind.name, item.default is Parameter.empty)
        for item in parameters
    )


def _signature_current(engine: str) -> bool:
    contract = ENGINE_CONTRACTS[engine]
    expected = tuple(zip(
        contract["parameters"], contract["parameter_kinds"],
        (True for _item in contract["parameters"]),
    ))
    return _actual_parameter_contract(engine) == expected


def _sha(value: object) -> bool:
    return capital.is_fingerprint(value)


def _sha_or_none(value: object) -> bool:
    return value is None or _sha(value)


def _optional_pension_authority(
    value: object, kind_field: str, blocker_field: str,
) -> bool:
    if value is None:
        return True
    if not isinstance(value, Mapping):
        return False
    kind = value.get(kind_field)
    blockers = value.get(blocker_field)
    return (
        (kind is None or isinstance(kind, str))
        and (
            blockers is None
            or type(blockers) is list
            and all(isinstance(blocker, str) for blocker in blockers)
        )
    )


def _pension_shape(payload: Mapping) -> bool:
    if set(payload) != set(ENGINE_CONTRACTS["pension_target_date"]["parameters"]):
        return False
    planning = payload.get("planning_result")
    source_id = payload.get("source_id")
    if not isinstance(planning, Mapping) or not isinstance(source_id, str):
        return False
    sources = planning.get("pension_inputs", [])
    if type(sources) is not list or not all(isinstance(item, Mapping) for item in sources):
        return False
    matches = [item for item in sources if item.get("source_id") == source_id]
    source = matches[0] if len(matches) == 1 else None
    monthly = source.get("monthly_amount_basis") if source is not None else None
    temporal = source.get("temporal_authority") if source is not None else None
    target = planning.get("retirement_target")
    return (
        (target is None or isinstance(target, Mapping))
        and _sha_or_none(planning.get("planning_calculation_input_fingerprint"))
        and _optional_pension_authority(
            monthly, "authority_kind", "basis_blockers",
        )
        and _optional_pension_authority(
            temporal, "temporal_authority_kind", "temporal_blockers",
        )
        and all(_sha_or_none(payload.get(field)) for field in (
            "supplied_planning_calculation_input_fingerprint",
            "supplied_monthly_basis_semantic_fingerprint",
            "supplied_monthly_basis_source_fingerprint",
            "supplied_temporal_semantic_fingerprint",
            "supplied_temporal_source_fingerprint",
        ))
    )


def _capital_shape(payload: Mapping) -> bool:
    if set(payload) != set(ENGINE_CONTRACTS["capital_projection"]["parameters"]):
        return False
    plan, authority = payload.get("plan"), payload.get("authority")
    target = plan.get("retirement_target") if isinstance(plan, Mapping) else None
    sources = authority.get("covered_capital_sources") if isinstance(authority, Mapping) else None
    capitals = plan.get("capital_inputs") if isinstance(plan, Mapping) else None
    common = (
        type(payload.get("client_id")) is int and payload["client_id"] > 0
        and isinstance(plan, Mapping) and isinstance(authority, Mapping)
        and type(capitals) is list and isinstance(target, Mapping)
        and type(plan.get("planning_input_ready")) is bool
        and type(target.get("retirement_target_ready")) is bool
        and isinstance(target.get("retirement_target_date"), str)
        and isinstance(plan.get("planning_base_date"), str)
        and _sha(plan.get("planning_calculation_input_fingerprint"))
        and authority.get("contract_version") == capital.basis.CONTRACT
        and type(sources) is list
        and type(authority.get("covered_source_count")) is int
        and authority.get("covered_source_count") == len(sources)
        and type(authority.get("projection_basis_ready")) is bool
        and type(authority.get("aggregate_blockers")) is list
        and _sha(authority.get("projection_basis_admission_fingerprint"))
        and _sha(authority.get("planning_calculation_input_fingerprint"))
        and authority.get("client_id") == payload["client_id"]
        and authority.get("planning_calculation_input_fingerprint")
        == plan.get("planning_calculation_input_fingerprint")
        and authority.get("retirement_target_date") == target.get("retirement_target_date")
        and authority.get("planning_base_date") == plan.get("planning_base_date")
    )
    if not common or len(capitals) != len(sources):
        return False
    capital_fields = {
        "id", "client_id", "source_id", "lifecycle_status",
        "known_value_amount", "value_as_of_date",
    }
    source_fields = {
        "source_id", "capital_asset_id", "projection_basis_source_readiness",
        "known_value_amount", "source_semantic_fingerprint",
        "economic_projection_start_date", "value_as_of_date",
        "retirement_target_date", "projection_timing_context_fingerprint",
        "compounding_convention", "day_count_convention", "blockers",
        "projection_basis_decision", "projection_basis_decision_fingerprint",
        "projection_basis_source_admission_fingerprint",
    }
    return all(
        isinstance(capital_item, Mapping) and capital_fields <= set(capital_item)
        and isinstance(source, Mapping) and source_fields <= set(source)
        and type(source.get("projection_basis_source_readiness")) is bool
        and type(source.get("blockers")) is list
        for capital_item, source in zip(capitals, sources)
    )


def _gap_shape(payload: Mapping) -> bool:
    if set(payload) != set(ENGINE_CONTRACTS["monthly_income_gap"]["parameters"]):
        return False
    db = payload.get("db")
    if not isinstance(db, Session):
        return False
    try:
        if db.in_transaction() or db.new or db.dirty or db.deleted:
            return False
        if db.get_bind().dialect.name not in {"postgresql", "sqlite"}:
            return False
    except BaseException:
        return False
    try:
        gap._validated_request(payload.get("request"))
    except gap.RMIGAContractError:
        return False
    return True


_SHAPE_VALIDATORS = {
    "pension_target_date": _pension_shape,
    "capital_projection": _capital_shape,
    "monthly_income_gap": _gap_shape,
}


def assess_engine_input_shape(engine: str, payload: object) -> dict:
    """Validate actual callable shape without calling an engine or admitting it."""
    if engine not in ENGINE_CONTRACTS or type(payload) is not dict:
        return {
            "structural_state": "INCOMPATIBLE",
            "execution_allowed": False,
            "admission_state": "NOT_EVALUATED",
            "blockers": ["ENGINE_INPUT_SHAPE_INVALID"],
        }
    contract = ENGINE_CONTRACTS[engine]
    signature_current = _signature_current(engine)
    structurally_valid = signature_current and _SHAPE_VALIDATORS[engine](payload)
    return {
        "engine": engine,
        "callable_path": contract["callable_path"],
        "callable_parameters": list(contract["parameters"]),
        "structural_state": (
            "STRUCTURALLY_COMPATIBLE_NOT_ADMITTED" if structurally_valid
            else "INCOMPATIBLE"
        ),
        "execution_allowed": False,
        "admission_state": "NOT_EVALUATED",
        "permission_state": "NOT_ADMITTED",
        "professional_eligibility_state": "NOT_EVALUATED",
        "tax_state": "NOT_EVALUATED",
        "blockers": ([] if structurally_valid else ["ENGINE_INPUT_SHAPE_INVALID"]),
    }


def assess_engine_compatibility(manifest: object) -> dict:
    """Map the inert manifest to exact engine adapter gaps; never call engines."""
    try:
        manifest = validate_inert_manifest(manifest)
    except ManifestValidationError:
        return {
            "schema_version": "SCENARIO_ENGINE_COMPATIBILITY_V1",
            "compatibility_state": "BLOCKED",
            "execution_allowed": False,
            "engines": {},
            "blockers": ["SCENARIO_MANIFEST_INVALID"],
        }
    common = []
    if manifest["scenario_status"] != "draft":
        common.append("SCENARIO_STATUS_NOT_DRAFT")
    if not manifest["decisions"]:
        common.append("SCENARIO_DECISIONS_EMPTY_OR_INVALID")
    elif any(item["source"] is None for item in manifest["decisions"]):
        common.append("SCENARIO_SOURCE_EVIDENCE_INCOMPLETE")
    engines = {}
    for engine, contract in ENGINE_CONTRACTS.items():
        blockers = [
            *common,
            *("MISSING_" + item.upper() for item in contract["scenario_adapter_requirements"]),
            "PERMISSION_NOT_ADMITTED",
            "PROFESSIONAL_ELIGIBILITY_NOT_EVALUATED",
            "TAX_NOT_EVALUATED",
        ]
        engines[engine] = {
            "callable_path": contract["callable_path"],
            "callable_parameters": list(contract["parameters"]),
            "structural_state": "SCENARIO_ADAPTER_MISSING",
            "admission_state": "NOT_EVALUATED",
            "execution_allowed": False,
            "result": None,
            "missing_verified_adapter_fields": list(contract["scenario_adapter_requirements"]),
            "blockers": blockers,
        }
    return {
        "schema_version": "SCENARIO_ENGINE_COMPATIBILITY_V1",
        "compatibility_state": "BLOCKED",
        "execution_allowed": False,
        "scenario_id": manifest["scenario_id"],
        "scenario_version": manifest["scenario_version"],
        "manifest_fingerprint": manifest["manifest_fingerprint"],
        "engines": engines,
        "blockers": [*common, "NO_SCENARIO_ENGINE_ADMISSION_CONTRACT"],
    }
