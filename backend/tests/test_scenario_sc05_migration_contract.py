"""SC-05: production head and migration privilege contract (no deployment)."""
from pathlib import Path
import re

from alembic.config import Config
from alembic.script import ScriptDirectory
from app.main import EXPECTED_ALEMBIC_HEAD


def test_sc05_single_alembic_head_matches_production_readiness():
    base = Path(__file__).resolve().parents[1]
    config = Config()
    config.set_main_option("script_location", str(base / "alembic"))
    scripts = ScriptDirectory.from_config(config)
    assert scripts.get_heads() == ["d6f1a9c3b704"]
    assert EXPECTED_ALEMBIC_HEAD == scripts.get_current_head()
    assert scripts.get_revision("c5e019a47d62").down_revision == "b7c5e1a90342"
    assert scripts.get_revision("d6f1a9c3b704").down_revision == "c5e019a47d62"


def test_sc05_migrations_define_explicit_minimum_privileges():
    folder = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    rights = {
        "b7c5e1a90342_scenario_pension_elections.py": ("scenario_draft_pension_elections", "SELECT, INSERT, DELETE"),
        "c5e019a47d62_professional_coefficient_reviews.py": ("scenario_coefficient_professional_reviews", "SELECT, INSERT"),
    }
    for filename, (table, grant) in rights.items():
        source = (folder / filename).read_text(encoding="utf-8")
        assert "CRTISBA_APPLICATION_DB_ROLE" in source
        assert "REVOKE ALL PRIVILEGES ON TABLE " + table in source
        assert "GRANT " + grant + " ON TABLE " + table in source
        assert re.search(r"def downgrade\(", source)
