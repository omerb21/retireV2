from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Callable, Literal, Mapping


TechnicalType = Literal["string", "decimal", "date", "enum", "identifier"]
NormalizationRule = Literal[
    "trimmed_string",
    "canonical_decimal",
    "iso_date",
    "enum_exact",
    "structured_identifier",
]
NormalizedCandidates = Mapping[str, tuple[Any, ...]]


class M07CalculationInputManifestError(LookupError):
    code = "calculation_input_manifest_unsupported"


class M07CalculationInputNormalizationError(ValueError):
    pass


@dataclass(frozen=True)
class CalculationInputFieldRule:
    field_code: str
    technical_type: TechnicalType
    normalization_rule: NormalizationRule
    nullable: bool = False
    enum_values: tuple[str, ...] = ()
    identifier_pattern: str | None = None
    condition_id: str | None = None
    required_when: Callable[[NormalizedCandidates], bool] | None = None
    constraint_id: str | None = None
    constraint: Callable[[Any], bool] | None = None

    def __post_init__(self) -> None:
        if not self.field_code.strip():
            raise ValueError("manifest field code must not be blank")
        compatible = {
            "string": "trimmed_string",
            "decimal": "canonical_decimal",
            "date": "iso_date",
            "enum": "enum_exact",
            "identifier": "structured_identifier",
        }
        if compatible[self.technical_type] != self.normalization_rule:
            raise ValueError("technical type and normalization rule do not match")
        if self.technical_type == "enum" and not self.enum_values:
            raise ValueError("enum fields require supported values")
        if self.technical_type != "enum" and self.enum_values:
            raise ValueError("enum values are supported only for enum fields")
        if self.technical_type == "identifier" and not self.identifier_pattern:
            raise ValueError("identifier fields require an explicit structure")
        if self.technical_type != "identifier" and self.identifier_pattern:
            raise ValueError("identifier structure is supported only for identifiers")
        if (self.condition_id is None) != (self.required_when is None):
            raise ValueError("conditional requirements need an ID and predicate")
        if (self.constraint_id is None) != (self.constraint is None):
            raise ValueError("calculation constraints need an ID and predicate")

    def is_required(self, candidates: NormalizedCandidates) -> bool:
        return self.required_when(candidates) if self.required_when else True

    def normalize(self, value: Any) -> Any:
        if value is None:
            if self.nullable:
                return None
            raise M07CalculationInputNormalizationError("null is not allowed")
        if self.normalization_rule == "trimmed_string":
            if not isinstance(value, str) or not value.strip():
                raise M07CalculationInputNormalizationError(
                    "value is not a non-blank string"
                )
            normalized: Any = value.strip()
        elif self.normalization_rule == "canonical_decimal":
            if isinstance(value, bool):
                raise M07CalculationInputNormalizationError(
                    "boolean is not a number"
                )
            try:
                decimal_value = Decimal(str(value))
            except (InvalidOperation, ValueError):
                raise M07CalculationInputNormalizationError(
                    "value is not a parseable number"
                ) from None
            if not decimal_value.is_finite():
                raise M07CalculationInputNormalizationError(
                    "number must be finite"
                )
            rendered = format(decimal_value, "f")
            if "." in rendered:
                rendered = rendered.rstrip("0").rstrip(".")
            normalized = "0" if rendered in {"", "-0"} else rendered
        elif self.normalization_rule == "iso_date":
            if isinstance(value, date):
                normalized = value.isoformat()
            elif isinstance(value, str):
                try:
                    normalized = date.fromisoformat(value).isoformat()
                except ValueError:
                    raise M07CalculationInputNormalizationError(
                        "value is not an ISO date"
                    ) from None
            else:
                raise M07CalculationInputNormalizationError(
                    "value is not a parseable date"
                )
        elif self.normalization_rule == "enum_exact":
            if not isinstance(value, str) or value not in self.enum_values:
                raise M07CalculationInputNormalizationError(
                    "value is not a supported enum member"
                )
            normalized = value
        else:
            if not isinstance(value, str) or re.fullmatch(
                self.identifier_pattern or "", value
            ) is None:
                raise M07CalculationInputNormalizationError(
                    "value does not match the required identifier structure"
                )
            normalized = value
        if self.constraint is not None and not self.constraint(normalized):
            raise M07CalculationInputNormalizationError(
                f"value violates calculation constraint {self.constraint_id}"
            )
        return normalized


@dataclass(frozen=True)
class CalculationInputManifest:
    calculation_scope: str
    manifest_version: str
    fields: tuple[CalculationInputFieldRule, ...]

    def __post_init__(self) -> None:
        if not self.calculation_scope.strip() or not self.manifest_version.strip():
            raise ValueError("manifest scope and version must not be blank")
        if not self.fields:
            raise ValueError("calculation-input manifest must contain fields")
        field_codes = [field.field_code for field in self.fields]
        if len(field_codes) != len(set(field_codes)):
            raise ValueError("manifest field codes must be unique")


class CalculationInputManifestRegistry:
    def __init__(
        self, manifests: tuple[CalculationInputManifest, ...] = ()
    ) -> None:
        self._manifests = {
            (manifest.calculation_scope, manifest.manifest_version): manifest
            for manifest in manifests
        }
        if len(self._manifests) != len(manifests):
            raise ValueError("manifest scope/version pairs must be unique")

    def resolve(
        self, *, calculation_scope: str, manifest_version: str
    ) -> CalculationInputManifest:
        manifest = self._manifests.get((calculation_scope, manifest_version))
        if manifest is None:
            raise M07CalculationInputManifestError(
                "calculation-input manifest is unsupported"
            )
        return manifest


M08A_FIXATION_CALCULATION_SCOPE = "m08a_fixation"
M08A_FIXATION_MANIFEST_VERSION = "1"
M08A_FIXATION_CALCULATION_INPUT_MANIFEST = CalculationInputManifest(
    calculation_scope=M08A_FIXATION_CALCULATION_SCOPE,
    manifest_version=M08A_FIXATION_MANIFEST_VERSION,
    fields=(
        CalculationInputFieldRule(
            field_code="eligibility_date",
            technical_type="date",
            normalization_rule="iso_date",
            nullable=False,
        ),
    ),
)

M07_CALCULATION_INPUT_MANIFEST_REGISTRY = CalculationInputManifestRegistry(
    manifests=(M08A_FIXATION_CALCULATION_INPUT_MANIFEST,)
)
