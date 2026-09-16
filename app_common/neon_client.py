"""
app_common/neon_client.py — acesso ao banco Neon (Postgres) para todo o app.

Único ponto de acesso ao banco em todo o app. Expõe um ``NeonClient`` com uma
API fluente (``client.table(nome).select(...).eq(...).execute()``, ``.insert()``,
``.update()``) que as camadas de serviço de ``app_postos``, ``app_envios`` e
``app_recebimento`` usam — e que os fakes de teste reproduzem, o que permite
testar a escrita sem tocar no banco real.

Conexão:
    A string de conexão vem dos Secrets do Streamlit, seção ``[neon]``:
        dsn         → endpoint COM pool (‑pooler), usado pelo app em runtime.
        dsn_direct  → endpoint SEM pool, usado para DDL/migração em lote.
    Uma conexão nova e curta é aberta por operação (Neon encerra conexões
    ociosas; conexões curtas evitam erros de socket morto no Streamlit Cloud).
"""

from __future__ import annotations

from typing import Any

import streamlit as st

try:  # psycopg (v3) é o driver oficial; import tardio-friendly.
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # noqa: BLE001 — reportado com mensagem clara ao usar
    psycopg = None  # type: ignore[assignment]
    dict_row = None  # type: ignore[assignment]


class DbConfigError(Exception):
    """Configuração ausente/incompleta do banco Neon (seção [neon] dos Secrets)."""


def _read_dsn(*, direct: bool = False) -> str:
    """Lê a string de conexão do Neon dos Secrets do Streamlit."""
    if psycopg is None:
        raise DbConfigError(
            "O driver 'psycopg' não está instalado. Adicione 'psycopg[binary]' ao "
            "requirements.txt."
        )
    try:
        cfg = st.secrets["neon"]
    except Exception as exc:  # noqa: BLE001 — ex.: secrets.toml ausente
        raise DbConfigError(
            "Nenhuma seção [neon] encontrada nos Secrets do Streamlit. Configure "
            "'dsn' (e opcionalmente 'dsn_direct') em .streamlit/secrets.toml."
        ) from exc

    dsn = cfg.get("dsn_direct") if direct else cfg.get("dsn")
    dsn = dsn or cfg.get("dsn")  # cai para o pooled se não houver direct
    if not dsn:
        raise DbConfigError("Seção [neon] encontrada, mas falta o campo 'dsn'.")
    return dsn


def _qi(identifier: str) -> str:
    """Quota um identificador (tabela/coluna), preservando maiúsculas (ex.: Envios_Radar)."""
    return '"' + str(identifier).replace('"', '""') + '"'


class _Response:
    def __init__(self, data: list[dict]):
        self.data = data


