"""
services/db_client.py — acesso ao banco Neon (Postgres) da área "Recebimento".

Camada fina de conveniência que reexporta o client único do app
(``app_common.neon_client``) com nomes locais, para o restante de
``app_recebimento`` não depender diretamente do módulo comum. A implementação
real (conexão psycopg, API fluente estilo PostgREST) vive em
``app_common/neon_client.py``.
"""

from __future__ import annotations

from app_common.neon_client import (  # noqa: F401 — reexport intencional
    DbConfigError,
    NeonClient as Client,
    fetch_all_rows,
    get_db_client,
)

__all__ = ["DbConfigError", "Client", "fetch_all_rows", "get_db_client"]
