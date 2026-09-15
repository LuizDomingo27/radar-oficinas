"""
app_common/scripts/bootstrap_neon.py — migração ÚNICA para o Neon.

Passos (idempotentes — seguro rodar mais de uma vez, nada é apagado):
  1. Cria as tabelas ``postos``, ``Envios_Radar`` e ``Recebimento_Radar`` no
     Neon a partir dos arquivos de migração em ``db_migrations/migrations``
     (CREATE TABLE IF NOT EXISTS).
  2. Migra os lançamentos de ``postos`` do Supabase -> Neon (só se o Neon ainda
     estiver vazio). A leitura do Supabase usa a service_role key, que continua
     válida mesmo sem a senha do projeto.
  3. Carrega os envios da planilha ENVIOS_OFICINAS.xlsx no Neon (dedup por
     row_hash — reexecutar não duplica).
  4. Carrega os recebimentos da planilha RECEBIMENTO.xlsx no Neon (mesma
     dedup por row_hash — reexecutar não duplica).

Uso:
    python -m app_common.scripts.bootstrap_neon
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from app_common.neon_client import NeonClient, _read_dsn, fetch_all_rows  # noqa: E402

MIGRATIONS_DIR = BASE_DIR / "db_migrations" / "migrations"
POSTOS_SQL = MIGRATIONS_DIR / "20260720120000_create_postos_table.sql"
ENVIOS_SQL = MIGRATIONS_DIR / "20260915120000_create_envios_radar_table.sql"
RECEBIMENTO_SQL = MIGRATIONS_DIR / "20260916120000_create_recebimento_radar_table.sql"

POSTOS_BUSINESS_COLS = [
    "frete", "mp", "oficina", "data_efetivos", "qtd_efetivos",
    "data_trabalhados", "qtd_trabalhados", "contratacoes", "demissoes", "semana",
]
_BATCH = 500


def _direct_client() -> NeonClient:
    return NeonClient(_read_dsn(direct=True))


def criar_tabelas(client: NeonClient) -> None:
    print("1) Criando tabelas no Neon (IF NOT EXISTS)...")
    for sql_file in (POSTOS_SQL, ENVIOS_SQL, RECEBIMENTO_SQL):
        client.execute_script(sql_file.read_text(encoding="utf-8"))
        print(f"   [OK] {sql_file.name}")


def _read_supabase_postos() -> list[dict]:
    """Lê todos os postos do Supabase (paginado) usando a service_role key."""
    import streamlit as st
    from supabase import create_client

    cfg = st.secrets["supabase"]
    sb = create_client(cfg["url"], cfg["service_role_key"])
    rows: list[dict] = []
    start, page = 0, 1000
    while True:
        resp = sb.table("postos").select("*").range(start, start + page - 1).execute()
        batch = resp.data or []
        rows.extend(batch)
        if len(batch) < page:
            break
        start += page
    return rows


def migrar_postos(client: NeonClient) -> None:
    print("2) Migrando 'postos' Supabase -> Neon...")
    existentes = fetch_all_rows(client, "postos", "id")
    if existentes:
        print(f"   - Neon já tem {len(existentes)} postos — migração pulada (idempotente).")
        return

    origem = _read_supabase_postos()
    print(f"   - Lidos {len(origem)} postos do Supabase.")
    if not origem:
        print("   - Nada a migrar.")
        return

    payload = [{c: r.get(c) for c in POSTOS_BUSINESS_COLS} for r in origem]
    inseridos = 0
    for i in range(0, len(payload), _BATCH):
        lote = payload[i : i + _BATCH]
        client.table("postos").insert(lote).execute()
        inseridos += len(lote)
    print(f"   [OK] {inseridos} postos inseridos no Neon.")


def carregar_envios(client: NeonClient) -> None:
    print("3) Carregando envios (ENVIOS_OFICINAS.xlsx) -> Neon...")
    from app_envios.core.config import DATASET_PATH, DATASET_SHEET_NAME
    from app_envios.services.data_writer import insert_bulk_records

    if not DATASET_PATH.exists():
        print(f"   - Planilha não encontrada em {DATASET_PATH} — pulando envios.")
        return
    df = pd.read_excel(DATASET_PATH, sheet_name=DATASET_SHEET_NAME)
    inseridos = insert_bulk_records(df, client=client)
    print(f"   [OK] {inseridos} envio(s) novo(s) inserido(s) (duplicados ignorados).")


def carregar_recebimento(client: NeonClient) -> None:
    print("4) Carregando recebimentos (RECEBIMENTO.xlsx) -> Neon...")
    from app_recebimento.core.config import DATASET_PATH, DATASET_SHEET_NAME
    from app_recebimento.services.data_writer import insert_bulk_records

    if not DATASET_PATH.exists():
        print(f"   - Planilha não encontrada em {DATASET_PATH} — pulando recebimentos.")
        return
    df = pd.read_excel(DATASET_PATH, sheet_name=DATASET_SHEET_NAME)
    inseridos = insert_bulk_records(df, client=client)
    print(f"   [OK] {inseridos} recebimento(s) novo(s) inserido(s) (duplicados ignorados).")


def main() -> int:
    try:
        client = _direct_client()
        criar_tabelas(client)
        migrar_postos(client)
        carregar_envios(client)
        carregar_recebimento(client)
        print("\nConcluído. Neon pronto (postos + Envios_Radar + Recebimento_Radar).")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"\nFALHOU: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
