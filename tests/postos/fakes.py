"""
tests/postos/fakes.py
---------------------
Fake mínimo do client do banco (``app_common.neon_client.NeonClient``).

Simula a API fluente (`client.table(...).select(...).eq(...).execute()`) sobre
listas de dicts EM MEMÓRIA — os testes NUNCA tocam o banco remoto de produção.
Suporta apenas os operadores efetivamente usados pela aplicação.
"""

from __future__ import annotations

import copy
import itertools
from typing import Any, Callable


class _Response:
    def __init__(self, data: list[dict]):
        self.data = data


class _Query:
    """Builder que acumula operação + filtros e resolve em `execute()`."""

    def __init__(self, table: "_FakeTable"):
        self._table = table
        self._op = "select"
        self._select_cols = "*"
        self._payload: dict | list[dict] | None = None
        self._filters: list[Callable[[dict], bool]] = []
        self._limit: int | None = None
        self._range: tuple[int, int] | None = None

    # -- operações --------------------------------------------------------
    def select(self, cols: str = "*") -> "_Query":
        self._op = "select"
        self._select_cols = cols
        return self

    def insert(self, payload: dict | list[dict]) -> "_Query":
        self._op = "insert"
        self._payload = payload
        return self

    def update(self, payload: dict) -> "_Query":
        self._op = "update"
        self._payload = payload
        return self

    # -- filtros ----------------------------------------------------------
    def eq(self, col: str, val: Any) -> "_Query":
        self._filters.append(lambda r: r.get(col) == val)
        return self

    def neq(self, col: str, val: Any) -> "_Query":
        self._filters.append(lambda r: r.get(col) != val)
        return self

    def gte(self, col: str, val: Any) -> "_Query":
        self._filters.append(lambda r: r.get(col) is not None and str(r.get(col)) >= str(val))
        return self

    def lte(self, col: str, val: Any) -> "_Query":
        self._filters.append(lambda r: r.get(col) is not None and str(r.get(col)) <= str(val))
        return self

    def limit(self, n: int) -> "_Query":
        self._limit = n
        return self

    def range(self, start: int, end: int) -> "_Query":
        self._range = (start, end)
        return self

    # -- execução ---------------------------------------------------------
    def _apply_filters(self, rows: list[dict]) -> list[dict]:
        out = rows
        for pred in self._filters:
            out = [r for r in out if pred(r)]
        return out

    def execute(self) -> _Response:
        rows = self._table.rows

        if self._op == "insert":
            payloads = self._payload if isinstance(self._payload, list) else [self._payload]
            inserted: list[dict] = []
            for p in payloads:
                record = copy.deepcopy(p)
                record.setdefault("id", self._table.next_id())
                rows.append(record)
                inserted.append(copy.deepcopy(record))
            return _Response(inserted)

        if self._op == "update":
            matched = self._apply_filters(rows)
            for r in matched:
                r.update(copy.deepcopy(self._payload or {}))
            return _Response([copy.deepcopy(r) for r in matched])

        # select
        matched = self._apply_filters(rows)
        if self._range is not None:
            start, end = self._range
            matched = matched[start : end + 1]
        if self._limit is not None:
            matched = matched[: self._limit]
        if self._select_cols and self._select_cols != "*":
            cols = [c.strip() for c in self._select_cols.split(",")]
            matched = [{c: r.get(c) for c in cols} for r in matched]
        else:
            matched = [copy.deepcopy(r) for r in matched]
        return _Response(matched)


class _FakeTable:
    def __init__(self, rows: list[dict], counter: "itertools.count[int]"):
        self.rows = rows
        self._counter = counter

    def next_id(self) -> int:
        return next(self._counter)

    def select(self, cols: str = "*") -> _Query:
        return _Query(self).select(cols)

    def insert(self, payload: dict | list[dict]) -> _Query:
        return _Query(self).insert(payload)

    def update(self, payload: dict) -> _Query:
        return _Query(self).update(payload)


class FakeNeonClient:
    """Client fake: `client.table(nome)` devolve um builder sobre memória."""

    def __init__(self, tables: dict[str, list[dict]] | None = None):
        self._tables: dict[str, list[dict]] = {}
        self._counters: dict[str, "itertools.count[int]"] = {}
        for name, rows in (tables or {}).items():
            self._tables[name] = [copy.deepcopy(r) for r in rows]
            max_id = max((int(r["id"]) for r in rows if "id" in r), default=0)
            self._counters[name] = itertools.count(max_id + 1)

    def table(self, name: str) -> _FakeTable:
        if name not in self._tables:
            self._tables[name] = []
            self._counters[name] = itertools.count(1)
        return _FakeTable(self._tables[name], self._counters[name])

    def rows(self, name: str) -> list[dict]:
        """Acesso direto às linhas de uma tabela — para asserções nos testes."""
        return self._tables.get(name, [])
