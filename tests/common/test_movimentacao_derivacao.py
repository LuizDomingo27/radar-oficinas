"""Testes de app_common.movimentacao.derivacao — colunas de período."""
from __future__ import annotations

import pandas as pd
import pytest

from app_common.movimentacao.area import ColunasMovimentacao as C
from app_common.movimentacao.derivacao import SEM_DATA_LABEL, add_derived

_COLUNA = "envio"


def _df(datas: list) -> pd.DataFrame:
    return pd.DataFrame({_COLUNA: pd.to_datetime(datas, errors="coerce")})


def test_deriva_ano_mes_semana_e_dia():
    df = add_derived(_df(["2026-01-02"]), coluna_data=_COLUNA)
    assert int(df[C.ANO].iloc[0]) == 2026
    assert int(df[C.SEMANA].iloc[0]) == 1
    assert df[C.ANO_MES].iloc[0] == "2026-01"
    assert df[C.MES_LABEL].iloc[0] == "Jan/2026"
    assert df[C.DIA_LABEL].iloc[0] == "02/01/2026"


def test_linha_sem_data_e_mantida_e_rotulada():
    """Linha sem data não pode sumir do relatório — ela vira 'Sem data'."""
    df = add_derived(_df(["2026-01-02", None]), coluna_data=_COLUNA)
    assert len(df) == 2
    assert df[C.MES_LABEL].iloc[1] == SEM_DATA_LABEL
    assert df[C.DIA_LABEL].iloc[1] == SEM_DATA_LABEL
    assert pd.isna(df[C.ANO].iloc[1])
    assert df[C.ANO_MES].iloc[1] is None


def test_data_invalida_vira_sem_data():
    df = add_derived(pd.DataFrame({_COLUNA: ["nao-e-data"]}), coluna_data=_COLUNA)
    assert df[C.MES_LABEL].iloc[0] == SEM_DATA_LABEL


def test_dataframe_vazio_ganha_as_colunas_derivadas():
    df = add_derived(_df([]), coluna_data=_COLUNA)
    assert df.empty
    for coluna in (C.ANO, C.ANO_MES, C.MES_LABEL, C.SEMANA, C.DIA, C.DIA_LABEL):
        assert coluna in df.columns


def test_nao_muta_o_dataframe_original():
    original = _df(["2026-01-02"])
    add_derived(original, coluna_data=_COLUNA)
    assert C.ANO not in original.columns


@pytest.mark.parametrize(
    "data,mes_label",
    [("2026-03-15", "Mar/2026"), ("2026-12-31", "Dez/2026"), ("2025-07-01", "Jul/2025")],
)
def test_rotulo_do_mes_em_portugues(data, mes_label):
    df = add_derived(_df([data]), coluna_data=_COLUNA)
    assert df[C.MES_LABEL].iloc[0] == mes_label
