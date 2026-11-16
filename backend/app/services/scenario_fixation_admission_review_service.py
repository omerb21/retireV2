"""Real fixation admission review without tax calculation or persistence."""
from __future__ import annotations

from typing import Any

from app.services import fixation_admission_service as admission
from app.services import scenario_fixation_admission_eligibility_service as eligibility
from app.services import scenario_fixation_admission_preparation_service as preparation
from app.services.scenario_input_manifest_service import _fingerprint


CONTRACT = "SCENARIO_FIXATION_ADMISSION_REVIEW_V1"


class _ExternalValidationAttempt(RuntimeError):
    pass


def _external_validation_forbidden(**_kwargs):
    raise _ExternalValidationAttempt


def _reason(
    code: str,
    *,
    path: str | None = None,
    message: str | None = None,
    source_id: str | None = None,
    source_ids: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "path": path,
        "message": message,
        "source_ids": sorted(set(source_ids or ([source_id] if source_id else []))),
    }


def _result(
    *,
    client_id: int,
    scenario_id: str,
    state: str,
    preparation_fingerprint: str,
    eligibility_fingerprint: str,
    reasons: list[dict[str, Any]],
) -> dict[str, Any]:
    ordered = sorted(
        reasons,
        key=lambda item: (
            item["code"], item["path"] or "", item["source_ids"], item["message"] or "",
        ),
    )
    preimage = {
        "contract": CONTRACT,
        "client_id": client_id,
        "scenario_id": scenario_id,
        "state": state,
        "preparation_fingerprint": preparation_fingerprint,
        "eligibility_fingerprint": eligibility_fingerprint,
        "reasons": ordered,
    }
    return {
        **preimage,
        "admission_review_fingerprint": _fingerprint(preimage),
        "admission_contract_validated": state == "ADMITTED_FOR_REVIEW",
        "professional_authority": False,
        "execution_allowed": False,
        "tax_calculation_performed": False,
        "tax_authority_approval": None,
    }


def _run_existing_admission(db, client_id: int, candidate: dict[str, Any]):
    """Invoke the canonical admission boundary with external work fail-closed."""
    try:
        context, admitted, errors, _resolution = admission.parse_and_admit_fixation_payload(
            candidate,
            client_id=client_id,
            db_session=db,
            cbs_calculator=_external_validation_forbidden,
            use_persisted_grants=False,
        )
    except _ExternalValidationAttempt:
        return None, [
            _reason(
                "FIXATION_ADMISSION_EXTERNAL_VALIDATION_FORBIDDEN",
                message="admission attempted external grant indexation",
            )
        ]
    mapped = [
        _reason(
            error.code,
            path=error.path,
            message=error.message,
            source_id=error.source_id,
        )
        for error in errors
    ]
    if context is None and not mapped:
        mapped.append(_reason("FIXATION_ADMISSION_CONTEXT_MISSING"))
    if admitted is None and not mapped:
        mapped.append(_reason("FIXATION_ADMISSION_REJECTED_WITHOUT_REASON"))
    return admitted, mapped


def review(
    db,
    client_id: int,
    scenario_id: str,
    *,
    expected_preparation_fingerprint: str,
    expected_eligibility_fingerprint: str,
) -> dict[str, Any]:
    """Revalidate current evidence and run admission only for the basic path."""
    current_eligibility = eligibility.assess(db, client_id, scenario_id)
    current_preparation = preparation.prepare(db, client_id, scenario_id)
    preparation_fingerprint = current_preparation["preparation_fingerprint"]
    eligibility_fingerprint = current_eligibility["eligibility_fingerprint"]

    if (
        expected_preparation_fingerprint != preparation_fingerprint
        or expected_eligibility_fingerprint != eligibility_fingerprint
        or current_eligibility["preparation_fingerprint"] != preparation_fingerprint
    ):
        return _result(
            client_id=client_id,
            scenario_id=scenario_id,
            state="REJECTED",
            preparation_fingerprint=preparation_fingerprint,
            eligibility_fingerprint=eligibility_fingerprint,
            reasons=[_reason("FIXATION_ADMISSION_REVIEW_STALE")],
        )

    if current_eligibility["state"] != "ELIGIBLE_FOR_ADMISSION_REVIEW":
        reasons = [
            _reason(
                item["code"],
                source_ids=item["source_ids"],
            )
            for item in current_eligibility["reasons"]
        ]
        return _result(
            client_id=client_id,
            scenario_id=scenario_id,
            state="REJECTED",
            preparation_fingerprint=preparation_fingerprint,
            eligibility_fingerprint=eligibility_fingerprint,
            reasons=reasons or [_reason("FIXATION_ADMISSION_REVIEW_NOT_ELIGIBLE")],
        )

    candidate = current_preparation.get("candidate")
    if not isinstance(candidate, dict):
        return _result(
            client_id=client_id,
            scenario_id=scenario_id,
            state="REJECTED",
            preparation_fingerprint=preparation_fingerprint,
            eligibility_fingerprint=eligibility_fingerprint,
            reasons=[_reason("FIXATION_ADMISSION_PREPARED_CANDIDATE_MISSING")],
        )

    admitted, reasons = _run_existing_admission(db, client_id, candidate)
    return _result(
        client_id=client_id,
        scenario_id=scenario_id,
        state="ADMITTED_FOR_REVIEW" if admitted is not None and not reasons else "REJECTED",
        preparation_fingerprint=preparation_fingerprint,
        eligibility_fingerprint=eligibility_fingerprint,
        reasons=reasons,
    )
