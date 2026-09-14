"""
ui/components/charts.py
--------------------------
Constrói configurações Apache ECharts 5.x e as renderiza como HTML autossuficiente
via st.components.v1.html(), sem dependência de streamlit-echarts.

Melhorias vs. versão anterior (ECharts 4 / streamlit-echarts):
  • DataZoom (slider + scroll via mouse) no gráfico de evolução
  • Pointer cruzado no tooltip do gráfico de linha
  • Tooltips HTML ricos com separadores visuais e bullets coloridos
  • Efeito glow/sombra na linha e nos pontos do indicador principal
  • Gradiente de área com 3 paradas (mais suave)
  • Label da markLine com fundo semi-transparente e borda arredondada
  • Toolbox com botão de salvar imagem
  • Animação suavizada (cubicOut, 800ms)
  • Eixo Y do ranking com formatador "%"
  • Tooltip do ranking com mini barra de progresso e dados extras
"""

from __future__ import annotations

import json
import pandas as pd
import streamlit as st
from app_postos.core.config import Theme, Columns
from app_postos.core.utils import format_delta_br, format_int_br, format_percent_br, trend_color, safe_div

_GREEN = "#18C99E"
_RED   = "#D93025"
_MM_CURTO_COLOR = "#FBBF24"
_MM_LONGO_COLOR = "#FB923C"
_LAST_N_WEEKS = 4

_ECHARTS_CDN = "https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"


def _format_value(value: float, is_percentage: bool) -> str:
    return format_percent_br(value) if is_percentage else format_int_br(value)


