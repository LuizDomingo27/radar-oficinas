"""
ui/components/charts.py — gráficos ECharts 5.x da área "Envios".

Cada função devolve um HTML autossuficiente (carrega o ECharts do CDN),
renderizado via ``st.components.v1.html``. Mesmo padrão de ``app_postos``:
tema escuro alinhado ao Radar, tooltips ricos e rótulos de valor nas barras.
"""

from __future__ import annotations

import json

import pandas as pd

from app_envios.core.config import Columns, Theme
from app_envios.core.utils import format_int_br, format_minutos_br

_ECHARTS_CDN = "https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"


def _echart_html(option: dict, formatter_js: str | None = None) -> str:
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
    renderer: 'canvas', backgroundColor: 'transparent'
  }});
  var option = {option_json};
  {formatter_block}
  chart.setOption(option);
  window.addEventListener('resize', function() {{ chart.resize(); }});
}})();
</script>
</body>
</html>"""


def _empty_html(texto: str = "Sem dados disponíveis") -> str:
    return _echart_html({
        "backgroundColor": "transparent",
        "title": {
            "text": texto, "left": "center", "top": "center",
            "textStyle": {"color": Theme.TEXT_MUTED, "fontSize": 14, "fontFamily": "Inter, sans-serif"},
        },
    })


def _bar_gradient(top: str, bottom: str) -> dict:
    return {
        "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
        "colorStops": [{"offset": 0, "color": top}, {"offset": 1, "color": bottom}],
    }


def build_top_oficinas_chart(df_top: pd.DataFrame, top_n: int = 10) -> str:
    """Barras verticais das oficinas que mais receberam peças (com minutos no tooltip)."""
    if df_top is None or df_top.empty:
        return _empty_html()

    df = df_top.copy()
    df["label_curto"] = df["rotulo"].astype(str).str.slice(0, 26)
    df["tt_pecas"] = df[Columns.QTD].apply(format_int_br)
    df["tt_min"] = df[Columns.MINUTOS].apply(format_minutos_br)

    series_data = [
        {
            "value": int(row[Columns.QTD]),
            "oficina_full": str(row["rotulo"]),
            "tt_pecas": str(row["tt_pecas"]),
            "tt_min": str(row["tt_min"]),
            # Rótulo já formatado em pt-BR (sem chaves → o ECharts o exibe
            # literalmente, em vez de {c} que mostraria o número cru).
            "label": {"formatter": str(row["tt_pecas"])},
        }
        for _, row in df.iterrows()
    ]

    option = {
        "backgroundColor": "transparent",
        "animation": True, "animationDuration": 800, "animationEasing": "cubicOut",
        "tooltip": {
            "trigger": "item",
            "backgroundColor": "rgba(22,27,34,0.97)",
            "borderColor": "rgba(79,208,195,0.28)", "borderWidth": 1,
            "padding": [10, 14], "confine": True,
            "textStyle": {"color": "#e8ecf2", "fontFamily": "Inter, sans-serif", "fontSize": 13},
        },
        "grid": {"left": "3%", "right": "4%", "bottom": "26%", "top": "12%", "containLabel": True},
        "xAxis": {
            "type": "category", "data": df["label_curto"].tolist(),
            "axisLine": {"show": False}, "axisTick": {"show": False}, "splitLine": {"show": False},
            "axisLabel": {
                "color": Theme.TEXT_PRIMARY, "fontFamily": "Inter, sans-serif", "fontSize": 11,
                "rotate": -40, "interval": 0, "overflow": "truncate", "width": 105,
            },
        },
        "yAxis": {
            "show": False, "type": "value", "splitLine": {"show": False},
            "axisLabel": {"show": False}, "axisLine": {"show": False}, "axisTick": {"show": False},
        },
        "series": [{
            "type": "bar", "barWidth": "55%", "data": series_data,
            "itemStyle": {"color": _bar_gradient("#4fd0c3", "rgba(79,208,195,0.30)"), "borderRadius": [6, 6, 0, 0]},
            "emphasis": {"itemStyle": {"shadowBlur": 16, "shadowColor": "rgba(79,208,195,0.55)"}},
            "label": {
                "show": True, "position": "top", "color": Theme.ACCENT, "fontWeight": "bold",
                "fontFamily": "Inter, sans-serif", "fontSize": 12,
                "backgroundColor": "rgba(22,27,34,0.88)", "padding": [3, 6], "borderRadius": 4,
            },
        }],
    }

    formatter_js = """
