"""
ui/layout.py
-------------
Camada de orquestração da interface: combina os componentes visuais
(`ui/components/*`) com os dados já processados pela camada de serviços
(`services/*`) para montar as seções da página.

Este módulo NÃO contém regra de negócio (cálculos) nem CSS bruto — apenas
"monta" a página a partir de peças já prontas, o que facilita reorganizar
a página (trocar ordem de seções, adicionar uma nova aba) sem tocar nas
camadas de baixo.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app_postos.core.config import Columns, INDICATORS, KPI_ORDER
from app_postos.core.errors import guard
from app_common.formatting import format_int_br, format_percent_br
from app_postos.services.analytics_service import (
    aggregate_by_mp,
    aggregate_by_oficina,
    latest_period_delta,
    monthly_evolution,
    weekly_evolution,
)
from app_postos.services.indicators_service import compute_kpis, kpi_value
from app_postos.ui.components.cards import KpiCardData, render_kpi_cards
from app_postos.ui.components.charts import (
    build_evolution_chart,
    build_absenteismo_ranking_chart,
)
import streamlit.components.v1 as components


@guard("renderizar os indicadores (KPIs)")
def render_kpi_section(df_filtered: pd.DataFrame) -> None:
    """Renderiza os 5 cards de KPI, cada um com a variação vs. semana anterior."""
    if df_filtered.empty:
        return

    semana_val = df_filtered[Columns.SEMANA].max()
    if pd.isna(semana_val):
        return
    semana_atual = int(semana_val)
    df_semana_atual = df_filtered[df_filtered[Columns.SEMANA] == semana_atual]
    kpis = compute_kpis(df_semana_atual)

    cards: list[KpiCardData] = []
    for key in KPI_ORDER:
        meta = INDICATORS[key]
        value = kpi_value(kpis, key)
        value_display = format_percent_br(value) if meta.is_percentage else format_int_br(value)

        serie = weekly_evolution(df_filtered, key)
        delta = latest_period_delta(serie)

        if len(serie) >= 2:
            semana_anterior = int(serie[Columns.SEMANA].iloc[-2])
            caption = f"vs. Semana {semana_anterior}"
        else:
            caption = "sem comparação"

        cards.append(
            KpiCardData(
                icon=meta.icon,
                label=meta.label,
                value_display=value_display,
                delta_pct=delta,
                delta_caption=caption,
                invert=(key in _INDICADORES_INVERTIDOS),
            )
        )

    st.markdown(f"#### Resultados da Semana {semana_atual}")
    render_kpi_cards(cards)


# Indicadores em que subir é ruim e cair é bom — cor invertida no gráfico
# de evolução (queda = verde, alta = vermelho).
_INDICADORES_INVERTIDOS = {"absenteismo", "ausencia", "demissoes"}


def _render_media_pill(value: float, is_percentage: bool) -> None:
    """Exibe a média simples do período como uma pílula ao lado do seletor.

    A média deixou de ser um rótulo dentro do gráfico (colidia com os rótulos
    de valor de cada ponto) e passou a ser anotada aqui, alinhada à direita da
    linha de indicadores — logo após o último botão (Taxa de Absenteísmo).
    """
    if value != value:  # NaN
        texto = "—"
    else:
        texto = format_percent_br(value) if is_percentage else format_int_br(value)
    st.markdown(
        '<div class="media-pill-wrap">'
        '<span class="media-pill" title="Média simples do período">'
        '<span class="mp-label">Média</span>'
        f'<span class="mp-value">{texto}</span>'
        '</span></div>',
        unsafe_allow_html=True,
    )


def _indicator_selector(tab_key: str) -> str:
    options = list(KPI_ORDER)
    labels = [INDICATORS[k].label for k in options]
    idx = st.radio(
        "Indicador",
        options=range(len(options)),
        format_func=lambda i: labels[i],
        horizontal=True,
        key=f"indicador_{tab_key}",
        label_visibility="collapsed",
    )
    return options[idx]


@guard("renderizar a evolução semanal")
def render_weekly_tab(df_filtered: pd.DataFrame) -> None:
    st.markdown("#### Evolução semanal por indicador")
    sel_col, pill_col = st.columns([4, 1], vertical_alignment="center")
    with sel_col:
        indicator_key = _indicator_selector("semanal")
    meta = INDICATORS[indicator_key]

    serie = weekly_evolution(df_filtered, indicator_key)
    if serie.empty:
        st.info("Sem dados para o filtro selecionado.")
        return

    with pill_col:
        media_val = float(serie["media"].iloc[0]) if len(serie) else float("nan")
        _render_media_pill(media_val, meta.is_percentage)

    x_labels = [f"S{int(s)}" for s in serie["semana"]]
    chart_html = build_evolution_chart(
        serie, x_col="semana", x_tick_labels=x_labels,
        value_label=meta.label, is_percentage=meta.is_percentage,
        invert_trend=(indicator_key in _INDICADORES_INVERTIDOS),
    )
    components.html(chart_html, height=400, scrolling=False)

    delta = latest_period_delta(serie)
    st.caption(
        f"Variação na última semana ({x_labels[-1]}) em relação à semana anterior: "
        f"**{_format_delta_caption(delta)}**"
    )


@guard("renderizar a evolução mensal")
def render_monthly_tab(df_filtered: pd.DataFrame) -> None:
    st.markdown("#### Evolução mensal por indicador")
    sel_col, pill_col = st.columns([4, 1], vertical_alignment="center")
    with sel_col:
        indicator_key = _indicator_selector("mensal")
    meta = INDICATORS[indicator_key]

    serie = monthly_evolution(df_filtered, indicator_key)
    if serie.empty:
        st.info("Sem dados para o filtro selecionado.")
        return

    with pill_col:
        media_val = float(serie["media"].iloc[0]) if len(serie) else float("nan")
        _render_media_pill(media_val, meta.is_percentage)

    x_labels = serie["mes_label"].tolist()
    chart_html = build_evolution_chart(
        serie, x_col="ano_mes", x_tick_labels=x_labels,
        value_label=meta.label, is_percentage=meta.is_percentage,
        invert_trend=(indicator_key in _INDICADORES_INVERTIDOS),
    )
    components.html(chart_html, height=400, scrolling=False)

    delta = latest_period_delta(serie)
    st.caption(
        f"Variação no último mês ({x_labels[-1]}) em relação ao mês anterior: "
        f"**{_format_delta_caption(delta)}**"
    )


def _format_delta_caption(delta: float) -> str:
    from app_common.formatting import format_delta_br

    if delta != delta:  # NaN
        return "sem base de comparação"
    return format_delta_br(delta)


def _render_table_semana_atual(df_semana: pd.DataFrame, semana_atual: int) -> None:
    """Tabela 1 — Resultados por MP para a semana atual filtrada."""
    #st.markdown(f"#### Resultados Da Semana {semana_atual}")

    grp = aggregate_by_mp(df_semana)
    if grp.empty:
        st.info("Sem dados para esta semana.")
        return

    rows = []
    for _, row in grp.iterrows():
        abs_val = row["absenteismo"]
        if abs_val != abs_val:          # NaN
            badge_class, abs_disp = "medium", "—"
        elif abs_val > 10.0:
            badge_class, abs_disp = "high", format_percent_br(abs_val)
        elif abs_val < 3.0:
            badge_class, abs_disp = "low", format_percent_br(abs_val)
        else:
            badge_class, abs_disp = "medium", format_percent_br(abs_val)

        rows.append(
            f'<tr>'
            f'<td style="text-align:left;font-weight:600;font-size:0.9rem;">{row[Columns.MP]}</td>'
            f'<td style="text-align:center;">{format_int_br(row["efetivos"])}</td>'
            f'<td style="text-align:center;">{format_int_br(row["trabalhados"])}</td>'
            f'<td style="text-align:center;">{format_int_br(row["ausencia"])}</td>'
            f'<td style="text-align:center;"><span class="badge-abs {badge_class}">{abs_disp}</span></td>'
            f'</tr>'
        )

    html = (
        '<div class="custom-table-container">'
        '<table class="custom-table">'
        '<thead><tr>'
        '<th style="text-align:left;">MP</th>'
        '<th style="text-align:center;">Efetivos</th>'
        '<th style="text-align:center;">Trabalhados</th>'
        '<th style="text-align:center;">Ausências</th>'
        '<th style="text-align:center;">Absenteísmo</th>'
        '</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        '</table></div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def _delta_cell(val_atual: float, val_ant: float, *, invert: bool = False) -> str:
    """
    Retorna HTML de uma célula com Δ% colorida.
    invert=True → queda é verde (ex.: ausência, absenteísmo).
    Para absenteísmo usa diferença em pontos percentuais (p.p.).
    """
    if val_ant == 0 or val_ant != val_ant or val_atual != val_atual:
        return '<td style="text-align:center;color:#5E8B83;">—</td>'

    delta_pct = (val_atual - val_ant) / abs(val_ant) * 100
    up = delta_pct > 0
    # Sinal visual
    arrow = "▲" if up else "▼"
    # Cor: se invert, subida é ruim (vermelho), descida é boa (verde)
    cor = ("#D93025" if up else "#18C99E") if invert else ("#18C99E" if up else "#D93025")
    sinal = "+" if up else ""
    # Diferença absoluta em unidades (o "número em questão" por trás do Δ%).
    diff = val_atual - val_ant
    diff_sinal = "+" if diff > 0 else ""
    diff_disp = f"{diff_sinal}{format_int_br(diff)}"
    return (
        f'<td style="text-align:center;color:{cor};font-weight:600;">'
        f'{arrow} {sinal}{delta_pct:.1f}% '
        f'<span style="color:#5E8B83;font-weight:400;">({diff_disp})</span>'
        f'</td>'
    )


def _delta_pp_cell(abs_atual: float, abs_ant: float) -> str:
    """
    Célula de Δ absenteísmo em pontos percentuais (p.p.).
    Subida = vermelho (piora), descida = verde (melhora).
    """
    if abs_ant != abs_ant or abs_atual != abs_atual:
        return '<td style="text-align:center;color:#5E8B83;">—</td>'

    delta = abs_atual - abs_ant
    arrow = "▲" if delta > 0 else "▼"
    cor = "#D93025" if delta > 0 else "#18C99E"
    sinal = "+" if delta > 0 else ""
    return (
        f'<td style="text-align:center;color:{cor};font-weight:600;">'
        f'{arrow} {sinal}{delta:.2f} p.p.'
        f'</td>'
    )


def _render_table_comparacao(
    df_atual: pd.DataFrame,
    df_anterior: pd.DataFrame,
    semana_atual: int,
    semana_ant: int,
    source_label: str = "",
) -> None:
    """
    Tabela 2 — Comparação por MP entre semana anterior e atual.
    source_label: texto extra indicando se a semana anterior veio do dataset completo.
    """
    st.markdown(
        f"#### Comparação Semana {semana_ant}  →  Semana {semana_atual}"
    )
    if source_label:
        st.caption(source_label)

    grp_atual = aggregate_by_mp(df_atual).set_index(Columns.MP)
    grp_ant   = aggregate_by_mp(df_anterior).set_index(Columns.MP)

    all_mps = sorted(set(grp_atual.index) | set(grp_ant.index))
    if not all_mps:
        st.info("Sem dados para comparação.")
        return

    rows = []
    for mp in all_mps:
        tem_atual = mp in grp_atual.index
        tem_ant   = mp in grp_ant.index

        if not tem_atual or not tem_ant:
            # MP presente só em uma semana — exibe traço em todas as colunas delta
            nota = "(apenas nesta semana)" if tem_atual else "(apenas na semana anterior)"
            rows.append(
                f'<tr>'
                f'<td style="text-align:left;font-weight:600;">{mp}</td>'
                f'<td colspan="4" style="text-align:center;color:#5E8B83;font-style:italic;">{nota}</td>'
                f'</tr>'
            )
            continue

        ra = grp_atual.loc[mp]
        rb = grp_ant.loc[mp]

        rows.append(
            f'<tr>'
            f'<td style="text-align:left;font-weight:600;">{mp}</td>'
            + _delta_cell(ra["efetivos"],    rb["efetivos"],    invert=False)
            + _delta_cell(ra["trabalhados"], rb["trabalhados"], invert=False)
            + _delta_cell(ra["ausencia"],    rb["ausencia"],    invert=True)
            + _delta_pp_cell(ra["absenteismo"], rb["absenteismo"])
            + '</tr>'
        )

    html = (
        '<div class="custom-table-container">'
        '<table class="custom-table">'
        '<thead><tr>'
        '<th style="text-align:left;">MP</th>'
        f'<th style="text-align:center;">Δ Efetivos<br><small style="font-weight:400;color:#5E8B83;">S{semana_ant}→S{semana_atual}</small></th>'
        f'<th style="text-align:center;">Δ Trabalhados<br><small style="font-weight:400;color:#5E8B83;">S{semana_ant}→S{semana_atual}</small></th>'
        f'<th style="text-align:center;">Δ Ausências<br><small style="font-weight:400;color:#5E8B83;">S{semana_ant}→S{semana_atual}</small></th>'
        f'<th style="text-align:center;">Δ Absenteísmo<br><small style="font-weight:400;color:#5E8B83;">S{semana_ant}→S{semana_atual}</small></th>'
        '</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        '</table></div>'
    )
    st.markdown(html, unsafe_allow_html=True)


@guard("renderizar a aba de oficinas")
def render_workshops_tab(df_filtered: pd.DataFrame, df_full: pd.DataFrame) -> None:
    """
    Aba Oficinas. Recebe df_filtered (recorte ativo) e df_full (dataset completo).

    Seções:
      1. Tabela por MP — semana atual filtrada.
      2. Tabela de comparação — semana atual vs. semana anterior.
         A semana anterior é detectada automaticamente: primeiro busca no
         df_filtered; se não existir (filtro de semana única), usa df_full.
      3. Gráfico de ranking (piores absenteísmos).
      4. Tabela completa por oficina+MP (existente).
    """
    st.markdown("#### Tabela Absenteísmo")

    if df_filtered.empty:
        st.info("Sem dados para o filtro selecionado.")
        return

    # ── Identificar semanas disponíveis ───────────────────────────────────
    semanas_filtradas = sorted(df_filtered[Columns.SEMANA].dropna().unique())
    semana_atual = int(semanas_filtradas[-1])
    df_semana_atual = df_filtered[df_filtered[Columns.SEMANA] == semana_atual]

    # Detectar semana anterior: primeiro no filtro, depois no dataset completo
    source_label = ""
    if len(semanas_filtradas) >= 2:
        semana_ant = int(semanas_filtradas[-2])
        df_semana_ant = df_filtered[df_filtered[Columns.SEMANA] == semana_ant]
    else:
        # Filtro de semana única → buscar semana anterior no dataset completo do mesmo ano
        ano_atual = int(df_filtered[Columns.ANO].iloc[0])
        df_year = df_full[df_full[Columns.ANO] == ano_atual]
        semanas_full = sorted(df_year[Columns.SEMANA].dropna().unique())
        idx_atual = semanas_full.index(semana_atual) if semana_atual in semanas_full else -1
        if idx_atual > 0:
            semana_ant = int(semanas_full[idx_atual - 1])
            df_semana_ant = df_year[df_year[Columns.SEMANA] == semana_ant]
            source_label = (
                f"Apenas a semana {semana_atual} está no filtro ativo. "
                f"A semana {semana_ant} foi buscada automaticamente no dataset completo do ano {ano_atual} para comparação."
            )
        else:
            semana_ant = None
            df_semana_ant = None

    # ── Tabela 1: Semana atual ────────────────────────────────────────────
    _render_table_semana_atual(df_semana_atual, semana_atual)
    st.markdown("""<br/><br/>""", unsafe_allow_html=True)
    # ── Tabela 2: Comparação ──────────────────────────────────────────────
    if semana_ant is not None and df_semana_ant is not None and not df_semana_ant.empty:
        _render_table_comparacao(
            df_semana_atual, df_semana_ant,
            semana_atual, semana_ant,
            source_label=source_label,
        )
    else:
        st.info("Não foi possível encontrar uma semana anterior para comparação.")

    st.markdown("""<br/><br/>""", unsafe_allow_html=True)
    st.markdown("### Tabela Completa")
    st.caption(f"Valores da semana {semana_atual} (respeitando os filtros de MP e oficina).")

    # ── Tabela HTML completa (por oficina+MP) ─────────────────────────────
    # Exibe apenas a semana atual, respeitando os demais filtros ativos.
    agrupado = aggregate_by_oficina(df_semana_atual)
    agrupado.index += 1  # numeração de exibição (a tabela começa em 1)

    rows_html = []
    for idx, row in agrupado.iterrows():
        oficina = row[Columns.OFICINA_MP]
        efetivos = format_int_br(row["efetivos"])
        trabalhados = format_int_br(row["trabalhados"])
        contratacoes = format_int_br(row["contratacoes"])
        demissoes = format_int_br(row["demissoes"])

        abs_val = row["absenteismo_%"]
        abs_display = format_percent_br(abs_val) if abs_val == abs_val else "—"

        if abs_val != abs_val:
            badge_class = "medium"
        elif abs_val > 10.0:
            badge_class = "high"
        elif abs_val < 3.0:
            badge_class = "low"
        else:
            badge_class = "medium"

        color_cont = "color: #18C99E; font-weight: 600;"
        color_dem  = "color: #D93025; font-weight: 600;"

        rows_html.append(
            f'<tr>'
            f'<td style="text-align: center; color: var(--text-muted); font-weight: 500;">{idx}</td>'
            f'<td style="text-align: left; font-weight: 500; font-size: 0.9rem;">{oficina}</td>'
            f'<td style="text-align: center;">{efetivos}</td>'
            f'<td style="text-align: center;">{trabalhados}</td>'
            f'<td style="text-align: center; {color_cont}">{contratacoes}</td>'
            f'<td style="text-align: center; {color_dem}">{demissoes}</td>'
            f'<td style="text-align: center;"><span class="badge-abs {badge_class}">{abs_display}</span></td>'
            f'</tr>'
        )

    table_html = (
        f'<div class="custom-table-container">'
        f'<table class="custom-table">'
        f'<thead>'
        f'<tr>'
        f'<th style="text-align: center; width: 50px;">#</th>'
        f'<th style="text-align: left;">Oficina</th>'
        f'<th style="text-align: center;">Efetivos</th>'
        f'<th style="text-align: center;">Trabalhados</th>'
        f'<th style="text-align: center;">Contratações</th>'
        f'<th style="text-align: center;">Demissões</th>'
        f'<th style="text-align: center;">Absenteísmo</th>'
        f'</tr>'
        f'</thead>'
        f'<tbody>'
        f'{"".join(rows_html)}'
        f'</tbody>'
        f'</table>'
        f'</div>'
    )
    st.markdown(table_html, unsafe_allow_html=True)
    
    st.markdown("""<br/><br/>""", unsafe_allow_html=True)
    
    st.markdown("#### Piores absenteísmos")
    
    # ── Gráfico:  ──────────────────────────────────────
    chart_html_ruim = build_absenteismo_ranking_chart(
        df_filtered, top_n=10, mode="piores"
    )
    components.html(chart_html_ruim, height=430, scrolling=False)
