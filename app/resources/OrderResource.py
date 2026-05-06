from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from .AbstractBaseResource import AbstractBaseResource
from ..services.MySQLDataService import MySQLDataService


class Order(BaseModel):
    orderNumber: Optional[int] = None
    orderDate: Optional[date] = None
    requiredDate: Optional[date] = None
    shippedDate: Optional[date] = None
    status: str = ""
    comments: Optional[str] = None
    customerNumber: Optional[int] = None


class OrderCollection(BaseModel):
    items: list[Order] = Field(default_factory=list)


class OrderResource(AbstractBaseResource):
    def __init__(self, config: dict | None = None) -> None:
        cfg = dict(config or {})
        super().__init__(cfg)
        service_config = {
            "table_name": "orders",
            "primary_key_fields": ["orderNumber"],
            **cfg,
        }
        self._service = MySQLDataService(service_config)

    def get(self, template: dict) -> OrderCollection:
        rows = self._service.retrieveByTemplate(template)
        return OrderCollection(items=[Order.model_validate(r) for r in rows])

    def get_by_id(self, id: str) -> Order:  # noqa: A002
        row = self._service.retrieveByPrimaryKey(int(id))
        if not row:
            raise ValueError(f"No order with orderNumber {id!r}")
        return Order.model_validate(row)

    def post(self, new_data: Order) -> str:
        data = new_data.model_dump(exclude_none=True, mode="json")
        if "orderNumber" not in data:
            raise ValueError("orderNumber is required (classicmodels has no auto-increment)")
        return self._service.create(data)

    def put(self, character_id: str, new_data: Order) -> int:
        data = new_data.model_dump(exclude_none=True, mode="json")
        data.pop("orderNumber", None)
        return self._service.updateByPrimaryKey(int(character_id), data)

    def delete(self, id: str) -> int:  # noqa: A002
        return self._service.deleteByPrimaryKey(int(id))
