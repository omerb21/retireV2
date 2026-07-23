from __future__ import annotations

import inspect
import os
import subprocess
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect as sqlalchemy_inspect, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base, load_all_models
from app.db.session import get_db
from app.main import app
from app.models.official_parameter_set import (
    OfficialParameterEvidenceImmutableError,
    OfficialParameterSet,
)
from app.schemas.fixation_admissibility import AcceptedParameterSet
from app.schemas.official_parameter_sets import (
    OFFICIAL_PARAMETER_FINGERPRINT_ALGORITHM,
    OFFICIAL_PARAMETER_RESOLVER_VERSION,
    OfficialParameterActivationRequest,
    OfficialParameterResolution,
    OfficialParameterSetCreate,
    OfficialParameterSupersessionRequest,
    OfficialParameterValues,
    OfficialParameterVerificationRequest,
)
from app.services.official_parameter_service import (
    OfficialParameterLifecycleError,
    OfficialParameterOverlapError,
    activate_official_parameter_set,
    canonical_official_parameter_json,
    create_official_parameter_set_draft,
    official_parameter_content,
    official_parameter_fingerprint,
    reject_official_parameter_set,
    resolve_official_parameter_admission_context,
    resolve_official_parameter_set,
    supersede_official_parameter_set,
    verify_official_parameter_set,
)
from app.schemas.official_parameter_sets import OfficialParameterRejectionRequest


load_all_models()
NOW = datetime(2026, 1, 2, 8, 0, tzinfo=timezone.utc)


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _request(
    *,
    parameter_set_id: str | None = "official-2026-r1",
    tax_year: int = 2026,
    effective_from: date = date(2026, 1, 1),
    effective_to: date | None = date(2026, 12, 31),
    version: str = "2026-r1",
    monthly_cap: str = "1000.000000",
    metadata: dict | None = None,
) -> OfficialParameterSetCreate:
    return OfficialParameterSetCreate(
        parameter_set_id=parameter_set_id,
        tax_year=tax_year,
        effective_from=effective_from,
        effective_to=effective_to,
        parameter_set_version=version,
        values={
            "monthly_cap": monthly_cap,
            "exemption_percentage": "0.5",
            "capital_multiplier": "180",
            "grant_impact_multiplier": "1.35",
        },
        source_type="official_publication",
        source_title="Official annual parameter publication",
        official_source_reference="official://tax-authority/2026/r1",
        source_publication_date=date(2025, 12, 15),
        source_recorded_at=NOW,
        source_evidence_metadata=metadata or {"document_id": "publication-2026-r1"},
        created_by="admin-creator",
    )


def _draft(
    db_session: Session,
    **overrides,
) -> OfficialParameterSet:
    return create_official_parameter_set_draft(
        db_session=db_session,
        request=_request(**overrides),
        timestamp=NOW,
    )


def _verify(
    db_session: Session,
    row: OfficialParameterSet,
) -> OfficialParameterSet:
    return verify_official_parameter_set(
        db_session=db_session,
        parameter_set_id=row.parameter_set_id,
        request=OfficialParameterVerificationRequest(
            verified_by="admin-verifier",
            verification_note="source and values checked",
        ),
        timestamp=NOW,
    )


def _activate(
    db_session: Session,
    row: OfficialParameterSet,
) -> OfficialParameterSet:
    return activate_official_parameter_set(
        db_session=db_session,
        parameter_set_id=row.parameter_set_id,
        request=OfficialParameterActivationRequest(activated_by="admin-activator"),
        timestamp=NOW,
    )


def _active(db_session: Session, **overrides) -> OfficialParameterSet:
    return _activate(db_session, _verify(db_session, _draft(db_session, **overrides)))


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _upgrade_database(db_path: Path) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=_backend_root(),
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )


