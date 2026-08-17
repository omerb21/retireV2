from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base, load_all_models
from app.db.session import get_db
from app.main import app
from app.models.client import Client
from app.models.m09_scenario_subject import M09SubjectRun
from app.models.retirement_facts import RecurringExpense, RecurringIncome
from app.services import m09_cashflow_service as factual_service
from app.services.m09_cashflow_service import M09CashflowError
from app.services.m10_comparison_service import PUBLIC_BLOCKERS, compare_runs
from app.services import m10_comparison_service as comparison_service
from app.schemas.m10_comparison import M10ComparisonRequest


HORIZON = {"start_month": "2026-01", "end_month": "2026-03"}
FAMILY = "declared_retirement_cashflow_adjustments"
METRICS_FOR_TEST = {"gross_inflow_total", "gross_outflow_total", "period_net"}


@pytest.fixture
def api(tmp_path: Path, monkeypatch):
    load_all_models()
    engine = create_engine(
        f"sqlite:///{tmp_path / 'pkg015.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    with sessions() as db:
        db.add_all(
            [
                Client(client_id=1, display_name="One", id_number="001", status="delivered"),
                Client(client_id=2, display_name="Two", id_number="002", status="delivered"),
                RecurringIncome(
                    client_id=1,
                    income_category="employment",
                    description="Income",
                    amount=Decimal("1000.00"),
                    amount_basis="gross",
                    frequency="monthly",
                    continuation_status="ongoing",
                    lifecycle_status="current",
                    source_status="planner entered",
                    verification_state="reviewed",
                ),
                RecurringExpense(
                    client_id=1,
                    expense_category="housing",
                    description="Expense",
                    amount=Decimal("300.00"),
                    frequency="monthly",
                    expense_type="mandatory",
                    continuation_status="ongoing",
                    lifecycle_status="current",
                    source_status="planner entered",
                    verification_state="reviewed",
                ),
            ]
        )
        db.commit()
    monkeypatch.setattr(factual_service, "list_m06_subjects", lambda _db, _client_id: [])

    def override():
        with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = override
    try:
        yield TestClient(app), sessions, engine
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def _pair(client: TestClient, amount: str = "100.00"):
    baseline = client.post("/api/clients/1/m09/subjects/baseline").json()
    adjusted = client.post(
        "/api/clients/1/m09/subjects",
        json={
            "scenario_family": FAMILY,
            "scenario_contract_version": "v1",
            "display_label": "Alternative",
            "adjustments": [
                {
                    "adjustment_type": "declared_additional_monthly_income",
                    "amount": amount,
                    "start_month": "2026-01",
                    "end_month": "2026-02",
                }
            ],
        },
    ).json()
    reference = client.post(
        f"/api/clients/1/m09/subjects/{baseline['scenario_subject_id']}/runs",
        json=HORIZON,
    ).json()
    compared = client.post(
        f"/api/clients/1/m09/subjects/{adjusted['scenario_subject_id']}/runs",
        json=HORIZON,
    ).json()
    return baseline, adjusted, reference, compared


def _request(reference, compared):
    return {
        "reference_run_id": reference["run_id"],
        "compared_run_id": compared["run_id"],
    }


def test_success_is_exact_stateless_and_deterministic(api):
    client, sessions, _ = api
    _, _, reference, compared = _pair(client)
    with sessions() as db:
        before = db.scalar(select(func.count()).select_from(M09SubjectRun))
    first = client.post("/api/clients/1/m10/compare", json=_request(reference, compared))
    second = client.post("/api/clients/1/m10/compare", json=_request(reference, compared))
    assert first.status_code == second.status_code == 200, first.text
    body = first.json()
    assert body == second.json()
    assert set(body) == {
        "comparison_contract_version",
        "pair_admission_contract",
        "comparison_result_schema",
        "comparison_fingerprint_schema",
        "comparison_fingerprint",
        "delta_direction",
        "client_id",
        "scenario_family",
        "scenario_contract_version",
        "horizon",
        "factual_baseline_material_fingerprint",
        "component_domain_contract_version",
        "versions",
        "reference_run",
        "compared_run",
        "monthly_comparisons",
        "range_totals",
    }
    assert body["delta_direction"] == "compared_minus_reference"
    assert [row["month"] for row in body["monthly_comparisons"]] == [
        "2026-01",
        "2026-02",
        "2026-03",
    ]
    assert [row["gross_inflow_total"]["delta"] for row in body["monthly_comparisons"]] == [
        "100.00",
        "100.00",
        "0.00",
    ]
    assert body["range_totals"]["gross_inflow_total"]["delta"] == "200.00"
    assert set(body["versions"]) == {
        "factual_engine_version",
        "factual_result_schema_version",
        "subject_engine_version",
        "subject_result_schema_version",
        "upstream_snapshot_schema_version",
        "factual_inventory_schema_version",
        "factual_upstream_versions",
    }
    run_keys = {
        "run_id",
        "scenario_subject_id",
        "subject_type",
        "calculation_semantic_fingerprint",
        "integrity_fingerprint",
        "adjustment_manifest_fingerprint",
        "factual_inventory_fingerprint",
        "upstream_snapshot_fingerprint",
        "semantic_result_fingerprint",
        "result_integrity_fingerprint",
    }
    assert set(body["reference_run"]) == set(body["compared_run"]) == run_keys
    metric_keys = {"reference_value", "compared_value", "delta", "relation"}
    assert set(body["monthly_comparisons"][0]) == {"month", *METRICS_FOR_TEST}
    assert all(
        set(comparison) == metric_keys
        for row in body["monthly_comparisons"]
        for comparison in (row["gross_inflow_total"], row["gross_outflow_total"], row["period_net"])
    )
    assert "null" not in json.dumps(body)
    assert all(
        isinstance(metric[key], str)
        for row in body["monthly_comparisons"]
        for metric in (row["gross_inflow_total"], row["gross_outflow_total"], row["period_net"])
        for key in ("reference_value", "compared_value", "delta")
    )
    material = {key: value for key, value in body.items() if key != "comparison_fingerprint"}
    expected = hashlib.sha256(
        json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert body["comparison_fingerprint"] == expected
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(M09SubjectRun)) == before


def test_strict_request_and_closed_resource_failure(api):
    client, _, _ = api
    _, _, reference, compared = _pair(client)
    assert client.post("/api/clients/1/m10/compare", json={}).status_code == 422
    assert (
        client.post(
            "/api/clients/1/m10/compare",
            json=_request(reference, compared) | {"client_id": 1},
        ).status_code
        == 422
    )
    for payload in (
        {"reference_run_id": "missing", "compared_run_id": compared["run_id"]},
        {"reference_run_id": reference["run_id"], "compared_run_id": "missing"},
    ):
        response = client.post("/api/clients/1/m10/compare", json=payload)
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "comparison_run_unavailable"
        assert "comparison_fingerprint" not in response.text
    foreign = client.post("/api/clients/2/m10/compare", json=_request(reference, compared))
    missing = client.post(
        "/api/clients/2/m10/compare",
        json={"reference_run_id": "missing-a", "compared_run_id": "missing-b"},
    )
    assert (foreign.status_code, foreign.json()) == (missing.status_code, missing.json())


def test_same_subject_and_role_precedence(api):
    client, _, _ = api
    _, _, reference, compared = _pair(client)
    same = client.post(
        "/api/clients/1/m10/compare",
        json={"reference_run_id": reference["run_id"], "compared_run_id": reference["run_id"]},
    )
    assert same.status_code == 409
    assert same.json()["detail"]["code"] == "comparison_same_subject"
    reversed_pair = client.post(
        "/api/clients/1/m10/compare",
        json={"reference_run_id": compared["run_id"], "compared_run_id": reference["run_id"]},
    )
    assert reversed_pair.status_code == 409
    assert reversed_pair.json()["detail"]["code"] == "comparison_pair_role_invalid"


def test_integrity_precedes_currentness(api):
    client, _, engine = api
    _, _, reference, compared = _pair(client)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "UPDATE m09_subject_runs SET result_integrity_fingerprint=? WHERE run_id=?",
            ("f" * 64, reference["run_id"]),
        )
    response = client.post("/api/clients/1/m10/compare", json=_request(reference, compared))
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "comparison_fingerprint_invalid"
    assert "comparison_fingerprint" not in response.json()


