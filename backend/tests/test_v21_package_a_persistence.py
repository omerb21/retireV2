from __future__ import annotations

import os
import subprocess
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import load_all_models
from app.models.client import Client
from app.models.missing_data_item import MissingDataItem
from app.models.retirement_fact_contracts import (
    ADVISORY_STATUSES,
    AMOUNT_BASES,
    ASSUMPTION_CATEGORIES,
    ASSUMPTION_OWNERS,
    CAPITAL_ASSET_CATEGORIES,
    CONTINUATION_STATUSES,
    EXPENSE_CATEGORIES,
    EXPENSE_TYPES,
    FREQUENCIES,
    INCOME_CATEGORIES,
    LIFECYCLE_STATUSES,
    PENSION_PRODUCT_TYPES,
    PLANNING_DOMAINS,
    SOURCE_STATUSES,
    TIMING_CONFIDENCES,
    VERIFICATION_STATES,
    WORK_AFTER_RETIREMENT_INTENTIONS,
)
from app.models.retirement_facts import (
    CapitalAsset,
    PensionHolding,
    PlannerAssumption,
    RecurringExpense,
    RecurringIncome,
    RetirementTimingWorkIntention,
)

load_all_models()


APPROVED_FACT_TABLES = {
    "pension_holding",
    "capital_asset",
    "recurring_income",
    "recurring_expense",
    "retirement_timing_work_intention",
    "planner_assumption",
}
MISSING_EXTENSION_FIELDS = {
    "planning_domain",
    "related_record_type",
    "related_record_id",
    "advisory_status",
    "neutral_reason",
}
ALLOWED_V21_FACT_MIGRATIONS = {
    "d1f4a8c2e9b0_v21_package_a_retirement_facts_foundation.py",
    "e2a7c9d4f1b3_v21_package_a_missing_data_extension.py",
}


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _upgrade_sqlite_database(db_path: Path) -> str:
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=_backend_root(),
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout + result.stderr


def _client(client_id: int = 1) -> Client:
    return Client(
        client_id=client_id,
        display_name=f"Client {client_id}",
        id_number=f"V21-{client_id}",
        birth_date=date(1970, 1, 1),
        status="active",
    )


def _commit_client(session: Session, client_id: int = 1) -> None:
    session.add(_client(client_id))
    session.commit()


def _constraint_sql(inspector, table_name: str) -> str:
    return " ".join(
        constraint["sqltext"] or ""
        for constraint in inspector.get_check_constraints(table_name)
    )


def _assert_value_set(inspector, table_name: str, column_name: str, values: tuple[str, ...]) -> None:
    sql = _constraint_sql(inspector, table_name)
    assert column_name in sql
    for value in values:
        assert f"'{value}'" in sql


def test_package_a_tables_models_and_relationships_exist(tmp_path: Path) -> None:
    db_path = tmp_path / "v21_package_a_tables.db"
    _upgrade_sqlite_database(db_path)

    inspector = inspect(create_engine(f"sqlite:///{db_path.as_posix()}"))
    tables = set(inspector.get_table_names())
    assert APPROVED_FACT_TABLES.issubset(tables)
    assert "fact_record" not in tables
    assert "generic_fact_record" not in tables

    assert PensionHolding.__tablename__ == "pension_holding"
    assert CapitalAsset.__tablename__ == "capital_asset"
    assert RecurringIncome.__tablename__ == "recurring_income"
    assert RecurringExpense.__tablename__ == "recurring_expense"
    assert RetirementTimingWorkIntention.__tablename__ == "retirement_timing_work_intention"
    assert PlannerAssumption.__tablename__ == "planner_assumption"

    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    with Session(engine) as session:
        _commit_client(session)
        session.add_all(
            [
                PensionHolding(
                    client_id=1,
                    provider_name="Provider",
                    product_type="pension fund",
                ),
                CapitalAsset(
                    client_id=1,
                    asset_category="bank deposit",
                    asset_description="Deposit",
                ),
                RecurringIncome(
                    client_id=1,
                    income_category="employment",
                    description="Salary",
                    amount=Decimal("100.00"),
                    amount_basis="gross",
                    frequency="monthly",
                    continuation_status="ongoing",
                ),
                RecurringExpense(
                    client_id=1,
                    expense_category="housing",
                    description="Rent",
                    amount=Decimal("50.00"),
                    frequency="monthly",
                    expense_type="mandatory",
                    continuation_status="ongoing",
                ),
                RetirementTimingWorkIntention(
                    client_id=1,
                    timing_confidence="known",
                    work_after_retirement_intention="stop working",
                ),
                PlannerAssumption(
                    client_id=1,
                    assumption_category="income",
                    title="Assumption",
                    assumption_value_text="Value",
                    rationale="Rationale",
                    owner="planner",
                ),
            ]
        )
        session.commit()

        client = session.get(Client, 1)
        assert client is not None
        assert len(client.pension_holdings) == 1
        assert len(client.capital_assets) == 1
        assert len(client.recurring_incomes) == 1
        assert len(client.recurring_expenses) == 1
        assert len(client.retirement_timing_work_intentions) == 1
        assert len(client.planner_assumptions) == 1


