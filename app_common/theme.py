"""
app_common/theme.py — paleta ÚNICA do app unificado.

Todas as áreas (Postos, Envios, Recebimento) usam a mesma identidade visual do
Radar: a decisão do time foi "manter a cor do Radar para todas". Declarar a
paleta aqui — e não em cada ``core/config.py`` — é o que impede as áreas de
divergirem visualmente com o tempo.
"""

from __future__ import annotations


class Theme:
    BG_PRIMARY = "#0d1015"
    BG_SECONDARY = "#161b22"
    CARD_BG = "#161b22"
    CARD_BORDER = "#2a323d"

    ACCENT = "#4fd0c3"
    ACCENT_SOFT = "rgba(79,208,195,0.16)"
    ACCENT_GLOW = "rgba(79,208,195,0.20)"

    POSITIVE = "#6cc596"
    NEGATIVE = "#ec7063"
    NEUTRAL = "#a3adbc"

    TEXT_PRIMARY = "#e8ecf2"
    TEXT_MUTED = "#a3adbc"

    FONT_HEADING = "'Sora', sans-serif"
    FONT_BODY = "'Inter', sans-serif"
