"""
ui/layout.py — orquestração da página de Recebimento.

Monta as seções a partir dos serviços de análise e dos componentes visuais,
sem regra de negócio própria: KPIs (cards), granularidade selecionável,
gráficos e a tabela de consulta por número da ordem (paginada, 15/página).
"""

from __future__ import annotations

import math

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from app_recebimento.core.config import (
    Columns,
    GRANULARITY_ORDER,
    GRANULARITIES,
    PAGE_SIZE_TABLE,
    TOP_N_OFICINAS,
)
from app_recebimento.core.errors import guard
from app_recebimento.core.utils import format_int_br, format_minutos_br
from app_recebimento.services.analytics_service import (
    aggregate_by,
    compute_kpis,
    series_por_mes,
    series_por_semana,
    top_oficinas_por_pecas,
)
from app_recebimento.ui.components.cards import KpiCardData, render_kpi_cards
from app_recebimento.ui.components.charts import build_periodo_chart, build_top_oficinas_chart


@guard("renderizar os indicadores de recebimento")
def render_kpi_section(df_filtered: pd.DataFrame) -> None:
    """Cards com os totais do recorte filtrado: peças, minutos e nº de recebimentos."""
    kpis = compute_kpis(df_filtered)
    cards = [
        KpiCardData("Peças Recebidas", format_int_br(kpis["pecas"]), f'{format_int_br(kpis["ordens"])} ordens'),
        KpiCardData("Minutos Recebidos", format_minutos_br(kpis["minutos"])),
        KpiCardData("Nº de Recebimentos", format_int_br(kpis["registros"]), "linhas de recebimento"),
    ]
    render_kpi_cards(cards)


def _render_metric_table(agg: pd.DataFrame, dim_label: str) -> None:
    """Tabela HTML (rótulo · peças · minutos · recebimentos) para a granularidade escolhida."""
    if agg.empty:
        st.info("Sem dados para o recorte selecionado.")
        return

    linhas = []
    for _, row in agg.iterrows():
        linhas.append(
            "<tr>"
            f'<td style="text-align:left;font-weight:500;">{row["rotulo"]}</td>'
            f'<td class="num">{format_int_br(row[Columns.QTD])}</td>'
            f'<td class="num">{format_minutos_br(row[Columns.MINUTOS])}</td>'
            f'<td class="num">{format_int_br(row["registros"])}</td>'
            "</tr>"
        )
    html = (
        '<div class="custom-table-container">'
        '<table class="custom-table"><thead><tr>'
        f'<th style="text-align:left;">{dim_label}</th>'
        '<th class="num">Peças</th><th class="num">Minutos</th><th class="num">Recebimentos</th>'
        "</tr></thead>"
        f'<tbody>{"".join(linhas)}</tbody></table></div>'
    )
    st.markdown(html, unsafe_allow_html=True)


@guard("renderizar a granularidade de recebimento")
def render_granularity_section(df_filtered: pd.DataFrame) -> None:
    """Total de peças e minutos por dimensão escolhida (MP, Oficinas, Mês, Semana, Dia)."""
    st.markdown(
        '<div class="gran-header"><span class="gh-title">Total de peças e minutos</span>'
        '<span class="gh-hint">Escolha a granularidade — referente ao recorte filtrado</span></div>',
        unsafe_allow_html=True,
    )

    options = list(GRANULARITY_ORDER)
    idx = st.radio(
        "Granularidade",
        options=range(len(options)),
        format_func=lambda i: GRANULARITIES[options[i]].label,
        horizontal=True,
        key="receb_granularidade",
        label_visibility="collapsed",
    )
    gran_key = options[idx]
    agg = aggregate_by(df_filtered, gran_key)
    _render_metric_table(agg, GRANULARITIES[gran_key].label)


@guard("renderizar os gráficos de recebimento")
def render_charts_section(df_filtered: pd.DataFrame, mes_selecionado: str | None = None) -> None:
    """
    Gráfico das 10 oficinas que mais entregaram peças + UM gráfico de recebimentos
    por período que se adapta ao filtro de mês:
      • Sem mês selecionado ("Todos os meses") → peças por MÊS.
      • Com um mês selecionado → peças por SEMANA daquele mês.
    """
    st.markdown("#### Top oficinas que mais entregaram peças")
    st.caption(f"As {TOP_N_OFICINAS} oficinas com maior volume de peças no recorte filtrado.")
    top = top_oficinas_por_pecas(df_filtered, TOP_N_OFICINAS)
    components.html(build_top_oficinas_chart(top, TOP_N_OFICINAS), height=430, scrolling=False)

    if mes_selecionado is None:
        st.markdown("#### Recebimentos por mês")
        st.caption("Selecione um mês no filtro acima para detalhar por semana.")
        serie = series_por_mes(df_filtered)
        titulo = "Peças por mês"
    else:
        st.markdown("#### Recebimentos por semana")
        st.caption("Semanas do mês selecionado. Volte para “Todos os meses” para ver a visão mensal.")
        serie = series_por_semana(df_filtered)
        titulo = "Peças por semana"
    components.html(build_periodo_chart(serie, titulo), height=380, scrolling=False)


