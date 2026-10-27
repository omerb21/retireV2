"""Stage 6 P1B migration/readiness and append-only DDL contract."""
import importlib.util
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.main import EXPECTED_ALEMBIC_HEAD


MIGRATION = "d6f1a9c3b704_stage6_pension_factor_admissions.py"


def test_single_head_and_readiness_are_stage6_p1b():
    base = Path(__file__).resolve().parents[1]
    config = Config()
    config.set_main_option("script_location", str(base / "alembic"))
    scripts = ScriptDirectory.from_config(config)
    assert scripts.get_heads() == ["d6f1a9c3b704"]
    assert EXPECTED_ALEMBIC_HEAD == "d6f1a9c3b704"
    assert scripts.get_revision("d6f1a9c3b704").down_revision == "c5e019a47d62"


def test_migration_has_exact_append_only_and_minimum_privilege_contract():
    path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / MIGRATION
    source = path.read_text(encoding="utf-8")
    assert "BEFORE UPDATE OR DELETE" in source
    assert "ERRCODE = 'P7501'" in source
    assert "CONSTRAINT = 'ck_s6_factor_admission_immutable'" in source
    assert "REVOKE ALL PRIVILEGES ON TABLE" in source
    assert "GRANT SELECT, INSERT ON TABLE" in source
    assert "GRANT UPDATE" not in source
    assert "GRANT DELETE" not in source


def test_migration_identity_is_linear():
    path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / MIGRATION
    spec = importlib.util.spec_from_file_location("stage6_p1b_migration", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    assert module.revision == "d6f1a9c3b704"
    assert module.down_revision == "c5e019a47d62"