def _echart_html(option: dict, formatter_js: str | None = None) -> str:
    """
    Serializa o dict de opções ECharts para JSON e o embute num HTML autossuficiente
    que carrega o ECharts 5.x a partir do CDN.

    Se formatter_js for fornecido, ele é injetado como option.tooltip.formatter
    após a serialização JSON (assim funções JS ficam fora do JSON, sem aspas).
    """
    option_json = json.dumps(option, ensure_ascii=False, default=str)
    formatter_block = ""
    if formatter_js:
        formatter_block = (
            "\n  option.tooltip = option.tooltip || {};"
            f"\n  option.tooltip.formatter = {formatter_js};"
        )
    return f"""<!DOCTYPE html>
<html style="margin:0;padding:0;height:100%;">
<head>
<meta charset="UTF-8">
<script src="{_ECHARTS_CDN}"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
html,body{{width:100%;height:100%;background:transparent;overflow:hidden;}}
#c{{width:100%;height:100%;}}
</style>
</head>
<body>
<div id="c"></div>
<script>
(function(){{
  var chart = echarts.init(document.getElementById('c'), null, {{
    renderer: 'canvas',
    backgroundColor: 'transparent'
  }});
  var option = {option_json};
  {formatter_block}
  chart.setOption(option);
  window.addEventListener('resize', function() {{ chart.resize(); }});
}})();
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Gráfico de evolução (linha) — semanal e mensal
# ---------------------------------------------------------------------------

def build_evolution_chart(
    serie: pd.DataFrame,
    x_col: str,
    x_tick_labels: list[str],
    value_label: str,
    is_percentage: bool = False,
    invert_trend: bool = False,
) -> str:
    """
    Retorna uma string HTML com o gráfico de linha de evolução ECharts 5.

    Camadas:
      • Área de preenchimento gradual (3 paradas, glow) + linha principal;
      • Pontos coloridos por tendência com efeito shadow;
      • Média simples do período (markLine com label em caixa);
      • MM4  — Média Móvel curto prazo (4 períodos, âmbar tracejado);
      • MM20 — Média Móvel longo prazo (20 períodos, laranja tracejado);
      • DataZoom (slider + scroll) quando há mais de 6 pontos;
      • Tooltip HTML rico com pointer cruzado;
      • Toolbox com salvar imagem.
    """
    df_plot = serie.copy()
    df_plot["x_label"] = x_tick_labels
    df_plot["tooltip_valor"] = df_plot["valor"].apply(
        lambda v: _format_value(v, is_percentage)
    )
    df_plot["tooltip_variacao"] = df_plot["variacao_pct"].apply(
        lambda d: format_delta_br(d) if d == d else "—"
    )
    df_plot["trend_color"] = df_plot["variacao_pct"].apply(
        lambda d: trend_color(d, invert=invert_trend)
    )

    media_val = float(df_plot["media"].iloc[0]) if len(df_plot) else 0.0
    media_label = f"Média: {_format_value(media_val, is_percentage)}"
    n_points = len(df_plot)

    main_data = []
    for _, row in df_plot.iterrows():
        val = row["valor"]
        main_data.append({
            "value": None if pd.isna(val) else float(val),
            "x_label": str(row["x_label"]),
            "tooltip_valor": str(row["tooltip_valor"]),
            "tooltip_variacao": str(row["tooltip_variacao"]),
            "itemStyle": {
                "color": str(row["trend_color"]),
                "borderColor": Theme.BG_PRIMARY,
                "borderWidth": 2,
                "shadowBlur": 10,
                "shadowColor": str(row["trend_color"]),
            },
        })

    mm_curto_data = [
        None if pd.isna(row["mm_curto"]) else float(row["mm_curto"])
        for _, row in df_plot.iterrows()
    ]
    mm_longo_data = [
        None if pd.isna(row["mm_longo"]) else float(row["mm_longo"])
        for _, row in df_plot.iterrows()
    ]

    use_zoom = n_points > 6
    grid_bottom = "22%" if use_zoom else "14%"

    data_zoom: list[dict] = []
    if use_zoom:
        data_zoom = [
            {"type": "inside", "start": 0, "end": 100, "minValueSpan": 3},
            {
                "type": "slider",
                "start": 0,
                "end": 100,
                "height": 22,
                "bottom": 10,
                "borderColor": Theme.CARD_BORDER,
                "backgroundColor": "#1b212b",
                "fillerColor": "rgba(79,208,195,0.18)",
                "handleStyle": {"color": Theme.ACCENT, "borderColor": Theme.ACCENT},
                "moveHandleStyle": {"color": Theme.ACCENT},
                "textStyle": {"color": Theme.TEXT_MUTED, "fontSize": 10},
                "dataBackground": {
                    "lineStyle": {"color": Theme.ACCENT_SOFT, "opacity": 0.3},
                    "areaStyle": {"color": "rgba(79,208,195,0.05)"},
                },
                "selectedDataBackground": {
                    "lineStyle": {"color": Theme.ACCENT, "opacity": 0.5},
                    "areaStyle": {"color": "rgba(79,208,195,0.1)"},
                },
            },
        ]

    option: dict = {
        "backgroundColor": "transparent",
        "animation": True,
        "animationDuration": 800,
        "animationEasing": "cubicOut",
        "tooltip": {
            "trigger": "axis",
            "backgroundColor": "rgba(22,27,34,0.97)",
            "borderColor": "rgba(79,208,195,0.28)",
            "borderWidth": 1,
            "padding": [10, 14],
            "confine": True,
            "textStyle": {
                "color": "#e8ecf2",
                "fontFamily": "Inter, sans-serif",
                "fontSize": 13,
            },
            "axisPointer": {
                "type": "cross",
                "crossStyle": {"color": "rgba(79,208,195,0.35)", "width": 1},
                "lineStyle": {
                    "color": "rgba(79,208,195,0.25)",
                    "type": "dashed",
                    "width": 1,
                },
                "label": {
                    "backgroundColor": "#0F1C22",
                    "borderColor": Theme.ACCENT,
                    "borderWidth": 1,
                    "color": Theme.ACCENT,
                    "fontSize": 11,
                },
            },
        },
        "toolbox": {
            "show": True,
            "right": "2%",
            "top": "1%",
            "feature": {
                "saveAsImage": {
                    "title": "Salvar",
                    "name": "grafico",
                    "backgroundColor": Theme.BG_PRIMARY,
                    "iconStyle": {"borderColor": Theme.TEXT_MUTED, "color": "transparent"},
                    "emphasis": {"iconStyle": {"borderColor": Theme.ACCENT}},
                },
                "restore": {
                    "title": "Resetar zoom",
                    "iconStyle": {"borderColor": Theme.TEXT_MUTED, "color": "transparent"},
                    "emphasis": {"iconStyle": {"borderColor": Theme.ACCENT}},
                },
            },
        },
        "legend": {
            "show": True,
            "data": [value_label, "MM4", "MM20"],
            "textStyle": {
                "color": Theme.TEXT_PRIMARY,
                "fontFamily": "Inter, sans-serif",
                "fontSize": 11,
            },
            "bottom": 42 if use_zoom else 4,
            "icon": "roundRect",
            "itemWidth": 18,
            "itemHeight": 4,
            "selectedMode": True,
            "inactiveColor": "#B5D4CD",
        },
        "dataZoom": data_zoom,
        "grid": {
            "left": "3%",
            "right": "5%",
            "bottom": grid_bottom,
            "top": "10%",
            "containLabel": True,
        },
        "xAxis": {
            "type": "category",
            "data": x_tick_labels,
            "boundaryGap": False,
            "axisLine": {"show": False},
            "axisTick": {"show": False},
            "splitLine": {"show": False},
            "axisLabel": {
                "color": Theme.TEXT_MUTED,
                "fontFamily": "Inter, sans-serif",
                "fontSize": 11,
                "rotate": -45 if n_points > 8 else 0,
                "margin": 8,
            },
        },
        "yAxis": {
            "show": False,
            "type": "value",
            "splitLine": {"show": False},
            "axisLabel": {"show": False},
            "axisLine": {"show": False},
            "axisTick": {"show": False},
        },
        "series": [
            {
                "name": value_label,
                "type": "line",
                "smooth": 0.4,
                "symbol": "circle",
                "symbolSize": 10,
                "data": main_data,
                "lineStyle": {
                    "width": 3,
                    "color": Theme.ACCENT,
                    "shadowBlur": 14,
                    "shadowColor": "rgba(79,208,195,0.35)",
                },
                "areaStyle": {
                    "color": {
                        "type": "linear",
                        "x": 0, "y": 0, "x2": 0, "y2": 1,
                        "colorStops": [
                            {"offset": 0,    "color": "rgba(79,208,195,0.22)"},
                            {"offset": 0.55, "color": "rgba(79,208,195,0.06)"},
                            {"offset": 1,    "color": "rgba(79,208,195,0.0)"},
                        ],
                    }
                },
                "emphasis": {
                    "scale": True,
                    "focus": "series",
                    "lineStyle": {
                        "width": 4,
                        "shadowBlur": 22,
                        "shadowColor": "rgba(79,208,195,0.55)",
                    },
                    "itemStyle": {
                        "shadowBlur": 18,
                        "shadowColor": "rgba(79,208,195,0.7)",
                    },
                },
                "markLine": {
                    "symbol": ["none", "none"],
                    "silent": True,
                    "animation": False,
                    "data": [
                        {
                            "yAxis": media_val,
                            "lineStyle": {
                                "color": Theme.ACCENT_SOFT,
                                "type": "dashed",
                                "width": 1.5,
                                "opacity": 0.75,
                            },
                            "label": {
                                "show": True,
                                "position": "insideEndTop",
                                "formatter": media_label,
                                "color": "#e8ecf2",
                                "fontWeight": "bold",
                                "fontSize": 11,
                                "fontFamily": "Inter, sans-serif",
                                "backgroundColor": "rgba(22,27,34,0.92)",
                                "padding": [3, 7],
                                "borderRadius": 4,
                                "borderColor": Theme.ACCENT_SOFT,
                                "borderWidth": 1,
                            },
                        }
                    ],
                },
            },
            {
                "name": "MM4",
                "type": "line",
                "smooth": 0.4,
                "showSymbol": False,
                "data": mm_curto_data,
                "lineStyle": {
                    "width": 1.5,
                    "type": "dashed",
                    "color": _MM_CURTO_COLOR,
                    "opacity": 0.85,
                },
                "emphasis": {"disabled": True},
            },
            {
                "name": "MM20",
                "type": "line",
                "smooth": 0.4,
                "showSymbol": False,
                "data": mm_longo_data,
                "lineStyle": {
                    "width": 1.5,
                    "type": "dashed",
                    "color": _MM_LONGO_COLOR,
                    "opacity": 0.85,
                },
                "emphasis": {"disabled": True},
            },
        ],
    }

    formatter_js = r"""
