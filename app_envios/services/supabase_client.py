"""
services/supabase_client.py — acesso ao banco (compatibilidade).

MIGRAÇÃO SUPABASE → NEON: a área Envios usa o Neon (Postgres). Este módulo é uma
fina camada de COMPATIBILIDADE que mantém os nomes históricos
(`get_supabase_client`, `fetch_all_rows`, `SupabaseConfigError`) importados pelo
restante de ``app_envios``, delegando para ``app_common.neon_client``.
A implementação real e única vive em ``app_common/neon_client.py``.
"""

from __future__ import annotations

from app_common.neon_client import (  # noqa: F401 — reexport intencional
    DbConfigError as SupabaseConfigError,
    NeonClient as Client,
    fetch_all_rows,
    get_db_client as get_supabase_client,
)

__all__ = ["SupabaseConfigError", "Client", "fetch_all_rows", "get_supabase_client"]
