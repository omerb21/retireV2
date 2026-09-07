from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator

from app.models.pension_product import COMPONENT_CODES


def exact_money(value: object) -> Decimal:
    # JSON monetary numbers are not an exact interchange format. Clients send
    # decimal strings; accepting floats would lose digits before validation.
    if isinstance(value, (float, bool)):
        raise ValueError("יש לשלוח סכום כמחרוזת עשרונית מדויקת")
    try:
        amount = Decimal(value)
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise ValueError("סכום לא תקין") from exc
    if not amount.is_finite() or abs(amount) >= Decimal("1000000000000000000"):
        raise ValueError("סכום מחוץ לטווח")
    if amount != amount.quantize(Decimal("0.01")):
        raise ValueError("מותרות עד שתי ספרות אחרי הנקודה")
    return amount.quantize(Decimal("0.01"))


Money = Annotated[Decimal, BeforeValidator(exact_money)]
ShortText = Annotated[str, Field(min_length=1, max_length=255)]


class ProductMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    product_name: ShortText
    product_type: ShortText
    provider_name: ShortText | None = None
    provider_identifier: str | None = Field(default=None, max_length=128)
    account_reference: ShortText | None = None
    start_date: date | None = None
    statement_date: date | None = None
    historical_employers: list[ShortText] = Field(default_factory=list, max_length=100)
    reported_product_total: Money | None
    reported_rewards_total: Money | None = None
    reported_severance_total: Money | None = None


class ProductCreate(ProductMetadata):
    reported_product_total: Money


class ProductUpdate(ProductMetadata):
    expected_version: int = Field(ge=1)
    components: dict[str, Money]

    @field_validator("components")
    @classmethod
    def fixed_components(cls, values: dict[str, Decimal]) -> dict[str, Decimal]:
        if set(values) != set(COMPONENT_CODES):
            raise ValueError("נדרשים בדיוק אחד עשר הרכיבים הקבועים")
        return values


class SelectedProductUpdate(ProductUpdate):
    product_id: str = Field(min_length=1, max_length=64)


class SaveSelected(BaseModel):
    model_config = ConfigDict(extra="forbid")
    products: list[SelectedProductUpdate] = Field(min_length=1, max_length=100)

    @field_validator("products")
    @classmethod
    def unique_products(cls, values: list[SelectedProductUpdate]) -> list[SelectedProductUpdate]:
        if len({value.product_id for value in values}) != len(values):
            raise ValueError("מוצר מופיע יותר מפעם אחת בבקשת השמירה")
        return values
