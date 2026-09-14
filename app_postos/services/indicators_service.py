"""
services/indicators_service.py
---------------------------------
Responsabilidade única: calcular os indicadores-chave (KPIs) exibidos nos
cards do topo da aplicação, a partir de um DataFrame já limpo/padronizado
(ver `services/data_cleaning.py`).

Regra de negócio do indicador de Absenteísmo:
    taxa_absenteismo (%) = (total_efetivos - total_trabalhados) / total_efetivos * 100

Ou seja, o percentual do efetivo planejado que NÃO foi efetivamente
trabalhado no período selecionado.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app_postos.core.config import Columns
from app_postos.core.utils import safe_div


@dataclass(frozen=True)
class KpiResult:
    total_efetivos: int
    total_trabalhados: int
    total_contratacoes: int
    total_demissoes: int
    taxa_absenteismo: float  # percentual (ex.: 12.3 significa 12,3%)
    total_ausencia: int


def compute_kpis(df: pd.DataFrame) -> KpiResult:
    """Calcula os KPIs agregados para o DataFrame filtrado recebido."""
    total_efetivos = int(df[Columns.QTD_EFETIVOS].sum())
    total_trabalhados = int(df[Columns.QTD_TRABALHADOS].sum())
    total_contratacoes = int(df[Columns.CONTRATACOES].sum())
    total_demissoes = int(df[Columns.DEMISSOES].sum())

    taxa_absenteismo = safe_div(
        total_efetivos - total_trabalhados, total_efetivos
    ) * 100

    total_ausencia = total_efetivos - total_trabalhados

    return KpiResult(
        total_efetivos=total_efetivos,
        total_trabalhados=total_trabalhados,
        total_contratacoes=total_contratacoes,
        total_demissoes=total_demissoes,
        taxa_absenteismo=taxa_absenteismo,
        total_ausencia=total_ausencia,
    )


def kpi_value(result: KpiResult, indicator_key: str) -> float:
    """Acessa o valor de um KPI pela chave usada em `core.config.INDICATORS`."""
    mapping = {
        "efetivos": result.total_efetivos,
        "trabalhados": result.total_trabalhados,
        "ausencia": result.total_ausencia,
        "contratacoes": result.total_contratacoes,
        "demissoes": result.total_demissoes,
        "absenteismo": result.taxa_absenteismo,
    }
    return mapping[indicator_key]
