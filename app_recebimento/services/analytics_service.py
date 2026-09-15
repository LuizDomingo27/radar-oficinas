"""
services/analytics_service.py — agregações da área "Recebimento".

Concentra toda a regra de agregação (peças e minutos) consumida pela UI:
KPIs, granularidade por dimensão (MP, Oficina, Mês, Semana, Dia), ranking das
oficinas que mais entregaram peças e as séries por mês/semana dos gráficos.
Não conhece Streamlit — recebe/entrega DataFrames.
"""

from __future__ import annotations

import pandas as pd

from app_recebimento.core.config import Columns

# Dimensões temporais: linhas sem data de recebimento não têm como ser posicionadas.
_TEMPORAL = {"mes", "semana", "dia"}


def compute_kpis(df: pd.DataFrame) -> dict:
    """Totais globais do recorte filtrado (para os cards)."""
    if df.empty:
        return {"pecas": 0, "minutos": 0.0, "registros": 0, "oficinas": 0, "ordens": 0}
    return {
        "pecas": int(df[Columns.QTD].sum()),
        "minutos": float(df[Columns.MINUTOS].sum()),
        "registros": int(len(df)),
        "oficinas": int(df[Columns.OFICINA].nunique()),
        "ordens": int(df[Columns.ORDEM].nunique()),
    }


# Como cada granularidade é agrupada: (coluna-chave, coluna-rótulo, coluna-ordenação).
_GRAN_SPEC = {
    "mp": (Columns.MP, Columns.MP, Columns.MP),
    "oficina": (Columns.OFICINA, Columns.OFICINA, Columns.OFICINA),
    "mes": (Columns.ANO_MES, Columns.MES_LABEL, Columns.ANO_MES),
    "semana": (Columns.SEMANA, Columns.SEMANA, Columns.SEMANA),
    "dia": (Columns.DIA, Columns.DIA_LABEL, Columns.DIA),
}


def aggregate_by(df: pd.DataFrame, granularity_key: str) -> pd.DataFrame:
    """
    Soma peças e minutos por dimensão. Retorna colunas:
      rotulo · qtd · minutos · registros

    Para dimensões temporais (mês/semana/dia), linhas sem data de recebimento
    são excluídas (não há período onde colocá-las); para MP/Oficina, tudo entra.
    """
    if granularity_key not in _GRAN_SPEC:
        raise ValueError(f"Granularidade desconhecida: {granularity_key}")

    key_col, label_col, order_col = _GRAN_SPEC[granularity_key]

    base = df
    if granularity_key in _TEMPORAL:
        base = df[df[Columns.RECEBIMENTO].notna()]

    if base.empty:
        return pd.DataFrame(columns=["rotulo", Columns.QTD, Columns.MINUTOS, "registros"])

    grp = (
        base.groupby([key_col], dropna=False)
        .agg(
            qtd=(Columns.QTD, "sum"),
            minutos=(Columns.MINUTOS, "sum"),
            registros=(Columns.ORDEM, "size"),
            _order=(order_col, "min"),
            _label=(label_col, "first"),
        )
        .reset_index()
    )
    grp = grp.sort_values("_order").reset_index(drop=True)
    out = pd.DataFrame({
        "rotulo": grp["_label"].astype(str),
        Columns.QTD: grp["qtd"].astype("int64"),
        Columns.MINUTOS: grp["minutos"].astype(float).round(2),
        "registros": grp["registros"].astype("int64"),
    })
    # MP/Oficina: ordena pelo volume de peças (maior primeiro), mais útil.
    if granularity_key not in _TEMPORAL:
        out = out.sort_values(Columns.QTD, ascending=False).reset_index(drop=True)
    return out


def top_oficinas_por_pecas(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """As `top_n` oficinas que mais entregaram peças. Colunas: rotulo · qtd · minutos."""
    if df.empty:
        return pd.DataFrame(columns=["rotulo", Columns.QTD, Columns.MINUTOS])
    grp = (
        df.groupby(Columns.OFICINA, as_index=False)
        .agg(qtd=(Columns.QTD, "sum"), minutos=(Columns.MINUTOS, "sum"))
        .sort_values("qtd", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )
    return grp.rename(columns={Columns.OFICINA: "rotulo", "qtd": Columns.QTD, "minutos": Columns.MINUTOS})


def series_por_mes(df: pd.DataFrame) -> pd.DataFrame:
    """Série de peças recebidas por mês (ordenada). Colunas: rotulo · qtd · minutos."""
    return aggregate_by(df, "mes")[["rotulo", Columns.QTD, Columns.MINUTOS]]


def series_por_semana(df: pd.DataFrame) -> pd.DataFrame:
    """Série de peças recebidas por semana ISO (ordenada). Colunas: rotulo · qtd · minutos.

    O rótulo usa o prefixo "W" (week) — ex.: "W10" — a pedido do time.
    """
    serie = aggregate_by(df, "semana")
    serie = serie.copy()
    serie["rotulo"] = serie["rotulo"].apply(lambda s: f"W{s}")
    return serie[["rotulo", Columns.QTD, Columns.MINUTOS]]
