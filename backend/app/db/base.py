from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def load_all_models() -> None:
    # Import models so they are registered on Base.metadata for Alembic.
    import app.models.actual_capitalization  # noqa: F401
    import app.models.client  # noqa: F401
    import app.models.client_profile  # noqa: F401
    import app.models.employment_record  # noqa: F401
    import app.models.fixation_audit_row  # noqa: F401
    import app.models.fixation_input_snapshot  # noqa: F401
    import app.models.fixation_result  # noqa: F401
    import app.models.fixation_run  # noqa: F401
    import app.models.fixation_validation_error  # noqa: F401
    import app.models.grant  # noqa: F401
