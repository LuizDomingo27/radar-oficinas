"""
services/data_cleaning.py — padroniza os dados brutos da planilha de envios.

``standardize_raw`` leva do contrato BRUTO (cabeçalhos de ENVIOS_OFICINAS.xlsx)
para o contrato snake_case persistido: limpeza de strings, normalização de MP,
tipos de qtd/minutos e data de envio como datetime. É o que a escrita
(``data_writer``) e a leitura (``data_loader``) têm em comum.

A derivação de período (ano, mês, semana, dia) NÃO está aqui: é idêntica em
Envios e Recebimento e vive em ``app_common.movimentacao.derivacao``.
"""

from __future__ import annotations

import pandas as pd

from app_envios.core.config import Columns, MP_NORMALIZATION_MAP, RAW_TO_DB_COLUMNS

_STRING_COLUMNS = [
    Columns.ORIGEM, Columns.ORDEM, Columns.OFICINA,
    Columns.MP, Columns.PDV, Columns.FRETE, Columns.SITUACAO,
]


def _strip_and_normalize_headers(df: pd.DataFrame) -> pd.DataFrame:
    """Remove espaços dos cabeçalhos (a planilha às vezes traz sobras)."""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def standardize_raw(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Converte o DataFrame BRUTO para o contrato snake_case persistido."""
    df = _strip_and_normalize_headers(df_raw)

    faltando = [c for c in RAW_TO_DB_COLUMNS if c not in df.columns]
    if faltando:
        raise ValueError(
            f"A planilha de envios está sem as colunas obrigatórias: {faltando}. "
            f"Colunas encontradas: {list(df.columns)}"
        )

    df = df[list(RAW_TO_DB_COLUMNS.keys())].rename(columns=RAW_TO_DB_COLUMNS)

    for col in _STRING_COLUMNS:
        df[col] = df[col].astype(str).str.strip()

    df[Columns.MP] = df[Columns.MP].str.upper().replace(MP_NORMALIZATION_MAP)

    df[Columns.QTD] = pd.to_numeric(df[Columns.QTD], errors="coerce").fillna(0).astype("int64")
    df[Columns.MINUTOS] = (
        pd.to_numeric(df[Columns.MINUTOS], errors="coerce").fillna(0.0).round(2)
    )
    df[Columns.ENVIO] = pd.to_datetime(df[Columns.ENVIO], errors="coerce")

    return df.reset_index(drop=True)
