"""
ui/styles.py — CSS da área "Recebimento".

Reaproveita o CSS do DESIGN SYSTEM compartilhado (mesma paleta do Radar) já
definido em ``app_postos.ui.styles`` e acrescenta apenas o que é específico de
Recebimento (barra de paginação e cabeçalho de dimensão). Manter uma única fonte
de verdade para o tema evita divergência visual entre as áreas do app unificado.
"""

from __future__ import annotations

from app_postos.ui.styles import build_css as _build_shared_css

_RECEB_EXTRA_RULES = """
/* ---------- Paginação da tabela de consulta ---------- */
.receb-pager {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 10px;
    font-size: 0.82rem;
    color: var(--text-muted);
    margin-top: 8px;
}
.receb-pager .pg-info {
    font-family: var(--font-body);
}
.receb-pager .pg-info strong {
    color: var(--text-primary);
    font-variant-numeric: tabular-nums;
}

/* ---------- Cabeçalho de seção de granularidade ---------- */
.gran-header {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    margin: 0.6rem 0 0.3rem 0;
}
.gran-header .gh-title {
    font-family: var(--font-heading);
    font-weight: 700;
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--accent);
}
.gran-header .gh-hint {
    font-size: 0.74rem;
    color: var(--text-muted);
}

/* Célula numérica com tabular-nums para alinhar peças/minutos */
.custom-table td.num {
    text-align: right;
    font-variant-numeric: tabular-nums;
}
.custom-table th.num { text-align: right; }
"""


def build_css() -> str:
    """CSS compartilhado (design system) + acréscimos de Recebimento num ÚNICO <style>.

    Os acréscimos são injetados ANTES do ``</style>`` do CSS compartilhado —
    dois blocos ``<style>`` separados num mesmo ``st.markdown`` fazem o Streamlit
    exibir o segundo como texto em vez de aplicá-lo.
    """
    return _build_shared_css().replace("</style>", _RECEB_EXTRA_RULES + "\n</style>")
