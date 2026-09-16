"""
app_common/movimentacao/ui/layout.py — orquestração das páginas de movimentação.

Monta as seções a partir dos serviços de análise e dos componentes visuais, sem
regra de negócio própria: KPIs (cards), granularidade selecionável, gráficos e a
tabela de consulta por número da ordem (paginada).

Envios e Recebimento usam EXATAMENTE estas seções; o que muda é o vocabulário,
que chega em ``area.vocabulario``.
"""

from __future__ import annotations

import math

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from app_common.errors import build_error_handlers
from app_common.formatting import format_int_br, format_minutos_br
from app_common.movimentacao.analytics import (
    aggregate_by,
    compute_kpis,
    series_por_mes,
    series_por_semana,
    top_oficinas_por_pecas,
)
from app_common.movimentacao.area import (
    COLUNA_REGISTROS,
    COLUNA_ROTULO,
    GRANULARITIES,
    GRANULARITY_ORDER,
    AreaMovimentacao,
    ColunasMovimentacao as C,
)
from app_common.movimentacao.ui.cards import KpiCardData, render_kpi_cards
from app_common.movimentacao.ui.charts import build_periodo_chart, build_top_oficinas_chart

_, guard = build_error_handlers("app_common.movimentacao")


@guard("renderizar os indicadores de movimentação")
def render_kpi_section(df_filtered: pd.DataFrame, area: AreaMovimentacao) -> None:
    """Cards com os totais do recorte filtrado: peças, minutos e nº de registros."""
    voc = area.vocabulario
    kpis = compute_kpis(df_filtered)
    cards = [
        KpiCardData(
            f"Peças {voc.pecas_participio}",
            format_int_br(kpis["pecas"]),
            f'{format_int_br(kpis["ordens"])} ordens',
        ),
        KpiCardData(f"Minutos {voc.minutos_participio}", format_minutos_br(kpis["minutos"])),
        KpiCardData(
            f"Nº de {voc.titulo_registros}",
            format_int_br(kpis["registros"]),
            f"linhas de {voc.singular}",
        ),
    ]
    render_kpi_cards(cards)


def _render_metric_table(agg: pd.DataFrame, dim_label: str, area: AreaMovimentacao) -> None:
    """Tabela HTML (rótulo · peças · minutos · registros) para a granularidade escolhida."""
    if agg.empty:
        st.info("Sem dados para o recorte selecionado.")
        return

    linhas = []
    for _, row in agg.iterrows():
        linhas.append(
            "<tr>"
            f'<td style="text-align:left;font-weight:500;">{row[COLUNA_ROTULO]}</td>'
            f'<td class="num">{format_int_br(row[C.QTD])}</td>'
            f'<td class="num">{format_minutos_br(row[C.MINUTOS])}</td>'
            f'<td class="num">{format_int_br(row[COLUNA_REGISTROS])}</td>'
            "</tr>"
        )
    html = (
        '<div class="custom-table-container">'
        '<table class="custom-table"><thead><tr>'
        f'<th style="text-align:left;">{dim_label}</th>'
        '<th class="num">Peças</th><th class="num">Minutos</th>'
        f'<th class="num">{area.vocabulario.titulo_registros}</th>'
        "</tr></thead>"
        f'<tbody>{"".join(linhas)}</tbody></table></div>'
    )
    st.markdown(html, unsafe_allow_html=True)


@guard("renderizar a granularidade de movimentação")
def render_granularity_section(df_filtered: pd.DataFrame, area: AreaMovimentacao) -> None:
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
        key=area.key("granularidade"),
        label_visibility="collapsed",
    )
    gran_key = options[idx]
    agg = aggregate_by(df_filtered, gran_key, coluna_data=area.coluna_data)
    _render_metric_table(agg, GRANULARITIES[gran_key].label, area)


@guard("renderizar os gráficos de movimentação")
def render_charts_section(
    df_filtered: pd.DataFrame, area: AreaMovimentacao, mes_selecionado: str | None = None
) -> None:
    """
    Gráfico das oficinas com maior volume + UM gráfico por período que se adapta
    ao filtro de mês:
      • Sem mês selecionado ("Todos os meses") → peças por MÊS.
      • Com um mês selecionado → peças por SEMANA daquele mês.
    """
    voc = area.vocabulario
    st.markdown(f"#### Top oficinas que mais {voc.verbo_oficina} peças")
    st.caption(
        f"As {area.top_n_oficinas} oficinas com maior volume de peças no recorte filtrado."
    )
    top = top_oficinas_por_pecas(df_filtered, area.top_n_oficinas)
    components.html(build_top_oficinas_chart(top), height=430, scrolling=False)

    if mes_selecionado is None:
        st.markdown(f"#### {voc.titulo_registros} por mês")
        st.caption("Selecione um mês no filtro acima para detalhar por semana.")
        serie = series_por_mes(df_filtered, coluna_data=area.coluna_data)
        titulo = "Peças por mês"
    else:
        st.markdown(f"#### {voc.titulo_registros} por semana")
        st.caption(
            "Semanas do mês selecionado. Volte para “Todos os meses” para ver a visão mensal."
        )
        serie = series_por_semana(df_filtered, coluna_data=area.coluna_data)
        titulo = "Peças por semana"
    components.html(build_periodo_chart(serie, titulo), height=380, scrolling=False)


