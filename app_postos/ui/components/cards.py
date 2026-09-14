"""
ui/components/cards.py
------------------------
Componente de apresentação responsável apenas por renderizar os cards de
KPI em HTML/CSS (grid responsivo). Não calcula nada — recebe os valores
já prontos vindos da camada de orquestração (`ui/layout.py`), que por sua
vez consome `services/indicators_service.py` e `services/analytics_service.py`.
"""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from app_postos.core.utils import format_delta_br, trend_arrow


@dataclass(frozen=True)
class KpiCardData:
    icon: str
    label: str
    value_display: str
    delta_pct: float | None = None
    delta_caption: str = "vs. semana anterior"
    # invert=True → indicador em que subir é ruim (absenteísmo, ausências,
    # demissões): aumento fica vermelho e queda fica verde. A seta continua
    # indicando a direção real da variação.
    invert: bool = False


def _delta_class(delta_pct: float | None, invert: bool = False) -> str:
    if delta_pct is None or delta_pct != delta_pct:  # NaN check
        return "neutral"
    if delta_pct == 0:
        return "neutral"
    subiu = delta_pct > 0
    if invert:
        subiu = not subiu
    return "positive" if subiu else "negative"


def _render_delta_html(card: KpiCardData) -> str:
    if card.delta_pct is None:
        return ""
    css_class = _delta_class(card.delta_pct, card.invert)
    arrow = trend_arrow(card.delta_pct)
    texto = format_delta_br(card.delta_pct)
    return (
        f'<div class="kpi-delta {css_class}">{arrow} {texto} '
        f'<span style="color: var(--text-muted); font-weight:400;">{card.delta_caption}</span></div>'
    )


def render_kpi_cards(cards: list[KpiCardData]) -> None:
    """
    Renderiza um grid responsivo de cards de KPI.

    Cada card exibe: icone ✦ + label (uppercase teal), valor grande (texto escuro)
    e delta de variacao. O emoji de icone foi removido do topo — o identificador
    visual e feito pelo simbolo ✦ prefixado ao label, alinhado ao design de referencia.
    """
    cards_html = "".join(
        f'<div class="kpi-card">'
        f'<div class="kpi-label"><span class="kpi-star">&#10022;</span> {card.label}</div>'
        f'<div class="kpi-value">{card.value_display}</div>'
        f'{_render_delta_html(card)}'
        f'</div>'
        for card in cards
    )
    st.markdown(f'<div class="kpi-grid">{cards_html}</div>', unsafe_allow_html=True)

