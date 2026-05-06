from __future__ import annotations

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from .AbstractBaseResource import AbstractBaseResource
from ..services.MySQLDataService import MySQLDataService


class OrderDetail(BaseModel):
    orderNumber: Optional[int] = None
    productCode: Optional[str] = None
    quantityOrdered: Optional[int] = None
    priceEach: Optional[Decimal] = None
    orderLineNumber: Optional[int] = None


class OrderDetailCollection(BaseModel):
    items: list[OrderDetail] = Field(default_factory=list)


class OrderDetailsResource(AbstractBaseResource):
    """Order details have a composite PK (orderNumber, productCode)."""

    def __init__(self, config: dict | None = None) -> None:
        cfg = dict(config or {})
        super().__init__(cfg)
        service_config = {
            "table_name": "orderdetails",
            "primary_key_fields": ["orderNumber", "productCode"],
            **cfg,
        }
        self._service = MySQLDataService(service_config)

    def get(self, template: dict) -> OrderDetailCollection:
        rows = self._service.retrieveByTemplate(template)
        return OrderDetailCollection(items=[OrderDetail.model_validate(r) for r in rows])

    def get_by_id(self, id: str) -> OrderDetail:  # noqa: A002
        # Resource-layer callers should use get_by_composite_key; this is a
        # convenience for "orderNumber:productCode" string keys.
        return self.get_by_composite_key(*self._split_composite(id))

    def get_by_composite_key(self, order_number: int, product_code: str) -> OrderDetail:
        row = self._service.retrieveByPrimaryKey(
            {"orderNumber": int(order_number), "productCode": str(product_code)}
        )
        if not row:
            raise ValueError(
                f"No orderdetail for orderNumber={order_number!r} productCode={product_code!r}"
            )
        return OrderDetail.model_validate(row)

    def get_by_order(self, order_number: int) -> OrderDetailCollection:
        return self.get({"orderNumber": int(order_number)})

    def post(self, new_data: OrderDetail) -> str:
        data = new_data.model_dump(exclude_none=True, mode="json")
        for required in ("orderNumber", "productCode"):
            if required not in data:
                raise ValueError(f"{required} is required for orderdetails")
        return self._service.create(data)

    def put(self, character_id: str, new_data: OrderDetail) -> int:
        order_number, product_code = self._split_composite(character_id)
        return self.put_by_composite_key(order_number, product_code, new_data)

    def put_by_composite_key(
        self, order_number: int, product_code: str, new_data: OrderDetail
    ) -> int:
        data = new_data.model_dump(exclude_none=True, mode="json")
        data.pop("orderNumber", None)
        data.pop("productCode", None)
        return self._service.updateByPrimaryKey(
            {"orderNumber": int(order_number), "productCode": str(product_code)}, data
        )

    def delete(self, id: str) -> int:  # noqa: A002
        order_number, product_code = self._split_composite(id)
        return self.delete_by_composite_key(order_number, product_code)

    def delete_by_composite_key(self, order_number: int, product_code: str) -> int:
        return self._service.deleteByPrimaryKey(
            {"orderNumber": int(order_number), "productCode": str(product_code)}
        )

    @staticmethod
    def _split_composite(id_str: str) -> tuple[int, str]:
        parts = str(id_str).split(":", 1)
        if len(parts) != 2:
            raise ValueError(
                "Composite id must be 'orderNumber:productCode' (got %r)" % id_str
            )
        return int(parts[0]), parts[1]
