"""v21 package a retirement facts foundation

Revision ID: d1f4a8c2e9b0
Revises: c9d4e7f1a2b5
Create Date: 2026-06-30 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d1f4a8c2e9b0"
down_revision: Union[str, None] = "c9d4e7f1a2b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _in_values(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


LIFECYCLE_STATUSES = ("current", "superseded")
SOURCE_STATUSES = (
    "not recorded",
    "client stated",
    "planner entered",
    "external statement",
    "employer information",
    "institution information",
    "government or tax source",
    "other",
)
VERIFICATION_STATES = (
    "collected - not yet reviewed",
    "reviewed",
    "verified",
    "partially verified",
    "verification not applicable",
)


def _context_checks(table_name: str) -> list[sa.CheckConstraint]:
    return [
        sa.CheckConstraint(
            f"lifecycle_status IN ({_in_values(LIFECYCLE_STATUSES)})",
            name=f"ck_{table_name}_lifecycle_status",
        ),
        sa.CheckConstraint(
            f"source_status IN ({_in_values(SOURCE_STATUSES)})",
            name=f"ck_{table_name}_source_status",
        ),
        sa.CheckConstraint(
            f"verification_state IN ({_in_values(VERIFICATION_STATES)})",
            name=f"ck_{table_name}_verification_state",
        ),
    ]


def _context_columns() -> list[sa.Column]:
    return [
        sa.Column(
            "lifecycle_status",
            sa.String(length=32),
            server_default="current",
            nullable=False,
        ),
        sa.Column(
            "source_status",
            sa.String(length=64),
            server_default="not recorded",
            nullable=False,
        ),
        sa.Column(
            "verification_state",
            sa.String(length=64),
            server_default="collected - not yet reviewed",
            nullable=False,
        ),
    ]


def _source_columns() -> list[sa.Column]:
    return [
        sa.Column("source_type", sa.String(length=255), nullable=True),
        sa.Column("source_date", sa.Date(), nullable=True),
        sa.Column("source_note", sa.Text(), nullable=True),
    ]


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
    ]


def _client_fk() -> sa.Column:
    return sa.Column("client_id", sa.Integer(), nullable=False)


def _client_fk_constraint(table_name: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["client_id"], ["clients.client_id"], name=f"fk_{table_name}_client_id"
    )


def upgrade() -> None:
    op.create_table(
        "pension_holding",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        _client_fk(),
        sa.Column("provider_name", sa.String(length=255), nullable=False),
        sa.Column("product_type", sa.String(length=64), nullable=False),
        *_context_columns(),
        sa.Column("product_name", sa.String(length=255), nullable=True),
        sa.Column("account_reference", sa.String(length=255), nullable=True),
        sa.Column("known_balance_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("balance_as_of_date", sa.Date(), nullable=True),
        sa.Column("known_monthly_pension_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("pension_amount_as_of_date", sa.Date(), nullable=True),
        *_source_columns(),
        *_timestamps(),
        *_context_checks("pension_holding"),
        sa.CheckConstraint(
            "product_type IN ('pension fund', 'provident fund', 'insurance policy', 'other')",
            name="ck_pension_holding_product_type",
        ),
        sa.CheckConstraint(
            "known_balance_amount IS NULL OR balance_as_of_date IS NOT NULL",
            name="ck_pension_holding_balance_date_required",
        ),
        sa.CheckConstraint(
            "known_monthly_pension_amount IS NULL OR pension_amount_as_of_date IS NOT NULL",
            name="ck_pension_holding_pension_amount_date_required",
        ),
        _client_fk_constraint("pension_holding"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "capital_asset",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        _client_fk(),
        sa.Column("asset_category", sa.String(length=64), nullable=False),
        sa.Column("asset_description", sa.String(length=255), nullable=False),
        *_context_columns(),
        sa.Column("known_value_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("value_as_of_date", sa.Date(), nullable=True),
        sa.Column("liquidity_note", sa.Text(), nullable=True),
        sa.Column("restriction_note", sa.Text(), nullable=True),
        *_source_columns(),
        *_timestamps(),
        *_context_checks("capital_asset"),
        sa.CheckConstraint(
            "asset_category IN ("
            "'bank deposit', 'investment account', 'securities', 'real estate', "
            "'private asset', 'other')",
            name="ck_capital_asset_asset_category",
        ),
        sa.CheckConstraint(
            "known_value_amount IS NULL OR value_as_of_date IS NOT NULL",
            name="ck_capital_asset_value_date_required",
        ),
        _client_fk_constraint("capital_asset"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "recurring_income",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        _client_fk(),
        sa.Column("income_category", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("amount_basis", sa.String(length=32), nullable=False),
        sa.Column("frequency", sa.String(length=32), nullable=False),
        sa.Column("continuation_status", sa.String(length=64), nullable=False),
        *_context_columns(),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        *_source_columns(),
        *_timestamps(),
        *_context_checks("recurring_income"),
        sa.CheckConstraint(
            "income_category IN ('employment', 'pension', 'rental', 'business', 'benefit', 'other')",
            name="ck_recurring_income_income_category",
        ),
        sa.CheckConstraint(
            "amount_basis IN ('gross', 'net', 'unknown')",
            name="ck_recurring_income_amount_basis",
        ),
        sa.CheckConstraint(
            "frequency IN ('monthly', 'quarterly', 'annual', 'other')",
            name="ck_recurring_income_frequency",
        ),
        sa.CheckConstraint(
            "continuation_status IN ('ongoing', 'known end date', 'unknown')",
            name="ck_recurring_income_continuation_status",
        ),
        _client_fk_constraint("recurring_income"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "recurring_expense",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        _client_fk(),
        sa.Column("expense_category", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("frequency", sa.String(length=32), nullable=False),
        sa.Column("expense_type", sa.String(length=32), nullable=False),
        sa.Column("continuation_status", sa.String(length=64), nullable=False),
        *_context_columns(),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        *_source_columns(),
        *_timestamps(),
        *_context_checks("recurring_expense"),
        sa.CheckConstraint(
            "expense_category IN ("
            "'housing', 'health', 'debt', 'insurance', 'living', 'family support', 'other')",
            name="ck_recurring_expense_expense_category",
        ),
        sa.CheckConstraint(
            "frequency IN ('monthly', 'quarterly', 'annual', 'other')",
            name="ck_recurring_expense_frequency",
        ),
        sa.CheckConstraint(
            "expense_type IN ('mandatory', 'discretionary', 'unknown')",
            name="ck_recurring_expense_expense_type",
        ),
        sa.CheckConstraint(
            "continuation_status IN ('ongoing', 'known end date', 'unknown')",
            name="ck_recurring_expense_continuation_status",
        ),
        _client_fk_constraint("recurring_expense"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "retirement_timing_work_intention",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        _client_fk(),
        sa.Column("timing_confidence", sa.String(length=64), nullable=False),
        sa.Column("work_after_retirement_intention", sa.String(length=64), nullable=False),
        *_context_columns(),
        sa.Column("planned_work_end_date", sa.Date(), nullable=True),
        sa.Column("intended_pension_start_date", sa.Date(), nullable=True),
        sa.Column("other_known_retirement_date", sa.Date(), nullable=True),
        sa.Column("other_known_retirement_date_label", sa.String(length=255), nullable=True),
        sa.Column("anticipated_work_end_date", sa.Date(), nullable=True),
        sa.Column("work_intention_note", sa.Text(), nullable=True),
        *_source_columns(),
        *_timestamps(),
        *_context_checks("retirement_timing_work_intention"),
        sa.CheckConstraint(
            "timing_confidence IN ('known', 'stated intention', 'uncertain', 'not recorded')",
            name="ck_retirement_timing_work_intention_timing_confidence",
        ),
        sa.CheckConstraint(
            "work_after_retirement_intention IN ("
            "'continue working', 'stop working', 'undecided', 'not recorded')",
            name="ck_retirement_timing_work_intention_work_intention",
        ),
        sa.CheckConstraint(
            "other_known_retirement_date IS NULL "
            "OR other_known_retirement_date_label IS NOT NULL",
            name="ck_retirement_timing_work_intention_other_date_label_required",
        ),
        _client_fk_constraint("retirement_timing_work_intention"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "planner_assumption",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        _client_fk(),
        sa.Column("assumption_category", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("assumption_value_text", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("owner", sa.String(length=64), nullable=False),
        sa.Column(
            "lifecycle_status",
            sa.String(length=32),
            server_default="current",
            nullable=False,
        ),
        sa.Column("effective_start_date", sa.Date(), nullable=True),
        sa.Column("effective_end_date", sa.Date(), nullable=True),
        sa.Column("review_date", sa.Date(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            f"lifecycle_status IN ({_in_values(LIFECYCLE_STATUSES)})",
            name="ck_planner_assumption_lifecycle_status",
        ),
        sa.CheckConstraint(
            "assumption_category IN ("
            "'income', 'expense', 'retirement timing', 'work intention', "
            "'asset value', 'pension value', 'other')",
            name="ck_planner_assumption_assumption_category",
        ),
        sa.CheckConstraint(
            "owner IN ('planner', 'client stated', 'other stated')",
            name="ck_planner_assumption_owner",
        ),
        _client_fk_constraint("planner_assumption"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("planner_assumption")
    op.drop_table("retirement_timing_work_intention")
    op.drop_table("recurring_expense")
    op.drop_table("recurring_income")
    op.drop_table("capital_asset")
    op.drop_table("pension_holding")