def test_global_schema_is_auditable_decimal_and_not_client_owned(db_session: Session) -> None:
    row = _draft(db_session, parameter_set_id=None)
    db_session.commit()

    assert row.status == "draft"
    assert row.parameter_set_id.startswith("official-params-")
    assert len(row.parameter_set_id) <= 64
    assert row.monthly_cap == Decimal("1000.000000")
    assert row.exemption_percentage == Decimal("0.5000000000")
    assert row.created_by == "admin-creator"
    assert row.source_recorded_at is not None
    assert row.parameter_payload["values"]["capital_multiplier"] == "180"
    assert row.content_fingerprint and len(row.content_fingerprint) == 64
    assert row.fingerprint_algorithm_version == OFFICIAL_PARAMETER_FINGERPRINT_ALGORITHM

    columns = OfficialParameterSet.__table__.columns
    assert "client_id" not in columns
    assert not any("client" in column.name for column in columns)
    assert not any(
        field in columns
        for field in ("accepted_for_use", "accepted_by", "client_decision_actor")
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("monthly_cap", "0"),
        ("monthly_cap", "-1"),
        ("exemption_percentage", "-0.01"),
        ("exemption_percentage", "1.01"),
        ("capital_multiplier", "0"),
        ("grant_impact_multiplier", "0"),
    ],
)
def test_parameter_values_reject_invalid_or_invented_numeric_content(
    field: str,
    value: str,
) -> None:
    values = {
        "monthly_cap": "1000",
        "exemption_percentage": "0.5",
        "capital_multiplier": "180",
        "grant_impact_multiplier": "1.35",
    }
    values[field] = value
    with pytest.raises(ValueError):
        OfficialParameterValues(**values)


def test_source_metadata_is_inert_json_only() -> None:
    payload = _request().model_dump(mode="python")
    payload["source_evidence_metadata"] = {"callable": object()}
    with pytest.raises(ValueError):
        OfficialParameterSetCreate(**payload)


def test_lifecycle_requires_verification_and_preserves_audit_actors(
    db_session: Session,
) -> None:
    row = _draft(db_session)
    with pytest.raises(OfficialParameterLifecycleError, match="only verified"):
        _activate(db_session, row)

    _verify(db_session, row)
    assert row.status == "verified"
    assert row.verified_by == "admin-verifier"
    assert row.verified_at == NOW
    assert row.verification_note == "source and values checked"

    _activate(db_session, row)
    db_session.commit()
    assert row.status == "active"
    assert row.activated_by == "admin-activator"
    assert row.activated_at is not None
    assert row.activated_at.replace(tzinfo=timezone.utc) == NOW


def test_active_values_and_effective_period_are_immutable(db_session: Session) -> None:
    row = _active(db_session)
    db_session.commit()

    row.monthly_cap = Decimal("1001")
    with pytest.raises(
        OfficialParameterEvidenceImmutableError,
        match="active official parameter-set evidence is immutable",
    ):
        db_session.flush()
    db_session.rollback()

    row = db_session.get(OfficialParameterSet, "official-2026-r1")
    assert row is not None
    row.effective_to = date(2027, 1, 1)
    with pytest.raises(ValueError, match="create a new revision"):
        db_session.flush()
    db_session.rollback()


@pytest.mark.parametrize(
    ("field_name", "forged_value"),
    [
        ("source_evidence_metadata", {"document_id": "forged"}),
        ("source_title", "Forged title"),
        ("created_by", "forged-creator"),
        ("created_at", datetime(2030, 1, 1, tzinfo=timezone.utc)),
        ("verified_by", "forged-verifier"),
        ("verified_at", datetime(2030, 1, 2, tzinfo=timezone.utc)),
        ("activated_by", "forged-activator"),
        ("activated_at", datetime(2030, 1, 3, tzinfo=timezone.utc)),
    ],
)
def test_active_authority_evidence_and_lifecycle_are_immutable(
    db_session: Session,
    field_name: str,
    forged_value: object,
) -> None:
    row = _active(db_session)
    db_session.commit()
    original_value = getattr(row, field_name)

    setattr(row, field_name, forged_value)
    with pytest.raises(
        OfficialParameterEvidenceImmutableError,
        match="evidence is immutable",
    ):
        db_session.flush()
    db_session.rollback()

    persisted = db_session.get(OfficialParameterSet, row.parameter_set_id)
    assert persisted is not None
    assert getattr(persisted, field_name) == original_value


