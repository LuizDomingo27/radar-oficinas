"""
services/supabase_client.py — acesso ao banco (compatibilidade).

MIGRAÇÃO SUPABASE → NEON: o app deixou de usar o Supabase (a senha do projeto foi
perdida) e passou a usar o Neon (Postgres). Este módulo virou uma fina camada de
COMPATIBILIDADE: mantém os nomes históricos (`get_supabase_client`,
`fetch_all_rows`, `SupabaseConfigError`) que o restante de ``app_postos`` importa,
mas por baixo delega tudo para ``app_common.neon_client`` (SQL via psycopg).

Manter os nomes evita tocar em data_loader/data_writer/record_service e nos testes
(cujo fake implementa a mesma API fluente). A implementação real e única do acesso
ao banco vive em ``app_common/neon_client.py``.
"""

from __future__ import annotations

from app_common.neon_client import (  # noqa: F401 — reexport intencional
    DbConfigError as SupabaseConfigError,
    NeonClient as Client,
    fetch_all_rows,
    get_db_client as get_supabase_client,
)

__all__ = ["SupabaseConfigError", "Client", "fetch_all_rows", "get_supabase_client"]
