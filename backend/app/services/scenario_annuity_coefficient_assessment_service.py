"""SC-05A: coefficient assessment intentionally closed until DB-owned admission.

No caller-supplied dict, flag or fingerprint can authorize catalog lookup.
SC-05 grants neither financial calculation nor planning execution.
"""
from app.services.annuity_coefficient_service import CATALOG_VERSION


def assess_coefficient_candidate(*, identity: dict, product: dict,
                                 profile: dict, pension_options: dict) -> dict:
    return {
        "schema_version": "SCENARIO_ANNUITY_COEFFICIENT_CANDIDATE_V1",
        "state": "BLOCKED",
        "blockers": ["COEFFICIENT_LOOKUP_NOT_AUTHORIZED"],
        "coefficient_candidate": None, "catalog_version": CATALOG_VERSION,
        "execution_allowed": False, "financial_result": None,
        "planning_snapshot": None, "authority_state": "NOT_EVALUATED",
    }
