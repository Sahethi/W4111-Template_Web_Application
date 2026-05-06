from __future__ import annotations

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from .AbstractBaseResource import AbstractBaseResource
from ..services.MySQLDataService import MySQLDataService


class Customer(BaseModel):
    customerNumber: Optional[int] = None
    customerName: str = ""
    contactLastName: str = ""
    contactFirstName: str = ""
    phone: str = ""
    addressLine1: str = ""
    addressLine2: Optional[str] = None
    city: str = ""
    state: Optional[str] = None
    postalCode: Optional[str] = None
    country: str = ""
    salesRepEmployeeNumber: Optional[int] = None
    creditLimit: Optional[Decimal] = None


class CustomerCollection(BaseModel):
    items: list[Customer] = Field(default_factory=list)


class CustomerResource(AbstractBaseResource):
    def __init__(self, config: dict | None = None) -> None:
        cfg = dict(config or {})
        super().__init__(cfg)
        service_config = {
            "table_name": "customers",
            "primary_key_fields": ["customerNumber"],
            **cfg,
        }
        self._service = MySQLDataService(service_config)

    def get(self, template: dict) -> CustomerCollection:
        rows = self._service.retrieveByTemplate(template)
        return CustomerCollection(items=[Customer.model_validate(r) for r in rows])

    def get_by_id(self, id: str) -> Customer:  # noqa: A002
        row = self._service.retrieveByPrimaryKey(int(id))
        if not row:
            raise ValueError(f"No customer with customerNumber {id!r}")
        return Customer.model_validate(row)

    def post(self, new_data: Customer) -> str:
        data = new_data.model_dump(exclude_none=True)
        if "customerNumber" not in data:
            raise ValueError("customerNumber is required (classicmodels has no auto-increment)")
        return self._service.create(data)

    def put(self, character_id: str, new_data: Customer) -> int:
        data = new_data.model_dump(exclude_none=True)
        data.pop("customerNumber", None)
        return self._service.updateByPrimaryKey(int(character_id), data)

    def delete(self, id: str) -> int:  # noqa: A002
        return self._service.deleteByPrimaryKey(int(id))
