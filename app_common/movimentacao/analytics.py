"""
app_common/movimentacao/analytics.py — agregações das áreas de movimentação.

Concentra toda a regra de agregação (peças e minutos) consumida pela UI: KPIs,
granularidade por dimensão (MP, Oficina, Mês, Semana, Dia), ranking das oficinas
por volume e as séries por mês/semana dos gráficos.

Não conhece Streamlit — recebe e entrega DataFrames. A única coisa que varia
entre as áreas é a coluna de data, recebida como parâmetro.
"""

from __future__ import annotations

import pandas as pd

from app_common.movimentacao.area import (
    COLUNA_REGISTROS,
    COLUNA_ROTULO,
    GRANULARIDADES_TEMPORAIS,
    ColunasMovimentacao as C,
)

# Como cada granularidade é agrupada: (coluna-chave, coluna-rótulo, coluna-ordenação).
_GRAN_SPEC = {
    "mp": (C.MP, C.MP, C.MP),
    "oficina": (C.OFICINA, C.OFICINA, C.OFICINA),
    "mes": (C.ANO_MES, C.MES_LABEL, C.ANO_MES),
    "semana": (C.SEMANA, C.SEMANA, C.SEMANA),
    "dia": (C.DIA, C.DIA_LABEL, C.DIA),
}

_COLUNAS_AGREGADAS = [COLUNA_ROTULO, C.QTD, C.MINUTOS, COLUNA_REGISTROS]
_COLUNAS_SERIE = [COLUNA_ROTULO, C.QTD, C.MINUTOS]


def compute_kpis(df: pd.DataFrame) -> dict:
    """Totais globais do recorte filtrado (para os cards)."""
    if df.empty:
        return {"pecas": 0, "minutos": 0.0, "registros": 0, "oficinas": 0, "ordens": 0}
    return {
        "pecas": int(df[C.QTD].sum()),
        "minutos": float(df[C.MINUTOS].sum()),
        "registros": int(len(df)),
        "oficinas": int(df[C.OFICINA].nunique()),
        "ordens": int(df[C.ORDEM].nunique()),
    }


def aggregate_by(df: pd.DataFrame, granularity_key: str, *, coluna_data: str) -> pd.DataFrame:
    """
    Soma peças e minutos por dimensão. Retorna colunas:
      rotulo · qtd · minutos · registros

    Para dimensões temporais (mês/semana/dia), linhas sem data são excluídas
    (não há período onde colocá-las); para MP/Oficina, tudo entra.
    """
    if granularity_key not in _GRAN_SPEC:
        raise ValueError(f"Granularidade desconhecida: {granularity_key}")

    key_col, label_col, order_col = _GRAN_SPEC[granularity_key]

    base = df
    if granularity_key in GRANULARIDADES_TEMPORAIS:
        base = df[df[coluna_data].notna()]

    if base.empty:
        return pd.DataFrame(columns=_COLUNAS_AGREGADAS)

    grp = (
        base.groupby([key_col], dropna=False)
        .agg(
            qtd=(C.QTD, "sum"),
            minutos=(C.MINUTOS, "sum"),
            registros=(C.ORDEM, "size"),
            _order=(order_col, "min"),
            _label=(label_col, "first"),
        )
        .reset_index()
    )
    grp = grp.sort_values("_order").reset_index(drop=True)
    out = pd.DataFrame({
        COLUNA_ROTULO: grp["_label"].astype(str),
        C.QTD: grp["qtd"].astype("int64"),
        C.MINUTOS: grp["minutos"].astype(float).round(2),
        COLUNA_REGISTROS: grp["registros"].astype("int64"),
    })
    # MP/Oficina: ordena pelo volume de peças (maior primeiro), mais útil.
    if granularity_key not in GRANULARIDADES_TEMPORAIS:
        out = out.sort_values(C.QTD, ascending=False).reset_index(drop=True)
    return out


def top_oficinas_por_pecas(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """As `top_n` oficinas com maior volume de peças. Colunas: rotulo · qtd · minutos."""
    if df.empty:
        return pd.DataFrame(columns=_COLUNAS_SERIE)
    grp = (
        df.groupby(C.OFICINA, as_index=False)
        .agg(qtd=(C.QTD, "sum"), minutos=(C.MINUTOS, "sum"))
        .sort_values("qtd", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )
    return grp.rename(
        columns={C.OFICINA: COLUNA_ROTULO, "qtd": C.QTD, "minutos": C.MINUTOS}
    )


def series_por_mes(df: pd.DataFrame, *, coluna_data: str) -> pd.DataFrame:
    """Série de peças por mês (ordenada). Colunas: rotulo · qtd · minutos."""
    return aggregate_by(df, "mes", coluna_data=coluna_data)[_COLUNAS_SERIE]


def series_por_semana(df: pd.DataFrame, *, coluna_data: str) -> pd.DataFrame:
    """
    Série de peças por semana ISO (ordenada). Colunas: rotulo · qtd · minutos.

    O rótulo usa o prefixo "W" (week) — ex.: "W10" — a pedido do time.
    """
    serie = aggregate_by(df, "semana", coluna_data=coluna_data).copy()
    serie[COLUNA_ROTULO] = serie[COLUNA_ROTULO].apply(lambda s: f"W{s}")
    return serie[_COLUNAS_SERIE]
