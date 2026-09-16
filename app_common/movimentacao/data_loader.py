"""
app_common/movimentacao/data_loader.py — leitura das tabelas de movimentação.

Lê a tabela da área no Neon e devolve um DataFrame já PADRONIZADO e ENRIQUECIDO
(colunas derivadas de data), pronto para a camada de análise/UI. Isola o resto
do app da fonte de dados: trocar o motor do banco não sai deste arquivo.
"""

from __future__ import annotations

import pandas as pd

from app_common.movimentacao.area import AreaMovimentacao, ColunasMovimentacao as C
from app_common.movimentacao.derivacao import add_derived
from app_common.neon_client import DbConfigError, fetch_all_rows, get_db_client

# Colunas criadas pelo banco e irrelevantes para a análise.
_COLUNAS_TECNICAS = ["id", "created_at"]


class DataLoadError(Exception):
    """Falha na leitura/validação da fonte de dados de uma área de movimentação."""


class EmptyDataError(DataLoadError):
    """Tabela acessível e válida, mas ainda sem nenhum registro (1º uso)."""


def empty_dataframe(area: AreaMovimentacao) -> pd.DataFrame:
    """DataFrame vazio com o contrato de colunas completo (persistidas + derivadas)."""
    base = pd.DataFrame(columns=area.colunas_persistidas)
    base[area.coluna_data] = pd.to_datetime(base[area.coluna_data], errors="coerce")
    base[C.QTD] = base[C.QTD].astype("int64")
    base[C.MINUTOS] = base[C.MINUTOS].astype("float64")
    return add_derived(base, coluna_data=area.coluna_data)


def load_clean_dataframe(area: AreaMovimentacao, *, client=None) -> pd.DataFrame:
    """Lê todos os registros da área no Neon e devolve o DataFrame limpo/derivado."""
    if client is None:
        try:
            client = get_db_client()
        except DbConfigError as exc:
            raise DataLoadError(str(exc)) from exc

    try:
        rows = fetch_all_rows(client, area.tabela)
    except Exception as exc:  # noqa: BLE001 — convertido em mensagem de tela
        raise DataLoadError(f"Falha ao ler os dados do banco: {exc}") from exc

    if not rows:
        raise EmptyDataError(
            f"A tabela '{area.tabela}' no banco não contém nenhum registro. "
            "Use a página de Lançamento de Dados para importar a planilha."
        )

    df = pd.DataFrame(rows).drop(columns=_COLUNAS_TECNICAS, errors="ignore")

    faltando = [c for c in area.colunas_persistidas if c not in df.columns]
    if faltando:
        raise DataLoadError(
            f"Os dados de '{area.tabela}' estão sem as colunas obrigatórias: "
            f"{faltando}. Colunas encontradas: {list(df.columns)}"
        )

    try:
        df[area.coluna_data] = pd.to_datetime(df[area.coluna_data], errors="coerce")
        df[C.QTD] = pd.to_numeric(df[C.QTD], errors="coerce").fillna(0).astype("int64")
        df[C.MINUTOS] = pd.to_numeric(df[C.MINUTOS], errors="coerce").fillna(0.0)
    except Exception as exc:  # noqa: BLE001 — convertido em mensagem de tela
        raise DataLoadError(f"Erro ao converter tipos vindos do banco: {exc}") from exc

    return add_derived(df, coluna_data=area.coluna_data)
