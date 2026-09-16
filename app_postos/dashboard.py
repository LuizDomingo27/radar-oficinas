"""
app_postos/dashboard.py
-------------------------
Ponto de entrada da experiência "Gestão de Postos de Trabalho" DENTRO do app
unificado do Radar de Oficinas. É a antiga `app.py` do APP_Postos convertida em
uma FUNÇÃO (`render_postos_page`) que o shell (`streamlit_app.py`) chama quando
a aba "Postos" está ativa — em vez de um `main()` que roda sozinho.

Diferenças em relação ao `app.py` original:
  • NÃO chama `st.set_page_config` — isso é responsabilidade do shell, que já
    configura a página uma única vez (o Streamlit só aceita uma chamada).
  • NÃO tem bloco `if __name__ == "__main__"` — não é executado diretamente.

Toda a lógica de negócio continua em `app_postos/services/` e a apresentação em
`app_postos/ui/`; aqui só se ORQUESTRA a ordem (navbar → carga → filtros →
render), idêntico ao comportamento original.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app_postos.core.config import APP_SUBTITLE, APP_TITLE
from app_postos.core.errors import error_boundary, guard
from app_postos.services.data_cleaning import clean_dataframe
from app_postos.services.data_loader import (
    REQUIRED_RAW_COLUMNS,
    EmptyDataError,
    load_raw_dataframe,
)
from app_postos.services.filter_service import apply_filters
from app_postos.ui.cadastro_view import render_cadastro_page
from app_postos.ui.components.export import render_export_controls
from app_postos.ui.components.filters import render_top_filters
from app_postos.ui.layout import (
    render_kpi_section,
    render_monthly_tab,
    render_weekly_tab,
    render_workshops_tab,
)

_PAGE_DASHBOARD = "postos_dashboard"
_PAGE_LANCAMENTO = "postos_lancamento"


@st.cache_data(show_spinner="Carregando dados de postos de trabalho...")
def _load_clean_data() -> pd.DataFrame:
    df_raw = load_raw_dataframe()
    return clean_dataframe(df_raw)


def _load_data_or_empty() -> pd.DataFrame:
    """
    Carrega os dados limpos. Se a tabela `postos` ainda não tiver nenhum
    registro (primeiro uso, antes da importação inicial), devolve um DataFrame
    vazio com o contrato de colunas correto em vez de propagar o erro — assim a
    página de Lançamento de Dados continua acessível para o primeiro cadastro.
    """
    try:
        return _load_clean_data()
    except EmptyDataError:
        return clean_dataframe(pd.DataFrame(columns=REQUIRED_RAW_COLUMNS))


def _render_navbar() -> str:
    """
    Sub-navbar interna do módulo Postos (Dashboard ↔ Lançamento de Dados).

    Usa chaves de `st.session_state` próprias (prefixo ``postos_``) para não
    colidir com o seletor de nível superior Radar/Postos do shell.
    """
    if "postos_page" not in st.session_state:
        st.session_state.postos_page = _PAGE_DASHBOARD

    col_brand, col_dash, col_lanc = st.columns([6, 2, 2], vertical_alignment="center")

    with col_brand:
        st.markdown(
            f"""
            <div class="app-navbar">
                <span class="brand-title">{APP_TITLE}</span>
                <span class="brand-sub">{APP_SUBTITLE}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_dash:
        if st.button(
            "Dashboard",
            use_container_width=True,
            type="primary" if st.session_state.postos_page == _PAGE_DASHBOARD else "secondary",
            key="postos_nav_dashboard",
        ):
            st.session_state.postos_page = _PAGE_DASHBOARD
            st.rerun()

    with col_lanc:
        if st.button(
            "Lançamento de Dados",
            use_container_width=True,
            type="primary" if st.session_state.postos_page == _PAGE_LANCAMENTO else "secondary",
            key="postos_nav_lancamento",
        ):
            st.session_state.postos_page = _PAGE_LANCAMENTO
            st.rerun()

    st.markdown('<div class="navbar-divider"></div>', unsafe_allow_html=True)
    return st.session_state.postos_page


@guard("montar o dashboard de postos")
def _render_dashboard(df: pd.DataFrame) -> None:
    selection = render_top_filters(df)
    df_filtrado = apply_filters(df, selection)

    render_export_controls(df_filtrado, df)

    if df_filtrado.empty:
        st.warning("Nenhum registro encontrado para os filtros selecionados.")
        return

    render_kpi_section(df_filtrado)

    tab_semanal, tab_mensal, tab_oficinas = st.tabs(
        ["Evolução Semanal", "Evolução Mensal", "Oficinas"]
    )

    with tab_semanal:
        render_weekly_tab(df_filtrado)

    with tab_mensal:
        render_monthly_tab(df_filtrado)

    with tab_oficinas:
        render_workshops_tab(df_filtrado, df)


def render_postos_page() -> None:
    """Renderiza a experiência completa de Postos como uma aba do app unificado.

    O CSS do módulo (`build_css`) e o `set_page_config` são responsabilidade do
    shell (`streamlit_app.py`), que os aplica ANTES de chamar esta função. Aqui
    só orquestramos navbar → carga de dados → página ativa.
    """
    page = _render_navbar()

    # Fatal apenas para falhas reais (config/conexão/schema). Tabela vazia é
    # tratada como estado válido de primeiro uso (ver _load_data_or_empty).
    with error_boundary("carregar os dados de postos de trabalho", fatal=True):
        df = _load_data_or_empty()

    if page == _PAGE_LANCAMENTO:
        render_cadastro_page(df)
    elif df.empty:
        st.info(
            "Ainda não há registros na tabela **postos**. Acesse "
            "**Lançamento de Dados** para cadastrar o primeiro lançamento "
            "manualmente ou importar uma planilha em lote."
        )
    else:
        _render_dashboard(df)
