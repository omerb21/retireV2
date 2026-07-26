from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.m07_evidence import (
    M07EvidenceRevision,
    M07FactEvidence,
    M07PlannerAssertion,
)
from app.schemas.m07_calculation_input_resolution import (
    AmbiguousInputCandidate,
    AmbiguousInputField,
    CalculationInputResolutionRequest,
    CalculationInputResolutionResult,
    CalculationInputSelection,
    CalculationInputSourceReference,
    CalculationReadyInputPayload,
)
from app.services.m07_calculation_input_manifest import (
    M07_CALCULATION_INPUT_MANIFEST_REGISTRY,
    CalculationInputFieldRule,
    CalculationInputManifestRegistry,
    M07CalculationInputNormalizationError,
)
from app.services.m07_evidence_service import (
    canonical_m07_json,
    canonicalize_m07_value,
    m07_fingerprint,
)


class M07CalculationInputReferenceError(LookupError):
    code = "evidence_revision_unavailable"


class M07CalculationInputSelectionError(ValueError):
    code = "calculation_input_selection_invalid"


SAFE_REVISION_MESSAGE = "calculation input evidence is unavailable"
SAFE_SELECTION_MESSAGE = "calculation input selection is invalid"


@dataclass(frozen=True)
class _Candidate:
    field_code: str
    identity: str
    value: Any
    source_reference: CalculationInputSourceReference


@dataclass(frozen=True)
class _NormalizedGroup:
    normalized_value: Any
    candidates: tuple[_Candidate, ...]

    @property
    def identities(self) -> tuple[str, ...]:
        return tuple(candidate.identity for candidate in self.candidates)

    @property
    def source_references(self) -> list[CalculationInputSourceReference]:
        return sorted(
            [candidate.source_reference for candidate in self.candidates],
            key=lambda reference: (
                reference.source_kind,
                reference.source_id,
            ),
        )


def _load_revision(
    *,
    db_session: Session,
    client_id: int,
    revision_id: str,
) -> M07EvidenceRevision:
    revision = db_session.scalar(
        select(M07EvidenceRevision).where(
            M07EvidenceRevision.client_id == client_id,
            M07EvidenceRevision.m07_evidence_revision_id == revision_id,
            M07EvidenceRevision.status == "finalized",
        )
    )
    if revision is None:
        raise M07CalculationInputReferenceError(SAFE_REVISION_MESSAGE)
    return revision


def _load_candidates(
    *,
    db_session: Session,
    client_id: int,
    revision_id: str,
    field_codes: set[str],
) -> list[_Candidate]:
    facts = db_session.scalars(
        select(M07FactEvidence)
        .where(
            M07FactEvidence.client_id == client_id,
            M07FactEvidence.m07_evidence_revision_id == revision_id,
            M07FactEvidence.field_code.in_(field_codes),
            M07FactEvidence.collection_state == "recorded",
            M07FactEvidence.verification_state.notin_(
                {"rejected", "superseded"}
            ),
        )
        .order_by(M07FactEvidence.field_code, M07FactEvidence.fact_evidence_id)
    ).all()
    assertions = db_session.scalars(
        select(M07PlannerAssertion)
        .where(
            M07PlannerAssertion.client_id == client_id,
            M07PlannerAssertion.m07_evidence_revision_id == revision_id,
            M07PlannerAssertion.field_code.in_(field_codes),
        )
        .order_by(
            M07PlannerAssertion.field_code,
            M07PlannerAssertion.assertion_id,
        )
    ).all()
    candidates = [
        _Candidate(
            field_code=fact.field_code,
            identity=f"fact:{fact.fact_evidence_id}",
            value=fact.structured_value,
            source_reference=CalculationInputSourceReference(
                source_kind="fact_evidence",
                source_id=fact.fact_evidence_id,
                source_type=fact.source_type,
                source_record_type=fact.source_record_type,
                source_record_id=fact.source_record_id,
                source_document_reference=fact.source_document_reference,
                assertion_id=fact.assertion_id,
            ),
        )
        for fact in facts
    ]
    candidates.extend(
        _Candidate(
            field_code=assertion.field_code,
            identity=f"assertion:{assertion.assertion_id}",
            value=assertion.asserted_value,
            source_reference=CalculationInputSourceReference(
                source_kind="planner_assertion",
                source_id=assertion.assertion_id,
                source_type="planner_assertion",
                assertion_id=assertion.assertion_id,
            ),
        )
        for assertion in assertions
    )
    return candidates