def test_reference_currentness_precedes_compared_currentness(api):
    client, _, _ = api
    baseline, adjusted, reference, compared = _pair(client)
    client.post(
        f"/api/clients/1/m09/subjects/{baseline['scenario_subject_id']}/runs", json=HORIZON
    )
    client.post(
        f"/api/clients/1/m09/subjects/{adjusted['scenario_subject_id']}/runs", json=HORIZON
    )
    response = client.post("/api/clients/1/m10/compare", json=_request(reference, compared))
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "comparison_run_not_current"
    assert response.json()["detail"]["message"] == "reference run is not current"


@pytest.mark.parametrize("side", ["reference", "compared"])
def test_each_side_must_be_current(api, side):
    client, _, _ = api
    baseline, adjusted, reference, compared = _pair(client)
    subject = baseline if side == "reference" else adjusted
    client.post(
        f"/api/clients/1/m09/subjects/{subject['scenario_subject_id']}/runs", json=HORIZON
    )
    response = client.post("/api/clients/1/m10/compare", json=_request(reference, compared))
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "comparison_run_not_current"
    assert response.json()["detail"]["message"] == f"{side} run is not current"


@pytest.mark.parametrize("side", ["reference", "compared"])
def test_each_side_must_be_eligible_after_currentness(api, side):
    client, _, engine = api
    _, _, reference, compared = _pair(client)
    run = reference if side == "reference" else compared
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "UPDATE m09_subject_runs SET warnings=? WHERE run_id=?",
            ('[{"code":"review","classification":"mandatory_review_warning"}]', run["run_id"]),
        )
    response = client.post("/api/clients/1/m10/compare", json=_request(reference, compared))
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "comparison_run_not_eligible"
    assert response.json()["detail"]["message"] == f"{side} run is not eligible"