function(params) {
  if (!params || params.length === 0) return '';
  var main = params.find(function(p) {
    return p.seriesName !== 'MM4' && p.seriesName !== 'MM20';
  });
  if (!main) main = params[0];
  var d = main.data || {};
  var label    = d.x_label || main.name || '';
  var valor    = d.tooltip_valor || (main.value != null ? String(main.value) : '—');
  var variacao = d.tooltip_variacao || '—';
  var invertTrend = __INVERT_TREND__;
  var varColor = '#5E8B83';
  if (variacao.indexOf('+') >= 0) varColor = invertTrend ? '#D93025' : '#18C99E';
  else if (variacao.indexOf('-') >= 0) varColor = invertTrend ? '#18C99E' : '#D93025';
  var dot = '<span style="display:inline-block;width:9px;height:9px;border-radius:50%;'
          + 'background:' + main.color + ';margin-right:6px;vertical-align:middle;'
          + 'box-shadow:0 0 6px ' + main.color + ';"></span>';
  var html = '<div style="font-family:Inter,sans-serif;padding:4px 2px;min-width:215px;">';
  html += '<div style="font-size:11px;font-weight:700;color:#5E8B83;letter-spacing:0.8px;'
        + 'text-transform:uppercase;margin-bottom:9px;padding-bottom:7px;'
        + 'border-bottom:1px solid rgba(79,208,195,0.20);">' + label + '</div>';
  html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:7px;">'
        + '<span style="color:#5E8B83;font-size:12px;">' + dot + main.seriesName + '</span>'
        + '<span style="font-weight:700;color:#e8ecf2;font-size:13px;">' + valor + '</span></div>';
  html += '<div style="display:flex;justify-content:space-between;align-items:center;">'
        + '<span style="color:#5E8B83;font-size:12px;">&nbsp;&nbsp;&nbsp;&nbsp;&#8597; Variação</span>'
        + '<span style="font-weight:600;color:' + varColor + ';font-size:12px;">' + variacao + '</span></div>';
  html += '</div>';
  return html;
}
""".replace("__INVERT_TREND__", "true" if invert_trend else "false")

    return _echart_html(option, formatter_js)


# ---------------------------------------------------------------------------
# Gráfico de ranking por absenteísmo (barras verticais)
# ---------------------------------------------------------------------------

def build_absenteismo_ranking_chart(
    df_filtered: pd.DataFrame,
    top_n: int = 10,
    mode: str = "piores",
) -> str:
    """
    Retorna uma string HTML com o gráfico de barras das TOP-N oficinas
    por absenteísmo (média das últimas 4 semanas disponíveis no filtro).

    mode: 'piores'   → MAIOR absenteísmo (barras vermelhas)
          'melhores' → MENOR absenteísmo (barras verdes)
    """
    _empty_option: dict = {
        "backgroundColor": "transparent",
        "title": {
            "text": "Sem dados disponíveis",
            "left": "center",
            "top": "center",
            "textStyle": {
                "color": Theme.TEXT_MUTED,
                "fontSize": 14,
                "fontFamily": "Inter, sans-serif",
            },
        },
    }

    if df_filtered.empty:
        return _echart_html(_empty_option)

    semanas_disponiveis = sorted(df_filtered[Columns.SEMANA].dropna().unique())
    ultimas = semanas_disponiveis[-_LAST_N_WEEKS:]
    df_janela = df_filtered[df_filtered[Columns.SEMANA].isin(ultimas)]

    agrupado = (
        df_janela
        .groupby(Columns.OFICINA_MP, as_index=False)
        .agg(
            efetivos=(Columns.QTD_EFETIVOS, "sum"),
            trabalhados=(Columns.QTD_TRABALHADOS, "sum"),
        )
    )
    agrupado["absenteismo"] = agrupado.apply(
        lambda r: safe_div(r["efetivos"] - r["trabalhados"], r["efetivos"]) * 100,
        axis=1,
    ).round(2)
    agrupado = agrupado.dropna(subset=["absenteismo"])

    if agrupado.empty:
        _empty_option["title"]["text"] = "Sem dados suficientes"
        return _echart_html(_empty_option)

    if mode == "piores":
        top = agrupado.nlargest(top_n, "absenteismo").copy()
        bar_gradient = {
            "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
            "colorStops": [
                {"offset": 0, "color": "#FF6B6B"},
                {"offset": 1, "color": "rgba(255,76,76,0.35)"},
            ],
        }
        label_color = _RED
        emphasis_shadow = "rgba(255,107,107,0.55)"
        title_text = ""  # O título desta seção é renderizado fora do gráfico (ver ui/layout.py).
        
    else:
        top = agrupado.nsmallest(top_n, "absenteismo").copy()
        bar_gradient = {
            "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
            "colorStops": [
                {"offset": 0, "color": "#18C99E"},
                {"offset": 1, "color": "rgba(24,201,158,0.25)"},
            ],
        }
        
        label_color = _GREEN
        emphasis_shadow = "rgba(24,201,158,0.45)"
        title_text = f"Top {top_n} Menores Absenteísmos — Média das Últimas {len(ultimas)} Semanas"

    top["oficina_label"] = top[Columns.OFICINA_MP].str[:28]
    top["tooltip_abs"]   = top["absenteismo"].apply(format_percent_br)
    top["tooltip_ef"]    = top["efetivos"].apply(format_int_br)
    top["tooltip_trab"]  = top["trabalhados"].apply(format_int_br)

    top = top.sort_values("absenteismo", ascending=True)
    y_data = top["oficina_label"].tolist()
    media_geral = float(top["absenteismo"].mean())

    series_data = [
        {
            "value": float(row["absenteismo"]),
            "oficina_full": str(row[Columns.OFICINA_MP]),
            "tooltip_abs":  str(row["tooltip_abs"]),
            "tooltip_ef":   str(row["tooltip_ef"]),
            "tooltip_trab": str(row["tooltip_trab"]),
        }
        for _, row in top.iterrows()
    ]

    bar_formatter_js = """
