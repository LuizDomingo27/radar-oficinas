"""
ui/components/cards.py — cards de indicadores da área "Recebimento".

Apenas apresentação (HTML/CSS): recebe os valores já formatados da camada de
orquestração e desenha o grid de cards, reutilizando as classes ``kpi-grid`` /
``kpi-card`` do design system compartilhado.
"""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st


@dataclass(frozen=True)
class KpiCardData:
    label: str
    value_display: str
    caption: str = ""


def render_kpi_cards(cards: list[KpiCardData]) -> None:
    """Renderiza um grid responsivo de cards (label teal + valor grande)."""
    partes = []
    for card in cards:
        caption_html = (
            f'<div class="kpi-delta neutral">{card.caption}</div>' if card.caption else ""
        )
        partes.append(
            f'<div class="kpi-card">'
            f'<div class="kpi-label"><span class="kpi-star">&#10022;</span> {card.label}</div>'
            f'<div class="kpi-value">{card.value_display}</div>'
            f'{caption_html}'
            f'</div>'
        )
    st.markdown(f'<div class="kpi-grid">{"".join(partes)}</div>', unsafe_allow_html=True)