def test_adjusted_versus_adjusted_is_rejected(api):
    client, _, _ = api
    _, _, _, first = _pair(client)
    second_subject = client.post(
        "/api/clients/1/m09/subjects",
        json={
            "scenario_family": FAMILY,
            "scenario_contract_version": "v1",
            "adjustments": [
                {
                    "adjustment_type": "declared_additional_monthly_expense",
                    "amount": "25.00",
                    "start_month": "2026-01",
                    "end_month": "2026-03",
                }
            ],
        },
    ).json()
    second = client.post(
        f"/api/clients/1/m09/subjects/{second_subject['scenario_subject_id']}/runs",
        json=HORIZON,
    ).json()
    response = client.post(
        "/api/clients/1/m10/compare",
        json={"reference_run_id": first["run_id"], "compared_run_id": second["run_id"]},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "comparison_pair_role_invalid"


@pytest.mark.parametrize("side", ["reference", "compared"])
@pytest.mark.parametrize(
    ("table", "column", "identity_column"),
    [
        ("m09_scenario_subjects", "integrity_fingerprint", "scenario_subject_id"),
        ("m09_subject_runs", "adjustment_manifest_fingerprint", "run_id"),
        ("m09_subject_runs", "factual_inventory_fingerprint", "run_id"),
        ("m09_subject_runs", "upstream_snapshot_fingerprint", "run_id"),
        ("m09_subject_monthly_results", "result_fingerprint", "run_id"),
    ],
)
def test_every_reference_and_compared_integrity_dimension_fails_closed(
    api, side, table, column, identity_column
):
    client, _, engine = api
    baseline, adjusted, reference, compared = _pair(client)
    run = reference if side == "reference" else compared
    subject = baseline if side == "reference" else adjusted
    identity = run["run_id"] if identity_column == "run_id" else subject["scenario_subject_id"]
    with engine.begin() as connection:
        connection.exec_driver_sql(
            f"UPDATE {table} SET {column}=? WHERE {identity_column}=?",
            ("f" * 64, identity),
        )
    response = client.post("/api/clients/1/m10/compare", json=_request(reference, compared))
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "comparison_fingerprint_invalid"


def test_reference_integrity_precedes_compared_integrity(api):
    client, _, engine = api
    _, _, reference, compared = _pair(client)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "UPDATE m09_subject_runs SET factual_inventory_fingerprint=? WHERE run_id=?",
            ("e" * 64, reference["run_id"]),
        )
        connection.exec_driver_sql(
            "UPDATE m09_subject_runs SET upstream_snapshot_fingerprint=? WHERE run_id=?",
            ("f" * 64, compared["run_id"]),
        )
    response = client.post("/api/clients/1/m10/compare", json=_request(reference, compared))
    assert response.status_code == 409
    assert response.json()["detail"] == {
        "code": "comparison_fingerprint_invalid",
        "message": "factual inventory fingerprint is invalid",
    }


def test_horizon_precedes_integrity(api):
    client, _, engine = api
    _, _, reference, compared = _pair(client)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "PRAGMA ignore_check_constraints=ON"
        )
        connection.exec_driver_sql(
            "UPDATE m09_subject_runs SET end_month=?, result_integrity_fingerprint=? WHERE run_id=?",
            ("2026-04", "f" * 64, compared["run_id"]),
        )
    response = client.post("/api/clients/1/m10/compare", json=_request(reference, compared))
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "comparison_horizon_mismatch"


