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

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.pension_product import COMPONENT_CODES, PensionProduct, PensionProductComponent, PensionProductSourceLink
from app.schemas.pension_product import ProductMetadata, ProductUpdate, exact_money
from app.services.pension_product_service import PensionProductError, _update_locked, audit, lock_client


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


def parse_source(raw: bytes) -> list[dict]:
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
        balances = dict.fromkeys(COMPONENT_CODES, Decimal("0.00"))
        for layer in node.iter("PerutYitraLeTkufa"):
            role = _one(layer, {"REKIV-ITRA-LETKUFA"}, diagnostics, "role")
            period = _one(layer, {"KOD-TECHULAT-SHICHVA"}, diagnostics, "period")
            amount = _one(layer, {"SACH-ITRA-LESHICHVA-BESHACH"}, diagnostics, "layer_amount")
            code = rewards_component(role or "", period or "")
            if code is None or amount is None:
                diagnostics.append({"code": "unmapped_layer", "role": role, "period": period, "value": amount})
            else:
                balances[code] += exact_money(amount.replace(",", ""))
        for tag, code in SEVERANCE_TAGS.items():
            for amount in _values(node, {tag}):
                balances[code] += exact_money(amount.replace(",", ""))
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
        metadata = ProductMetadata(
            product_name=field(["SHEM-TOCHNIT", "TOCHNIT", "SHEM_TOCHNIT"], "product_name") or "שם תכנית לא נמסר",
            product_type=PRODUCT_TYPE_LABELS.get(product_type, "סוג מוצר לא ממופה") if product_type else "סוג מוצר לא נמסר",
            provider_name=provider_name, provider_identifier=provider_id, account_reference=account,
            start_date=_date(field(["TAARICH-TCHILAT-HAFRASHA", "TAARICH-TCHILA", "TAARICH-HITZTARFUT-RISHON", "TAARICH-HITZTARFUT"], "start_date")),
            statement_date=_date(field(["TAARICH-NECHONUT-YITROT", "TAARICH-YITROT", "TAARICH-NECHONUT"], "statement_date")),
            historical_employers=sorted(set(_values(node, {"SHEM-MAASIK", "SHEM-MESHALEM", "SHEM-BAAL-POLISA-SHEEINO-MEVUTAH", "SHEM-BAAL-POLISA", "SHEM-MAFKID", "SHEM-BEALIM", "SHEM-HAMESHALLEM"}))),
            reported_product_total=summary(["TOTAL-CHISACHON-MTZBR", "TOTAL-ERKEI-PIDION"], "reported_product_total"),
            reported_rewards_total=summary(["YITRAT-KASPEY-TAGMULIM"], "reported_rewards_total"),
            reported_severance_total=summary(["YITRAT-PITZUIM"], "reported_severance_total"),
        )
        # Raw source is retained in full; enumerate non-authoritative fields too.
        diagnostics.append({"code": "source_fields", "fields": [{"tag": child.tag, "value": child.text.strip()} for child in node.iter() if not len(child) and child.text and child.text.strip()]})
        results.append({"identity": identity, "metadata": metadata, "components": {code: exact_money(value) for code, value in balances.items()}, "diagnostics": diagnostics})
    if len({item["identity"] for item in results}) != len(results):
        raise PensionProductError("DUPLICATE_SOURCE_ACCOUNT", "הקובץ מכיל סמכויות מתחרות לאותו חשבון", 422)
    return results


def import_source(db: Session, client_id: int, raw: bytes, filename: str, actor: str) -> list[PensionProduct]:
    accounts = parse_source(raw)
    checksum = hashlib.sha256(raw).hexdigest()
    lock_client(db, client_id)
    products = []
    for account in accounts:
        identity = account["identity"]
        metadata = account["metadata"]
        product = db.scalar(select(PensionProduct).where(PensionProduct.client_id == client_id, PensionProduct.source_identity == identity).with_for_update().execution_options(populate_existing=True))
        previous = db.scalar(select(PensionProductSourceLink).where(PensionProductSourceLink.client_id == client_id, PensionProductSourceLink.source_identity == identity, PensionProductSourceLink.checksum == checksum))
        if previous:
            if product is None:
                raise PensionProductError("DELETED_SOURCE_PRODUCT", "המוצר ממקור זה נמחק; ייבוא חוזר לא ישחזר אותו אוטומטית")
            products.append(product)
            continue
        if product:
            if metadata.statement_date is None or product.statement_date is None or metadata.statement_date <= product.statement_date:
                raise PensionProductError("SOURCE_NOT_NEWER", "המקור אינו חדש יותר מהנתונים הקיימים")
            product = _update_locked(db, client_id, product.product_id, ProductUpdate(**metadata.model_dump(), expected_version=product.version, components=account["components"]), actor)
        else:
            product = PensionProduct(product_id=uuid4().hex, client_id=client_id, source_kind="imported", source_identity=identity, version=1, created_by=actor, updated_by=actor, **metadata.model_dump())
            db.add(product)
            db.flush()
            db.add_all([PensionProductComponent(component_id=uuid4().hex, product_id=product.product_id, component_code=code, balance=balance) for code, balance in account["components"].items()])
            db.flush()
            audit(db, product, "import", actor)
        db.add(PensionProductSourceLink(source_link_id=uuid4().hex, client_id=client_id, product_id=product.product_id, source_identity=identity, checksum=checksum, filename=filename, raw_content=raw, statement_date=metadata.statement_date, diagnostics=account["diagnostics"]))
        db.flush()
        products.append(product)
    return products
