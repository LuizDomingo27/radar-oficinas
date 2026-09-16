"""
Testes de app_common.movimentacao.analytics.

Rodam contra AS DUAS áreas (Envios e Recebimento) com os mesmos dados, porque o
ponto do núcleo compartilhado é justamente que as duas produzam o mesmo número.
"""
from __future__ import annotations

import pandas as pd
import pytest

from app_common.movimentacao.analytics import (
    aggregate_by,
    compute_kpis,
    series_por_mes,
    series_por_semana,
    top_oficinas_por_pecas,
)
from app_common.movimentacao.area import ColunasMovimentacao as C
from app_common.movimentacao.derivacao import add_derived
from app_envios.core.config import AREA as AREA_ENVIOS
from app_recebimento.core.config import AREA as AREA_RECEBIMENTO

AREAS = [AREA_ENVIOS, AREA_RECEBIMENTO]
IDS = [a.chave for a in AREAS]


def _df(area) -> pd.DataFrame:
    """Mesmo conjunto de fatos, materializado na coluna de data de cada área."""
    base = pd.DataFrame({
        C.ORDEM: ["1", "2", "3", "4"],
        C.OFICINA: ["A", "A", "B", "B"],
        C.QTD: [100, 200, 50, 30],
        C.MINUTOS: [1000.0, 2000.0, 500.0, 300.0],
        C.MP: ["JEANS", "MALHA", "JEANS", "JEANS"],
        area.coluna_data: pd.to_datetime(
            ["2026-01-05", "2026-02-10", "2026-01-06", None]
        ),
    })
    return add_derived(base, coluna_data=area.coluna_data)


@pytest.mark.parametrize("area", AREAS, ids=IDS)
def test_compute_kpis(area):
    k = compute_kpis(_df(area))
    assert k == {
        "pecas": 380, "minutos": 3800.0, "registros": 4, "oficinas": 2, "ordens": 4
    }


@pytest.mark.parametrize("area", AREAS, ids=IDS)
def test_compute_kpis_vazio(area):
    k = compute_kpis(_df(area).iloc[0:0])
    assert k == {"pecas": 0, "minutos": 0.0, "registros": 0, "oficinas": 0, "ordens": 0}


@pytest.mark.parametrize("area", AREAS, ids=IDS)
def test_aggregate_by_oficina_ordena_por_pecas(area):
    agg = aggregate_by(_df(area), "oficina", coluna_data=area.coluna_data)
    assert agg["rotulo"].tolist() == ["A", "B"]
    assert agg[C.QTD].tolist() == [300, 80]
    assert agg["registros"].tolist() == [2, 2]


@pytest.mark.parametrize("area", AREAS, ids=IDS)
def test_aggregate_by_mp_soma_tudo(area):
    agg = aggregate_by(_df(area), "mp", coluna_data=area.coluna_data)
    assert set(agg["rotulo"]) == {"JEANS", "MALHA"}
    assert int(agg[C.QTD].sum()) == 380


@pytest.mark.parametrize("area", AREAS, ids=IDS)
def test_aggregate_by_mes_exclui_linha_sem_data(area):
    agg = aggregate_by(_df(area), "mes", coluna_data=area.coluna_data)
    assert agg["rotulo"].tolist() == ["Jan/2026", "Fev/2026"]
    assert int(agg[C.QTD].sum()) == 350


@pytest.mark.parametrize("area", AREAS, ids=IDS)
def test_aggregate_by_dataframe_vazio(area):
    agg = aggregate_by(_df(area).iloc[0:0], "oficina", coluna_data=area.coluna_data)
    assert agg.empty
    assert list(agg.columns) == ["rotulo", C.QTD, C.MINUTOS, "registros"]


@pytest.mark.parametrize("area", AREAS, ids=IDS)
def test_aggregate_by_granularidade_desconhecida(area):
    with pytest.raises(ValueError, match="Granularidade desconhecida"):
        aggregate_by(_df(area), "trimestre", coluna_data=area.coluna_data)


@pytest.mark.parametrize("area", AREAS, ids=IDS)
def test_top_oficinas(area):
    top = top_oficinas_por_pecas(_df(area), top_n=1)
    assert top["rotulo"].tolist() == ["A"]
    assert int(top[C.QTD].iloc[0]) == 300


@pytest.mark.parametrize("area", AREAS, ids=IDS)
def test_top_oficinas_vazio(area):
    assert top_oficinas_por_pecas(_df(area).iloc[0:0]).empty


@pytest.mark.parametrize("area", AREAS, ids=IDS)
def test_series_por_mes(area):
    sm = series_por_mes(_df(area), coluna_data=area.coluna_data)
    assert list(sm.columns) == ["rotulo", C.QTD, C.MINUTOS]
    assert int(sm[C.QTD].sum()) == 350


@pytest.mark.parametrize("area", AREAS, ids=IDS)
def test_series_por_semana_prefixo_w(area):
    ss = series_por_semana(_df(area), coluna_data=area.coluna_data)
    assert all(str(r).startswith("W") for r in ss["rotulo"])


def test_as_duas_areas_produzem_os_mesmos_numeros():
    """A garantia central do núcleo compartilhado: mesmo fato, mesmo resultado."""
    kpi_envios = compute_kpis(_df(AREA_ENVIOS))
    kpi_receb = compute_kpis(_df(AREA_RECEBIMENTO))
    assert kpi_envios == kpi_receb
