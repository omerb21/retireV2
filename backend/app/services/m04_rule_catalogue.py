from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from app.models.m04_classification import M04_CATALOGUE_VERSION


@dataclass(frozen=True)
class ExactRule:
    rule_id: str
    matcher_type: str
    exact_matcher_value: str
    scope: str
    output_product_family: str | None
    output_component_kind: str | None
    output_interpretation: str | None
    rationale: str
    authority_reference: str
    conflict_behavior: str = "unresolved"

    def evidence(self) -> dict[str, Any]:
        return {"catalogue_version": M04_CATALOGUE_VERSION, **asdict(self)}


def _asset_rule(product_family: str) -> ExactRule:
    return ExactRule(
        rule_id=f"m04.asset.product-type.{product_family}",
        matcher_type="declared_product_type_exact",
        exact_matcher_value=product_family,
        scope="asset",
        output_product_family=product_family,
        output_component_kind=None,
        output_interpretation=None,
        rationale="The persisted declared product type exactly equals a bounded accepted family token.",
        authority_reference="PKG_009_FINAL_PACKAGE_DEFINITION.md section 5.1",
    )


CATALOGUE: tuple[ExactRule, ...] = (
    *tuple(
        _asset_rule(family)
        for family in (
            "insurance_policy",
            "savings_policy",
            "provident_fund",
            "investment_provident_fund",
            "education_fund",
            "pension_fund",
        )
    ),
    ExactRule(
        rule_id="m04.component.label.contribution-hebrew",
        matcher_type="component_label_exact",
        exact_matcher_value="תגמולים",
        scope="component",
        output_product_family=None,
        output_component_kind="contribution_component",
        output_interpretation=None,
        rationale="The accepted component contract explicitly states that contribution_component represents תגמולים.",
        authority_reference="PKG_009_FINAL_PACKAGE_DEFINITION.md section 5.2",
    ),
    ExactRule(
        rule_id="m04.component.token.contribution",
        matcher_type="component_code_exact",
        exact_matcher_value="contribution_component",
        scope="component",
        output_product_family=None,
        output_component_kind="contribution_component",
        output_interpretation=None,
        rationale="The persisted code exactly equals the accepted bounded component token.",
        authority_reference="PKG_009_FINAL_PACKAGE_DEFINITION.md section 5.2",
    ),
    ExactRule(
        rule_id="m04.component.token.severance",
        matcher_type="component_code_exact",
        exact_matcher_value="severance_component",
        scope="component",
        output_product_family=None,
        output_component_kind="severance_component",
        output_interpretation=None,
        rationale="The persisted code exactly equals the accepted bounded component token.",
        authority_reference="PKG_009_FINAL_PACKAGE_DEFINITION.md section 5.2",
    ),
)


def _matches(rule: ExactRule, snapshot: dict[str, Any], component: dict[str, Any] | None) -> bool:
    if rule.matcher_type == "declared_product_type_exact":
        return snapshot.get("declared_product_type") == rule.exact_matcher_value
    if component is None:
        return False
    if rule.matcher_type == "component_label_exact":
        return component.get("original_label") == rule.exact_matcher_value
    if rule.matcher_type == "component_code_exact":
        return component.get("original_code") == rule.exact_matcher_value
    if rule.matcher_type == "product_identifier_exact":
        return snapshot.get("product_identifier") == rule.exact_matcher_value
    return False


def evaluate_exact_catalogue(
    snapshot: dict[str, Any],
    *,
    catalogue: Iterable[ExactRule] = CATALOGUE,
) -> dict[str, Any]:
    rules = tuple(catalogue)
    asset_matches = [
        rule for rule in rules if rule.scope == "asset" and _matches(rule, snapshot, None)
    ]
    asset_outputs = {
        rule.output_product_family
        for rule in asset_matches
        if rule.output_product_family is not None
    }
    conflicts: list[str] = []
    unresolved_reasons: list[str] = []
    if len(asset_outputs) > 1:
        conflicts.append("conflicting_exact_asset_rules")
        product_family = "unknown_or_unresolved"
    elif asset_outputs:
        product_family = next(iter(asset_outputs))
    else:
        product_family = "unknown_or_unresolved"
        unresolved_reasons.append("no_exact_asset_rule")

    component_results: list[dict[str, Any]] = []
    all_evidence = [rule.evidence() for rule in asset_matches]
    for component in snapshot.get("components", []):
        matches = [
            rule
            for rule in rules
            if rule.scope == "component" and _matches(rule, snapshot, component)
        ]
        outputs = {
            rule.output_component_kind
            for rule in matches
            if rule.output_component_kind is not None
        }
        if len(outputs) > 1:
            conflicts.append(
                f"conflicting_exact_component_rules:{component['evidence_identity']}"
            )
            component_kind = "unknown_component"
        elif outputs:
            component_kind = next(iter(outputs))
        else:
            component_kind = "unknown_component"
            unresolved_reasons.append(
                f"no_exact_component_rule:{component['evidence_identity']}"
            )
        evidence = [rule.evidence() for rule in matches]
        all_evidence.extend(evidence)
        component_results.append(
            {
                "evidence_identity": component["evidence_identity"],
                "original_label": component.get("original_label"),
                "original_code": component.get("original_code"),
                "component_kind": component_kind,
                "interpretation": "unresolved",
                "matched_rule_evidence": evidence,
                "explanation": (
                    "Exact component rule matched; pension/capital interpretation "
                    "remains unresolved."
                    if matches and len(outputs) == 1
                    else "No single approved exact component rule resolved this component."
                ),
                "current_employer_related": component.get(
                    "current_employer_related", "unknown"
                ),
            }
        )

    if not component_results:
        unresolved_reasons.append("no_structured_components")
    else:
        unresolved_reasons.append("component_interpretation_unresolved")
    if snapshot.get("target_kind") == "source_evidence_review" and not any(
        (
            snapshot.get("declared_provider_name"),
            snapshot.get("product_name"),
            snapshot.get("declared_product_type"),
            snapshot.get("product_identifier"),
            snapshot.get("components"),
        )
    ):
        unresolved_reasons.append("opaque_uploaded_facts_unavailable")

    return {
        "catalogue_version": M04_CATALOGUE_VERSION,
        "product_family": product_family,
        "aggregate_interpretation": "unresolved",
        "components": component_results,
        "matched_rule_evidence": all_evidence,
        "conflicts": list(dict.fromkeys(conflicts)),
        "unresolved_reasons": list(dict.fromkeys(unresolved_reasons)),
    }
