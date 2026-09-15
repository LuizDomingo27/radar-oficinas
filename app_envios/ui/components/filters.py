"""
ui/components/filters.py — filtros no topo da página de Envios.

Cascata Ano → Mês → MP → Oficina. O Ano é obrigatório (inicia no mais recente),
pois toda a análise é "referente ao ano filtrado". Linhas sem data de envio não
pertencem a nenhum ano e ficam de fora do recorte anual (informado ao usuário).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app_envios.core.config import Columns


def _all_or_selected(selected: list, options: list) -> list:
    return list(options) if not selected else selected


def render_filters(df: pd.DataFrame) -> tuple[pd.DataFrame, int, str | None]:
    """
    Renderiza os filtros e devolve (df_filtrado, qtd_sem_data_excluidas, mes_sel).

    `qtd_sem_data_excluidas` = linhas sem data de envio descartadas pelo filtro
    de ano (para exibir um aviso transparente na UI).
    `mes_sel` = período mensal escolhido (ex.: "2026-03") ou None para "todos os
    meses" — usado pelo gráfico para alternar entre visão mensal e semanal.
    """
    st.markdown(
        '<div class="filter-bar-header"><span class="fb-title">Filtros</span>'
        '<span class="fb-hint">Refine por ano, mês, matéria-prima e oficina</span></div>',
        unsafe_allow_html=True,
    )

    anos = sorted(df[Columns.ANO].dropna().astype(int).unique().tolist(), reverse=True)
    if not anos:
        return df, 0, None

    col_ano, col_mes, col_mp, col_of = st.columns([0.9, 1.3, 1.8, 2.4])

    with col_ano:
        ano_sel = st.selectbox("Ano de Análise", options=anos, index=0, key="envios_filtro_ano")

    sem_data = int(df[Columns.ENVIO].isna().sum())
    df_ano = df[df[Columns.ANO] == ano_sel]

    meses = (
        df_ano[[Columns.ANO_MES, Columns.MES_LABEL]]
        .dropna(subset=[Columns.ANO_MES])
        .drop_duplicates()
        .sort_values(Columns.ANO_MES)
    )
    mes_label_by_period = dict(zip(meses[Columns.ANO_MES], meses[Columns.MES_LABEL]))
    mes_options: list = [None, *mes_label_by_period.keys()]

    with col_mes:
        mes_sel = st.selectbox(
            "Mês",
            options=mes_options,
            format_func=lambda v: "Todos os meses" if v is None else mes_label_by_period[v],
            key="envios_filtro_mes",
        )

    df_periodo = df_ano if mes_sel is None else df_ano[df_ano[Columns.ANO_MES] == mes_sel]

    mp_options = sorted(df_periodo[Columns.MP].dropna().unique().tolist())
    with col_mp:
        mp_sel = st.multiselect("Matéria-prima (MP)", options=mp_options, placeholder="Todas",
                                key="envios_filtro_mp")
    mp_selected = _all_or_selected(mp_sel, mp_options)

    df_mp = df_periodo[df_periodo[Columns.MP].isin(mp_selected)]
    oficina_options = sorted(df_mp[Columns.OFICINA].dropna().unique().tolist())
    with col_of:
        of_sel = st.multiselect("Oficinas", options=oficina_options, placeholder="Todas",
                                key="envios_filtro_oficina")
    of_selected = _all_or_selected(of_sel, oficina_options)

    df_filtrado = df_mp[df_mp[Columns.OFICINA].isin(of_selected)]
    return df_filtrado, sem_data, mes_sel