@pytest.mark.parametrize("status", ["verified", "active", "superseded", "rejected"])
def test_authority_evidence_records_cannot_be_deleted(
    db_session: Session,
    status: str,
) -> None:
    row = _draft(db_session)
    if status == "verified":
        _verify(db_session, row)
    elif status in {"active", "superseded"}:
        _activate(db_session, _verify(db_session, row))
        if status == "superseded":
            supersede_official_parameter_set(
                db_session=db_session,
                parameter_set_id=row.parameter_set_id,
                request=OfficialParameterSupersessionRequest(
                    superseded_by="admin-superseder"
                ),
                timestamp=NOW,
            )
    else:
        reject_official_parameter_set(
            db_session=db_session,
            parameter_set_id=row.parameter_set_id,
            request=OfficialParameterRejectionRequest(
                rejected_by="admin-rejector",
                rejection_note="invalid evidence",
            ),
            timestamp=NOW,
        )
    db_session.commit()

    db_session.delete(row)
    with pytest.raises(
        OfficialParameterEvidenceImmutableError,
        match="cannot be deleted",
    ):
        db_session.flush()
    db_session.rollback()
    assert db_session.get(OfficialParameterSet, row.parameter_set_id) is not None


def test_active_set_is_corrected_by_separate_revision_and_can_be_superseded(
    db_session: Session,
) -> None:
    active = _active(db_session)
    revision = _draft(
        db_session,
        parameter_set_id="official-2026-r2",
        version="2026-r2",
        monthly_cap="1001",
    )
    supersede_official_parameter_set(
        db_session=db_session,
        parameter_set_id=active.parameter_set_id,
        request=OfficialParameterSupersessionRequest(
            superseded_by="admin-superseder"
        ),
        timestamp=NOW,
    )
    db_session.commit()

    assert active.status == "superseded"
    assert active.superseded_by == "admin-superseder"
    assert active.superseded_at is not None
    assert revision.status == "draft"
    assert revision.monthly_cap == Decimal("1001")


def test_active_cannot_be_superseded_outside_lifecycle_service(
    db_session: Session,
) -> None:
    row = _active(db_session)
    db_session.commit()

    row.status = "superseded"
    row.superseded_by = "direct-caller"
    row.superseded_at = NOW
    with pytest.raises(
        OfficialParameterEvidenceImmutableError,
        match="only be superseded through the lifecycle service",
    ):
        db_session.flush()
    db_session.rollback()

    persisted = db_session.get(OfficialParameterSet, row.parameter_set_id)
    assert persisted is not None
    assert persisted.status == "active"
    assert persisted.superseded_by is None
    assert persisted.superseded_at is None


def test_active_content_cannot_change_during_attempted_supersession(
    db_session: Session,
) -> None:
    row = _active(db_session)
    db_session.commit()

    row.status = "superseded"
    row.superseded_by = "direct-caller"
    row.superseded_at = NOW
    row.source_title = "forged"
    with pytest.raises(
        OfficialParameterEvidenceImmutableError,
        match="evidence is immutable",
    ):
        db_session.flush()
    db_session.rollback()

    persisted = db_session.get(OfficialParameterSet, row.parameter_set_id)
    assert persisted is not None
    assert persisted.status == "active"
    assert persisted.source_title == "Official annual parameter publication"
    assert persisted.superseded_by is None
    assert persisted.superseded_at is None


@pytest.mark.parametrize(
    ("field_name", "forged_value"),
    [
        ("source_title", "forged"),
        ("monthly_cap", Decimal("9999")),
        ("created_by", "forged-creator"),
        ("created_at", datetime(2030, 1, 1, tzinfo=timezone.utc)),
        ("verified_by", "forged-verifier"),
        ("verified_at", datetime(2030, 1, 2, tzinfo=timezone.utc)),
        ("activated_by", "forged-activator"),
        ("activated_at", datetime(2030, 1, 3, tzinfo=timezone.utc)),
        ("superseded_by", "forged-superseder"),
        ("superseded_at", datetime(2030, 1, 4, tzinfo=timezone.utc)),
    ],
)
def test_superseded_evidence_is_immutable_after_commit_and_reload(
    db_session: Session,
    field_name: str,
    forged_value: object,
) -> None:
    row = _active(db_session)
    supersede_official_parameter_set(
        db_session=db_session,
        parameter_set_id=row.parameter_set_id,
        request=OfficialParameterSupersessionRequest(
            superseded_by="admin-superseder"
        ),
        timestamp=NOW,
    )
    db_session.commit()
    parameter_set_id = row.parameter_set_id
    db_session.expunge_all()
    persisted = db_session.get(OfficialParameterSet, parameter_set_id)
    assert persisted is not None
    original_values = {
        column.name: getattr(persisted, column.name)
        for column in OfficialParameterSet.__table__.columns
    }

    setattr(persisted, field_name, forged_value)
    with pytest.raises(
        OfficialParameterEvidenceImmutableError,
        match="superseded official parameter-set evidence is immutable",
    ):
        db_session.flush()
    db_session.rollback()

    reloaded = db_session.get(OfficialParameterSet, parameter_set_id)
    assert reloaded is not None
    assert {
        column.name: getattr(reloaded, column.name)
        for column in OfficialParameterSet.__table__.columns
    } == original_values