def _normalize_groups(
    *,
    rule: CalculationInputFieldRule,
    candidates: list[_Candidate],
) -> tuple[_NormalizedGroup, ...]:
    grouped: dict[str, tuple[Any, list[_Candidate]]] = {}
    for candidate in candidates:
        try:
            normalized = rule.normalize(candidate.value)
        except M07CalculationInputNormalizationError:
            continue
        key = canonical_m07_json(normalized)
        if key not in grouped:
            grouped[key] = (normalized, [])
        grouped[key][1].append(candidate)
    return tuple(
        _NormalizedGroup(
            normalized_value=normalized,
            candidates=tuple(
                sorted(candidates_for_value, key=lambda item: item.identity)
            ),
        )
        for _, (normalized, candidates_for_value) in sorted(grouped.items())
    )


def _selection_by_field(
    *,
    request: CalculationInputResolutionRequest,
    manifest_field_codes: set[str],
) -> dict[str, CalculationInputSelection]:
    selections: dict[str, CalculationInputSelection] = {}
    for selection in request.selections:
        if selection.field_code not in manifest_field_codes:
            raise M07CalculationInputSelectionError(SAFE_SELECTION_MESSAGE)
        if (
            selection.b1_evidence_revision_id is not None
            and selection.b1_evidence_revision_id
            != request.b1_evidence_revision_id
        ):
            raise M07CalculationInputSelectionError(SAFE_SELECTION_MESSAGE)
        if selection.field_code in selections:
            raise M07CalculationInputSelectionError(SAFE_SELECTION_MESSAGE)
        selections[selection.field_code] = selection
    return selections


def _selected_group(
    *,
    selection: CalculationInputSelection,
    rule: CalculationInputFieldRule,
    groups: tuple[_NormalizedGroup, ...],
    identity_fields: dict[str, str],
) -> _NormalizedGroup | None:
    if selection.candidate_identity is not None:
        selected_field = identity_fields.get(selection.candidate_identity)
        if selected_field is not None and selected_field != selection.field_code:
            raise M07CalculationInputSelectionError(SAFE_SELECTION_MESSAGE)
        return next(
            (
                group
                for group in groups
                if selection.candidate_identity in group.identities
            ),
            None,
        )
    try:
        normalized_selection = rule.normalize(
            selection.selected_normalized_value
        )
    except M07CalculationInputNormalizationError:
        return None
    key = canonical_m07_json(normalized_selection)
    return next(
        (
            group
            for group in groups
            if canonical_m07_json(group.normalized_value) == key
        ),
        None,
    )


def _ambiguous_field(
    field_code: str, groups: tuple[_NormalizedGroup, ...]
) -> AmbiguousInputField:
    return AmbiguousInputField(
        field_code=field_code,
        candidates=[
            AmbiguousInputCandidate(
                normalized_value=group.normalized_value,
                candidate_identities=list(group.identities),
                source_references=group.source_references,
            )
            for group in groups
        ],
    )


