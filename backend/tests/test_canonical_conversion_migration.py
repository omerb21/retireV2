"""Real PostgreSQL exact-money widening, with transactional downgrade guards."""
import os
from pathlib import Path
import subprocess
import sys
from decimal import Decimal

from sqlalchemy import create_engine, text, select
from sqlalchemy.orm import Session

from test_recovery_migration_postgresql import postgres_url
from test_canonical_component_conversion import seeded, request
from app.models.retirement_facts import CapitalAsset
from app.db.base import load_all_models
from app.services.canonical_component_conversion_service import execute

BACKEND = Path(__file__).resolve().parents[1]
REVISION = "f5a1c8d4e632"


def migrate(url, action, target, success=True):
    result = subprocess.run([sys.executable, "-m", "alembic", action, target], cwd=BACKEND,
        env=dict(os.environ, DATABASE_URL=url, PYTHONIOENCODING="utf-8"), capture_output=True, text=True, encoding="utf-8")
    assert (result.returncode == 0) == success, result.stdout + result.stderr
    return result.stdout + result.stderr


def test_postgresql_exact_capital_upgrade_and_fail_closed_downgrade(postgres_url):
    load_all_models()
    migrate(postgres_url, "upgrade", "e4f0b7c3d521")
    engine = create_engine(postgres_url)
    try:
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO clients (client_id,display_name,id_number) VALUES (1,'test','123456789')"))
            connection.execute(text("INSERT INTO capital_asset (client_id,asset_category,asset_description,known_value_amount,value_as_of_date) VALUES (1,'other','legacy',999999999999.99,'2026-01-01')"))
        migrate(postgres_url, "upgrade", REVISION)
        with engine.connect() as connection:
            assert connection.execute(text("SELECT known_value_amount FROM capital_asset")).scalar_one() == Decimal("999999999999.99")
            assert connection.execute(text("SELECT numeric_precision,numeric_scale FROM information_schema.columns WHERE table_name='capital_asset' AND column_name='known_value_amount'")).one() == (20, 2)
        migrate(postgres_url, "downgrade", "e4f0b7c3d521")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT known_value_amount FROM capital_asset")).scalar_one() == Decimal("999999999999.99")
        migrate(postgres_url, "upgrade", REVISION)
        with Session(engine) as db, db.begin():
            asset = db.scalar(select(CapitalAsset))
            assert asset.origin_kind == "manual"
            asset.known_value_amount = Decimal("123.45")
        with Session(engine) as db, db.begin():
            asset = db.scalar(select(CapitalAsset))
            assert asset.known_value_amount == Decimal("123.45")
            asset.known_value_amount = Decimal("999999999999999999.99")
        failure = migrate(postgres_url, "downgrade", "e4f0b7c3d521", success=False)
        assert "CAPITAL_ASSET_DOWNGRADE_PRECISION_LOSS" in failure
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == REVISION
            assert connection.execute(text("SELECT known_value_amount FROM capital_asset")).scalar_one() == Decimal("999999999999999999.99")
        source = seeded(engine, balance="999999999999999999.99")
        with Session(engine) as db, db.begin():
            result = execute(db, 1, request(source, amount=None), "test")
        with Session(engine) as db:
            asset = db.get(CapitalAsset, result["conversions"][0]["destination_id"])
            assert asset.known_value_amount == Decimal("999999999999999999.99")
            assert asset.origin_kind == "canonical_component_conversion"
    finally:
        engine.dispose()
