"""
Testes de app_common.movimentacao.data_loader.

Cobre o contrato de leitura das duas áreas com o client fake em memória — os
testes NUNCA tocam o Neon real. Inclui o caminho torto: tabela vazia, coluna
faltando, tipo inválido e falha de conexão.
"""
from __future__ import annotations

import pandas as pd
import pytest

from app_common.movimentacao.area import ColunasMovimentacao as C
from app_common.movimentacao.data_loader import (
    DataLoadError,
    EmptyDataError,
    empty_dataframe,
    load_clean_dataframe,
)
from app_envios.core.config import AREA as AREA_ENVIOS
from app_recebimento.core.config import AREA as AREA_RECEBIMENTO
from tests.postos.fakes import FakeNeonClient

AREAS = [AREA_ENVIOS, AREA_RECEBIMENTO]
IDS = [a.chave for a in AREAS]


def _linha(area, **overrides) -> dict:
    """Uma linha no formato exato em que o banco devolve (todas as persistidas)."""
    valores = {
        C.ROW_HASH: "abc123",
        C.ORDEM: "300222101",
        C.OFICINA: "OFICINA X",
        C.QTD: 238,
        C.MINUTOS: 4360.16,
        C.MP: "JEANS",
        area.coluna_data: "2026-01-02",
        # Só existem em Envios; ignorados quando a área não as persiste.
        "origem": "JEANS",
        "pdv": "NAO_PDV",
        "frete": "R.A",
        "situacao": "Enviado",
    }
    valores.update(overrides)
    return {c: valores[c] for c in area.colunas_persistidas}


class _ClientQueQuebra:
    """Client cujo acesso falha — simula rede/credencial ruim na leitura."""

    def table(self, name):
        raise RuntimeError("conexão recusada")


# ---------------------------------------------------------------------------
# empty_dataframe
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("area", AREAS, ids=IDS)
def test_empty_dataframe_tem_contrato_completo(area):
    df = empty_dataframe(area)
    assert df.empty
    for coluna in area.colunas_persistidas:
        assert coluna in df.columns
    for coluna in (C.ANO, C.ANO_MES, C.MES_LABEL, C.SEMANA, C.DIA, C.DIA_LABEL):
        assert coluna in df.columns


@pytest.mark.parametrize("area", AREAS, ids=IDS)
def test_empty_dataframe_tipos_numericos(area):
    df = empty_dataframe(area)
    assert df[C.QTD].dtype == "int64"
    assert df[C.MINUTOS].dtype == "float64"


# ---------------------------------------------------------------------------
# load_clean_dataframe — caminho feliz
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("area", AREAS, ids=IDS)
def test_load_converte_tipos_e_deriva_periodos(area):
    client = FakeNeonClient({area.tabela: [_linha(area)]})
    df = load_clean_dataframe(area, client=client)

    assert len(df) == 1
    assert df[C.QTD].dtype == "int64"
    assert df[C.MINUTOS].iloc[0] == 4360.16
    assert pd.api.types.is_datetime64_any_dtype(df[area.coluna_data])
    assert df[C.MES_LABEL].iloc[0] == "Jan/2026"


@pytest.mark.parametrize("area", AREAS, ids=IDS)
def test_load_descarta_colunas_tecnicas_do_banco(area):
    linha = {**_linha(area), "id": 1, "created_at": "2026-01-02T10:00:00"}
    df = load_clean_dataframe(area, client=FakeNeonClient({area.tabela: [linha]}))
    assert "id" not in df.columns
    assert "created_at" not in df.columns


@pytest.mark.parametrize("area", AREAS, ids=IDS)
def test_load_qtd_e_minutos_invalidos_viram_zero(area):
    linha = _linha(area, **{C.QTD: None, C.MINUTOS: "n/d"})
    df = load_clean_dataframe(area, client=FakeNeonClient({area.tabela: [linha]}))
    assert int(df[C.QTD].iloc[0]) == 0
    assert float(df[C.MINUTOS].iloc[0]) == 0.0


@pytest.mark.parametrize("area", AREAS, ids=IDS)
def test_load_data_invalida_vira_nulo_sem_quebrar(area):
    linha = _linha(area, **{area.coluna_data: "data-invalida"})
    df = load_clean_dataframe(area, client=FakeNeonClient({area.tabela: [linha]}))
    assert pd.isna(df[area.coluna_data].iloc[0])
    assert df[C.MES_LABEL].iloc[0] == "Sem data"


# ---------------------------------------------------------------------------
# load_clean_dataframe — caminho torto
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("area", AREAS, ids=IDS)
def test_tabela_vazia_e_caso_previsto_com_mensagem_de_acao(area):
    client = FakeNeonClient({area.tabela: []})
    with pytest.raises(EmptyDataError) as ctx:
        load_clean_dataframe(area, client=client)
    # A mensagem precisa dizer o que o usuário faz agora.
    assert "Lançamento de Dados" in str(ctx.value)
    assert area.tabela in str(ctx.value)


@pytest.mark.parametrize("area", AREAS, ids=IDS)
def test_coluna_obrigatoria_faltando(area):
    linha = _linha(area)
    del linha[C.OFICINA]
    client = FakeNeonClient({area.tabela: [linha]})
    with pytest.raises(DataLoadError) as ctx:
        load_clean_dataframe(area, client=client)
    assert C.OFICINA in str(ctx.value)


@pytest.mark.parametrize("area", AREAS, ids=IDS)
def test_falha_de_leitura_vira_erro_de_dominio(area):
    with pytest.raises(DataLoadError) as ctx:
        load_clean_dataframe(area, client=_ClientQueQuebra())
    assert "banco" in str(ctx.value)
    # Nenhuma menção ao banco antigo pode sobrar na mensagem de tela.
    assert "supabase" not in str(ctx.value).lower()


def test_empty_data_error_e_um_data_load_error():
    """O dashboard captura EmptyDataError antes; a hierarquia precisa valer."""
    assert issubclass(EmptyDataError, DataLoadError)
