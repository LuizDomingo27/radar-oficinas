"""
scripts/migrate_excel_to_supabase.py — carga inicial da planilha de envios.

Popula a tabela ``Envios_Radar`` do Supabase a partir de ENVIOS_OFICINAS.xlsx,
reaproveitando ``services.data_writer.insert_bulk_records`` — a MESMA rotina
(e a mesma deduplicação por row_hash) usada pela tela de Importação em Lote.

Pré-requisitos:
    1. Tabela ``Envios_Radar`` já criada no Supabase (aplique a migração
       db_migrations/migrations/20260915120000_create_envios_radar_table.sql
       no SQL Editor do Supabase).
    2. ``.streamlit/secrets.toml`` com a seção [supabase] preenchida.

Uso:
    python -m app_envios.scripts.migrate_excel_to_supabase [caminho_do_excel]
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from app_envios.core.config import DATASET_PATH, DATASET_SHEET_NAME  # noqa: E402
from app_envios.services.data_writer import insert_bulk_records  # noqa: E402


def run_migration(excel_path: Path = DATASET_PATH) -> bool:
    print(f"Iniciando carga de {excel_path.name} para a tabela Envios_Radar...")

    if not excel_path.exists():
        print(f"Erro: planilha não encontrada em: {excel_path}")
        return False

    try:
        df = pd.read_excel(excel_path, sheet_name=DATASET_SHEET_NAME)
        print(f"Planilha carregada. Total de linhas: {len(df)}")
    except Exception as exc:  # noqa: BLE001
        print(f"Erro ao ler a planilha: {exc}")
        return False

    try:
        inseridos = insert_bulk_records(df)
        print(f"Carga concluída. {inseridos} novo(s) envio(s) inserido(s) (duplicados ignorados).")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"Erro durante a gravação no Supabase: {exc}")
        return False


if __name__ == "__main__":
    excel_arg = Path(sys.argv[1]) if len(sys.argv) > 1 else DATASET_PATH
    ok = run_migration(excel_arg)
    sys.exit(0 if ok else 1)