@pytest.mark.parametrize(
    ("model", "kwargs"),
    [
        (PensionHolding, {"provider_name": "Provider", "product_type": "pension fund"}),
        (CapitalAsset, {"asset_category": "bank deposit", "asset_description": "Deposit"}),
        (
            RecurringIncome,
            {
                "income_category": "employment",
                "description": "Salary",
                "amount": Decimal("100.00"),
                "amount_basis": "gross",
                "frequency": "monthly",
                "continuation_status": "ongoing",
            },
        ),
        (
            RecurringExpense,
            {
                "expense_category": "housing",
                "description": "Rent",
                "amount": Decimal("50.00"),
                "frequency": "monthly",
                "expense_type": "mandatory",
                "continuation_status": "ongoing",
            },
        ),
        (
            RetirementTimingWorkIntention,
            {
                "timing_confidence": "known",
                "work_after_retirement_intention": "stop working",
            },
        ),
        (
            PlannerAssumption,
            {
                "assumption_category": "income",
                "title": "Assumption",
                "assumption_value_text": "Value",
                "rationale": "Rationale",
                "owner": "planner",
            },
        ),
    ],
)
def test_package_a_fact_records_require_client_id(tmp_path: Path, model, kwargs: dict) -> None:
    db_path = tmp_path / f"{model.__tablename__}_client_required.db"
    _upgrade_sqlite_database(db_path)
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    with Session(engine) as session:
        session.add(model(**kwargs))
        with pytest.raises(IntegrityError):
            session.commit()


def test_package_a_defaults_and_check_contracts(tmp_path: Path) -> None:
    db_path = tmp_path / "v21_package_a_defaults.db"
    _upgrade_sqlite_database(db_path)
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    inspector = inspect(engine)

    for table_name in APPROVED_FACT_TABLES - {"planner_assumption"}:
        _assert_value_set(inspector, table_name, "lifecycle_status", LIFECYCLE_STATUSES)
        _assert_value_set(inspector, table_name, "source_status", SOURCE_STATUSES)
        _assert_value_set(inspector, table_name, "verification_state", VERIFICATION_STATES)

    _assert_value_set(inspector, "pension_holding", "product_type", PENSION_PRODUCT_TYPES)
    _assert_value_set(inspector, "capital_asset", "asset_category", CAPITAL_ASSET_CATEGORIES)
    _assert_value_set(inspector, "recurring_income", "income_category", INCOME_CATEGORIES)
    _assert_value_set(inspector, "recurring_income", "amount_basis", AMOUNT_BASES)
    _assert_value_set(inspector, "recurring_income", "frequency", FREQUENCIES)
    _assert_value_set(inspector, "recurring_income", "continuation_status", CONTINUATION_STATUSES)
    _assert_value_set(inspector, "recurring_expense", "expense_category", EXPENSE_CATEGORIES)
    _assert_value_set(inspector, "recurring_expense", "frequency", FREQUENCIES)
    _assert_value_set(inspector, "recurring_expense", "expense_type", EXPENSE_TYPES)
    _assert_value_set(inspector, "recurring_expense", "continuation_status", CONTINUATION_STATUSES)
    _assert_value_set(
        inspector, "retirement_timing_work_intention", "timing_confidence", TIMING_CONFIDENCES
    )
    _assert_value_set(
        inspector,
        "retirement_timing_work_intention",
        "work_after_retirement_intention",
        WORK_AFTER_RETIREMENT_INTENTIONS,
    )
    _assert_value_set(inspector, "planner_assumption", "lifecycle_status", LIFECYCLE_STATUSES)
    _assert_value_set(
        inspector, "planner_assumption", "assumption_category", ASSUMPTION_CATEGORIES
    )
    _assert_value_set(inspector, "planner_assumption", "owner", ASSUMPTION_OWNERS)

    with Session(engine) as session:
        _commit_client(session)
        pension = PensionHolding(
            client_id=1,
            provider_name="Provider",
            product_type="provident fund",
        )
        assumption = PlannerAssumption(
            client_id=1,
            assumption_category="expense",
            title="Assumption",
            assumption_value_text="Value",
            rationale="Rationale",
            owner="planner",
        )
        session.add_all([pension, assumption])
        session.commit()

        assert pension.lifecycle_status == "current"
        assert pension.source_status == "not recorded"
        assert pension.verification_state == "collected - not yet reviewed"
        assert assumption.lifecycle_status == "current"


