from copy import deepcopy
from decimal import Decimal
import importlib.util
from pathlib import Path

import pytest

from app.models.pension_product import COMPONENT_CODES
_spec = importlib.util.spec_from_file_location("recovery_migration", Path(__file__).resolve().parents[1] / "alembic/versions/d3e9a6b2c410_canonical_pension_source.py")
_migration = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_migration)
CutoverConflict = _migration.CutoverConflict
build_cutover_plan = _migration.build_cutover_plan


def intake(identifier="A"):
    return {"intake_id": identifier, "client_id": 1, "record_kind": "manual", "lifecycle_status": "accepted_for_review", "declared_provider_name": "גוף", "declared_account_reference": "123", "manual_technical_reference": f"manual-{identifier}", "declared_total_balance_amount": Decimal("100"), "declared_component_values": [{"code": COMPONENT_CODES[0], "value": "12.34"}, {"code": "contribution_component", "value": "87.66"}]}


def revision():
    return {"revision_id": "R", "predecessor_revision_id": None, "client_id": 1, "subject_id": "S", "intake_id": "A", "state": "reconciled", "provider_name": "גוף", "account_reference": "123", "effective_total_value": Decimal("100")}


def test_preflight_deterministic_counts_exact_only_and_no_source_mutation():
    rows = [intake()]
    original = deepcopy(rows)
    result = build_cutover_plan(rows, [], [])
    assert result["counts"] == {"products": 1, "components": 11, "source_links": 1, "conflicts": 0, "unmapped_values": 1}
    assert sum(result["products"][0]["components"].values()) == Decimal("12.34")
    assert result["products"][0]["reported_rewards_total"] is None
    assert rows == original
    assert build_cutover_plan(rows, [], []) == result


def test_competing_active_intakes_abort_even_when_timestamps_differ():
    first, second = intake(), intake("B")
    first["declared_statement_date"] = "2026-08-01"
    second["declared_statement_date"] = "2026-09-01"
    with pytest.raises(CutoverConflict) as error:
        build_cutover_plan([second, first], [], [])
    assert [row["record_id"] for row in error.value.conflicts] == ["A", "B"]


@pytest.mark.parametrize("field,value,code", [("effective_total_value", Decimal("99"), "ledger_source_total_conflict"), ("account_reference", "different", "ledger_source_identity_conflict"), ("intake_id", "missing", "ledger_without_unique_active_source")])
def test_competing_ledger_authority_aborts(field, value, code):
    ledger = revision()
    ledger[field] = value
    with pytest.raises(CutoverConflict) as error:
        build_cutover_plan([intake()], [ledger], [])
    assert code in {item["code"] for item in error.value.conflicts}


def test_conflicting_component_balance_aborts():
    with pytest.raises(CutoverConflict) as error:
        build_cutover_plan([intake()], [revision()], [{"revision_id": "R", "original_code": COMPONENT_CODES[0], "effective_value": Decimal("99")}])
    assert error.value.conflicts[0]["code"] == "ledger_source_component_conflict"


def test_ledger_branching_is_not_resolved_by_timestamp():
    first, second = revision(), revision()
    second["revision_id"] = "R2"
    with pytest.raises(CutoverConflict) as error:
        build_cutover_plan([intake()], [first, second], [])
    assert {item["code"] for item in error.value.conflicts} == {"competing_ledger_leaves"}


def test_history_retained_but_superseded_authority_not_migrated():
    previous, current = intake("old"), intake()
    previous["lifecycle_status"] = "superseded"
    result = build_cutover_plan([previous, current], [], [])
    assert result["counts"]["products"] == 1
    assert previous["lifecycle_status"] == "superseded"


def test_opaque_upload_is_preserved_without_invented_product():
    upload = {"intake_id": "file", "client_id": 1, "record_kind": "uploaded_source", "lifecycle_status": "uploaded"}
    assert build_cutover_plan([upload], [], [])["counts"]["products"] == 0
