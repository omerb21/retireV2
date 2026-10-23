"""Isolated API contract tests: one employment period can own historical grants."""
from __future__ import annotations

from tests.test_phase9_api import _build_client, _create_client


def _employment(client, cid, name="Company A", start="2010-01-01", end="2020-01-01", current=False):
    res = client.post(f"/api/clients/{cid}/employment-records", json={
        "employer_name": name, "work_start_date": start,
        "work_end_date": None if current else end, "is_current": current, "notes": None,
    })
    assert res.status_code == 200, res.text
    return res.json()["employment_record_id"]


def _grant(client, cid):
    res = client.post(f"/api/clients/{cid}/grants", json={
        "employer_name": "Company A", "employer_withholding_file_number": "123456789",
        "employment_start_date": "2010-01-01", "employment_end_date": "2020-01-01",
        "grant_receipt_date": "2020-02-01", "exempt_grant_amount": "1200.00",
    })
    assert res.status_code == 200, res.text
    assert res.json()["employment_record_id"] is None
    return res.json()["grant_id"]


def test_explicit_link_and_protection_for_ended_employment_period(tmp_path):
    client, _, _ = _build_client(tmp_path)
    try:
        cid = _create_client(client)["client_id"]
        first = _employment(client, cid)
        # Return to the SAME legal employer after prior termination: new period.
        later = _employment(client, cid, start="2021-01-01", end="2024-01-01")
        gid = _grant(client, cid)
        endpoint = f"/api/clients/{cid}/grants/{gid}/employment-link"
        result = client.post(endpoint, json={"employment_record_id": first})
        assert result.status_code == 200, result.text
        assert result.json()["employment_record_id"] == first
        second_grant = _grant(client, cid)
        assert client.post(f"/api/clients/{cid}/grants/{second_grant}/employment-link", json={"employment_record_id": first}).status_code == 409
        assert next(item for item in client.get(f"/api/clients/{cid}/grants").json() if item["grant_id"] == gid)["employment_record_id"] == first
        assert client.post(endpoint, json={"employment_record_id": later}).status_code in (409, 422)
        # Existing linked records cannot silently lose their period identity.
        bad_employment = client.put(f"/api/clients/{cid}/employment-records/{first}", json={
            "employer_name": "Company A", "work_start_date": "2011-01-01",
            "work_end_date": "2020-01-01", "is_current": False, "notes": None,
        })
        assert bad_employment.status_code == 409
        bad_grant = client.put(f"/api/clients/{cid}/grants/{gid}", json={
            "employer_name": "Company A", "employer_withholding_file_number": "123456789",
            "employment_start_date": "2010-01-01", "employment_end_date": "2021-01-01",
            "grant_receipt_date": "2020-02-01", "exempt_grant_amount": "1200.00",
        })
        assert bad_grant.status_code == 409
        assert client.delete(f"/api/clients/{cid}/employment-records/{first}").status_code == 409
        assert next(item for item in client.get(f"/api/clients/{cid}/grants").json() if item["grant_id"] == gid)["employment_record_id"] == first
    finally:
        client.close()


def test_reject_other_client_current_period_and_period_mismatch(tmp_path):
    client, _, _ = _build_client(tmp_path)
    try:
        a = _create_client(client, id_number="10501")["client_id"]
        b = _create_client(client, id_number="10502")["client_id"]
        other = _employment(client, b)
        active = _employment(client, a, current=True)
        mismatched = _employment(client, a, start="2018-01-01", end="2020-01-01")
        gid = _grant(client, a)
        endpoint = f"/api/clients/{a}/grants/{gid}/employment-link"
        assert client.post(endpoint, json={"employment_record_id": other}).status_code == 404
        assert client.post(endpoint, json={"employment_record_id": active}).status_code == 422
        assert client.post(endpoint, json={"employment_record_id": mismatched}).status_code == 422
        assert client.get(f"/api/clients/{a}/grants").json()[0]["employment_record_id"] is None
    finally:
        client.close()


def test_atomic_creation_for_ended_period_and_fail_closed_for_invalid_periods(tmp_path):
    client, _, _ = _build_client(tmp_path)
    try:
        a = _create_client(client, id_number="20501")["client_id"]
        b = _create_client(client, id_number="20502")["client_id"]
        historic = _employment(client, a)
        current = _employment(client, a, current=True)
        other = _employment(client, b)
        payload = {
            "employer_name": "Company A", "employer_withholding_file_number": "123456789",
            "employment_start_date": "2010-01-01", "employment_end_date": "2020-01-01",
            "grant_receipt_date": "2020-02-01", "exempt_grant_amount": "1200.00",
        }
        url = f"/api/clients/{a}/employment-records/{historic}/grants"
        result = client.post(url, json=payload)
        assert result.status_code == 200, result.text
        assert result.json()["employment_record_id"] == historic
        assert client.post(url, json=payload).status_code == 409
        assert client.get(f"/api/clients/{a}/grants").json()[0]["employment_record_id"] == historic
        assert client.post(f"/api/clients/{a}/employment-records/{current}/grants", json=payload).status_code == 422
        assert client.post(f"/api/clients/{a}/employment-records/{other}/grants", json=payload).status_code == 404
        incorrect = {**payload, "employment_end_date": "2021-01-01"}
        assert client.post(url, json=incorrect).status_code == 422
        assert len(client.get(f"/api/clients/{a}/grants").json()) == 1
    finally:
        client.close()


def test_create_historical_employment_with_single_grant_transaction(tmp_path):
    client, _, _ = _build_client(tmp_path)
    try:
        cid = _create_client(client, id_number="30501")["client_id"]
        url = f"/api/clients/{cid}/historical-employment-settlements"
        base = {"employment": {
            "employer_name": "Repeated legal employer", "work_start_date": "2005-01-01",
            "work_end_date": "2010-01-01", "is_current": False, "notes": None,
        }}
        bad = client.post(url, json={**base, "exempt_grant_status": "recorded"})
        assert bad.status_code == 422
        assert client.get(f"/api/clients/{cid}/employment-records").json() == []
        created = client.post(url, json={**base, "exempt_grant_status": "recorded",
            "employer_withholding_file_number": "99101",
            "grant_receipt_date": "2010-01-20", "exempt_grant_amount": "2500.00"})
        assert created.status_code == 200, created.text
        period_id = created.json()["employment_record_id"]
        assert created.json()["grant_id"]
        grants = client.get(f"/api/clients/{cid}/grants").json()
        assert len(grants) == 1 and grants[0]["employment_record_id"] == period_id
        second = client.post(url, json={**base,
            "employment": {**base["employment"], "work_start_date": "2012-01-01",
                "work_end_date": "2019-01-01"},
            "exempt_grant_status": "none"})
        assert second.status_code == 200, second.text
        assert second.json()["grant_id"] is None
        assert len(client.get(f"/api/clients/{cid}/employment-records").json()) == 2
        assert len(client.get(f"/api/clients/{cid}/grants").json()) == 1
    finally:
        client.close()
