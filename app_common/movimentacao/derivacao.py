"""
app_common/movimentacao/derivacao.py — colunas de período derivadas da data.

Ano, ano_mês, rótulo do mês, semana ISO, dia e rótulo do dia saem todos da data
da movimentação. A regra é idêntica em Envios e Recebimento — só muda qual
coluna carrega a data —, então mora aqui uma vez só.

Linhas SEM data são MANTIDAS: elas entram nos totais e na granularidade por
MP/Oficina, mas ficam de fora das granularidades temporais, onde recebem o
rótulo "Sem data" em vez de sumir silenciosamente do relatório.
"""

from __future__ import annotations

import pandas as pd

from app_common.movimentacao.area import ColunasMovimentacao as C

_MESES_PT = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}

SEM_DATA_LABEL = "Sem data"


def add_derived(df: pd.DataFrame, *, coluna_data: str) -> pd.DataFrame:
    """Deriva ano, ano_mes, mes_label, semana, dia e dia_label da data informada."""
    df = df.copy()
    data = pd.to_datetime(df[coluna_data], errors="coerce")

    iso = data.dt.isocalendar()
    df[C.ANO] = data.dt.year.astype("Int64")
    df[C.SEMANA] = iso["week"].astype("Int64")
    df[C.DIA] = data.dt.normalize()

    periodo = data.dt.to_period("M")
    df[C.ANO_MES] = periodo.astype(str).where(data.notna(), None)
    df[C.MES_LABEL] = data.apply(
        lambda d: f"{_MESES_PT[d.month]}/{d.year}" if pd.notna(d) else SEM_DATA_LABEL
    )
    df[C.DIA_LABEL] = data.apply(
        lambda d: d.strftime("%d/%m/%Y") if pd.notna(d) else SEM_DATA_LABEL
    )
    return df
