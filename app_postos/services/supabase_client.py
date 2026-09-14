"""
services/supabase_client.py
-----------------------------
Responsabilidade única: criar e expor um client Supabase único (singleton)
para toda a aplicação, e paginar leituras que excedam o limite padrão de
resposta do PostgREST.

Por que service_role e não anon key:
    Esta é uma aplicação interna sem autenticação de usuário final — todas as
    leituras/gravações são feitas pelo servidor Streamlit. A service_role key
    ignora Row Level Security, então NUNCA deve ser exposta ao navegador: ela
    só existe aqui, no backend Python, lida a partir dos Secrets do Streamlit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

if TYPE_CHECKING:  # apenas para type hints — não exige a lib instalada em runtime/testes
    from supabase import Client

# Tamanho de página usado ao ler tabelas inteiras. O PostgREST (API do
# Supabase) limita cada resposta a 1000 linhas por padrão — sem paginação,
# tabelas maiores que isso teriam dados truncados silenciosamente.
_PAGE_SIZE = 1000


class SupabaseConfigError(Exception):
    """Erro de domínio para configuração ausente/incompleta do Supabase."""


@st.cache_resource(show_spinner=False)
def get_supabase_client() -> Client:
    """
    Devolve um client Supabase cacheado (uma única conexão reaproveitada
    entre reruns do Streamlit).
    """
    try:
        cfg = st.secrets["supabase"]
    except Exception as exc:  # noqa: BLE001 — ex.: secrets.toml ausente/malformado
        raise SupabaseConfigError(
            "Nenhuma seção [supabase] encontrada nos Secrets do Streamlit. "
            "Configure 'url' e 'service_role_key' em .streamlit/secrets.toml "
            "(veja .streamlit/secrets.toml.example)."
        ) from exc

    url = cfg.get("url")
    key = cfg.get("service_role_key")
    faltando = [nome for nome, valor in (("url", url), ("service_role_key", key)) if not valor]
    if faltando:
        raise SupabaseConfigError(
            f"Seção [supabase] encontrada, mas faltam os campos: {', '.join(faltando)}."
        )

    # Import tardio: a dependência `supabase` só é necessária quando de fato
    # criamos uma conexão real (produção). Isso mantém os módulos que apenas
    # importam este arquivo — e os testes com client injetado — livres da lib.
    from supabase import create_client

    return create_client(url, key)


def fetch_all_rows(client: Client, table: str, columns: str = "*") -> list[dict]:
    """Lê TODAS as linhas de `table`, paginando em blocos de `_PAGE_SIZE`."""
    rows: list[dict] = []
    start = 0
    while True:
        response = (
            client.table(table).select(columns).range(start, start + _PAGE_SIZE - 1).execute()
        )
        batch = response.data or []
        rows.extend(batch)
        if len(batch) < _PAGE_SIZE:
            break
        start += _PAGE_SIZE
    return rows