@pytest.mark.parametrize("forged_status", ["active", "verified", "rejected"])
def test_superseded_status_cannot_change(
    db_session: Session,
    forged_status: str,
) -> None:
    row = _active(db_session)
    supersede_official_parameter_set(
        db_session=db_session,
        parameter_set_id=row.parameter_set_id,
        request=OfficialParameterSupersessionRequest(
            superseded_by="admin-superseder"
        ),
        timestamp=NOW,
    )
    db_session.commit()
    parameter_set_id = row.parameter_set_id
    db_session.expunge_all()
    persisted = db_session.get(OfficialParameterSet, parameter_set_id)
    assert persisted is not None

    persisted.status = forged_status
    with pytest.raises(
        OfficialParameterEvidenceImmutableError,
        match="superseded official parameter-set evidence is immutable",
    ):
        db_session.flush()
    db_session.rollback()
    assert db_session.get(OfficialParameterSet, parameter_set_id).status == "superseded"


def test_rejected_and_superseded_sets_do_not_resolve(db_session: Session) -> None:
    rejected = _draft(db_session, parameter_set_id="rejected-r1", version="rejected-r1")
    reject_official_parameter_set(
        db_session=db_session,
        parameter_set_id=rejected.parameter_set_id,
        request=OfficialParameterRejectionRequest(
            rejected_by="admin-rejector",
            rejection_note="source could not be verified",
        ),
        timestamp=NOW,
    )
    assert rejected.status == "rejected"
    assert rejected.rejected_by == "admin-rejector"

    active = _active(
        db_session,
        parameter_set_id="active-r2",
        version="active-r2",
    )
    supersede_official_parameter_set(
        db_session=db_session,
        parameter_set_id=active.parameter_set_id,
        request=OfficialParameterSupersessionRequest(
            superseded_by="admin-superseder"
        ),
        timestamp=NOW,
    )
    assert active.status == "superseded"
    assert active.superseded_by == "admin-superseder"

    result = resolve_official_parameter_set(
        db_session=db_session,
        tax_year=2026,
        effective_date=date(2026, 6, 1),
        resolution_timestamp=NOW,
    )
    assert result.result == "unavailable"
    assert result.reason_codes == ["official_parameter_set_unavailable"]


def test_activation_prevents_active_period_overlap(db_session: Session) -> None:
    _active(db_session)
    overlapping = _verify(
        db_session,
        _draft(
            db_session,
            parameter_set_id="official-2026-r2",
            version="2026-r2",
            effective_from=date(2026, 6, 1),
            effective_to=None,
        ),
    )
    with pytest.raises(OfficialParameterOverlapError, match="overlaps"):
        _activate(db_session, overlapping)


def test_exact_match_resolves_full_values_and_evidence(db_session: Session) -> None:
    row = _active(db_session)
    result = resolve_official_parameter_set(
        db_session=db_session,
        tax_year=2026,
        effective_date=date(2026, 7, 1),
        resolution_timestamp=NOW,
    )

    assert result.result == "resolved"
    assert result.selected_parameter_set_id == row.parameter_set_id
    assert result.values == OfficialParameterValues(
        monthly_cap="1000",
        exemption_percentage="0.5",
        capital_multiplier="180",
        grant_impact_multiplier="1.35",
    )
    assert result.parameter_set_version == "2026-r1"
    assert result.evidence is not None
    assert result.evidence.official_source_reference == "official://tax-authority/2026/r1"
    assert result.resolver_contract_version == OFFICIAL_PARAMETER_RESOLVER_VERSION
    assert result.reason_codes == []
    assert result.candidate_ids == []


@pytest.mark.parametrize(
    ("tax_year", "effective_date"),
    [
        (2025, date(2026, 6, 1)),
        (2027, date(2027, 6, 1)),
        (2026, date(2025, 12, 31)),
        (2026, date(2027, 1, 1)),
    ],
)
def test_resolution_has_no_year_or_period_fallback(
    db_session: Session,
    tax_year: int,
    effective_date: date,
) -> None:
    _active(db_session)
    result = resolve_official_parameter_set(
        db_session=db_session,
        tax_year=tax_year,
        effective_date=effective_date,
        resolution_timestamp=NOW,
    )
    assert result.result == "unavailable"
    assert result.selected_parameter_set_id is None
    assert result.values is None
    assert result.reason_codes == ["official_parameter_set_unavailable"]


