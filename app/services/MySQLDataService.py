from __future__ import annotations

import os
from typing import Any

import pymysql
from pymysql.cursors import DictCursor

from .AbstractBaseDataService import AbstractBaseDataService


class MySQLDataService(AbstractBaseDataService):
    """Persists records in a MySQL table.

    Required config keys:
        - table_name: table to read/write
        - primary_key_fields: list of PK column names (single-column tables use a one-element list)

    Optional config keys (fall back to environment variables):
        - host (env MYSQL_HOST, default "localhost")
        - port (env MYSQL_PORT, default 3306)
        - user (env MYSQL_USER, default "root")
        - password (env MYSQL_PASSWORD, default "")
        - database (env MYSQL_DATABASE, default "classicmodels")
        - auto_increment_pk: bool — when True, omit PK on INSERT and return lastrowid
    """

    def __init__(self, config: dict) -> None:
        super().__init__(config)

        if "table_name" not in config:
            raise ValueError("MySQLDataService config requires 'table_name'")
        self._table = str(config["table_name"])

        pk_fields = config.get("primary_key_fields")
        if pk_fields is None:
            pk_fields = [str(config.get("primary_key_field", "id"))]
        if isinstance(pk_fields, str):
            pk_fields = [pk_fields]
        self._pk_fields: list[str] = [str(f) for f in pk_fields]
        if not self._pk_fields:
            raise ValueError("MySQLDataService requires at least one primary key field")

        self._auto_increment_pk: bool = bool(config.get("auto_increment_pk", False))

        self._conn_kwargs = {
            "host": str(config.get("host", os.getenv("MYSQL_HOST", "localhost"))),
            "port": int(config.get("port", os.getenv("MYSQL_PORT", "3306"))),
            "user": str(config.get("user", os.getenv("MYSQL_USER", "root"))),
            "password": str(config.get("password", os.getenv("MYSQL_PASSWORD", ""))),
            "database": str(config.get("database", os.getenv("MYSQL_DATABASE", "classicmodels"))),
            "cursorclass": DictCursor,
            "autocommit": True,
        }

    def _connect(self) -> pymysql.connections.Connection:
        return pymysql.connect(**self._conn_kwargs)

    def _qident(self, name: str) -> str:
        # Backtick-quote identifiers; reject backticks in caller-supplied names.
        if "`" in name:
            raise ValueError(f"Invalid identifier: {name!r}")
        return f"`{name}`"

    def _normalize_pk(self, primary_key: Any) -> dict[str, Any]:
        if isinstance(primary_key, dict):
            pk = {k: primary_key[k] for k in self._pk_fields if k in primary_key}
            missing = [k for k in self._pk_fields if k not in pk]
            if missing:
                raise ValueError(f"Missing primary key parts: {missing}")
            return pk
        if len(self._pk_fields) != 1:
            raise ValueError(
                f"Table {self._table!r} has composite PK {self._pk_fields}; "
                "pass a dict to retrieve/update/delete by primary key"
            )
        return {self._pk_fields[0]: primary_key}

    def _where_pk(self, pk: dict[str, Any]) -> tuple[str, list[Any]]:
        clauses = [f"{self._qident(k)} = %s" for k in self._pk_fields]
        params = [pk[k] for k in self._pk_fields]
        return " AND ".join(clauses), params

    def retrieveByPrimaryKey(self, primary_key: Any) -> dict:
        pk = self._normalize_pk(primary_key)
        where, params = self._where_pk(pk)
        sql = f"SELECT * FROM {self._qident(self._table)} WHERE {where} LIMIT 1"
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                row = cur.fetchone()
        return dict(row) if row else {}

    def retrieveByTemplate(self, template: dict) -> list[dict]:
        if template:
            clauses = [f"{self._qident(k)} = %s" for k in template]
            where = " WHERE " + " AND ".join(clauses)
            params = list(template.values())
        else:
            where = ""
            params = []
        sql = f"SELECT * FROM {self._qident(self._table)}{where}"
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
        return [dict(r) for r in rows]

    def create(self, payload: dict) -> str:
        data = {k: v for k, v in payload.items() if v is not None or not self._auto_increment_pk or k not in self._pk_fields}
        if self._auto_increment_pk:
            for k in self._pk_fields:
                data.pop(k, None)

        if not data:
            raise ValueError("create() requires at least one column value")

        cols = list(data.keys())
        col_sql = ", ".join(self._qident(c) for c in cols)
        placeholders = ", ".join(["%s"] * len(cols))
        sql = f"INSERT INTO {self._qident(self._table)} ({col_sql}) VALUES ({placeholders})"
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, list(data.values()))
                last_id = cur.lastrowid

        if self._auto_increment_pk and len(self._pk_fields) == 1:
            return str(last_id)

        # Composite or caller-supplied PK: stitch the values together for the return.
        pk_values = [str(payload.get(k, "")) for k in self._pk_fields]
        return ",".join(pk_values)

    def updateByPrimaryKey(self, primary_key: Any, payload: dict) -> int:
        pk = self._normalize_pk(primary_key)
        # Don't allow PK columns to be rewritten via the update body.
        data = {k: v for k, v in payload.items() if k not in self._pk_fields}
        if not data:
            return 0
        set_sql = ", ".join(f"{self._qident(c)} = %s" for c in data)
        where, where_params = self._where_pk(pk)
        sql = f"UPDATE {self._qident(self._table)} SET {set_sql} WHERE {where}"
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, list(data.values()) + where_params)
                return cur.rowcount

    def deleteByPrimaryKey(self, primary_key: Any) -> int:
        pk = self._normalize_pk(primary_key)
        where, params = self._where_pk(pk)
        sql = f"DELETE FROM {self._qident(self._table)} WHERE {where}"
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.rowcount
