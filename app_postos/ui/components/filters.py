"""
ui/components/filters.py
---------------------------
Filtros laterais da aplicação. Segue o mesmo padrão já adotado em outros
projetos: um helper `select_all_popover` que substitui o `st.multiselect`
padrão por um popover compacto com opção de "selecionar todos", guardando
o estado em `st.session_state` para manter a seleção entre re-execuções.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app_postos.core.config import Columns
from app_common.formatting import all_or_selected
from app_postos.services.filter_service import FilterSelection


def render_top_filters(df: pd.DataFrame) -> FilterSelection:
    """
    Renderiza os filtros no TOPO da página (barra horizontal), substituindo a
    antiga sidebar. Mantém a lógica de cascata e devolve a seleção atual do
    usuário. O ano é sempre obrigatório e inicia no mais recente.

    Os widgets são dispostos em colunas, mas o Streamlit os executa de cima
    para baixo, então a cascata continua funcionando: Ano → Mês → MP →
    Oficinas → Semanas. Quando nenhum mês é escolhido, todo o ano permanece
    no recorte.
    """
    st.markdown(
        """
        <div class="filter-bar-header">
            <span class="fb-title">Filtros</span>
            <span class="fb-hint">Refine as análises por ano, mês, matéria-prima, oficina e semana</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Inicializa estados dos filtros no session_state, se necessário
    if "filtro_mp_widget" not in st.session_state:
        st.session_state.filtro_mp_widget = []
    if "filtro_mes_widget" not in st.session_state:
        st.session_state.filtro_mes_widget = None
    if "filtro_oficinas_widget" not in st.session_state:
        st.session_state.filtro_oficinas_widget = []
    if "filtro_semanas_widget" not in st.session_state:
        st.session_state.filtro_semanas_widget = []

    col_ano, col_mes, col_mp, col_oficinas, col_semanas = st.columns(
        [0.9, 1.3, 1.6, 2.4, 1.5]
    )

    # 1. Filtro de Ano (selectbox simples - prioriza o ano mais recente)
    ano_options = sorted(df[Columns.ANO].unique().tolist(), reverse=True)

    if "previous_ano" not in st.session_state:
        st.session_state.previous_ano = ano_options[0]

    with col_ano:
        ano_selected = st.selectbox(
            "Ano de Análise",
            options=ano_options,
            index=0,
            help="Selecione o ano para filtrar todas as análises do dashboard.",
        )

    # Se o ano de análise mudou, resetamos todos os filtros em cascata
    if ano_selected != st.session_state.previous_ano:
        st.session_state.filtro_mes_widget = None
        st.session_state.filtro_mp_widget = []
        st.session_state.filtro_oficinas_widget = []
        st.session_state.filtro_semanas_widget = []
        st.session_state.previous_ano = ano_selected

    # Filtra o DataFrame temporariamente pelo ano selecionado para cascatear as opções
    df_ano = df[df[Columns.ANO] == ano_selected]

    # 2. Mês - opcional; vazio significa todo o ano selecionado.
    month_labels = (
        df_ano[[Columns.ANO_MES, Columns.MES_LABEL]]
        .drop_duplicates()
        .sort_values(Columns.ANO_MES)
    )
    month_label_by_period = dict(
        zip(month_labels[Columns.ANO_MES], month_labels[Columns.MES_LABEL])
    )
    month_options: list[str | None] = [None, *month_label_by_period.keys()]

    with col_mes:
        month_selected = st.selectbox(
            "Mês",
            options=month_options,
            format_func=lambda value: (
                "Todos os meses" if value is None else month_label_by_period[value]
            ),
            key="filtro_mes_widget",
            help="Selecione um mês ou mantenha todos os meses do ano escolhido.",
        )

    df_periodo = (
        df_ano
        if month_selected is None
        else df_ano[df_ano[Columns.ANO_MES] == month_selected]
    )

    # 3. Matéria-prima (MP) - Cascata Nível 1
    mp_options = sorted(df_periodo[Columns.MP].unique().tolist())
    st.session_state.filtro_mp_widget = [x for x in st.session_state.filtro_mp_widget if x in mp_options]

    with col_mp:
        mp_sel = st.multiselect(
            "Matéria-prima (MP)",
            options=mp_options,
            placeholder="Todos",
            key="filtro_mp_widget",
        )
    mp_selected = all_or_selected(mp_sel, mp_options)

    # 4. Oficinas (Oficina · MP) - Cascata Nível 2
    df_mp = df_periodo[df_periodo[Columns.MP].isin(mp_selected)]
    oficina_options = sorted(df_mp[Columns.OFICINA_MP].unique().tolist())
    st.session_state.filtro_oficinas_widget = [x for x in st.session_state.filtro_oficinas_widget if x in oficina_options]

    with col_oficinas:
        oficinas_sel = st.multiselect(
            "Oficinas (Oficina · MP)",
            options=oficina_options,
            placeholder="Todos",
            key="filtro_oficinas_widget",
        )
    oficinas_selected = all_or_selected(oficinas_sel, oficina_options)

    # 5. Semanas - Cascata Nível 3 (já limitado também pelo mês)
    df_oficina = df_mp[df_mp[Columns.OFICINA_MP].isin(oficinas_selected)]
    semanas_options = sorted(df_oficina[Columns.SEMANA].unique().tolist())
    semanas_str_options = [f"Semana {w}" for w in semanas_options]
    st.session_state.filtro_semanas_widget = [x for x in st.session_state.filtro_semanas_widget if x in semanas_str_options]

    with col_semanas:
        semanas_sel = st.multiselect(
            "Semanas",
            options=semanas_str_options,
            placeholder="Todos",
            key="filtro_semanas_widget",
        )
    semanas_selected_str = all_or_selected(semanas_sel, semanas_str_options)

    semanas_selected = []
    for s_str in semanas_selected_str:
        try:
            num = int(s_str.replace("Semana ", ""))
            semanas_selected.append(num)
        except ValueError:
            pass

    return FilterSelection(
        ano=ano_selected,
        mp=mp_selected,
        oficinas=oficinas_selected,
        semanas=semanas_selected,
        ano_mes=month_selected,
    )