function(params) {
  if (!params) return '';
  var d = params.data || {};
  var barColor = typeof params.color === 'string' ? params.color : '#3FE0C5';
  var maxAbs = 50;
  var pct = Math.min(100, Math.round(((d.value || 0) / maxAbs) * 100));
  var html = '<div style="font-family:Inter,sans-serif;padding:4px 2px;min-width:220px;">';
  html += '<div style="font-size:11px;font-weight:700;color:#5E8B83;letter-spacing:0.7px;'
        + 'text-transform:uppercase;margin-bottom:9px;padding-bottom:7px;'
        + 'border-bottom:1px solid rgba(79,208,195,0.20);word-break:break-word;">'
        + (d.oficina_full || '') + '</div>';
  html += '<div style="margin-bottom:8px;">'
        + '<div style="display:flex;justify-content:space-between;margin-bottom:5px;">'
        + '<span style="color:#5E8B83;font-size:12px;">Absenteísmo</span>'
        + '<span style="font-weight:700;font-size:13px;color:' + barColor + ';">' + (d.tooltip_abs || '—') + '</span>'
        + '</div>'
        + '<div style="height:6px;background:#1A2D35;border-radius:3px;overflow:hidden;">'
        + '<div style="height:100%;width:' + pct + '%;background:' + barColor + ';border-radius:3px;'
        + 'box-shadow:0 0 8px ' + barColor + ';transition:width 0.3s;"></div>'
        + '</div></div>';
  html += '<div style="height:1px;background:linear-gradient(90deg,rgba(79,208,195,0.25),transparent);margin-bottom:7px;"></div>';
  html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px;">'
        + '<span style="color:#5E8B83;font-size:12px;">Efetivos</span>'
        + '<span style="font-weight:600;color:#e8ecf2;font-size:12px;">' + (d.tooltip_ef || '—') + '</span>'
        + '</div>';
  html += '<div style="display:flex;justify-content:space-between;align-items:center;">'
        + '<span style="color:#5E8B83;font-size:12px;">Trabalhados</span>'
        + '<span style="font-weight:600;color:#e8ecf2;font-size:12px;">' + (d.tooltip_trab || '—') + '</span>'
        + '</div>';
  html += '</div>';
  return html;
}
"""

    option: dict = {
        "backgroundColor": "transparent",
        "animation": True,
        "animationDuration": 900,
        "animationEasing": "elasticOut",
        "title": {
            "text": title_text,
            "left": "left",
            "top": "2%",
            "textStyle": {
                "color": Theme.TEXT_PRIMARY,
                "fontFamily": "Sora, sans-serif",
                "fontSize": 14,
                "fontWeight": "bold",
            },
        },
        "tooltip": {
            "trigger": "item",
            "backgroundColor": "rgba(22,27,34,0.97)",
            "borderColor": "rgba(79,208,195,0.28)",
            "borderWidth": 1,
            "padding": [10, 14],
            "confine": True,
            "textStyle": {
                "color": "#e8ecf2",
                "fontFamily": "Inter, sans-serif",
                "fontSize": 13,
            },
        },
        "grid": {
            "left": "3%",
            "right": "4%",
            "bottom": "28%",
            "top": "18%",
            "containLabel": True,
        },
        "xAxis": {
            "type": "category",
            "data": y_data,
            "axisLine": {"show": False},
            "axisTick": {"show": False},
            "splitLine": {"show": False},
            "axisLabel": {
                "color": Theme.TEXT_PRIMARY,
                "fontFamily": "Inter, sans-serif",
                "fontSize": 11,
                "rotate": -40,
                "interval": 0,
                "overflow": "truncate",
                "width": 110,
            },
        },
        "yAxis": {
            "show": False,
            "type": "value",
            "splitLine": {"show": False},
            "axisLabel": {"show": False},
            "axisLine": {"show": False},
            "axisTick": {"show": False},
        },
        "series": [
            {
                "type": "bar",
                "barWidth": "50%",
                "data": series_data,
                "itemStyle": {
                    "color": bar_gradient,
                    "borderRadius": [6, 6, 0, 0],
                },
                "emphasis": {
                    "itemStyle": {
                        "shadowBlur": 16,
                        "shadowColor": emphasis_shadow,
                    }
                },
                "label": {
                    "show": True,
                    "position": "top",
                    "color": label_color,
                    "fontWeight": "bold",
                    "fontFamily": "Inter, sans-serif",
                    "fontSize": 13,
                    "backgroundColor": "rgba(22,27,34,0.88)",
                    "padding": [3, 6],
                    "borderRadius": 4,
                    "formatter": "{c}%",
                },
                "markLine": {
                    "symbol": ["none", "none"],
                    "silent": True,
                    "animation": False,
                    "data": [
                        {
                            "yAxis": media_geral,
                            "lineStyle": {
                                "color": Theme.NEUTRAL,
                                "type": "dashed",
                                "width": 2,
                                "opacity": 0.7,
                            },
                            "label": {
                                "show": True,
                                "position": "insideEndTop",
                                "formatter": f"Média: {format_percent_br(media_geral)}",
                                "color": "#e8ecf2",
                                "fontWeight": "bold",
                                "fontSize": 11,
                                "fontFamily": "Inter, sans-serif",
                                "backgroundColor": "rgba(22,27,34,0.92)",
                                "padding": [3, 7],
                                "borderRadius": 4,
                            },
                        }
                    ],
                },
            }
        ],
    }

    return _echart_html(option, bar_formatter_js)
