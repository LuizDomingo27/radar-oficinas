"""Testes de app_recebimento.services.data_cleaning."""
from __future__ import annotations

import pandas as pd

from app_recebimento.core.config import Columns, RawColumns
from app_recebimento.services.data_cleaning import (
    SEM_DATA_LABEL,
    add_derived,
    clean_dataframe,
    standardize_raw,
)


def _raw_df() -> pd.DataFrame:
    return pd.DataFrame({
        RawColumns.DIA: ["2026-01-02", None],
        RawColumns.OFICINA: ["OFICINA X ", " OFICINA Y"],
        RawColumns.ORDEM: [300222936, 300223074],
        RawColumns.MP: ["Jeans", "Malha"],
        RawColumns.QTD: [896, None],
        RawColumns.MINUTOS: [15581.444, 16321.30],
    })


def test_standardize_normaliza_strings_e_mp():
    df = standardize_raw(_raw_df())
    assert df[Columns.ORDEM].tolist() == ["300222936", "300223074"]
    assert df[Columns.OFICINA].tolist() == ["OFICINA X", "OFICINA Y"]
    assert df[Columns.MP].tolist() == ["JEANS", "MALHA"]


def test_standardize_tipos_e_nulos():
    df = standardize_raw(_raw_df())
    assert df[Columns.QTD].tolist() == [896, 0]
    assert df[Columns.MINUTOS].tolist() == [15581.44, 16321.30]  # arredondado a 2 casas
    assert pd.isna(df[Columns.RECEBIMENTO].iloc[1])


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
