"""Recognized XML source mapping, without inferred or generic balances.

Mapping authority: immutable FIRST_RECOVERY_PKG_001 definition, section 11.
V1 e4bd8618's processor supplies the XML field names, not its heuristics.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4
from xml.etree import ElementTree as ET

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.pension_product import COMPONENT_CODES, PensionProduct, PensionProductComponent, PensionProductSourceLink
from app.schemas.pension_product import ProductMetadata, ProductUpdate, exact_money
from app.services.pension_product_service import PensionProductError, _update_locked, audit, component_balances, lock_client, product_response


ROLE_CODES = {"2": "עובד", "8": "עובד", "3": "מעביד", "9": "מעביד"}
PERIOD_CODES = {"1": "עד_2000", "2": "אחרי_2000", "7": "אחרי_2008_לא_משלמת", "9": "אחרי_2008_לא_משלמת", "13": "אחרי_2008_לא_משלמת"}
SEVERANCE_TAGS = {
    "ERECH-PIDION-PITZUIM-MAASIK-NOCHECHI": COMPONENT_CODES[0],
    "YITRAT-PITZUIM-MAASIK-NOCHECHI": COMPONENT_CODES[0],
    "ERECH-PIDION-PITZUIM-LEKITZBA-MAAVIDIM-KODMIM": COMPONENT_CODES[1],
    "TZVIRAT-PITZUIM-PTURIM-MAAVIDIM-KODMIM": COMPONENT_CODES[2],
    "YITRAT-PITZUIM-LELO-HITCHASHBENOT": COMPONENT_CODES[2],
    "TZVIRAT-PITZUIM-MAAVIDIM-KODMIM-BERETZEF-ZECHUYOT": COMPONENT_CODES[3],
    "TZVIRAT-PITZUIM-MAAVIDIM-KODMIM-BERETZEF-KITZBA": COMPONENT_CODES[4],
}
ACCOUNT_TAGS = {"HeshbonOPolisa", "Heshbon", "Account", "Policy", "Polisa", "PensionAccount", "PensionPolicy", "KupatGemel", "BituachMenahalim", "KerenPensia"}
PRODUCT_TYPE_LABELS = {"1": "פוליסת ביטוח חיים משולב חיסכון", "2": "פוליסת ביטוח חיים", "3": "קופת גמל", "4": "קרן פנסיה", "5": "פוליסת חיסכון טהור"}


def rewards_component(role: str, period: str) -> str | None:
    if role not in ROLE_CODES or period not in PERIOD_CODES:
        return None
    return f"תגמולי_{ROLE_CODES[role]}_{PERIOD_CODES[period]}"


def source_identity(provider_identifier: str | None, provider_name: str | None, account_reference: str, source_reference: str | None = None) -> str:
    """Prefer a provider identifier; otherwise exact normalized provider name.

    Missing provider/account identity needs an explicit stable source reference,
    not a checksum (which changes for newer statements) or a guessed identity.
    """
    provider = provider_identifier or provider_name
    if provider and account_reference:
        identity = ["provider-account", "id" if provider_identifier else "name", provider.strip(), account_reference.strip()]
    elif source_reference:
        identity = ["source", source_reference]
    else:
        raise PensionProductError("AMBIGUOUS_PRODUCT_IDENTITY", "חסר זיהוי חד־משמעי של הגוף המנהל והחשבון", 422)
    return hashlib.sha256(json.dumps(identity, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def _values(node: ET.Element, tags: set[str]) -> list[str]:
    return [child.text.strip() for child in node.iter() if child.tag in tags and child.text and child.text.strip()]


def _one(node: ET.Element, tags: set[str], diagnostics: list, field: str) -> str | None:
    values = sorted(set(_values(node, tags)))
    if len(values) > 1:
        diagnostics.append({"code": "ambiguous_field", "field": field, "values": values})
        return None
    return values[0] if values else None


def _date(value: str | None) -> date | None:
    if not value:
        return None
    for pattern in ("%Y%m%d", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            pass
    raise PensionProductError("INVALID_SOURCE_DATE", "תאריך המקור אינו תקין", 422)


def _parse_source(raw: bytes) -> list[dict]:
    if not raw or len(raw) > 26_214_400:
        raise PensionProductError("INVALID_SOURCE_SIZE", "גודל קובץ המקור אינו תקין", 422)
    try:
        content = raw.decode("utf-8-sig")
        if "<!DOCTYPE" in content.upper() or "<!ENTITY" in content.upper():
            raise ValueError("DTD and entities are not permitted")
        root = ET.fromstring(content)
    except (UnicodeError, ET.ParseError, ValueError) as exc:
        raise PensionProductError("INVALID_SOURCE_XML", "נדרש קובץ מקור XML תקין בקידוד UTF-8", 422) from exc
    # Namespace prefixes do not change the recognized professional field names.
    for node in root.iter():
        node.tag = node.tag.rsplit("}", 1)[-1]
    parents = {child: parent for parent in root.iter() for child in parent}
    nodes = [node for node in root.iter() if node.tag in ACCOUNT_TAGS]
    # Nested account candidates are ambiguous instead of being imported twice.
    if any(any(child in nodes for child in list(node.iter())[1:]) for node in nodes):
        raise PensionProductError("AMBIGUOUS_ACCOUNT_STRUCTURE", "מבנה החשבונות בקובץ אינו חד־משמעי", 422)
    if not nodes:
        raise PensionProductError("NO_SOURCE_ACCOUNTS", "לא נמצאו חשבונות בקובץ", 422)
    results = []
    for node in nodes:
        diagnostics: list[dict] = []
        def field(tags, name):
            return _one(node, set(tags), diagnostics, name)
        def provider_field(tags, name):
            current = node
            while current is not None:
                # Ancestors: only their direct metadata, never another account.
                container = current if current is node else ET.Element("metadata")
                if current is not node:
                    container.extend(child for child in current if child.tag in tags)
                value = _one(container, set(tags), diagnostics, name)
                if value is not None:
                    return value
                if any(item.get("field") == name for item in diagnostics):
                    return None
                current = parents.get(current)
            return None
        provider_name = provider_field(["SHEM-YATZRAN", "SHEM-METAFEL", "SHEM_HA_MOSAD", "Provider", "Company"], "provider_name")
        provider_id = provider_field(["KOD-MEZAHE-YATZRAN", "KOD-YATZRAN", "MEZAHE-YATZRAN"], "provider_identifier")
        account = field(["MISPAR-POLISA-O-HESHBON", "MISPAR-HESHBON", "MISPAR-POLISA"], "account_reference")
        identity = source_identity(provider_id, provider_name, account or "")
        # Sparse facts: absence is not an explicitly reported zero.
        balances: dict[str, Decimal] = {}
        for layer in node.iter("PerutYitraLeTkufa"):
            layer_diagnostics_start = len(diagnostics)
            role = _one(layer, {"REKIV-ITRA-LETKUFA"}, diagnostics, "role")
            period = _one(layer, {"KOD-TECHULAT-SHICHVA"}, diagnostics, "period")
            amount = _one(layer, {"SACH-ITRA-LESHICHVA-BESHACH"}, diagnostics, "layer_amount")
            code = rewards_component(role or "", period or "")
            if code is not None and any(item.get("field") == "layer_amount" and item.get("code") == "ambiguous_field" for item in diagnostics[layer_diagnostics_start:]):
                raise PensionProductError("AMBIGUOUS_SOURCE_FACT", "סכום רכיב המקור אינו חד־משמעי", 422)
            if code is None or amount is None:
                diagnostics.append({"code": "unmapped_layer", "role": role, "period": period, "value": amount})
            else:
                balances[code] = balances.get(code, Decimal("0.00")) + exact_money(amount.replace(",", ""))
        for tag, code in SEVERANCE_TAGS.items():
            for amount in _values(node, {tag}):
                balances[code] = balances.get(code, Decimal("0.00")) + exact_money(amount.replace(",", ""))
        def summary(tags, name):
            # A component/layer total nested inside an account is NOT proven to
            # be the account's summary. Preserve it in diagnostics, not here.
            summary_node = ET.Element("account_summary")
            summary_node.extend(child for child in node if child.tag in tags)
            value = _one(summary_node, set(tags), diagnostics, name)
            return None if value is None else exact_money(value.replace(",", ""))
        product_type = field(["SUG-MUTZAR"], "product_type")
        if product_type and product_type not in PRODUCT_TYPE_LABELS:
            diagnostics.append({"code": "unmapped_product_type", "value": product_type})
        metadata = dict(
            product_name=field(["SHEM-TOCHNIT", "TOCHNIT", "SHEM_TOCHNIT"], "product_name"),
            product_type=product_type,
            provider_name=provider_name, provider_identifier=provider_id, account_reference=account,
            start_date=_date(field(["TAARICH-TCHILAT-HAFRASHA", "TAARICH-TCHILA", "TAARICH-HITZTARFUT-RISHON", "TAARICH-HITZTARFUT"], "start_date")),
            statement_date=_date(field(["TAARICH-NECHONUT-YITROT", "TAARICH-YITROT", "TAARICH-NECHONUT"], "statement_date")),
            historical_employers=sorted(set(_values(node, {"SHEM-MAASIK", "SHEM-MESHALEM", "SHEM-BAAL-POLISA-SHEEINO-MEVUTAH", "SHEM-BAAL-POLISA", "SHEM-MAFKID", "SHEM-BEALIM", "SHEM-HAMESHALLEM"}))),
            reported_product_total=summary(["TOTAL-CHISACHON-MTZBR", "TOTAL-ERKEI-PIDION"], "reported_product_total"),
            reported_rewards_total=summary(["YITRAT-KASPEY-TAGMULIM"], "reported_rewards_total"),
            reported_severance_total=summary(["YITRAT-PITZUIM"], "reported_severance_total"),
        )
        if any(item.get("code") == "ambiguous_field" and item.get("field") in metadata for item in diagnostics):
            raise PensionProductError("AMBIGUOUS_SOURCE_FACT", "פרטי המקור אינם חד־משמעיים", 422)
        # Raw source is retained in full; enumerate non-authoritative fields too.
        diagnostics.append({"code": "source_fields", "fields": [{"tag": child.tag, "value": child.text.strip()} for child in node.iter() if not len(child) and child.text and child.text.strip()]})
        results.append({"identity": identity, "metadata": metadata, "components": {code: exact_money(value) for code, value in balances.items()}, "diagnostics": diagnostics})
    if len({item["identity"] for item in results}) != len(results):
        raise PensionProductError("DUPLICATE_SOURCE_ACCOUNT", "הקובץ מכיל סמכויות מתחרות לאותו חשבון", 422)
    return results


def _prepare_batch(files: list[tuple[str, bytes]]) -> tuple[str, list[dict], list[dict]]:
    if not files:
        raise PensionProductError("EMPTY_SOURCE_BATCH", "יש לבחור לפחות קובץ אחד", 422)
    selected = []
    checksums: dict[str, str] = {}
    for filename, raw in files:
        if not raw or len(raw) > 26_214_400:
            raise PensionProductError("INVALID_SOURCE_SIZE", f"גודל קובץ המקור אינו תקין: {filename}", 422)
        checksum = hashlib.sha256(raw).hexdigest()
        if checksum in checksums:
            raise PensionProductError("DUPLICATE_BATCH_FILE", f"אותו תוכן נבחר פעמיים: {checksums[checksum]}, {filename}", 422)
        checksums[checksum] = filename
        selected.append({"filename": filename, "raw": raw, "checksum": checksum})
    batch_identity = hashlib.sha256(("pension-source-batch-v1" + "".join(sorted(checksums))).encode()).hexdigest()
    grouped: dict[str, dict] = {}
    diagnostics = []
    for source in sorted(selected, key=lambda item: item["checksum"]):
        filename = source["filename"]
        try:
            accounts = _parse_source(source["raw"])
        except PensionProductError as error:
            raise PensionProductError(error.code, f"{error.message}: {filename}", error.status_code) from error
        except ValueError as error:
            raise PensionProductError("INVALID_SOURCE_FACT", f"נתון המקור אינו תקין: {filename}", 422) from error
        for account in accounts:
            identity = account["identity"]
            merged = grouped.setdefault(identity, {"identity": identity, "metadata": {}, "components": {}, "sources": []})
            names = sorted({filename, *(item["filename"] for item in merged["sources"])})
            def conflict(field):
                raise PensionProductError("SOURCE_BATCH_CONFLICT", f"נתוני מקור סותרים ({field}) בקבצים: {', '.join(names)}")
            for field, value in account["metadata"].items():
                if field == "historical_employers":
                    merged["metadata"][field] = sorted(set(merged["metadata"].get(field, [])) | set(value))
                elif value is not None:
                    if field in merged["metadata"] and merged["metadata"][field] != value:
                        conflict(field)
                    merged["metadata"][field] = value
            for code, value in account["components"].items():
                if code in merged["components"] and merged["components"][code] != value:
                    conflict(code)
                merged["components"][code] = value
            merged["sources"].append({**source, "statement_date": account["metadata"]["statement_date"], "diagnostics": account["diagnostics"]})
            diagnostics.append({"filename": filename, "checksum": source["checksum"], "source_identity": identity, "diagnostics": account["diagnostics"]})
    for merged in grouped.values():
        metadata = merged["metadata"]
        metadata.setdefault("product_name", "שם תכנית לא נמסר")
        product_type = metadata.get("product_type")
        metadata["product_type"] = PRODUCT_TYPE_LABELS.get(product_type, "סוג מוצר לא ממופה") if product_type else "סוג מוצר לא נמסר"
        metadata.setdefault("reported_product_total", None)
        try:
            merged["metadata"] = ProductMetadata(**metadata)
        except ValueError as error:
            names = ", ".join(sorted(item["filename"] for item in merged["sources"]))
            raise PensionProductError("INVALID_SOURCE_FACT", f"פרטי המקור אינם תקינים: {names}", 422) from error
        merged["components"] = {code: merged["components"].get(code, Decimal("0.00")) for code in COMPONENT_CODES}
    return batch_identity, [grouped[key] for key in sorted(grouped)], diagnostics


def import_source_batch(db: Session, client_id: int, files: list[tuple[str, bytes]], actor: str) -> dict:
    """The sole professional import engine; caller owns the single transaction."""
    batch_identity, accounts, diagnostics = _prepare_batch(files)
    checksums = {item["checksum"] for account in accounts for item in account["sources"]}
    lock_client(db, client_id)
    previous = list(db.scalars(select(PensionProductSourceLink).where(
        PensionProductSourceLink.client_id == client_id,
        or_(PensionProductSourceLink.checksum.in_(checksums), PensionProductSourceLink.batch_identity == batch_identity),
    )))
    def response(products):
        return {"batch_identity": batch_identity, "file_count": len(files), "product_count": len(products),
                "products": [product_response(db, product) for product in products], "diagnostics": diagnostics}
    if previous:
        if {row.checksum for row in previous} != checksums or any(row.batch_identity != batch_identity for row in previous):
            names = ", ".join(sorted(filename for filename, _ in files))
            raise PensionProductError("PARTIAL_OVERLAP_SOURCE_BATCH", f"הקבצים חופפים לאצוות ייבוא קודמת אך אינם אותה אצווה: {names}")
        ids = sorted({row.product_id for row in previous})
        products = list(db.scalars(select(PensionProduct).where(PensionProduct.client_id == client_id, PensionProduct.product_id.in_(ids)).order_by(PensionProduct.product_id)))
        if len(products) != len(ids):
            names = ", ".join(sorted(filename for filename, _ in files))
            raise PensionProductError("DELETED_SOURCE_PRODUCT", f"מוצר ממקור זה נמחק; ייבוא חוזר לא ישחזר אותו אוטומטית: {names}")
        return response(products)

    # All existing-product checks and request validation precede any product,
    # component, source-link or audit mutation.
    plan = []
    for account in accounts:
        metadata = account["metadata"]
        product = db.scalar(select(PensionProduct).where(PensionProduct.client_id == client_id, PensionProduct.source_identity == account["identity"]).with_for_update().execution_options(populate_existing=True))
        request = None
        if product:
            if metadata.statement_date is None or product.statement_date is None or metadata.statement_date <= product.statement_date:
                names = ", ".join(sorted(item["filename"] for item in account["sources"]))
                raise PensionProductError("SOURCE_NOT_NEWER", f"המקור אינו חדש יותר מהנתונים הקיימים: {names}")
            component_balances(db, product.product_id)
            request = ProductUpdate(**metadata.model_dump(), expected_version=product.version, components=account["components"])
        plan.append((account, product, request))
    products = []
    for account, product, request in plan:
        metadata = account["metadata"]
        if product:
            product = _update_locked(db, client_id, product.product_id, request, actor)
        else:
            product = PensionProduct(product_id=uuid4().hex, client_id=client_id, source_kind="imported", source_identity=account["identity"], version=1, created_by=actor, updated_by=actor, **metadata.model_dump())
            db.add(product)
            db.flush()
            db.add_all([PensionProductComponent(component_id=uuid4().hex, product_id=product.product_id, component_code=code, balance=value) for code, value in account["components"].items()])
            db.flush()
            audit(db, product, "import", actor)
        for source in account["sources"]:
            db.add(PensionProductSourceLink(source_link_id=uuid4().hex, client_id=client_id, product_id=product.product_id,
                source_identity=account["identity"], checksum=source["checksum"], batch_identity=batch_identity,
                filename=source["filename"][:255], raw_content=source["raw"], statement_date=source["statement_date"], diagnostics=source["diagnostics"]))
        db.flush()
        products.append(product)
    return response(products)
