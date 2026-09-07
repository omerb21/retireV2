"""The only boundary for current pension balances used by downstream modules."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.pension_product import PensionProduct
from app.services.pension_product_service import lock_client, product_response


def current_products(db: Session, client_id: int) -> list[dict]:
    # Read metadata and components under the same serialization boundary so a
    # writer cannot produce a mixed-version response between the two queries.
    lock_client(db, client_id)
    products = db.scalars(select(PensionProduct).where(PensionProduct.client_id == client_id).order_by(PensionProduct.product_id)).all()
    return [product_response(db, product) for product in products]


def conversion_source_availability(db: Session, client_id: int) -> dict:
    products = current_products(db, client_id)
    # This package does not define a conversion rule matrix for the recovered
    # ontology. Never reconstruct legacy review/ledger authority to enable it.
    return {"available": False, "reason_code": "CANONICAL_CONVERSION_CONTRACT_NOT_IMPLEMENTED", "canonical_product_count": len(products)}
