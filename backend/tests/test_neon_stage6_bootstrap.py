"""Safety guards for the dedicated Neon Stage 6 schema bootstrap."""
import pytest

from scripts.neon_stage6_bootstrap import validate_url


VALID = (
    "postgresql+psycopg2://migration-user:secret@"
    "ep-raspy-mouse-b90m3k25.c-7.eu-central-1.aws.neon.tech/"
    "retire_v2_stage6_validation?sslmode=require"
)


def test_neon_direct_pg16_url_is_allowed():
    assert validate_url(VALID) == VALID


@pytest.mark.parametrize("unsafe_url", [
    "postgresql://user:password@dpg-dbgqtbec6qcc73cdo640-a.frankfurt-postgres.render.com/"
    "retire_v2_stage6_validation?sslmode=require",
    "postgresql://user:password@ep-raspy-mouse-b90m3k25.c-7.eu-central-1.aws.neon.tech/"
    "retire_v2_production?sslmode=require",
    "postgresql://user:password@ep-raspy-mouse-b90m3k25-pooler.c-7.eu-central-1.aws.neon.tech/"
    "retire_v2_stage6_validation?sslmode=require",
    "postgresql://user:password@ep-raspy-mouse-b90m3k25.c-7.eu-central-1.aws.neon.tech/"
    "retire_v2_stage6_validation",
    "postgresql://user:password@ep-raspy-mouse-b90m3k25.c-7.eu-central-1.aws.neon.tech/"
    "retire_v2_stage6_validation?sslmode=disable",
    "sqlite:///retire_v2_stage6_validation",
])
def test_unsafe_database_targets_are_rejected_without_exposing_secret(unsafe_url):
    with pytest.raises(RuntimeError) as excinfo:
        validate_url(unsafe_url)
    assert "password" not in str(excinfo.value)
    assert "secret" not in str(excinfo.value)


def test_neon_url_requires_an_authenticated_user():
    with pytest.raises(RuntimeError, match="credentials"):
        validate_url(
            "postgresql://ep-raspy-mouse-b90m3k25.c-7.eu-central-1.aws.neon.tech/"
            "retire_v2_stage6_validation?sslmode=require"
        )
