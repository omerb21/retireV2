"""V1 reference provenance and all coefficient lookup branches."""
from datetime import date
from decimal import Decimal
import json
from types import SimpleNamespace
import pytest
from app.services import annuity_coefficient_service as coefficients


def test_snapshot_reference_only_identity_counts_and_hashes():
    snapshot = json.loads(coefficients.SNAPSHOT.read_text(encoding="utf-8"))
    assert snapshot["commit"] == "e4bd8618cb194aff5f7b9aa0b5388f71cf838292"
    assert snapshot["repository"] == "omerb21/retire"
    expected = {
        "product_to_generation_map": (8, "4490306ea1a58c77267fd5127df3927e86a3ef591180f672cd1dc660e228687b"),
        "policy_generation_coefficient": (147, "b55d9f304002e4d10bfa2fa7a1514dac0c77a5ca04f84d2e3012d4e3a47b16ae"),
        "company_annuity_coefficient": (6, "b9dab64e4840ea9f0c7bdc15d9db282d03a7e36b1c7c016432837a7bc75f7f21"),
        "pension_fund_coefficient": (75440, "c931231927a6aa49a655a4f9417bec4a6ebba55985057a7adb25e43004cb6319"),
    }
    assert set(snapshot["tables"]) == set(expected)
    for name, (count, sha) in expected.items():
        assert len(snapshot["tables"][name]) == snapshot["sources"][name]["rows"] == count
        assert snapshot["sources"][name]["sha256"] == sha
    assert coefficients.catalog() == snapshot["tables"]


@pytest.mark.parametrize("sex", ["male", "female"])
def test_generation_and_company_lookup_parity(sex):
    profile = SimpleNamespace(gender=sex, birth_date=None)
    product = SimpleNamespace(product_type="ביטוח מנהלים", start_date=date(1989, 1, 1))
    result = coefficients.coefficient(product, profile, date(2030, 1, 1), retirement_age=60)
    assert result["source"] == "policy_generation_coefficient"
    assert Decimal(result["annuity_factor"]) == Decimal("169.20" if sex == "male" else "189.20")
    company = next(r for r in coefficients.catalog()["company_annuity_coefficient"] if r["sex"] == ("זכר" if sex == "male" else "נקבה"))
    result = coefficients.coefficient(product, profile, date(2030, 1, 1), retirement_age=int(company["age"]),
        company_name=company["company_name"], option_name=company["option_name"], target_year=2030)
    expected = round(float(company["base_coefficient"]) * (1 + float(company["annual_increment_rate"]) * (2030 - int(company["base_year"]))), 2)
    assert result["source"] == "company_annuity_coefficient"
    assert Decimal(result["annuity_factor"]) == Decimal(str(expected))
    assert not result["fallback_used"]


@pytest.mark.parametrize("kind", ["קרן פנסיה", "קופת גמל", "קרן השתלמות"])
def test_pension_latest_row_lookup_and_actual_age(kind):
    row = max(coefficients.catalog()["pension_fund_coefficient"], key=lambda r: int(r["id"]))
    profile = SimpleNamespace(gender="female", birth_date=date(1950, 1, 1))
    result = coefficients.coefficient(SimpleNamespace(product_type=kind, start_date=None), profile, date(2030, 1, 1),
        retirement_age=60, spouse_age_diff=int(row["spouse_age_diff"]), survivors_option=row["survivors_option"])
    assert result["source"] == "pension_fund_coefficient"
    assert result["lookup_keys"]["age"] == 80
    expected = round(float(row["base_coefficient"]) * float(row["adjust_percent"]), 2)
    assert Decimal(result["annuity_factor"]) == Decimal(str(expected))


def test_default_200_missing_and_lookup_error(monkeypatch):
    product = SimpleNamespace(product_type="insurance", start_date=None)
    result = coefficients.coefficient(product, None, date(2030, 1, 1), retirement_age=130)
    assert result["annuity_factor"] == "200.00"
    assert result["warnings"] == ["ANNUITY_COEFFICIENT_DEFAULT_200"]
    assert result["fallback_used"]
    def broken():
        raise OSError("missing catalog")
    monkeypatch.setattr(coefficients, "catalog", broken)
    result = coefficients.coefficient(product, None, date(2030, 1, 1))
    assert result["annuity_factor"] == "200.00" and result["source"] == "error"
    assert result["warnings"] == ["ANNUITY_COEFFICIENT_DEFAULT_200"]


def test_decimal_coefficient_rounding_matches_v1_reference_arithmetic_over_complete_catalog():
    # Floats appear only in this V1 parity oracle; money never uses floats.
    tables = coefficients.catalog()
    for row in tables["pension_fund_coefficient"]:
        decimal = Decimal(row["base_coefficient"]) * (Decimal(row["adjust_percent"]) or 1)
        v1 = float(row["base_coefficient"]) * (float(row["adjust_percent"]) or 1)
        assert decimal.quantize(Decimal(".01")) == Decimal(str(round(v1, 2)))
    for row in tables["company_annuity_coefficient"]:
        for year in range(1900, 2301):
            delta = year - int(row["base_year"])
            decimal = Decimal(row["base_coefficient"]) * (1 + Decimal(row["annual_increment_rate"]) * delta)
            v1 = float(row["base_coefficient"]) * (1 + float(row["annual_increment_rate"]) * delta)
            assert decimal.quantize(Decimal(".01")) == Decimal(str(round(v1, 2)))


@pytest.mark.parametrize("start,expected,generation", [(None, "209.35", "Y2013_PLUS"), (date(1989, 1, 1), "134.20", "PRE_1990")])
def test_insurance_generation_date_precedence(start, expected, generation):
    # V1 e4bd8618, usePensionConversion: parsed product date || paymentDateISO.
    product = SimpleNamespace(product_type="ביטוח מנהלים", start_date=start)
    result = coefficients.coefficient(product, None, date(2030, 7, 15), retirement_age=67)
    assert result["annuity_factor"] == expected
    assert result["source"] == "policy_generation_coefficient"
    assert result["lookup_keys"]["generation_code"] == generation
    assert result["lookup_keys"]["generation_date"] == (start or date(2030, 7, 15)).isoformat()
    assert result["lookup_keys"]["generation_date_source"] == ("product_start_date" if start else "pension_start_date")
    assert result["warnings"] == [] and not result["fallback_used"]


def test_insurance_substitution_exhausted_no_generation_match():
    product = SimpleNamespace(product_type="ביטוח מנהלים", start_date=None)
    result = coefficients.coefficient(product, None, date(2300, 1, 1))
    assert result["annuity_factor"] == "200.00"
    assert result["warnings"] == ["ANNUITY_COEFFICIENT_DEFAULT_200"]
