"""
core/utils.py — utilitários de INDICADOR específicos do Postos.

Só o que traduz uma variação em semântica visual (cor e seta de tendência) mora
aqui. Formatação pt-BR, divisão segura e o padrão "selecionar todos" são iguais
em todas as áreas e vivem em ``app_common.formatting``.
"""

from __future__ import annotations

import math
from typing import Optional

from app_common.theme import Theme


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