def _format_data(value) -> str:
    if value is None or pd.isna(value):
        return "Sem data"
    return pd.Timestamp(value).strftime("%d/%m/%Y")


@guard("renderizar a tabela de consulta de movimentação")
def render_consulta_table(df_filtered: pd.DataFrame, area: AreaMovimentacao) -> None:
    """
    Tabela de consulta por número da ordem, com as colunas
    [Ordem, Oficina, Qtd, Minutos, Data, MP], busca por ORDEM e paginação.
    """
    voc = area.vocabulario
    page_size = area.page_size_tabela

    st.markdown(f"#### Consulta de {voc.plural} por ordem")
    st.caption(
        f"Busque pelo número da ordem ou navegue pelas páginas ({page_size} por página)."
    )

    busca = st.text_input(
        "Número da ordem",
        key=area.key("busca_ordem"),
        placeholder=f"Digite o número da ordem (ex.: {voc.exemplo_ordem})",
    ).strip()

    df = df_filtered
    if busca:
        df = df[df[C.ORDEM].astype(str).str.contains(busca, case=False, na=False)]

    df = df.sort_values([area.coluna_data, C.ORDEM], na_position="last")
    total = len(df)

    if total == 0:
        st.info(f"Nenhum {voc.singular} encontrado para a consulta atual.")
        return

    total_paginas = max(1, math.ceil(total / page_size))

    # Estado de paginação. A busca reinicia para a página 1.
    key_pagina = area.key("pagina")
    key_busca_anterior = area.key("busca_anterior")
    if st.session_state.get(key_busca_anterior) != busca:
        st.session_state[key_pagina] = 1
        st.session_state[key_busca_anterior] = busca
    pagina = st.session_state.get(key_pagina, 1)
    pagina = min(max(1, pagina), total_paginas)

    col_prev, col_info, col_next = st.columns([1, 3, 1], vertical_alignment="center")
    with col_prev:
        if st.button("← Anterior", use_container_width=True, disabled=pagina <= 1,
                     key=area.key("prev")):
            st.session_state[key_pagina] = pagina - 1
            st.rerun()
    with col_next:
        if st.button("Próxima →", use_container_width=True, disabled=pagina >= total_paginas,
                     key=area.key("next")):
            st.session_state[key_pagina] = pagina + 1
            st.rerun()
    with col_info:
        ini = (pagina - 1) * page_size + 1
        fim = min(pagina * page_size, total)
        st.markdown(
            f'<div class="mov-pager"><span class="pg-info">Mostrando <strong>{ini}</strong>–'
            f'<strong>{fim}</strong> de <strong>{format_int_br(total)}</strong> · '
            f'Página <strong>{pagina}</strong>/<strong>{total_paginas}</strong></span></div>',
            unsafe_allow_html=True,
        )

    inicio = (pagina - 1) * page_size
    pagina_df = df.iloc[inicio : inicio + page_size]

    linhas = []
    for _, row in pagina_df.iterrows():
        linhas.append(
            "<tr>"
            f'<td style="text-align:left;font-weight:600;">{row[C.ORDEM]}</td>'
            f'<td style="text-align:left;">{row[C.OFICINA]}</td>'
            f'<td class="num">{format_int_br(row[C.QTD])}</td>'
            f'<td class="num">{format_minutos_br(row[C.MINUTOS])}</td>'
            f'<td style="text-align:center;">{_format_data(row[area.coluna_data])}</td>'
            f'<td style="text-align:center;">{row[C.MP]}</td>'
            "</tr>"
        )
    html = (
        '<div class="custom-table-container">'
        '<table class="custom-table"><thead><tr>'
        '<th style="text-align:left;">Ordem</th>'
        '<th style="text-align:left;">Oficina</th>'
        '<th class="num">Qtd</th>'
        '<th class="num">Minutos</th>'
        f'<th style="text-align:center;">{voc.rotulo_data}</th>'
        '<th style="text-align:center;">MP</th>'
        "</tr></thead>"
        f'<tbody>{"".join(linhas)}</tbody></table></div>'
    )
    st.markdown(html, unsafe_allow_html=True)