def test_inconsistent_multiple_active_candidates_fail_closed_as_ambiguous(
    db_session: Session,
) -> None:
    first = _verify(db_session, _draft(db_session))
    second = _verify(
        db_session,
        _draft(
            db_session,
            parameter_set_id="official-2026-r2",
            version="2026-r2",
        ),
    )
    for row in (first, second):
        row.status = "active"
        row.activated_at = NOW
        row.activated_by = "inconsistent-import-fixture"
    db_session.flush()

    result = resolve_official_parameter_set(
        db_session=db_session,
        tax_year=2026,
        effective_date=date(2026, 6, 1),
        resolution_timestamp=NOW,
    )
    assert result.result == "ambiguous"
    assert result.selected_parameter_set_id is None
    assert result.values is None
    assert result.reason_codes == ["multiple_official_parameter_sets_applicable"]
    assert result.candidate_ids == ["official-2026-r1", "official-2026-r2"]


def test_resolution_is_global_and_client_independent(db_session: Session) -> None:
    _active(db_session)
    parameters = inspect.signature(resolve_official_parameter_set).parameters
    assert "client_id" not in parameters
    assert not any("client" in name for name in parameters)

    first = resolve_official_parameter_set(
        db_session=db_session,
        tax_year=2026,
        effective_date=date(2026, 6, 1),
        resolution_timestamp=NOW,
    )
    second = resolve_official_parameter_set(
        db_session=db_session,
        tax_year=2026,
        effective_date=date(2026, 6, 1),
        resolution_timestamp=NOW,
    )
    assert first == second


def test_fingerprint_is_canonical_and_excludes_volatile_timestamps() -> None:
    values_a = OfficialParameterValues(
        monthly_cap=Decimal("1000.00"),
        exemption_percentage=Decimal("0.5000"),
        capital_multiplier=Decimal("180.0"),
        grant_impact_multiplier=Decimal("1.350"),
    )
    values_b = OfficialParameterValues(
        monthly_cap=Decimal("1000"),
        exemption_percentage=Decimal("0.5"),
        capital_multiplier=Decimal("180"),
        grant_impact_multiplier=Decimal("1.35"),
    )
    first = official_parameter_content(
        tax_year=2026,
        effective_from=date(2026, 1, 1),
        effective_to=None,
        schema_version="pkg004a.official-parameter-set.v1",
        parameter_set_version="r1",
        values=values_a,
        source_type="publication",
        source_title="Title",
        official_source_reference="official://r1",
        source_publication_date=date(2025, 12, 1),
        source_evidence_metadata={"b": 2, "a": 1},
    )
    second = official_parameter_content(
        tax_year=2026,
        effective_from=date(2026, 1, 1),
        effective_to=None,
        schema_version="pkg004a.official-parameter-set.v1",
        parameter_set_version="r1",
        values=values_b,
        source_type="publication",
        source_title="Title",
        official_source_reference="official://r1",
        source_publication_date=date(2025, 12, 1),
        source_evidence_metadata={"a": 1, "b": 2},
    )
    assert canonical_official_parameter_json(first) == canonical_official_parameter_json(second)
    assert official_parameter_fingerprint(first) == official_parameter_fingerprint(second)
    assert "created_at" not in first and "source_recorded_at" not in first

    changed = {**second, "values": values_b.model_copy(update={"monthly_cap": Decimal("1001")})}
    assert official_parameter_fingerprint(first) != official_parameter_fingerprint(changed)


def test_evidence_json_numbers_are_canonical_and_semantic_changes_are_distinct() -> None:
    first = {"confidence": 0.5, "whole": 1.0, "nested": [{"score": 0.25}]}
    equivalent = {
        "nested": [{"score": Decimal("0.2500")}],
        "whole": 1,
        "confidence": Decimal("0.500"),
    }
    changed = {"confidence": 0.6, "whole": 1, "nested": [{"score": 0.25}]}

    assert canonical_official_parameter_json(first) == canonical_official_parameter_json(
        equivalent
    )
    assert official_parameter_fingerprint(first) == official_parameter_fingerprint(
        equivalent
    )
    assert official_parameter_fingerprint(first) != official_parameter_fingerprint(changed)
    assert "0.5" in canonical_official_parameter_json(first)


