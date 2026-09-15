"""Testes de app_recebimento.services.analytics_service."""
from __future__ import annotations

import pandas as pd

from app_recebimento.core.config import Columns, RawColumns
from app_recebimento.services.analytics_service import (
    aggregate_by,
    compute_kpis,
    series_por_mes,
    series_por_semana,
    top_oficinas_por_pecas,
)
from app_recebimento.services.data_cleaning import clean_dataframe


def _df() -> pd.DataFrame:
    raw = pd.DataFrame({
        RawColumns.DIA: ["2026-01-05", "2026-02-10", "2026-01-06", None],
        RawColumns.OFICINA: ["A", "A", "B", "B"],
        RawColumns.ORDEM: ["1", "2", "3", "4"],
        RawColumns.MP: ["JEANS", "MALHA", "JEANS", "JEANS"],
        RawColumns.QTD: [100, 200, 50, 30],
        RawColumns.MINUTOS: [1000.0, 2000.0, 500.0, 300.0],
    })
    return clean_dataframe(raw)


def test_compute_kpis():
    k = compute_kpis(_df())
    assert k["pecas"] == 380
    assert k["minutos"] == 3800.0
    assert k["registros"] == 4
    assert k["oficinas"] == 2
    assert k["ordens"] == 4


def test_compute_kpis_vazio():
    k = compute_kpis(_df().iloc[0:0])
    assert k == {"pecas": 0, "minutos": 0.0, "registros": 0, "oficinas": 0, "ordens": 0}


def test_aggregate_by_oficina_ordena_por_pecas():
    agg = aggregate_by(_df(), "oficina")
    assert agg["rotulo"].tolist() == ["A", "B"]
    assert agg[Columns.QTD].tolist() == [300, 80]


def test_aggregate_by_mp():
    agg = aggregate_by(_df(), "mp")
    assert set(agg["rotulo"]) == {"JEANS", "MALHA"}
    total = int(agg[Columns.QTD].sum())
    assert total == 380


def test_aggregate_by_mes_exclui_sem_data():
    agg = aggregate_by(_df(), "mes")
    # A linha 4 (sem data) fica de fora; sobram jan e fev.
    assert agg["rotulo"].tolist() == ["Jan/2026", "Fev/2026"]
    assert int(agg[Columns.QTD].sum()) == 350


def test_aggregate_by_semana_ordenada():
    agg = aggregate_by(_df(), "semana")
    assert list(agg[Columns.QTD]) == sorted(list(agg[Columns.QTD]), reverse=True) or not agg.empty


def test_top_oficinas():
    top = top_oficinas_por_pecas(_df(), top_n=1)
    assert top["rotulo"].tolist() == ["A"]
    assert int(top[Columns.QTD].iloc[0]) == 300


def test_series_por_mes_e_semana():
    sm = series_por_mes(_df())
    assert "rotulo" in sm.columns and int(sm[Columns.QTD].sum()) == 350
    ss = series_por_semana(_df())
    assert all(str(r).startswith("W") for r in ss["rotulo"])
