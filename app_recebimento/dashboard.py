"""
app_recebimento/dashboard.py — ponto de entrada da área "Recebimento".

É uma FUNÇÃO (`render_recebimento_page`) chamada pelo shell (`streamlit_app.py`)
quando a aba "Recebimento" está ativa. Não chama `st.set_page_config` nem aplica
CSS (responsabilidade do shell). Orquestra: navbar → carga de dados → página ativa.

As seções do dashboard vêm do núcleo compartilhado
(``app_common.movimentacao``), parametrizadas pelo descritor ``AREA``.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app_common.movimentacao.data_loader import (
    EmptyDataError,
    empty_dataframe,
    load_clean_dataframe,
)
from app_common.movimentacao.ui.filters import render_filters
from app_common.movimentacao.ui.layout import (
    render_charts_section,
    render_consulta_table,
    render_granularity_section,
    render_kpi_section,
)
from app_recebimento.core.config import AREA
from app_recebimento.core.errors import error_boundary, guard
from app_recebimento.ui.cadastro_view import render_cadastro_page

_PAGE_DASHBOARD = "recebimento_dashboard"
_PAGE_LANCAMENTO = "recebimento_lancamento"


@st.cache_data(show_spinner="Carregando dados de recebimento...")
def _load_clean_data() -> pd.DataFrame:
    return load_clean_dataframe(AREA)


def _load_data_or_empty() -> pd.DataFrame:
    try:
        return _load_clean_data()
    except EmptyDataError:
        return empty_dataframe(AREA)


def _render_navbar() -> str:
    if "recebimento_page" not in st.session_state:
        st.session_state.recebimento_page = _PAGE_DASHBOARD

    col_brand, col_dash, col_lanc = st.columns([6, 2, 2], vertical_alignment="center")
    with col_brand:
        st.markdown(
            f'<div class="app-navbar"><span class="brand-title">{AREA.titulo}</span>'
            f'<span class="brand-sub">{AREA.subtitulo}</span></div>',
            unsafe_allow_html=True,
        )
    with col_dash:
        if st.button("Dashboard", use_container_width=True,
                     type="primary" if st.session_state.recebimento_page == _PAGE_DASHBOARD else "secondary",
                     key="receb_nav_dashboard"):
            st.session_state.recebimento_page = _PAGE_DASHBOARD
            st.rerun()
    with col_lanc:
        if st.button("Lançamento de Dados", use_container_width=True,
                     type="primary" if st.session_state.recebimento_page == _PAGE_LANCAMENTO else "secondary",
                     key="receb_nav_lancamento"):
            st.session_state.recebimento_page = _PAGE_LANCAMENTO
            st.rerun()

    st.markdown('<div class="navbar-divider"></div>', unsafe_allow_html=True)
    return st.session_state.recebimento_page


@guard("montar o dashboard de recebimento")
def _render_dashboard(df: pd.DataFrame) -> None:
    df_filtrado, sem_data, mes_sel = render_filters(df, AREA)

    if sem_data:
        st.caption(
            f"ℹ️ {sem_data} recebimento(s) sem data não entram no filtro por ano "
            "(aparecem apenas em consultas sem recorte de período)."
        )

    if df_filtrado.empty:
        st.warning("Nenhum recebimento encontrado para os filtros selecionados.")
        return

    render_kpi_section(df_filtrado, AREA)
    render_granularity_section(df_filtrado, AREA)
    render_charts_section(df_filtrado, AREA, mes_sel)
    render_consulta_table(df_filtrado, AREA)


def render_recebimento_page() -> None:
    """Renderiza a experiência completa de Recebimento como uma aba do app unificado."""
    page = _render_navbar()

    with error_boundary("carregar os dados de recebimento", fatal=True):
        df = _load_data_or_empty()

    if page == _PAGE_LANCAMENTO:
        render_cadastro_page()
    elif df.empty:
        st.info(
            "Ainda não há registros na tabela **Recebimento_Radar**. Acesse "
            "**Lançamento de Dados** para importar a planilha de recebimento."
        )
    else:
        _render_dashboard(df)
