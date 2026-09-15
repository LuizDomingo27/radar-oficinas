"""
services/data_loader.py — lê os recebimentos da tabela ``Recebimento_Radar`` (Neon).

Devolve um DataFrame já PADRONIZADO e ENRIQUECIDO (colunas derivadas de data),
pronto para a camada de análise/UI. Isola o resto do app da fonte de dados.
"""

from __future__ import annotations

import pandas as pd

from app_recebimento.core.config import Columns, DB_COLUMNS_PERSISTED, DB_TABLE_RECEBIMENTO
from app_recebimento.services.data_cleaning import add_derived
from app_recebimento.services.db_client import (
    DbConfigError,
    fetch_all_rows,
    get_db_client,
)

# Colunas mínimas esperadas ao ler a tabela.
REQUIRED_DB_COLUMNS = list(DB_COLUMNS_PERSISTED)


class DataLoadError(Exception):
    """Falha na leitura/validação da fonte de dados de recebimento."""


class EmptyDataError(DataLoadError):
    """Tabela acessível e válida, mas ainda sem nenhum registro (1º uso)."""


def empty_dataframe() -> pd.DataFrame:
    """DataFrame vazio com o contrato de colunas completo (persistidas + derivadas)."""
    base = pd.DataFrame(columns=DB_COLUMNS_PERSISTED)
    base[Columns.RECEBIMENTO] = pd.to_datetime(base[Columns.RECEBIMENTO], errors="coerce")
    base[Columns.QTD] = base[Columns.QTD].astype("int64")
    base[Columns.MINUTOS] = base[Columns.MINUTOS].astype("float64")
    return add_derived(base)


def load_clean_dataframe() -> pd.DataFrame:
    """Lê todos os recebimentos do Neon e devolve o DataFrame limpo/derivado."""
    try:
        client = get_db_client()
    except DbConfigError as exc:
        raise DataLoadError(str(exc)) from exc

    try:
        rows = fetch_all_rows(client, DB_TABLE_RECEBIMENTO)
    except Exception as exc:  # noqa: BLE001
        raise DataLoadError(f"Falha ao ler os dados do banco: {exc}") from exc

    if not rows:
        raise EmptyDataError(
            f"A tabela '{DB_TABLE_RECEBIMENTO}' no banco não contém nenhum "
            "registro. Use a página de Lançamento de Dados para importar a planilha."
        )

    df = pd.DataFrame(rows).drop(columns=["id", "created_at"], errors="ignore")

    faltando = [c for c in REQUIRED_DB_COLUMNS if c not in df.columns]
    if faltando:
        raise DataLoadError(
            f"Os dados de '{DB_TABLE_RECEBIMENTO}' estão sem as colunas "
            f"obrigatórias: {faltando}. Colunas encontradas: {list(df.columns)}"
        )

    try:
        df[Columns.RECEBIMENTO] = pd.to_datetime(df[Columns.RECEBIMENTO], errors="coerce")
        df[Columns.QTD] = pd.to_numeric(df[Columns.QTD], errors="coerce").fillna(0).astype("int64")
        df[Columns.MINUTOS] = pd.to_numeric(df[Columns.MINUTOS], errors="coerce").fillna(0.0)
    except Exception as exc:  # noqa: BLE001
        raise DataLoadError(f"Erro ao converter tipos vindos do banco: {exc}") from exc

    return add_derived(df)