function(p){
  if(!p) return '';
  var d = p.data || {};
  var html = '<div style="font-family:Inter,sans-serif;padding:4px 2px;min-width:210px;">';
  html += '<div style="font-size:11px;font-weight:700;color:#5E8B83;letter-spacing:0.7px;'
        + 'text-transform:uppercase;margin-bottom:9px;padding-bottom:7px;'
        + 'border-bottom:1px solid rgba(79,208,195,0.20);word-break:break-word;">' + (d.oficina_full||'') + '</div>';
  html += '<div style="display:flex;justify-content:space-between;margin-bottom:5px;">'
        + '<span style="color:#5E8B83;font-size:12px;">Peças</span>'
        + '<span style="font-weight:700;color:#4fd0c3;font-size:13px;">' + (d.tt_pecas||'—') + '</span></div>';
  html += '<div style="display:flex;justify-content:space-between;">'
        + '<span style="color:#5E8B83;font-size:12px;">Minutos</span>'
        + '<span style="font-weight:600;color:#e8ecf2;font-size:12px;">' + (d.tt_min||'—') + '</span></div>';
  html += '</div>';
  return html;
}
"""
    return _echart_html(option, formatter_js)


def build_periodo_chart(serie: pd.DataFrame, value_label: str, color_top: str = "#4fd0c3") -> str:
    """Barras de peças enviadas por período (mês ou semana), com minutos no tooltip."""
    if serie is None or serie.empty:
        return _empty_html("Sem dados de período")

    df = serie.copy()
    df["tt_pecas"] = df[Columns.QTD].apply(format_int_br)
    df["tt_min"] = df[Columns.MINUTOS].apply(format_minutos_br)

    series_data = [
        {"value": int(row[Columns.QTD]), "periodo": str(row["rotulo"]),
         "tt_pecas": str(row["tt_pecas"]), "tt_min": str(row["tt_min"]),
         # Rótulo já formatado em pt-BR (exibido literalmente pelo ECharts).
         "label": {"formatter": str(row["tt_pecas"])}}
        for _, row in df.iterrows()
    ]
    n = len(df)

    option = {
        "backgroundColor": "transparent",
        "animation": True, "animationDuration": 800, "animationEasing": "cubicOut",
        "title": {
            "text": value_label, "left": "left", "top": "1%",
            "textStyle": {"color": Theme.TEXT_PRIMARY, "fontFamily": "Sora, sans-serif",
                          "fontSize": 13, "fontWeight": "bold"},
        },
        "tooltip": {
            "trigger": "item",
            "backgroundColor": "rgba(22,27,34,0.97)",
            "borderColor": "rgba(79,208,195,0.28)", "borderWidth": 1,
            "padding": [10, 14], "confine": True,
            "textStyle": {"color": "#e8ecf2", "fontFamily": "Inter, sans-serif", "fontSize": 13},
        },
        "grid": {"left": "3%", "right": "4%", "bottom": "14%", "top": "18%", "containLabel": True},
        "xAxis": {
            "type": "category", "data": df["rotulo"].astype(str).tolist(),
            "axisLine": {"show": False}, "axisTick": {"show": False}, "splitLine": {"show": False},
            "axisLabel": {"color": Theme.TEXT_MUTED, "fontFamily": "Inter, sans-serif",
                          "fontSize": 11, "rotate": -40 if n > 8 else 0, "interval": 0},
        },
        "yAxis": {
            "show": False, "type": "value", "splitLine": {"show": False},
            "axisLabel": {"show": False}, "axisLine": {"show": False}, "axisTick": {"show": False},
        },
        "series": [{
            "type": "bar", "barWidth": "55%" if n <= 12 else "70%", "data": series_data,
            "itemStyle": {"color": _bar_gradient(color_top, "rgba(79,208,195,0.25)"), "borderRadius": [5, 5, 0, 0]},
            "emphasis": {"itemStyle": {"shadowBlur": 14, "shadowColor": "rgba(79,208,195,0.5)"}},
            "label": {
                "show": n <= 16, "position": "top", "color": Theme.TEXT_PRIMARY, "fontWeight": "bold",
                "fontFamily": "Inter, sans-serif", "fontSize": 11,
            },
        }],
    }

    formatter_js = """
function(p){
  if(!p) return '';
  var d = p.data || {};
  var html = '<div style="font-family:Inter,sans-serif;padding:4px 2px;min-width:190px;">';
  html += '<div style="font-size:11px;font-weight:700;color:#5E8B83;letter-spacing:0.7px;'
        + 'text-transform:uppercase;margin-bottom:9px;padding-bottom:7px;'
        + 'border-bottom:1px solid rgba(79,208,195,0.20);">' + (d.periodo||'') + '</div>';
  html += '<div style="display:flex;justify-content:space-between;margin-bottom:5px;">'
        + '<span style="color:#5E8B83;font-size:12px;">Peças</span>'
        + '<span style="font-weight:700;color:#4fd0c3;font-size:13px;">' + (d.tt_pecas||'—') + '</span></div>';
  html += '<div style="display:flex;justify-content:space-between;">'
        + '<span style="color:#5E8B83;font-size:12px;">Minutos</span>'
        + '<span style="font-weight:600;color:#e8ecf2;font-size:12px;">' + (d.tt_min||'—') + '</span></div>';
  html += '</div>';
  return html;
}
"""
    return _echart_html(option, formatter_js)