class _Query:
    """Builder que acumula operação + filtros e resolve em ``execute()`` como SQL."""

    def __init__(self, client: "NeonClient", table: str):
        self._client = client
        self._table = table
        self._op = "select"
        self._select_cols = "*"
        self._payload: dict | list[dict] | None = None
        self._where: list[tuple[str, str, Any]] = []  # (col, operador SQL, valor)
        self._limit: int | None = None
        self._offset: int | None = None

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
        self._where.append((col, "=", val))
        return self

    def neq(self, col: str, val: Any) -> "_Query":
        self._where.append((col, "<>", val))
        return self

    def gte(self, col: str, val: Any) -> "_Query":
        self._where.append((col, ">=", val))
        return self

    def lte(self, col: str, val: Any) -> "_Query":
        self._where.append((col, "<=", val))
        return self

    def limit(self, n: int) -> "_Query":
        self._limit = n
        return self

    def range(self, start: int, end: int) -> "_Query":
        # Intervalo INCLUSIVO [start, end] — a convenção que o app já usava.
        self._offset = start
        self._limit = end - start + 1
        return self

    # -- montagem SQL -----------------------------------------------------
    def _where_sql(self) -> tuple[str, list]:
        if not self._where:
            return "", []
        parts, params = [], []
        for col, op, val in self._where:
            parts.append(f"{_qi(col)} {op} %s")
            params.append(val)
        return " WHERE " + " AND ".join(parts), params

    def _build(self) -> tuple[str, list]:
        qtable = _qi(self._table)

        if self._op == "select":
            cols = "*"
            if self._select_cols and self._select_cols != "*":
                cols = ", ".join(_qi(c.strip()) for c in self._select_cols.split(","))
            where_sql, params = self._where_sql()
            sql = f"SELECT {cols} FROM {qtable}{where_sql}"
            if self._limit is not None:
                sql += f" LIMIT {int(self._limit)}"
            if self._offset:
                sql += f" OFFSET {int(self._offset)}"
            return sql, params

        if self._op == "insert":
            rows = self._payload if isinstance(self._payload, list) else [self._payload]
            rows = [r for r in rows if r is not None]
            if not rows:
                return "", []
            cols = list(rows[0].keys())
            col_sql = ", ".join(_qi(c) for c in cols)
            placeholders = "(" + ", ".join(["%s"] * len(cols)) + ")"
            values_sql = ", ".join([placeholders] * len(rows))
            params: list = []
            for r in rows:
                params.extend(r.get(c) for c in cols)
            sql = f"INSERT INTO {qtable} ({col_sql}) VALUES {values_sql} RETURNING *"
            return sql, params

        if self._op == "update":
            payload = self._payload or {}
            set_sql = ", ".join(f"{_qi(c)} = %s" for c in payload.keys())
            params = list(payload.values())
            where_sql, where_params = self._where_sql()
            params.extend(where_params)
            sql = f"UPDATE {qtable} SET {set_sql}{where_sql} RETURNING *"
            return sql, params

        raise ValueError(f"Operação não suportada: {self._op}")

    # -- execução ---------------------------------------------------------
    def execute(self) -> _Response:
        sql, params = self._build()
        if not sql:
            return _Response([])
        rows = self._client._run(sql, params, fetch=True)
        return _Response(rows)


class NeonClient:
    """Client do Neon com a API fluente usada pelo app (SQL por baixo)."""

    def __init__(self, dsn: str):
        self._dsn = dsn

    def table(self, name: str) -> _Query:
        return _Query(self, name)

    def _run(self, sql: str, params: list, *, fetch: bool) -> list[dict]:
        with psycopg.connect(self._dsn, connect_timeout=15, autocommit=True) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, params)
                if cur.description is None:  # comando sem retorno
                    return []
                return list(cur.fetchall())

    def execute_script(self, sql_script: str) -> None:
        """Executa um script DDL (várias instruções separadas por ';')."""
        statements = _split_sql_statements(sql_script)
        with psycopg.connect(self._dsn, connect_timeout=30, autocommit=True) as conn:
            with conn.cursor() as cur:
                for stmt in statements:
                    cur.execute(stmt)


def _split_sql_statements(sql_script: str) -> list[str]:
    """Remove comentários de linha (-- ...) e divide o script em instruções."""
    linhas = []
    for linha in sql_script.splitlines():
        sem_comentario = linha.split("--", 1)[0]
        if sem_comentario.strip():
            linhas.append(sem_comentario)
    texto = "\n".join(linhas)
    return [s.strip() for s in texto.split(";") if s.strip()]


@st.cache_resource(show_spinner=False)
def _cached_client(dsn: str) -> NeonClient:
    return NeonClient(dsn)


def get_db_client(*, direct: bool = False) -> NeonClient:
    """Devolve um ``NeonClient`` para o endpoint pedido (pooled por padrão)."""
    dsn = _read_dsn(direct=direct)
    try:
        return _cached_client(dsn)
    except Exception:  # noqa: BLE001 — fora do runtime do Streamlit (scripts)
        return NeonClient(dsn)


def fetch_all_rows(client: NeonClient, table: str, columns: str = "*") -> list[dict]:
    """Lê TODAS as linhas de ``table`` (paginação não é necessária no Neon)."""
    return client.table(table).select(columns).execute().data