def test_schema_accepted_float_metadata_is_persisted_without_runtime_type_error(
    db_session: Session,
) -> None:
    row = _draft(
        db_session,
        metadata={
            "confidence": 0.5,
            "nested": [{"whole": 1.0, "score": 0.25}],
        },
    )
    db_session.commit()

    canonical_metadata = row.parameter_payload["source"]["source_evidence_metadata"]
    assert canonical_metadata == {
        "confidence": "0.5",
        "nested": [{"score": "0.25", "whole": "1"}],
    }
    assert row.content_fingerprint == official_parameter_fingerprint(
        official_parameter_content(
            tax_year=row.tax_year,
            effective_from=row.effective_from,
            effective_to=row.effective_to,
            schema_version=row.schema_version,
            parameter_set_version=row.parameter_set_version,
            values=_request().values,
            source_type=row.source_type,
            source_title=row.source_title,
            official_source_reference=row.official_source_reference,
            source_publication_date=row.source_publication_date,
            source_evidence_metadata={
                "confidence": Decimal("0.500"),
                "nested": [{"whole": 1, "score": Decimal("0.2500")}],
            },
        )
    )


@pytest.mark.parametrize("non_finite", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_evidence_numbers_are_rejected_at_schema_boundary(
    non_finite: float,
) -> None:
    payload = _request().model_dump(mode="python")
    payload["source_evidence_metadata"] = {
        "nested": [{"confidence": non_finite}]
    }
    with pytest.raises(ValueError, match="must be finite"):
        OfficialParameterSetCreate(**payload)


def test_authority_mapping_is_repository_resolved_not_caller_blessed(
    db_session: Session,
) -> None:
    accepted_fields = AcceptedParameterSet.model_fields
    assert {"client_id", "accepted_for_use", "accepted_by"} <= set(accepted_fields)

    empty_context = resolve_official_parameter_admission_context(
        db_session=db_session,
        tax_year=2026,
        effective_date=date(2026, 6, 1),
        resolution_timestamp=NOW,
    )
    assert empty_context is None

    caller_constructed_result = OfficialParameterResolution(
        result="resolved",
        requested_tax_year=2026,
        requested_effective_date=date(2026, 6, 1),
        selected_parameter_set_id="caller-set",
        values=_request().values,
        parameter_set_version="caller-r1",
        schema_version="pkg004a.official-parameter-set.v1",
        resolution_timestamp=NOW,
    )
    assert caller_constructed_result.values == _request().values
    assert (
        resolve_official_parameter_admission_context(
            db_session=db_session,
            tax_year=2026,
            effective_date=date(2026, 6, 1),
            resolution_timestamp=NOW,
        )
        is None
    )

    _active(db_session)
    context = resolve_official_parameter_admission_context(
        db_session=db_session,
        tax_year=2026,
        effective_date=date(2026, 6, 1),
        resolution_timestamp=NOW,
    )
    assert context is not None
    assert context.parameter_set_id == "official-2026-r1"
    assert context.source_type == "official_publication"
    assert context.source_title == "Official annual parameter publication"
    assert context.official_source_reference == "official://tax-authority/2026/r1"
    assert context.source_publication_date == date(2025, 12, 15)
    assert context.source_recorded_at.replace(tzinfo=timezone.utc) == NOW
    assert context.source_evidence_metadata == {
        "document_id": "publication-2026-r1"
    }
    assert context.verification_note == "source and values checked"
    assert context.verified_by == "admin-verifier"
    assert context.verified_at.replace(tzinfo=timezone.utc) == NOW
    assert context.activated_by == "admin-activator"
    assert context.activated_at.replace(tzinfo=timezone.utc) == NOW
    assert context.content_fingerprint
    assert (
        context.fingerprint_algorithm_version
        == OFFICIAL_PARAMETER_FINGERPRINT_ALGORITHM
    )
    assert context.parameter_set_version == "2026-r1"
    assert context.values == _request().values
    assert not hasattr(context, "client_id")
    assert not hasattr(context, "accepted_for_use")
    assert not hasattr(context, "accepted_by")

    mapping_parameters = inspect.signature(
        resolve_official_parameter_admission_context
    ).parameters
    assert not any(
        name in mapping_parameters
        for name in ("values", "trusted", "token", "authority", "client_id")
    )


def test_resolution_does_not_call_engine_or_cbs(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _active(db_session)
    monkeypatch.setattr(
        "app.engines.fixation_engine.calculate_fixation",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("resolver called fixation engine")
        ),
    )
    monkeypatch.setattr(
        "app.services.cbs_indexation_adapter.calculate_cbs_indexation",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("resolver called CBS")
        ),
    )
    result = resolve_official_parameter_set(
        db_session=db_session,
        tax_year=2026,
        effective_date=date(2026, 6, 1),
        resolution_timestamp=NOW,
    )
    assert result.result == "resolved"