def _bypass_m09_authorities(monkeypatch):
    monkeypatch.setattr(comparison_service, "_check_run_integrity", lambda *_args: None)
    monkeypatch.setattr(
        comparison_service,
        "subject_currentness",
        lambda *_args: SimpleNamespace(
            assessment_contract_version="m09-subject-currentness-v1", is_current=True
        ),
    )
    monkeypatch.setattr(
        comparison_service,
        "subject_eligibility",
        lambda *_args: SimpleNamespace(
            eligibility_contract_version="m09-to-m10-eligibility-v2",
            eligible_for_m10=True,
        ),
    )


def test_factual_material_precedes_component_domain(monkeypatch, api):
    client, _, engine = api
    _, _, reference, compared = _pair(client)
    _bypass_m09_authorities(monkeypatch)
    with engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA ignore_check_constraints=ON")
        connection.exec_driver_sql(
            "UPDATE m09_subject_runs SET factual_baseline_material_fingerprint=?, component_domain_contract_version=? WHERE run_id=?",
            ("f" * 64, "unsupported", compared["run_id"]),
        )
    response = client.post("/api/clients/1/m10/compare", json=_request(reference, compared))
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "comparison_factual_baseline_material_mismatch"


def test_manifest_identity_precedes_month_alignment(monkeypatch, api):
    client, _, engine = api
    _, _, reference, compared = _pair(client)
    _bypass_m09_authorities(monkeypatch)
    original_subject = comparison_service._subject
    semantic = {}

    def semantically_identical_subject(db, run):
        subject = original_subject(db, run)
        if subject.subject_type == "baseline":
            semantic["reference"] = subject.calculation_semantic_fingerprint
            return subject
        copied = SimpleNamespace(
            **{key: value for key, value in subject.__dict__.items() if not key.startswith("_")}
        )
        copied.calculation_semantic_fingerprint = semantic["reference"]
        return copied

    monkeypatch.setattr(comparison_service, "_subject", semantically_identical_subject)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "DELETE FROM m09_subject_monthly_results WHERE run_id=? AND month=?",
            (compared["run_id"], "2026-03"),
        )
    response = client.post("/api/clients/1/m10/compare", json=_request(reference, compared))
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "comparison_semantically_identical_manifest"


def test_month_alignment_precedes_numeric_domain(monkeypatch, api):
    client, _, engine = api
    _, _, reference, compared = _pair(client)
    _bypass_m09_authorities(monkeypatch)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "DELETE FROM m09_subject_monthly_results WHERE run_id=? AND month=?",
            (compared["run_id"], "2026-03"),
        )
        connection.exec_driver_sql(
            "UPDATE m09_subject_runs SET range_totals=? WHERE run_id=?",
            ('{"gross_inflow_total":"1e2","gross_outflow_total":"0.00","period_net":"0.00"}', compared["run_id"]),
        )
    response = client.post("/api/clients/1/m10/compare", json=_request(reference, compared))
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "comparison_month_alignment_mismatch"


def test_direct_service_enforces_client_scope(api):
    client, sessions, _ = api
    _, _, reference, compared = _pair(client)
    with sessions() as db, pytest.raises(M09CashflowError) as captured:
        compare_runs(db, 2, M10ComparisonRequest(**_request(reference, compared)))
    assert (captured.value.status_code, captured.value.code) == (
        404,
        "comparison_run_unavailable",
    )


def test_public_blocker_vocabulary_is_closed():
    assert PUBLIC_BLOCKERS == (
        "comparison_run_unavailable",
        "comparison_same_subject",
        "comparison_pair_role_invalid",
        "comparison_scenario_contract_mismatch",
        "comparison_horizon_mismatch",
        "comparison_factual_baseline_material_mismatch",
        "comparison_component_domain_contract_mismatch",
        "comparison_engine_version_mismatch",
        "comparison_result_schema_version_mismatch",
        "comparison_factual_upstream_version_mismatch",
        "comparison_run_not_current",
        "comparison_run_not_eligible",
        "comparison_fingerprint_invalid",
        "comparison_semantically_identical_manifest",
        "comparison_month_alignment_mismatch",
        "comparison_numeric_domain_invalid",
    )


