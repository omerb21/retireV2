"""Administrative archival protection, not pension-source progression.

Canonical products deliberately do not depend on this check. It preserves
existing record-safety behavior for out-of-scope cashflow/scenario writes.
"""
from app.models.client import Client
from app.services.m01_case_service import M01CaseError


def ensure_client_record_writable(client: Client) -> None:
    if client.status == "archived":
        raise M01CaseError(status_code=409, code="archived_case_read_only", message="Archived administrative records are read-only")
