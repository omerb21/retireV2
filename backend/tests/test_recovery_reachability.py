"""Executable cutover inventory: remaining legacy references are not authority."""
import ast
from pathlib import Path
import re

from app.main import app

ROOT = Path(__file__).resolve().parents[2]
LEGACY = re.compile(r"PensionHolding|pension_holding|pension-holdings|\bm0[2345]\w*|contribution_component", re.I)
# Each match in these files has the bounded role stated here, not a current
# product/balance reader. Tests below also inspect executable imports and routes.
ALLOWED_PRODUCTION_MATCHES = {
    "backend/app/db/base.py": "archive model/FK and guard registration before first query",
    "backend/app/api/clients_routes.py": "GET-only persisted analysis text by historical FK",
    "backend/app/models/client.py": "historical ORM FK relationship, never traversed by current reader",
    "backend/app/models/retirement_facts.py": "archive-only PensionHolding table with immutable cutover triggers",
    "backend/app/models/pension_analysis_record.py": "historical analysis FK, no create/update endpoint",
    "backend/app/models/pension_analysis_record_contracts.py": "persisted historical response identifier",
    "backend/app/models/pension_product.py": "optional archived raw-source FK; not a balance",
    "backend/app/models/m02_intake.py": "frozen intake and preserved raw evidence",
    "backend/app/models/m03_review.py": "frozen review/annotation archive and FK targets",
    "backend/app/models/m04_classification.py": "frozen classification archive and FK targets",
    "backend/app/models/m05_ledger.py": "frozen ledger archive and immutable SQL lexical guards",
    "backend/app/models/m06_conversion.py": "historical source FKs and shared immutable SQL guard",
    "backend/app/schemas/m06_conversion.py": "historical response fields; old request shapes only reach fail-closed actions",
    "backend/app/services/m06_conversion_service.py": "historical fingerprints/snapshots and documentation of removed source",
    "backend/app/services/m09_cashflow_service.py": "preserved M06 predecessor snapshot field; eligibility closes current use",
    "backend/app/services/m02_storage.py": "backend-only raw-source integrity/storage primitives",
    "backend/app/services/pension_source_download.py": "backend-only archived raw-source streaming",
    "frontend/src/api/m06ConversionApi.ts": "read-only historical M06 response/FK types",
}


def test_all_remaining_production_legacy_matches_have_a_classified_retained_role():
    found = set()
    for directory in ("backend/app", "frontend/src"):
        for path in (ROOT / directory).rglob("*"):
            if path.suffix not in {".py", ".ts", ".tsx"} or ".test." in path.name:
                continue
            if LEGACY.search(path.read_text(encoding="utf-8")):
                found.add(path.relative_to(ROOT).as_posix())
    assert found <= ALLOWED_PRODUCTION_MATCHES.keys(), sorted(found - ALLOWED_PRODUCTION_MATCHES.keys())


def test_obsolete_routes_are_not_registered_and_analysis_is_get_only():
    paths = {route.path: getattr(route, "methods", set()) for route in app.routes}
    for path in paths:
        assert not any(fragment in path for fragment in ("/m02", "/m03", "/m04", "/m05", "/pension-intake", "/source-review", "/classification", "/pension-ledger", "/case/lifecycle"))
    holding = {p: m for p, m in paths.items() if "pension-holdings" in p}
    assert holding == {"/api/clients/{client_id}/pension-holdings/{pension_holding_id}/analysis-record": {"GET"}}
    assert "/api/clients/{client_id}/pension-products" in paths


def test_current_services_do_not_import_legacy_balance_models_or_services():
    for folder in ("backend/app/services", "backend/app/api"):
        for path in (ROOT / folder).glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    assert not re.search(r"app\.(models|services)\.m0[2345]_(?!storage)", module), (path, module)
                    assert not any(alias.name == "PensionHolding" for alias in node.names), path
    reader = (ROOT / "backend/app/services/canonical_pension_source_reader.py").read_text(encoding="utf-8")
    assert "select(PensionProduct)" in reader
    assert not LEGACY.search(reader)


def test_removed_ui_and_service_files_cannot_be_reactivated():
    removed = (
        "frontend/src/pages/M02PensionIntakeScreen.tsx", "frontend/src/pages/M03SourceReviewScreen.tsx",
        "frontend/src/pages/M04ClassificationScreen.tsx", "frontend/src/pages/M05LedgerScreen.tsx",
        "frontend/src/pages/PensionAnalysisRecordSection.tsx",
        "frontend/src/api/m02IntakeApi.ts", "frontend/src/api/m03ReviewApi.ts",
        "frontend/src/api/m04ClassificationApi.ts", "frontend/src/api/m05LedgerApi.ts",
        "backend/app/services/m02_intake_service.py", "backend/app/services/m03_review_service.py",
        "backend/app/services/m04_classification_service.py", "backend/app/services/m05_ledger_service.py",
        "backend/app/services/m04_rule_catalogue.py",
    )
    assert not [p for p in removed if (ROOT / p).exists()]
    for path in (ROOT / "frontend/src").rglob("*"):
        if path.suffix not in {".ts", ".tsx"} or ".test." in path.name:
            continue
        source = path.read_text(encoding="utf-8")
        assert not re.search(r"pension-holdings|accepted_for_review|metadata_review|start_revalidation|contribution_component|allowed_lifecycle_targets", source), path


def test_no_pension_holding_current_source_registration_or_analysis_mutator_remains():
    clients = (ROOT / "backend/app/api/clients_routes.py").read_text(encoding="utf-8")
    assert "select(PensionHolding)" not in clients
    assert "def create_pension_analysis_record" not in clients
    assert "def update_pension_analysis_record" not in clients
    m07 = (ROOT / "backend/app/services/m07_evidence_service.py").read_text(encoding="utf-8")
    assert '"pension_holding":' not in m07