def resolve_calculation_inputs(
    *,
    db_session: Session,
    client_id: int,
    request: CalculationInputResolutionRequest,
    manifest_registry: CalculationInputManifestRegistry = (
        M07_CALCULATION_INPUT_MANIFEST_REGISTRY
    ),
) -> CalculationInputResolutionResult:
    manifest = manifest_registry.resolve(
        calculation_scope=request.calculation_scope,
        manifest_version=request.manifest_version,
    )
    _load_revision(
        db_session=db_session,
        client_id=client_id,
        revision_id=request.b1_evidence_revision_id,
    )
    rules = {rule.field_code: rule for rule in manifest.fields}
    candidates = _load_candidates(
        db_session=db_session,
        client_id=client_id,
        revision_id=request.b1_evidence_revision_id,
        field_codes=set(rules),
    )
    by_field: dict[str, list[_Candidate]] = {field_code: [] for field_code in rules}
    identity_fields: dict[str, str] = {}
    for candidate in candidates:
        by_field[candidate.field_code].append(candidate)
        identity_fields[candidate.identity] = candidate.field_code
    groups_by_field = {
        field_code: _normalize_groups(
            rule=rule,
            candidates=by_field[field_code],
        )
        for field_code, rule in rules.items()
    }
    normalized_candidates = {
        field_code: tuple(
            group.normalized_value for group in groups_by_field[field_code]
        )
        for field_code in rules
    }
    selections = _selection_by_field(
        request=request,
        manifest_field_codes=set(rules),
    )

    selected_values: dict[str, Any] = {}
    source_references: dict[
        str, list[CalculationInputSourceReference]
    ] = {}
    missing_fields: list[str] = []
    ambiguous_fields: list[AmbiguousInputField] = []
    for field_code in sorted(rules):
        rule = rules[field_code]
        if not rule.is_required(normalized_candidates):
            continue
        groups = groups_by_field[field_code]
        selection = selections.get(field_code)
        if not groups:
            missing_fields.append(field_code)
            continue
        if selection is not None:
            selected = _selected_group(
                selection=selection,
                rule=rule,
                groups=groups,
                identity_fields=identity_fields,
            )
            if selected is None:
                ambiguous_fields.append(_ambiguous_field(field_code, groups))
                continue
            selected_values[field_code] = selected.normalized_value
            source_references[field_code] = selected.source_references
            continue
        if len(groups) == 1:
            selected_values[field_code] = groups[0].normalized_value
            source_references[field_code] = groups[0].source_references
            continue
        ambiguous_fields.append(_ambiguous_field(field_code, groups))

    if missing_fields:
        outcome = "missing_inputs"
    elif ambiguous_fields:
        outcome = "ambiguous_inputs"
    else:
        outcome = "resolved"
    material_result = {
        "client_id": client_id,
        "calculation_scope": manifest.calculation_scope,
        "manifest_version": manifest.manifest_version,
        "b1_evidence_revision_id": request.b1_evidence_revision_id,
        "normalized_selected_values": selected_values,
        "source_references": {
            field_code: [
                reference.model_dump(mode="python")
                for reference in references
            ]
            for field_code, references in sorted(source_references.items())
        },
        "missing_fields": sorted(missing_fields),
        "ambiguous_fields": [
            field.model_dump(mode="python")
            for field in sorted(
                ambiguous_fields, key=lambda item: item.field_code
            )
        ],
        "outcome": outcome,
    }
    canonical_result = canonicalize_m07_value(material_result)
    fingerprint = m07_fingerprint(canonical_result)
    calculation_payload = None
    if outcome == "resolved":
        calculation_payload = CalculationReadyInputPayload(
            client_id=client_id,
            calculation_scope=manifest.calculation_scope,
            manifest_version=manifest.manifest_version,
            b1_evidence_revision_id=request.b1_evidence_revision_id,
            normalized_selected_values=selected_values,
            source_references=source_references,
            resolution_fingerprint=fingerprint,
        )
    return CalculationInputResolutionResult(
        client_id=client_id,
        calculation_scope=manifest.calculation_scope,
        manifest_version=manifest.manifest_version,
        b1_evidence_revision_id=request.b1_evidence_revision_id,
        normalized_selected_values=selected_values,
        source_references=source_references,
        missing_fields=sorted(missing_fields),
        ambiguous_fields=sorted(
            ambiguous_fields, key=lambda item: item.field_code
        ),
        outcome=outcome,
        canonical_result=canonical_result,
        fingerprint=fingerprint,
        calculation_payload=calculation_payload,
    )
