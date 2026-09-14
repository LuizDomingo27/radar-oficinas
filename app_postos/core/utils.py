"""
core/utils.py
--------------
Funções utilitárias genéricas, sem dependência de Streamlit nem de
regras de negócio específicas. Podem ser reaproveitadas por qualquer
camada (services ou ui).
"""

from __future__ import annotations

import math
from typing import Optional

import pandas as pd

from app_postos.core.config import Theme


# ---------------------------------------------------------------------------
# Formatação numérica (padrão pt-BR)
# ---------------------------------------------------------------------------
def format_int_br(value: Optional[float]) -> str:
    """Formata um número como inteiro no padrão brasileiro (1.234)."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    return f"{int(round(value)):,}".replace(",", ".")


def format_percent_br(value: Optional[float], decimals: int = 1) -> str:
    """Formata um número como percentual no padrão brasileiro (12,3%)."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    texto = f"{value:.{decimals}f}%"
    return texto.replace(".", ",")


def format_delta_br(value: Optional[float], decimals: int = 1) -> str:
    """
    Formata uma variação percentual com sinal explícito (+3,2% / -1,5%).
    Usado nos indicadores de diferença entre semanas/meses.
    """
    if value is None or (isinstance(value, float) and math.isnan(value)) or math.isinf(value):
        return "—"
    sinal = "+" if value > 0 else ""
    texto = f"{sinal}{value:.{decimals}f}%".replace(".", ",")
    return texto


# ---------------------------------------------------------------------------
# Matemática segura
# ---------------------------------------------------------------------------
def safe_div(numerator: float, denominator: float) -> float:
    """Divisão seguindo a regra: retorna NaN quando o denominador é 0/NaN."""
    if denominator in (0, None) or (isinstance(denominator, float) and math.isnan(denominator)):
        return float("nan")
    return numerator / denominator


def pct_change(current: float, previous: float) -> float:
    """
    Variação percentual entre dois valores: (atual - anterior) / anterior * 100.
    Retorna NaN se não houver base de comparação válida.
    """
    if previous in (0, None) or (isinstance(previous, float) and math.isnan(previous)):
        return float("nan")
    return ((current - previous) / previous) * 100


# ---------------------------------------------------------------------------
# Helpers de cor (usados pelos gráficos para indicar tendência)
# ---------------------------------------------------------------------------
def trend_color(delta: Optional[float], invert: bool = False) -> str:
    """
    Retorna a cor do tema correspondente à tendência (alta/baixa/neutra).

    invert=True inverte a semântica alta=positivo/baixa=negativo — usado por
    indicadores onde subir é ruim (ex.: absenteísmo), em que queda é que
    representa melhora e deve aparecer em verde.
    """
    if delta is None or (isinstance(delta, float) and math.isnan(delta)):
        return Theme.NEUTRAL
    if delta > 0:
        return Theme.NEGATIVE if invert else Theme.POSITIVE
    if delta < 0:
        return Theme.POSITIVE if invert else Theme.NEGATIVE
    return Theme.NEUTRAL


def trend_arrow(delta: Optional[float]) -> str:
    """Retorna um símbolo de seta correspondente à tendência."""
    if delta is None or (isinstance(delta, float) and math.isnan(delta)):
        return "→"
    if delta > 0:
        return "▲"
    if delta < 0:
        return "▼"
    return "→"


# ---------------------------------------------------------------------------
# Helpers de seleção (padrão "selecionar todos" usado nos filtros)
# ---------------------------------------------------------------------------
def all_or_selected(selected: list, full_options: list) -> list:
    """
    Quando nada está selecionado em um multiselect, a convenção do app é
    tratar como "todos selecionados" (evita dashboards vazios por engano).
    """
    if not selected:
        return list(full_options)
    return selected


def chunk_list(items: list, size: int) -> list[list]:
    """Divide uma lista em grupos de tamanho `size` (útil para grids)."""
    return [items[i : i + size] for i in range(0, len(items), size)]
