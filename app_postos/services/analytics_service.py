"""
services/analytics_service.py
---------------------------------
Responsabilidade única: construir as séries de evolução (semanal e
mensal) de cada indicador, incluindo média do período e variação
percentual entre pontos consecutivos — dados consumidos pelos gráficos
de linha da camada `ui`.

Por que a taxa de absenteísmo é recalculada por grupo (e não é uma média
simples das taxas semanais): absenteísmo é uma razão entre duas somas
(efetivos e trabalhados). Calcular a média das taxas semanais distorce
o resultado quando o efetivo varia entre semanas/oficinas. Por isso,
agregamos primeiro os totais de cada grupo (semana ou mês) e só then
aplicamos a fórmula da taxa.
"""

from __future__ import annotations

import pandas as pd

from app_postos.core.config import Columns
from app_common.formatting import safe_div

_BASE_SUM_COLUMNS = [
    Columns.QTD_EFETIVOS,
    Columns.QTD_TRABALHADOS,
    Columns.CONTRATACOES,
    Columns.DEMISSOES,
]


def _grouped_totals(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """Soma as métricas-base por grupo (ex.: por semana, ou por mês)."""
    return (
        df.groupby(group_cols, as_index=False)[_BASE_SUM_COLUMNS]
        .sum()
        .sort_values(group_cols)
        .reset_index(drop=True)
    )


# Indicadores cuja evolução mensal NÃO deve somar as semanas do mês.
# Efetivos e trabalhados são um retrato de headcount (estoque), não um fluxo
# acumulável: somar as semanas do mês infla o valor (ex.: 4× o efetivo real).
# Para esses dois usamos a fotografia da ÚLTIMA semana do mês. Os demais
# indicadores (contratações, demissões, ausência e absenteísmo) continuam
# somando/derivando dos totais do mês, conforme regra de negócio confirmada.
_LAST_WEEK_MONTHLY_INDICATORS = frozenset({"efetivos", "trabalhados"})


def _last_week_totals(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """Totais da ÚLTIMA semana de cada grupo (ex.: a última semana de cada mês).

    Primeiro soma as métricas-base por (grupo + semana) — consolidando as
    oficinas de cada semana — e depois mantém, para cada grupo, apenas a
    semana de maior número. Isso é coerente com o "resultado da semana atual"
    dos KPIs, que também usa a maior semana do recorte (ver ui/layout.py).

    Devolve um DataFrame com o mesmo contrato de colunas de `_grouped_totals`
    (as colunas de `group_cols` + `_BASE_SUM_COLUMNS`), para ser consumido
    de forma intercambiável por `_finalize_series`.
    """
    weekly = df.groupby(
        [*group_cols, Columns.SEMANA], as_index=False
    )[_BASE_SUM_COLUMNS].sum()
    if weekly.empty:
        return weekly.drop(columns=[Columns.SEMANA]).reset_index(drop=True)
    last_week_idx = weekly.groupby(group_cols)[Columns.SEMANA].idxmax()
    return (
        weekly.loc[last_week_idx]
        .drop(columns=[Columns.SEMANA])
        .sort_values(group_cols)
        .reset_index(drop=True)
    )


def _metric_value_series(grouped: pd.DataFrame, indicator_key: str) -> pd.Series:
    """Deriva a coluna 'valor' a partir dos totais agregados, por indicador."""
    if indicator_key == "efetivos":
        return grouped[Columns.QTD_EFETIVOS]
    if indicator_key == "trabalhados":
        return grouped[Columns.QTD_TRABALHADOS]
    if indicator_key == "contratacoes":
        return grouped[Columns.CONTRATACOES]
    if indicator_key == "demissoes":
        return grouped[Columns.DEMISSOES]
    if indicator_key == "ausencia":
        return grouped[Columns.QTD_EFETIVOS] - grouped[Columns.QTD_TRABALHADOS]
    if indicator_key == "absenteismo":
        return grouped.apply(
            lambda row: safe_div(
                row[Columns.QTD_EFETIVOS] - row[Columns.QTD_TRABALHADOS],
                row[Columns.QTD_EFETIVOS],
            )
            * 100,
            axis=1,
        )
    raise ValueError(f"Indicador desconhecido: {indicator_key}")


def _finalize_series(grouped: pd.DataFrame, x_col: str, indicator_key: str) -> pd.DataFrame:
    """
    Adiciona valor, variação percentual ponto-a-ponto e média simples:

      • valor        — valor do indicador em cada período.
      • variacao_pct — variação percentual em relação ao período anterior.
      • media        — média aritmética simples de todos os pontos da série
                       (exibida como linha de referência no gráfico).
    """
    out = grouped[[x_col]].copy()
    out["valor"] = _metric_value_series(grouped, indicator_key)
    out["variacao_pct"] = out["valor"].pct_change() * 100
    out["media"] = out["valor"].mean()
    return out


def weekly_evolution(df: pd.DataFrame, indicator_key: str) -> pd.DataFrame:
    """
    Série semanal do indicador informado.

    Retorna colunas: semana, valor, variacao_pct, media.
    `variacao_pct` é a variação percentual em relação à semana anterior
    dentro do recorte filtrado (não necessariamente semanas consecutivas
    no calendário, caso haja semanas sem dados no filtro atual).
    """
    grouped = _grouped_totals(df, [Columns.SEMANA])
    return _finalize_series(grouped, Columns.SEMANA, indicator_key)


def monthly_evolution(df: pd.DataFrame, indicator_key: str) -> pd.DataFrame:
    """
    Série mensal do indicador informado.

    Retorna colunas: ano_mes, mes_label, valor, variacao_pct, media.
    O período mensal é sempre derivado de `data_efetivos` (ver
    `services/data_cleaning.py` para o porquê).

    Efetivos e trabalhados usam a fotografia da última semana do mês
    (ver `_last_week_totals` e `_LAST_WEEK_MONTHLY_INDICATORS`); os demais
    indicadores usam a soma/derivação dos totais do mês.
    """
    label_map = df.drop_duplicates(Columns.ANO_MES).set_index(Columns.ANO_MES)[Columns.MES_LABEL]

    if indicator_key in _LAST_WEEK_MONTHLY_INDICATORS:
        grouped = _last_week_totals(df, [Columns.ANO_MES])
    else:
        grouped = _grouped_totals(df, [Columns.ANO_MES])
    serie = _finalize_series(grouped, Columns.ANO_MES, indicator_key)
    serie[Columns.MES_LABEL] = serie[Columns.ANO_MES].map(label_map)
    return serie


def latest_period_delta(serie: pd.DataFrame) -> float:
    """Variação percentual do último ponto da série em relação ao anterior."""
    if len(serie) < 2:
        return float("nan")
    return float(serie["variacao_pct"].iloc[-1])


# ---------------------------------------------------------------------------
# Agregações por dimensão (MP e oficina) — consumidas pelas tabelas e pelo
# ranking da camada `ui`. Ficam aqui, e não nas funções de desenho, porque
# `groupby`, soma de indicador e cálculo de taxa são regra de negócio: a `ui`
# só formata o que recebe pronto.
# ---------------------------------------------------------------------------

# Janela do ranking de absenteísmo por oficina: as N últimas semanas presentes
# no recorte filtrado (regra de negócio, não preferência de gráfico).
RANKING_ULTIMAS_SEMANAS = 4

_MP_COLUMNS = ["efetivos", "trabalhados", "contratacoes", "demissoes",
               "ausencia", "absenteismo"]
_OFICINA_COLUMNS = ["efetivos", "trabalhados", "contratacoes", "demissoes",
                    "absenteismo_%"]


def _somas_por(df: pd.DataFrame, chave: str) -> pd.DataFrame:
    """Soma as quatro métricas-base agrupando por ``chave``."""
    return df.groupby(chave, as_index=False).agg(
        efetivos=(Columns.QTD_EFETIVOS, "sum"),
        trabalhados=(Columns.QTD_TRABALHADOS, "sum"),
        contratacoes=(Columns.CONTRATACOES, "sum"),
        demissoes=(Columns.DEMISSOES, "sum"),
    )


def _taxa_absenteismo(grp: pd.DataFrame, casas: int) -> pd.Series:
    """Taxa de absenteísmo (%) por linha já agregada, com ``casas`` decimais.

    Razão entre somas (ausência ÷ efetivos), nunca média de taxas — pelo mesmo
    motivo explicado no topo deste módulo.
    """
    return grp.apply(
        lambda r: safe_div(r["efetivos"] - r["trabalhados"], r["efetivos"]) * 100,
        axis=1,
    ).round(casas)


def aggregate_by_mp(df: pd.DataFrame) -> pd.DataFrame:
    """
    Totais por matéria-prima, com ausência e taxa de absenteísmo (2 casas).

    Ordenado pelo nome da MP. DataFrame vazio devolve o mesmo contrato de
    colunas, vazio — quem desenha só precisa checar ``.empty``.
    """
    if df.empty:
        return pd.DataFrame(columns=[Columns.MP, *_MP_COLUMNS])

    grp = _somas_por(df, Columns.MP)
    grp["ausencia"] = grp["efetivos"] - grp["trabalhados"]
    grp["absenteismo"] = _taxa_absenteismo(grp, casas=2)
    return grp.sort_values(Columns.MP).reset_index(drop=True)


def aggregate_by_oficina(df: pd.DataFrame) -> pd.DataFrame:
    """
    Totais por oficina+MP, com taxa de absenteísmo (1 casa), do menor para o
    maior absenteísmo — a ordem em que a Tabela Completa é lida.
    """
    if df.empty:
        return pd.DataFrame(columns=[Columns.OFICINA_MP, *_OFICINA_COLUMNS])

    grp = _somas_por(df, Columns.OFICINA_MP)
    grp["absenteismo_%"] = _taxa_absenteismo(grp, casas=1)
    return grp.sort_values("absenteismo_%", ascending=True).reset_index(drop=True)


def absenteismo_por_oficina(
    df: pd.DataFrame, *, semanas: int = RANKING_ULTIMAS_SEMANAS
) -> tuple[pd.DataFrame, int]:
    """
    Absenteísmo por oficina+MP nas ``semanas`` últimas semanas do recorte.

    Devolve ``(agregado, semanas_usadas)`` — o segundo valor é quantas semanas
    realmente existiam no recorte, usado no título do gráfico. Oficinas sem taxa
    calculável (efetivo zero) saem do resultado.
    """
    if df.empty:
        return pd.DataFrame(columns=[Columns.OFICINA_MP, "efetivos", "trabalhados",
                                     "absenteismo"]), 0

    disponiveis = sorted(df[Columns.SEMANA].dropna().unique())
    ultimas = disponiveis[-semanas:]
    janela = df[df[Columns.SEMANA].isin(ultimas)]

    grp = janela.groupby(Columns.OFICINA_MP, as_index=False).agg(
        efetivos=(Columns.QTD_EFETIVOS, "sum"),
        trabalhados=(Columns.QTD_TRABALHADOS, "sum"),
    )
    grp["absenteismo"] = _taxa_absenteismo(grp, casas=2)
    return grp.dropna(subset=["absenteismo"]), len(ultimas)


def ranking_absenteismo(agregado: pd.DataFrame, *, mode: str, top_n: int) -> pd.DataFrame:
    """
    As ``top_n`` oficinas do ranking, sempre ordenadas do menor para o maior
    absenteísmo (ordem de desenho das barras).

    mode: ``'piores'`` → maiores taxas · ``'melhores'`` → menores taxas.
    """
    if mode not in ("piores", "melhores"):
        raise ValueError(f"Modo de ranking desconhecido: {mode}")
    if agregado.empty:
        return agregado

    escolhidas = (
        agregado.nlargest(top_n, "absenteismo")
        if mode == "piores"
        else agregado.nsmallest(top_n, "absenteismo")
    )
    return escolhidas.sort_values("absenteismo", ascending=True).reset_index(drop=True)


def media_absenteismo(ranking: pd.DataFrame) -> float:
    """Média simples das taxas do ranking (linha de referência do gráfico)."""
    if ranking.empty:
        return float("nan")
    return float(ranking["absenteismo"].mean())
