"""SC-05A candidate-factor boundary tests; never execute a conversion."""
from datetime import date
import pytest
from app.services import scenario_annuity_coefficient_assessment_service as subject


def facts():
    return (
        dict(client_id=7, scenario_id="s", scenario_version=1,
             manifest_fingerprint="a"*64, decision_id="d", product_id="p",
             component_id="c", product_version=1, action="pension",
             source_verified=True),
        dict(product_id="p", version=1, product_type="קרן פנסיה", start_date=None),
        dict(gender="female", birth_date=date(1965, 4, 2)),
        dict(pension_start_date=date(2032, 5, 1), effective_date=date(2031, 5, 1),
             target_year=2032, survivors_option="תקנוני", spouse_age_diff=0,
             professional_permission_verified=True),
    )


def test_explicit_catalog_match_is_not_admission(monkeypatch):
    calls = []
    def lookup(*args, **kwargs):
        calls.append(kwargs)
        return dict(annuity_factor="201.25", source="pension_fund_coefficient",
                    catalog_version=subject.CATALOG_VERSION, fallback_used=False,
                    warnings=[], lookup_keys={"age": 67})
    monkeypatch.setattr(subject, "coefficient", lookup)
    identity, product, profile, options = facts()
    result = subject.assess_coefficient_candidate(identity=identity, product=product,
                                                  profile=profile, pension_options=options)
    assert result["state"] == "COEFFICIENT_CANDIDATE_NOT_ADMITTED"
    assert result["coefficient_candidate"]["annuity_factor"] == "201.25"
    assert result["execution_allowed"] is False
    assert result["financial_result"] is None and result["planning_snapshot"] is None
    assert result["authority_state"] == "NOT_EVALUATED"
    assert len(calls) == 1


@pytest.mark.parametrize("change,target", [
    ({"gender": None}, "profile"), ({"birth_date": None}, "profile"),
    ({"pension_start_date": None}, "options"),
    ({"effective_date": None}, "options"),
    ({"target_year": None}, "options"),
    ({"survivors_option": None}, "options"),
    ({"spouse_age_diff": None}, "options"),
    ({"professional_permission_verified": False}, "options"),
    ({"source_verified": False}, "identity"),
])
def test_missing_authority_never_calls_coefficient(monkeypatch, change, target):
    monkeypatch.setattr(subject, "coefficient", lambda *a, **kw: pytest.fail("unsafe coefficient invocation"))
    identity, product, profile, options = facts()
    {"identity": identity, "product": product, "profile": profile, "options": options}[target].update(change)
    result = subject.assess_coefficient_candidate(identity=identity, product=product,
                                                  profile=profile, pension_options=options)
    assert result["state"] == "BLOCKED"
    assert result["coefficient_candidate"] is None


@pytest.mark.parametrize("source,fallback,warnings", [
    ("default", True, ["ANNUITY_COEFFICIENT_DEFAULT_200"]),
    ("error", True, ["ANNUITY_COEFFICIENT_DEFAULT_200"]),
    ("pension_fund_coefficient", False, ["unexpected-warning"]),
])
def test_fallback_or_warning_never_admitted(monkeypatch, source, fallback, warnings):
    monkeypatch.setattr(subject, "coefficient", lambda *a, **kw: dict(
        annuity_factor="200.00", source=source,
        catalog_version=subject.CATALOG_VERSION, fallback_used=fallback,
        warnings=warnings, lookup_keys={}))
    identity, product, profile, options = facts()
    result = subject.assess_coefficient_candidate(identity=identity, product=product,
                                                  profile=profile, pension_options=options)
    assert result["state"] == "UNRESOLVED"
    assert result["coefficient_candidate"] is None
    assert result["execution_allowed"] is False


def test_insurance_needs_generation_date(monkeypatch):
    monkeypatch.setattr(subject, "coefficient", lambda *a, **kw: pytest.fail("unsafe lookup"))
    identity, product, profile, options = facts()
    product["product_type"] = "ביטוח מנהלים"
    result = subject.assess_coefficient_candidate(identity=identity, product=product,
                                                  profile=profile, pension_options=options)
    assert result["state"] == "BLOCKED"
    assert result["blockers"] == ["INSURANCE_GENERATION_DATE_REQUIRED"]


def test_stale_product_identity_is_blocked():
    identity, product, profile, options = facts()
    product["version"] = 2
    result = subject.assess_coefficient_candidate(identity=identity, product=product,
                                                  profile=profile, pension_options=options)
    assert result["blockers"] == ["PRODUCT_IDENTITY_STALE"]
