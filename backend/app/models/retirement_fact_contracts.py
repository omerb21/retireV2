from __future__ import annotations

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

PENSION_PRODUCT_TYPES = ("pension fund", "provident fund", "insurance policy", "other")
CAPITAL_ASSET_CATEGORIES = (
    "bank deposit",
    "investment account",
    "securities",
    "real estate",
    "private asset",
    "other",
)
INCOME_CATEGORIES = ("employment", "pension", "rental", "business", "benefit", "other")
AMOUNT_BASES = ("gross", "net", "unknown")
FREQUENCIES = ("monthly", "quarterly", "annual", "other")
CONTINUATION_STATUSES = ("ongoing", "known end date", "unknown")
EXPENSE_CATEGORIES = (
    "housing",
    "health",
    "debt",
    "insurance",
    "living",
    "family support",
    "other",
)
EXPENSE_TYPES = ("mandatory", "discretionary", "unknown")
TIMING_CONFIDENCES = ("known", "stated intention", "uncertain", "not recorded")
WORK_AFTER_RETIREMENT_INTENTIONS = (
    "continue working",
    "stop working",
    "undecided",
    "not recorded",
)
ASSUMPTION_CATEGORIES = (
    "income",
    "expense",
    "retirement timing",
    "work intention",
    "asset value",
    "pension value",
    "other",
)
ASSUMPTION_OWNERS = ("planner", "client stated", "other stated")
PLANNING_DOMAINS = (
    "pension holdings",
    "capital assets",
    "recurring income",
    "recurring expenses",
    "retirement timing",
    "work intention",
    "planner assumptions",
    "other",
)
ADVISORY_STATUSES = ("open", "resolved", "no longer relevant")
