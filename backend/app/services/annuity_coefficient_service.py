"""Controlled V1 coefficient lookup, independent of legacy conversion authority."""
from datetime import date
from decimal import Decimal, ROUND_HALF_EVEN
from functools import lru_cache
import hashlib
import json
from pathlib import Path

CATALOG_VERSION = "v1-annuity-e4bd8618cb194aff5f7b9aa0b5388f71cf838292"
SNAPSHOT = Path(__file__).resolve().parents[1] / "data/annuity_coefficients/snapshot.json"


@lru_cache(maxsize=1)
def catalog():
    raw = SNAPSHOT.read_bytes()
    result = json.loads(raw)
    canonical = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(canonical).hexdigest() != "f92d073f3bc956a8cc756cd587fbe218bf4c607e6c972f44b74143d121f70060":
        raise ValueError("coefficient catalog content mismatch")
    if result["version"] != CATALOG_VERSION:
        raise ValueError("coefficient catalog version mismatch")
    return result["tables"]


def coefficient(product, profile, pension_start_date: date, *, retirement_age=None,
                company_name=None, option_name=None, survivors_option="תקנוני",
                spouse_age_diff=0, target_year=None):
    gender = (getattr(profile, "gender", None) or "").lower()
    sex = "נקבה" if gender in ("f", "female", "נקבה", "נ") else "זכר"
    birth = getattr(profile, "birth_date", None)
    age = retirement_age if retirement_age is not None else 67
    if birth:
        age = pension_start_date.year - birth.year - ((pension_start_date.month, pension_start_date.day) < (birth.month, birth.day))
    year = target_year if target_year is not None else date.today().year
    keys = {"product_type": product.product_type, "start_date": product.start_date.isoformat() if product.start_date else None,
            "sex": sex, "age": age, "company_name": company_name, "option_name": option_name,
            "survivors_option": survivors_option or "תקנוני", "spouse_age_diff": spouse_age_diff, "target_year": year}
    def result(value, source, notes="", fallback=False):
        factor = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
        if not factor.is_finite() or factor <= 0:
            raise ValueError("nonpositive coefficient")
        return {"annuity_factor": str(factor), "source": source, "lookup_keys": keys,
                "notes": notes, "catalog_version": CATALOG_VERSION, "fallback_used": fallback,
                "warnings": ["ANNUITY_COEFFICIENT_DEFAULT_200"] if fallback else []}
    try:
        tables = catalog()
        pension = any(token in product.product_type.lower() for token in
            ("קרן פנסיה", "פנסיה מקיפה", "פנסיה כללית", "קופת גמל", "קרן השתלמות", "pension", "provident", "education"))
        if pension:
            rows = [r for r in tables["pension_fund_coefficient"] if r["sex"] == sex
                    and int(r["retirement_age"]) == age and r["survivors_option"] == keys["survivors_option"]
                    and int(r["spouse_age_diff"]) == spouse_age_diff]
            if rows:
                row = max(rows, key=lambda r: int(r["id"]))
                base, adjustment = Decimal(row["base_coefficient"]), Decimal(row["adjust_percent"])
                return result(base if adjustment == 0 else base * adjustment, "pension_fund_coefficient", row.get("notes") or "")
        else:
            # V1 usePensionConversion sends product start date || paymentDateISO.
            # Canonical requests require that same explicit pension start date;
            # the separate V1 retirement-year-only route does not apply here.
            generation_date = product.start_date or pension_start_date
            keys["generation_date"] = generation_date.isoformat() if generation_date else None
            keys["generation_date_source"] = "product_start_date" if product.start_date else "pension_start_date"
            generation = next((r["generation_code"] for r in tables["product_to_generation_map"]
                if generation_date and r["product_type"] == "ביטוח מנהלים" and r["rule_from_date"] <= generation_date.isoformat() <= r["rule_to_date"]), None)
            if generation:
                keys["generation_code"] = generation
                if company_name and option_name:
                    row = next((r for r in tables["company_annuity_coefficient"] if r["company_name"] == company_name
                        and r["option_name"] == option_name and r["sex"] == sex and int(r["age"]) == age), None)
                    if row:
                        value = Decimal(row["base_coefficient"]) * (1 + Decimal(row["annual_increment_rate"]) * (year - int(row["base_year"])))
                        return result(value, "company_annuity_coefficient", row.get("notes") or "")
                row = next((r for r in tables["policy_generation_coefficient"] if r["generation_code"] == generation and int(r["age"]) == age), None)
                if row:
                    value = row["female_coefficient" if sex == "נקבה" else "male_coefficient"]
                    if value and Decimal(value) > 0:
                        return result(value, "policy_generation_coefficient", row.get("notes") or "")
        return result(200, "default", "לא נמצא מקדם מתאים; נעשה שימוש במקדם 200", True)
    except (ValueError, ArithmeticError, KeyError, TypeError, OSError):
        return result(200, "error", "חיפוש המקדם נכשל; נעשה שימוש במקדם 200", True)
