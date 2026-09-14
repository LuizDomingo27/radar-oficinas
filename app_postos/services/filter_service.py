"""Contrato e regra pura dos filtros aplicados ao dashboard."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app_postos.core.config import Columns


@dataclass(frozen=True)
class FilterSelection:
    ano: int
    mp: list[str]
    oficinas: list[str]
    semanas: list[int]
    ano_mes: str | None = None


def apply_filters(df: pd.DataFrame, selection: FilterSelection) -> pd.DataFrame:
    """Aplica todos os filtros; mês vazio mantém todo o ano selecionado."""
    period_mask = True
    if selection.ano_mes is not None:
        period_mask = df[Columns.ANO_MES] == selection.ano_mes

    return df[
        (df[Columns.ANO] == selection.ano)
        & period_mask
        & df[Columns.MP].isin(selection.mp)
        & df[Columns.OFICINA_MP].isin(selection.oficinas)
        & df[Columns.SEMANA].isin(selection.semanas)
    ]
