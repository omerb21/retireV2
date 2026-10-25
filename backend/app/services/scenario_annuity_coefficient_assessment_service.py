"""SC-05A: fail-closed, non-executing annuity coefficient assessment.

A factor is only a candidate, never scenario planning or tax authority.
Callers must supply a database-verified decision/product/profile provenance.
"""
from __future__ import annotations

import re
from datetime import date
from types import SimpleNamespace

from app.services.annuity_coefficient_service import coefficient, CATALOG_VERSION

SHA = re.compile(r"^[0-9a-f]{64}$")


def assess_coefficient_candidate(*, identity: dict, product: dict,
                                 profile: dict, pension_options: dict) -> dict:
    base = {
        "schema_version": "SCENARIO_ANNUITY_COEFFICIENT_CANDIDATE_V1",
        "state": "BLOCKED", "blockers": [],
        "coefficient_candidate": None,
        "catalog_version": CATALOG_VERSION,
        "execution_allowed": False, "financial_result": None,
        "planning_snapshot": None, "authority_state": "NOT_EVALUATED",
    }

    def reject(code):
        return {**base, "blockers": [code]}

    if not all(type(arg) is dict for arg in (identity, product, profile, pension_options)):
        return reject("INVALID_ASSESSMENT_INPUT")
    if (type(identity.get("client_id")) is not int or identity["client_id"] <= 0
            or not isinstance(identity.get("scenario_id"), str) or not identity["scenario_id"]
            or type(identity.get("scenario_version")) is not int or identity["scenario_version"] <= 0
            or not isinstance(identity.get("manifest_fingerprint"), str)
            or not SHA.fullmatch(identity["manifest_fingerprint"])
            or not all(isinstance(identity.get(k), str) and identity[k]
                       for k in ("decision_id", "product_id", "component_id"))
            or type(identity.get("product_version")) is not int or identity["product_version"] <= 0
            or identity.get("action") != "pension"
            or identity.get("source_verified") is not True):
        return reject("UNVERIFIED_SCENARIO_IDENTITY")
    if product.get("product_id") != identity["product_id"] or product.get("version") != identity["product_version"]:
        return reject("PRODUCT_IDENTITY_STALE")
    kind = product.get("product_type")
    if not isinstance(kind, str) or not kind:
        return reject("PRODUCT_TYPE_MISSING")
    gender = profile.get("gender")
    birth = profile.get("birth_date")
    if gender not in ("male", "female", "זכר", "נקבה") or type(birth) is not date:
        return reject("EXPLICIT_PROFILE_FACTS_REQUIRED")
    start = pension_options.get("pension_start_date")
    effective = pension_options.get("effective_date")
    if type(start) is not date or type(effective) is not date or start < effective:
        return reject("EXPLICIT_PENSION_DATES_REQUIRED")
    if (type(pension_options.get("target_year")) is not int
            or pension_options["target_year"] < 1900 or pension_options["target_year"] > 2300
            or type(pension_options.get("survivors_option")) is not str
            or not pension_options["survivors_option"]
            or type(pension_options.get("spouse_age_diff")) is not int
            or not -100 <= pension_options["spouse_age_diff"] <= 100):
        return reject("EXPLICIT_PENSION_OPTIONS_REQUIRED")
    if ("retirement_age" in pension_options and pension_options["retirement_age"] is not None):
        return reject("RETIREMENT_AGE_MUST_DERIVE_FROM_BIRTH_DATE")
    if ("ביטוח מנהלים" in kind or "insurance" in kind.lower()) and type(product.get("start_date")) is not date:
        return reject("INSURANCE_GENERATION_DATE_REQUIRED")
    if pension_options.get("professional_permission_verified") is not True:
        return reject("PROFESSIONAL_PERMISSION_NOT_VERIFIED")
    try:
        found = coefficient(
            SimpleNamespace(product_type=kind, start_date=product.get("start_date")),
            SimpleNamespace(gender=gender, birth_date=birth),
            pension_start_date=start, target_year=pension_options["target_year"],
            survivors_option=pension_options["survivors_option"],
            spouse_age_diff=pension_options["spouse_age_diff"],
            company_name=pension_options.get("company_name"),
            option_name=pension_options.get("option_name"),
        )
    except Exception:
        return reject("COEFFICIENT_CATALOG_UNAVAILABLE")
    if (found.get("fallback_used") is not False
            or found.get("source") in ("default", "error", None)
            or found.get("catalog_version") != CATALOG_VERSION
            or not isinstance(found.get("annuity_factor"), str)
            or found.get("warnings")):
        return {**base, "state": "UNRESOLVED", "blockers": ["COEFFICIENT_CATALOG_MATCH_MISSING"]}
    safe = {key: identity[key] for key in (
        "client_id", "scenario_id", "scenario_version", "manifest_fingerprint",
        "decision_id", "product_id", "component_id", "product_version")}
    return {**base, **safe, "state": "COEFFICIENT_CANDIDATE_NOT_ADMITTED",
            "coefficient_candidate": {
                "annuity_factor": found["annuity_factor"],
                "source": found["source"], "catalog_version": CATALOG_VERSION,
                "lookup_keys": found["lookup_keys"],
            }}
