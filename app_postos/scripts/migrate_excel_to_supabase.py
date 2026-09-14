"""
scripts/migrate_excel_to_supabase.py
--------------------------------------
Script utilitário para popular a tabela `postos` do Supabase a partir da
planilha Excel original (POSTOS.xlsx). Reaproveita
`services.data_writer.insert_bulk_records` — a mesma rotina usada pela tela
de Importação em Lote — garantindo que a deduplicação (Oficina + MP +
Semana) seja idêntica nos dois caminhos.

Pré-requisitos:
    1. A tabela `postos` já criada no Supabase
       (ver `supabase/migrations/20260720120000_create_postos_table.sql`).
    2. `.streamlit/secrets.toml` com a seção [supabase] preenchida
       (ver `.streamlit/secrets.toml.example`).

Uso:
    python -m scripts.migrate_excel_to_supabase [caminho_do_excel]
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))  # permite rodar como `python scripts/migrate_excel_to_supabase.py`

from app_postos.core.config import DATASET_PATH, DATASET_SHEET_NAME  # noqa: E402
from app_postos.services.data_writer import insert_bulk_records  # noqa: E402


def run_migration(excel_path: Path = DATASET_PATH) -> bool:
    """Lê a planilha e insere no Supabase os registros ainda não existentes."""
    print(f"Iniciando migração de {excel_path.name} para o Supabase...")

    if not excel_path.exists():
        print(f"Erro: Arquivo Excel não encontrado em: {excel_path}")
        return False

    try:
        df = pd.read_excel(excel_path, sheet_name=DATASET_SHEET_NAME)
        print(f"Excel carregado com sucesso. Total de linhas: {len(df)}")
    except Exception as exc:
        print(f"Erro ao ler o arquivo Excel: {exc}")
        return False

    try:
        inseridos = insert_bulk_records(df)
        print(
            f"Migração concluída. {inseridos} novo(s) registro(s) inserido(s) "
            "no Supabase (duplicados ignorados)."
        )
        return True
    except Exception as exc:
        print(f"Erro durante a gravação no Supabase: {exc}")
        return False


if __name__ == "__main__":
    excel_arg = Path(sys.argv[1]) if len(sys.argv) > 1 else DATASET_PATH
    run_migration(excel_arg)