def test_package_a_field_validation_rules(tmp_path: Path) -> None:
    db_path = tmp_path / "v21_package_a_field_rules.db"
    _upgrade_sqlite_database(db_path)
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    with Session(engine) as session:
        _commit_client(session)
        session.add(
            PensionHolding(
                client_id=1,
                provider_name="Provider",
                product_type="pension fund",
                known_balance_amount=Decimal("1000.00"),
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        session.add(
            PensionHolding(
                client_id=1,
                provider_name="Provider",
                product_type="pension fund",
                known_monthly_pension_amount=Decimal("100.00"),
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        session.add(
            CapitalAsset(
                client_id=1,
                asset_category="securities",
                asset_description="Portfolio",
                known_value_amount=Decimal("1000.00"),
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        session.add(
            RetirementTimingWorkIntention(
                client_id=1,
                timing_confidence="known",
                work_after_retirement_intention="undecided",
                other_known_retirement_date=date(2030, 1, 1),
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_planner_assumptions_are_separate_from_fact_source_context() -> None:
    columns = set(PlannerAssumption.__table__.columns.keys())
    assert {"source_status", "verification_state", "source_type", "source_date", "source_note"}.isdisjoint(
        columns
    )
    assert {"calculation_id", "readiness_status", "recommendation"}.isdisjoint(columns)
    assert {"owner", "rationale", "assumption_value_text"}.issubset(columns)


def test_missing_data_v21_extension_is_nullable_and_legacy_compatible(tmp_path: Path) -> None:
    db_path = tmp_path / "v21_missing_data_legacy.db"
    _upgrade_sqlite_database(db_path)
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    inspector = inspect(engine)
    columns = {column["name"]: column for column in inspector.get_columns("missing_data_items")}

    assert MISSING_EXTENSION_FIELDS.issubset(columns)
    for field_name in MISSING_EXTENSION_FIELDS:
        assert columns[field_name]["nullable"] is True
        assert columns[field_name]["default"] is None

    assert set(PLANNING_DOMAINS) == {
        "pension holdings",
        "capital assets",
        "recurring income",
        "recurring expenses",
        "retirement timing",
        "work intention",
        "planner assumptions",
        "other",
    }
    assert set(ADVISORY_STATUSES) == {"open", "resolved", "no longer relevant"}

    with Session(engine) as session:
        _commit_client(session)
        legacy_item = MissingDataItem(
            missing_data_item_id="MD-LEGACY",
            client_id=1,
            missing_item_type="legacy",
            missing_item_label="Legacy item",
            missing_status="missing",
        )
        domain_level_item = MissingDataItem(
            missing_data_item_id="MD-DOMAIN",
            client_id=1,
            missing_item_type="v21",
            missing_item_label="Domain item",
            missing_status="missing",
            planning_domain="pension holdings",
            advisory_status=None,
            related_record_type=None,
            related_record_id=None,
            neutral_reason=None,
        )
        session.add_all([legacy_item, domain_level_item])
        session.commit()

        persisted_legacy = session.get(MissingDataItem, "MD-LEGACY")
        persisted_domain = session.get(MissingDataItem, "MD-DOMAIN")
        assert persisted_legacy is not None
        assert persisted_domain is not None
        assert persisted_legacy.planning_domain is None
        assert persisted_legacy.related_record_type is None
        assert persisted_legacy.related_record_id is None
        assert persisted_legacy.advisory_status is None
        assert persisted_legacy.neutral_reason is None
        assert persisted_domain.related_record_type is None
        assert persisted_domain.related_record_id is None
        assert persisted_domain.advisory_status is None


def test_existing_missing_data_rows_are_not_backfilled_or_defaulted(tmp_path: Path) -> None:
    db_path = tmp_path / "v21_missing_data_no_backfill.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    subprocess.run(
        ["alembic", "upgrade", "d1f4a8c2e9b0"],
        cwd=_backend_root(),
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    with Session(engine) as session:
        session.execute(
            text(
                """
                INSERT INTO clients (client_id, display_name, id_number, birth_date, status)
                VALUES (1, 'Client 1', 'V21-1', '1970-01-01', 'active')
                """
            )
        )
        session.execute(
            text(
                """
                INSERT INTO missing_data_items (
                    missing_data_item_id,
                    client_id,
                    missing_item_type,
                    missing_item_label,
                    missing_status
                )
                VALUES ('MD-BEFORE', 1, 'legacy', 'Legacy item', 'missing')
                """
            )
        )
        session.commit()

    subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=_backend_root(),
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    with Session(engine) as session:
        row = session.execute(
            text(
                """
                SELECT planning_domain, related_record_type, related_record_id,
                       advisory_status, neutral_reason
                FROM missing_data_items
                WHERE missing_data_item_id = 'MD-BEFORE'
                """
            )
        ).one()
        assert row == (None, None, None, None, None)


def test_package_a_migration_boundary_and_future_package_b_enforcement() -> None:
    versions_dir = _backend_root() / "alembic" / "versions"
    v21_package_a_migrations = {
        path.name
        for path in versions_dir.glob("*v21_package_a*.py")
    }
    assert v21_package_a_migrations == ALLOWED_V21_FACT_MIGRATIONS

    missing_migration = (
        versions_dir / "e2a7c9d4f1b3_v21_package_a_missing_data_extension.py"
    ).read_text(encoding="utf-8")
    assert "server_default" not in missing_migration
    assert ".execute(" not in missing_migration
    assert "UPDATE " not in missing_migration.upper()
    assert "nullable=True" in missing_migration
    assert "advisory_status = open" not in missing_migration

    # Package A deliberately permits null planning_domain/advisory_status.
    # Package B is the future API-contract layer for V2.1 creation enforcement:
    # required planning_domain and advisory_status = open for new V2.1 records.
    assert True
