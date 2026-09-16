"""
app_common/scripts/bootstrap_neon.py — migração ÚNICA para o Neon.

Passos (idempotentes — seguro rodar mais de uma vez, nada é apagado):
  1. Cria as tabelas ``postos``, ``Envios_Radar`` e ``Recebimento_Radar`` no
     Neon a partir dos arquivos de migração em ``db_migrations/migrations``
     (CREATE TABLE IF NOT EXISTS).
  2. Carrega os lançamentos de ``postos`` da planilha POSTOS.xlsx no Neon (só
     se o Neon ainda estiver vazio; a dedup por Oficina+MP+Semana+Data Efetivos
     impede duplicata se rodar de novo).
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


def _direct_client() -> NeonClient:
    return NeonClient(_read_dsn(direct=True))


def criar_tabelas(client: NeonClient) -> None:
    print("1) Criando tabelas no Neon (IF NOT EXISTS)...")
    for sql_file in (POSTOS_SQL, ENVIOS_SQL, RECEBIMENTO_SQL):
        client.execute_script(sql_file.read_text(encoding="utf-8"))
        print(f"   [OK] {sql_file.name}")


def carregar_postos(client: NeonClient) -> None:
    print("2) Carregando postos (POSTOS.xlsx) -> Neon...")
    from app_postos.core.config import DATASET_PATH, DATASET_SHEET_NAME
    from app_postos.services.data_writer import insert_bulk_records

    existentes = fetch_all_rows(client, "postos", "id")
    if existentes:
        print(f"   - Neon ja tem {len(existentes)} postos - carga pulada (idempotente).")
        return

    if not DATASET_PATH.exists():
        print(f"   - Planilha nao encontrada em {DATASET_PATH} - pulando postos.")
        return
    df = pd.read_excel(DATASET_PATH, sheet_name=DATASET_SHEET_NAME)
    inseridos = insert_bulk_records(df)
    print(f"   [OK] {inseridos} posto(s) novo(s) inserido(s) (duplicados ignorados).")


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
        carregar_postos(client)
        carregar_envios(client)
        carregar_recebimento(client)
        print("\nConcluído. Neon pronto (postos + Envios_Radar + Recebimento_Radar).")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"\nFALHOU: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
