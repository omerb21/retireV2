"""M12 report is descriptive, read-only, and emits printable Hebrew PDF."""
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import Mock
import pytest
from app.services.m12_draft_report_service import build
from app.services.m12_draft_pdf import render_pdf
from app.services.scenario_draft_service import DraftError

def _client():
    return SimpleNamespace(
        display_name="לקוח סינתטי",
        birth_date=None, employment_status="unknown",
        planned_retirement_date=None, planned_retirement_age=67,
    )

def _empty_database():
    db=Mock()
    db.get.return_value=_client()
    db.scalars.return_value=[]
    db.scalar.return_value=None
    return db

def test_partially_populated_draft_does_not_invent_money_or_calculations():
    db=_empty_database()
    content=build(db, 901)
    assert content["draft"] is True
    assert content["client"]["planned_retirement_age"] == 67
    assert content["preferred"] is None
    assert content["cashflow_results"] is None
    assert content["calculation_traceability"] == "not_established"
    assert not content["pension_products"]
    assert not content["capital_assets"]
    assert any("לא נשמרה חלופה" in w for w in content["warnings"])
    db.commit.assert_not_called()

def test_missing_client_fails_closed():
    db=_empty_database()
    db.get.return_value=None
    with pytest.raises(DraftError, match="CLIENT_NOT_FOUND"):
        build(db, 999)

def test_complete_synthetic_pdf_is_valid_and_not_an_authorized_calculation():
    content=build(_empty_database(), 901)
    content["pension_products"]=[{
        "name":"קרן פנסיה סינתטית","type":"pension_fund","provider":"גוף מדומה",
        "reported_total":"123456.78","statement_date":"2026-10-01",
        "verification":"דיווח מקור, אינו אישור חישוב",
    }]
    content["preferred"]={"name":"חלופה מקצועית מדומה","version_at_selection":2,
                          "rationale":"שמירה על גמישות תזרימית ללא תוצאת חישוב חדשה",
                          "saved_at":"2026-11-15T10:00:00Z","outdated":False}
    content["scenarios"]=[{"name":"חלופה מקצועית מדומה","version":2,"status":"draft",
                            "preferred":True,"decisions":[{
                                "component":"תגמולים","action":"pension",
                                "declared_amount":"25000.00","effective_date":"2027-01-01",
                                "validation_state":"unverified","qualified_calculation":False,
                            }]}]
    result=render_pdf(content)
    assert result.startswith(b"%PDF")
    assert len(result)>1200
    assert content["cashflow_results"] is None
    assert content["calculation_traceability"] == "not_established"

def test_partial_synthetic_pdf_also_renders():
    result=render_pdf(build(_empty_database(), 902))
    assert result.startswith(b"%PDF") and len(result)>900

def test_multi_page_synthetic_report_preserves_qualified_absence_and_rtl_artifact():
    sample = build(_empty_database(), 903)
    sample["pension_products"] = [{
        "name": "קרן פנסיה סינתטית " + str(i) + " ארוכת שם לצורך בדיקת גלישת טקסט",
        "provider": "חברת ניהול סינתטית", "type": "קרן פנסיה",
        "reported_total": "1234567.89", "statement_date": "2026-11-01",
        "verification": "דיווח מקור אינו אישור חישוב"
    } for i in range(19)]
    sample["capital_assets"] = [{
        "name": "נכס הוני סינתטי " + str(i) + " - תיאור ארוך שמטרתו לבחון חלוקת עמודים",
        "category": "נכס הוני", "value": "2345678.12",
        "value_date": "2026-10-01", "verification": "unverified"
    } for i in range(9)]
    sample["preferred"] = {
        "name": "חלופה סינתטית מועדפת", "rationale": "נימוק מקצועי ארוך " * 28,
        "version_at_selection": 2, "saved_at": "2026-11-15T00:00:00Z", "outdated": True,
    }
    sample["warnings"].extend(["מידע מהותי אינו מאומת."] * 4)
    payload = render_pdf(sample)
    assert payload.startswith(b"%PDF") and len(payload) > 3000
    assert sample["cashflow_results"] is None
    assert sample["calculation_traceability"] == "not_established"
    destination = Path("../acceptance-evidence/m12-updated-multipage-synthetic.pdf")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload)
