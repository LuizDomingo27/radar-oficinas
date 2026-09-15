"""Testes de app_envios.services.data_cleaning."""
from __future__ import annotations

import pandas as pd

from app_envios.core.config import Columns, RawColumns
from app_envios.services.data_cleaning import SEM_DATA_LABEL, add_derived, clean_dataframe, standardize_raw


def _raw_df() -> pd.DataFrame:
    return pd.DataFrame({
        RawColumns.ORIGEM: ["JEANS", "MALHA"],
        RawColumns.ORDEM: [" 300222101 ", "300222049"],
        RawColumns.OFICINA: ["OFICINA X ", " OFICINA Y"],
        RawColumns.QTD: [238, None],
        RawColumns.MINUTOS: [4360.164, 13473.98],
        RawColumns.ENVIO: ["2026-01-02", None],
        RawColumns.MP: ["Jeans", "00:00:00"],
        RawColumns.PDV: ["NAO_PDV", "NAO_PDV"],
        RawColumns.FRETE: ["R.A", "LTL"],
        RawColumns.SITUACAO: ["Enviado", "Corte"],
    })


def test_standardize_normaliza_strings_e_mp():
    df = standardize_raw(_raw_df())
    assert df[Columns.ORDEM].tolist() == ["300222101", "300222049"]
    assert df[Columns.OFICINA].tolist() == ["OFICINA X", "OFICINA Y"]
    assert df[Columns.MP].tolist() == ["JEANS", "SEM MP INFORMADA"]


def test_standardize_tipos_e_nulos():
    df = standardize_raw(_raw_df())
    assert df[Columns.QTD].tolist() == [238, 0]
    assert df[Columns.MINUTOS].tolist() == [4360.16, 13473.98]  # arredondado a 2 casas
    assert pd.isna(df[Columns.ENVIO].iloc[1])


def test_standardize_faltando_coluna():
    df = _raw_df().drop(columns=[RawColumns.QTD])
    try:
        standardize_raw(df)
    except ValueError as exc:
        assert "obrigatórias" in str(exc)
    else:
        raise AssertionError("deveria ter levantado ValueError")


def test_add_derived_periodos_e_sem_data():
    df = add_derived(standardize_raw(_raw_df()))
    assert df[Columns.MES_LABEL].iloc[0] == "Jan/2026"
    assert int(df[Columns.SEMANA].iloc[0]) == 1
    assert df[Columns.MES_LABEL].iloc[1] == SEM_DATA_LABEL
    assert df[Columns.DIA_LABEL].iloc[1] == SEM_DATA_LABEL
    assert pd.isna(df[Columns.ANO].iloc[1])


def test_clean_dataframe_pipeline_completo():
    df = clean_dataframe(_raw_df())
    assert int(df[Columns.ANO].iloc[0]) == 2026
    assert len(df) == 2