def _format_data(value) -> str:
    if value is None or pd.isna(value):
        return "Sem data"
    return pd.Timestamp(value).strftime("%d/%m/%Y")


@guard("renderizar a tabela de consulta de recebimento")
def render_consulta_table(df_filtered: pd.DataFrame) -> None:
    """
    Tabela de consulta por número da ordem, com as colunas
    [Ordem, Oficina, Qtd, Minutos, Recebimento, MP], busca por ORDEM e paginação
    de 15 linhas por página.
    """
    st.markdown("#### Consulta de recebimentos por ordem")
    st.caption("Busque pelo número da ordem ou navegue pelas páginas (15 por página).")

    busca = st.text_input(
        "Número da ordem",
        key="receb_busca_ordem",
        placeholder="Digite o número da ordem (ex.: 300222936)",
    ).strip()

    df = df_filtered
    if busca:
        df = df[df[Columns.ORDEM].astype(str).str.contains(busca, case=False, na=False)]

    df = df.sort_values([Columns.RECEBIMENTO, Columns.ORDEM], na_position="last")
    total = len(df)

    if total == 0:
        st.info("Nenhum recebimento encontrado para a consulta atual.")
        return

    total_paginas = max(1, math.ceil(total / PAGE_SIZE_TABLE))

    # Estado de paginação. A busca reinicia para a página 1.
    if st.session_state.get("_receb_busca_anterior") != busca:
        st.session_state.receb_pagina = 1
        st.session_state._receb_busca_anterior = busca
    pagina = st.session_state.get("receb_pagina", 1)
    pagina = min(max(1, pagina), total_paginas)

    col_prev, col_info, col_next = st.columns([1, 3, 1], vertical_alignment="center")
    with col_prev:
        if st.button("← Anterior", use_container_width=True, disabled=pagina <= 1, key="receb_prev"):
            st.session_state.receb_pagina = pagina - 1
            st.rerun()
    with col_next:
        if st.button("Próxima →", use_container_width=True, disabled=pagina >= total_paginas, key="receb_next"):
            st.session_state.receb_pagina = pagina + 1
            st.rerun()
    with col_info:
        ini = (pagina - 1) * PAGE_SIZE_TABLE + 1
        fim = min(pagina * PAGE_SIZE_TABLE, total)
        st.markdown(
            f'<div class="receb-pager"><span class="pg-info">Mostrando <strong>{ini}</strong>–'
            f'<strong>{fim}</strong> de <strong>{format_int_br(total)}</strong> · '
            f'Página <strong>{pagina}</strong>/<strong>{total_paginas}</strong></span></div>',
            unsafe_allow_html=True,
        )

    inicio = (pagina - 1) * PAGE_SIZE_TABLE
    pagina_df = df.iloc[inicio : inicio + PAGE_SIZE_TABLE]

    linhas = []
    for _, row in pagina_df.iterrows():
        linhas.append(
            "<tr>"
            f'<td style="text-align:left;font-weight:600;">{row[Columns.ORDEM]}</td>'
            f'<td style="text-align:left;">{row[Columns.OFICINA]}</td>'
            f'<td class="num">{format_int_br(row[Columns.QTD])}</td>'
            f'<td class="num">{format_minutos_br(row[Columns.MINUTOS])}</td>'
            f'<td style="text-align:center;">{_format_data(row[Columns.RECEBIMENTO])}</td>'
            f'<td style="text-align:center;">{row[Columns.MP]}</td>'
            "</tr>"
        )
    html = (
        '<div class="custom-table-container">'
        '<table class="custom-table"><thead><tr>'
        '<th style="text-align:left;">Ordem</th>'
        '<th style="text-align:left;">Oficina</th>'
        '<th class="num">Qtd</th>'
        '<th class="num">Minutos</th>'
        '<th style="text-align:center;">Recebimento</th>'
        '<th style="text-align:center;">MP</th>'
        "</tr></thead>"
        f'<tbody>{"".join(linhas)}</tbody></table></div>'
    )
    st.markdown(html, unsafe_allow_html=True)
