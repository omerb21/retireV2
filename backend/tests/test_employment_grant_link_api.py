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
        assert client.get(f"/api/clients/{cid}/grants").json()[0]["employment_record_id"] == first
        assert client.post(endpoint, json={"employment_record_id": later}).status_code in (409, 422)
        assert client.delete(f"/api/clients/{cid}/employment-records/{first}").status_code == 409
        assert client.get(f"/api/clients/{cid}/grants").json()[0]["employment_record_id"] == first
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
