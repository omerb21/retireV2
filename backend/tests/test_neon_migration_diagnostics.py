"""Safe migration failure diagnostics must be useful without showing connection data."""
from scripts.safe_neon_stage6_runner import show_safe_failure_summary


def test_reports_migration_revision_and_postgres_error(capsys):
    trace = (
        "INFO [alembic.runtime.migration] Running upgrade  -> a2f36c3147d2, phase 1\n"
        "psycopg2.errors.UndefinedTable: relation missing_dependency does not exist\n"
    )
    show_safe_failure_summary(trace)
    output = capsys.readouterr().out
    assert "LAST_ATTEMPTED_MIGRATION: a2f36c3147d2" in output
    assert "POSTGRES_ERROR_TYPE: UndefinedTable" in output
    assert "relation missing_dependency does not exist" in output


def test_redacts_url_bearing_db_error(capsys):
    trace = (
        "psycopg2.errors.InvalidParameterValue: "
        "could not parse postgresql://fakeuser:example@invalid-host/test\n"
    )
    show_safe_failure_summary(trace)
    output = capsys.readouterr().out
    assert "POSTGRES_ERROR_TYPE: InvalidParameterValue" in output
    assert "example" not in output
    assert "postgresql://" not in output


def test_reports_non_sql_error_class(capsys):
    trace = "Traceback...\nValueError: unrelated driver failure\n"
    show_safe_failure_summary(trace)
    output = capsys.readouterr().out
    assert "LAST_ATTEMPTED_MIGRATION: not reported" in output
    assert "MIGRATION_ERROR_TYPE: ValueError" in output


def test_reports_windows_python_type_error_location(capsys):
    trace = (
        'Traceback (most recent call last):\\n'
        '  File "C:\\\\work\\\\backend\\\\alembic\\\\env.py", line 32, in <module>\\n'
        '    configure()\\n'
        'TypeError: unsupported operand type(s) for +: NoneType and str\\n'
    )
    show_safe_failure_summary(trace)
    output = capsys.readouterr().out
    assert "MIGRATION_ERROR_TYPE: TypeError" in output
    assert "FAILURE_LOCATION: env.py:32 (<module>)" in output
    assert "MIGRATION_ERROR_DETAIL: unsupported operand type(s)" in output
