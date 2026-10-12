from pathlib import Path
import re


def test_rtdir_limiter_migration_is_single_additive_child_with_exact_contract():
    path = Path(__file__).parents[1] / "alembic" / "versions" / "b3c9d6f2a410_rtdir_login_rate_limit.py"
    source = path.read_text(encoding="utf-8")
    assert 'revision = "b3c9d6f2a410"' in source
    assert 'down_revision = "a2b8c5e1f309"' in source
    assert '"rtdir_login_rate_limit_buckets"' in source
    for name in (
        "ck_rtdir_login_bucket_key_hex", "ck_rtdir_login_bucket_kind",
        "ck_rtdir_login_failure_count", "ck_rtdir_login_lock_window",
        "ix_rtdir_login_rate_limit_buckets_updated_at",
    ):
        assert name in source
    for forbidden in (
        "retirement_monthly_income_target_elections", "planning_input_decisions",
        "canonical_pension", "capital_assets",
    ):
        assert forbidden not in source


def test_accepted_obligation_and_producer_inventories_are_exact_and_traced():
    root = Path(__file__).resolve().parents[2]
    definition = (root / "specs/runtime/RETIREMENT_TARGET_DATE_INCOME_READINESS_VERTICAL_SLICE_DEFINITION.md").read_text(encoding="utf-8")
    evidence = (root / "specs/runtime/RTDIR_IMPLEMENTATION_EVIDENCE.md").read_text(encoding="utf-8")
    for prefix, count in (("AC", 45), ("NAC", 28), ("SC", 16)):
        identifiers = {int(value) for value in re.findall(rf"\| `{prefix}-(\d{{3}})` \|", definition)}
        assert identifiers == set(range(1, count + 1))
        assert f"`{prefix}-001..{prefix}-{count:03d}`" in evidence
    assert "97 observations" in evidence
    assert all(fragment in evidence for fragment in (
        "18 Planning Input", "29 RIT", "30 reached", "20 RTICB",
        "73 route-reached and 24 preempted",
    ))
