"""
Testes de app_common.movimentacao.area — o contrato que as duas áreas declaram.

Aqui moram as asserções que impedem Envios e Recebimento de divergirem: nomes de
coluna comuns, namespace de widget e coerência de cada descritor com a sua
própria configuração.
"""
from __future__ import annotations

import pytest

from app_common.movimentacao.area import (
    GRANULARITIES,
    GRANULARITY_ORDER,
    AreaMovimentacao,
    ColunasMovimentacao,
    VocabularioMovimentacao,
)
from app_envios.core.config import AREA as AREA_ENVIOS, Columns as ColunasEnvios
from app_recebimento.core.config import AREA as AREA_RECEBIMENTO, Columns as ColunasRecebimento

AREAS = [AREA_ENVIOS, AREA_RECEBIMENTO]
IDS = [a.chave for a in AREAS]


def test_granularidades_e_ordem_batem():
    assert set(GRANULARITY_ORDER) == set(GRANULARITIES)
    assert len(GRANULARITY_ORDER) == len(GRANULARITIES)


@pytest.mark.parametrize("area", AREAS, ids=IDS)
def test_key_namespeia_por_area(area):
    assert area.key("filtro_ano") == f"{area.chave}_filtro_ano"


def test_areas_nao_compartilham_prefixo_de_widget():
    """Prefixos iguais colidiriam no session_state do Streamlit entre as abas."""
    assert AREA_ENVIOS.chave != AREA_RECEBIMENTO.chave


@pytest.mark.parametrize("area", AREAS, ids=IDS)
def test_coluna_de_data_esta_entre_as_persistidas(area):
    assert area.coluna_data in area.colunas_persistidas


@pytest.mark.parametrize("area", AREAS, ids=IDS)
def test_colunas_comuns_estao_persistidas(area):
    """O núcleo compartilhado agrega por estas colunas — todas precisam existir."""
    for coluna in (
        ColunasMovimentacao.ROW_HASH,
        ColunasMovimentacao.ORDEM,
        ColunasMovimentacao.OFICINA,
        ColunasMovimentacao.QTD,
        ColunasMovimentacao.MINUTOS,
        ColunasMovimentacao.MP,
    ):
        assert coluna in area.colunas_persistidas


@pytest.mark.parametrize("colunas", [ColunasEnvios, ColunasRecebimento], ids=IDS)
def test_as_areas_herdam_os_nomes_comuns(colunas):
    """'oficina' precisa significar a mesma coluna nos dois lados."""
    assert issubclass(colunas, ColunasMovimentacao)
    assert colunas.OFICINA == ColunasMovimentacao.OFICINA
    assert colunas.QTD == ColunasMovimentacao.QTD


@pytest.mark.parametrize("area", AREAS, ids=IDS)
def test_vocabulario_preenchido(area):
    voc = area.vocabulario
    for campo in (
        voc.singular, voc.plural, voc.pecas_participio, voc.minutos_participio,
        voc.titulo_registros, voc.verbo_oficina, voc.rotulo_data, voc.exemplo_ordem,
    ):
        assert campo and campo.strip()


@pytest.mark.parametrize("area", AREAS, ids=IDS)
def test_descritor_e_imutavel(area):
    """Congelado de propósito: ninguém reconfigura a área em tempo de render."""
    with pytest.raises(Exception):
        area.tabela = "outra"


def test_tabelas_das_areas_sao_distintas():
    assert AREA_ENVIOS.tabela != AREA_RECEBIMENTO.tabela


def test_descritor_aceita_os_padroes_documentados():
    area = AreaMovimentacao(
        chave="x",
        titulo="T",
        subtitulo="S",
        tabela="Tab",
        coluna_data="data",
        colunas_persistidas=["data"],
        vocabulario=VocabularioMovimentacao(
            singular="item", plural="itens", pecas_participio="Feitas",
            minutos_participio="Feitos", titulo_registros="Itens",
            verbo_oficina="fizeram", rotulo_data="Data", exemplo_ordem="1",
        ),
    )
    assert area.top_n_oficinas == 10
    assert area.page_size_tabela == 15