@pytest.mark.parametrize(
    ("reference", "compared", "delta", "relation"),
    [
        ("0.00", "0.00", "0.00", "equal"),
        ("1.00", "2.00", "1.00", "compared_greater_than_reference"),
        ("2.00", "1.00", "-1.00", "compared_lower_than_reference"),
        (
            "-999999999999999999.99",
            "999999999999999999.99",
            "1999999999999999999.98",
            "compared_greater_than_reference",
        ),
        (
            "999999999999999999.99",
            "-999999999999999999.99",
            "-1999999999999999999.98",
            "compared_lower_than_reference",
        ),
    ],
)
def test_decimal_domain_and_numeric_relations(reference, compared, delta, relation):
    result = comparison_service._metric(reference, compared)
    assert result == {
        "reference_value": reference,
        "compared_value": compared,
        "delta": delta,
        "relation": relation,
    }


def test_negative_zero_is_canonical_and_outflow_relation_is_numeric():
    result = comparison_service._metric(Decimal("-0.00"), Decimal("1.00"))
    assert result["reference_value"] == "0.00"
    assert result["relation"] == "compared_greater_than_reference"


@pytest.mark.parametrize("value", [1.0, "1e2", "1.001", "01.00", "NaN", "Infinity"])
def test_numeric_coercion_rounding_and_nonfinite_values_fail_closed(value):
    with pytest.raises(M09CashflowError) as captured:
        comparison_service._metric(value, "0.00")
    assert captured.value.code == "comparison_numeric_domain_invalid"


def _inventory(domains):
    return SimpleNamespace(factual_inventory={"domains": domains})


def _candidate(identity, *, included=True, components=None):
    return {
        "candidate_identity": identity,
        "source_identity": identity,
        "source_version": "unversioned",
        "source_fingerprint": "a" * 64,
        "included": included,
        "components": components or [],
    }


def test_upstream_projection_preserves_persisted_order_and_closed_shape():
    run = _inventory(
        [
            {
                "domain_identity": "recurring_expense",
                "candidates": [_candidate("z"), _candidate("a", included=False)],
            },
            {
                "domain_identity": "recurring_income",
                "candidates": [_candidate("b")],
            },
        ]
    )
    projection = comparison_service._upstream_versions(run)
    assert [item["candidate_identity"] for item in projection] == ["z", "b"]
    assert all(item["handoff_contract_versions"] == [] for item in projection)
    assert set(projection[0]) == {
        "domain_identity",
        "candidate_identity",
        "source_identity",
        "source_version",
        "source_fingerprint",
        "handoff_contract_versions",
    }


def test_upstream_projection_no_included_candidates_is_empty():
    run = _inventory(
        [{"domain_identity": "recurring_income", "candidates": [_candidate("a", included=False)]}]
    )
    assert comparison_service._upstream_versions(run) == []


@pytest.mark.parametrize(
    "domains",
    [
        [{"domain_identity": "recurring_income", "candidates": [_candidate("a") | {"included": "true"}]}],
        [{"domain_identity": "unknown", "candidates": []}],
        [
            {
                "domain_identity": "recurring_income",
                "candidates": [_candidate("a"), _candidate("a")],
            }
        ],
        [{"domain_identity": "m06_monthly_pension", "candidates": [_candidate("a")]}],
        [
            {
                "domain_identity": "m06_monthly_pension",
                "candidates": [
                    _candidate(
                        "a",
                        components=[
                            {"provenance": {"handoff_contract_version": "m06-to-m09-monthly-amount-v1"}},
                            {"provenance": {"handoff_contract_version": "wrong"}},
                        ],
                    )
                ],
            }
        ],
    ],
)
def test_malformed_upstream_projection_fails_closed(domains):
    with pytest.raises(M09CashflowError) as captured:
        comparison_service._upstream_versions(_inventory(domains))
    assert captured.value.code == "comparison_factual_upstream_version_mismatch"


def test_valid_m06_projection_emits_singleton_handoff_contract():
    run = _inventory(
        [
            {
                "domain_identity": "m06_monthly_pension",
                "candidates": [
                    _candidate(
                        "m06:a",
                        components=[
                            {
                                "provenance": {
                                    "handoff_contract_version": "m06-to-m09-monthly-amount-v1"
                                }
                            },
                            {
                                "provenance": {
                                    "handoff_contract_version": "m06-to-m09-monthly-amount-v1"
                                }
                            },
                        ],
                    )
                ],
            }
        ]
    )
    assert comparison_service._upstream_versions(run)[0]["handoff_contract_versions"] == [
        "m06-to-m09-monthly-amount-v1"
    ]


def test_canonical_fingerprint_key_order_is_stable_and_array_order_is_bound():
    assert factual_service._digest({"b": "2", "a": "1"}) == factual_service._digest(
        {"a": "1", "b": "2"}
    )
    assert factual_service._digest({"values": ["a", "b"]}) != factual_service._digest(
        {"values": ["b", "a"]}
    )