def test_read_only_api_lists_reads_and_resolves_without_write_boundary(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "pkg004a-api.db"
    _upgrade_database(db_path)
    session_local = sessionmaker(bind=create_engine(f"sqlite:///{db_path.as_posix()}"))
    with session_local() as session:
        _active(session)
        for index in range(55):
            _draft(
                session,
                parameter_set_id=f"draft-{index:03d}",
                version=f"draft-{index:03d}",
            )
        session.commit()

    def override_db():
        with session_local() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        resolved = client.get(
            "/api/official-parameter-sets/resolve",
            params={"tax_year": 2026, "effective_date": "2026-06-01"},
        )
        assert resolved.status_code == 200
        assert resolved.json()["result"] == "resolved"
        assert resolved.json()["selected_parameter_set_id"] == "official-2026-r1"

        listed = client.get(
            "/api/official-parameter-sets",
            params={"tax_year": 2026, "status": "active"},
        )
        assert listed.status_code == 200
        assert [item["parameter_set_id"] for item in listed.json()["items"]] == [
            "official-2026-r1"
        ]
        assert listed.json()["total"] == 1
        assert "count" not in listed.json()
        assert listed.json()["offset"] == 0
        assert listed.json()["limit"] == 50
        safe_fields = set(listed.json()["items"][0])
        assert not safe_fields & {
            "source_evidence_metadata",
            "verification_note",
            "created_by",
            "verified_by",
            "activated_by",
            "rejected_by",
            "superseded_by",
            "source_recorded_at",
        }

        default_page = client.get("/api/official-parameter-sets")
        assert default_page.status_code == 200
        assert default_page.json()["total"] == 56
        assert "count" not in default_page.json()
        assert default_page.json()["limit"] == 50
        assert len(default_page.json()["items"]) == 50
        first_ids = [
            item["parameter_set_id"] for item in default_page.json()["items"]
        ]
        assert first_ids == sorted(first_ids)

        second_page = client.get(
            "/api/official-parameter-sets",
            params={"offset": 50, "limit": 10},
        )
        assert second_page.status_code == 200
        assert second_page.json()["offset"] == 50
        assert second_page.json()["limit"] == 10
        assert second_page.json()["total"] == 56
        assert len(second_page.json()["items"]) == 6

        assert client.get(
            "/api/official-parameter-sets",
            params={"limit": 101},
        ).status_code == 422
        assert client.get(
            "/api/official-parameter-sets",
            params={"limit": -1},
        ).status_code == 422
        assert client.get(
            "/api/official-parameter-sets",
            params={"offset": -1},
        ).status_code == 422

        read = client.get("/api/official-parameter-sets/official-2026-r1")
        assert read.status_code == 200
        assert read.json()["status"] == "active"
        assert "client_id" not in read.json()
        assert "source_evidence_metadata" not in read.json()
        assert "verification_note" not in read.json()
        assert "activated_by" not in read.json()

        assert client.get("/api/official-parameter-sets/missing").status_code == 404
        assert client.post("/api/official-parameter-sets", json={}).status_code == 405
    finally:
        app.dependency_overrides.clear()


def test_model_and_runtime_schema_are_aligned_and_global() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    columns = {
        column["name"]: column
        for column in sqlalchemy_inspect(engine).get_columns("official_parameter_sets")
    }
    assert set(columns) == {column.name for column in OfficialParameterSet.__table__.columns}
    assert "client_id" not in columns
    assert columns["parameter_set_id"]["type"].length == 64
    assert columns["content_fingerprint"]["type"].length == 64
    assert columns["monthly_cap"]["type"].scale == 6
    assert columns["exemption_percentage"]["type"].scale == 10
