"""Testes de app_recebimento.services.data_cleaning."""
from __future__ import annotations

import pandas as pd

from app_recebimento.core.config import Columns, RawColumns
from app_recebimento.services.data_cleaning import standardize_raw


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
