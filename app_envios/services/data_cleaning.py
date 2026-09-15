"""
services/data_cleaning.py — padroniza e enriquece os dados de envios.

Duas responsabilidades:
  • ``standardize_raw`` — do contrato BRUTO (cabeçalhos da planilha) para o
    contrato snake_case persistido (limpeza de strings, normalização de MP,
    tipos de qtd/minutos, data de envio como datetime). É o que a escrita
    (data_writer) e a leitura (data_loader) têm em comum.
  • ``add_derived`` / ``clean_dataframe`` — deriva ano, mês, semana e dia a
    partir da data de envio, para as granularidades e os gráficos.

Linhas SEM data de envio (a planilha traz ~326) são mantidas: entram nos totais
e na granularidade por MP/Oficina, mas ficam de fora das granularidades
temporais (mês/semana/dia), onde recebem rótulo "Sem data".
"""

from __future__ import annotations

import pandas as pd

from app_envios.core.config import Columns, MP_NORMALIZATION_MAP, RAW_TO_DB_COLUMNS, RawColumns

_MESES_PT = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}

_STRING_COLUMNS = [
    Columns.ORIGEM, Columns.ORDEM, Columns.OFICINA,
    Columns.MP, Columns.PDV, Columns.FRETE, Columns.SITUACAO,
]

SEM_DATA_LABEL = "Sem data"


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


def add_derived(df: pd.DataFrame) -> pd.DataFrame:
    """Deriva ano, ano_mes, mes_label, semana, dia e dia_label da data de envio."""
    df = df.copy()
    envio = pd.to_datetime(df[Columns.ENVIO], errors="coerce")

    iso = envio.dt.isocalendar()
    df[Columns.ANO] = envio.dt.year.astype("Int64")
    df[Columns.SEMANA] = iso["week"].astype("Int64")
    df[Columns.DIA] = envio.dt.normalize()

    periodo = envio.dt.to_period("M")
    df[Columns.ANO_MES] = periodo.astype(str).where(envio.notna(), None)
    df[Columns.MES_LABEL] = envio.apply(
        lambda d: f"{_MESES_PT[d.month]}/{d.year}" if pd.notna(d) else SEM_DATA_LABEL
    )
    df[Columns.DIA_LABEL] = envio.apply(
        lambda d: d.strftime("%d/%m/%Y") if pd.notna(d) else SEM_DATA_LABEL
    )
    return df


def clean_dataframe(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Pipeline completo: padroniza + deriva (usado pela leitura para a UI)."""
    return add_derived(standardize_raw(df_raw))
