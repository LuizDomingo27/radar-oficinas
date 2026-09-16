"""
Testes de app_common.errors — a garantia de que nenhuma tela mostra traceback.

Não sobem o Streamlit: substituem `st` por um duplo que registra as chamadas,
o que é suficiente para verificar o contrato (mensagem amigável, detalhe
recolhido, log no servidor e, quando fatal, interrupção da página).
"""
from __future__ import annotations

import logging
from contextlib import contextmanager

import pytest

import app_common.errors as mod
from app_common.errors import build_error_handlers, friendly_message


class _StParado(Exception):
    """Sinaliza que `st.stop()` foi chamado (o Streamlit real levanta algo assim)."""


class _FakeSt:
    def __init__(self):
        self.erros: list[str] = []
        self.codigos: list[str] = []
        self.parou = False

    def error(self, mensagem):
        self.erros.append(mensagem)

    def code(self, texto, language=None):
        self.codigos.append(texto)

    @contextmanager
    def expander(self, _titulo):
        yield

    def stop(self):
        self.parou = True
        raise _StParado()


@pytest.fixture
def st_fake(monkeypatch):
    fake = _FakeSt()
    monkeypatch.setattr(mod, "st", fake)
    return fake


def test_friendly_message_diz_o_que_fazer_agora():
    msg = friendly_message("carregar os dados")
    assert "carregar os dados" in msg
    assert "recarregar a página" in msg
    assert "suporte" in msg


def test_error_boundary_converte_excecao_em_mensagem(st_fake):
    error_boundary, _ = build_error_handlers("teste_boundary")
    with error_boundary("carregar os dados"):
        raise ValueError("detalhe cru")

    assert len(st_fake.erros) == 1
    assert "carregar os dados" in st_fake.erros[0]
    # O traceback não vaza para a mensagem principal.
    assert "Traceback" not in st_fake.erros[0]
    # O detalhe técnico fica no bloco recolhido.
    assert st_fake.codigos == ["ValueError: detalhe cru"]


def test_error_boundary_nao_interfere_no_caminho_feliz(st_fake):
    error_boundary, _ = build_error_handlers("teste_ok")
    with error_boundary("somar"):
        resultado = 1 + 1
    assert resultado == 2
    assert st_fake.erros == []


def test_error_boundary_fatal_interrompe_a_pagina(st_fake):
    error_boundary, _ = build_error_handlers("teste_fatal")
    with pytest.raises(_StParado):
        with error_boundary("carregar a fonte", fatal=True):
            raise RuntimeError("sem conexão")
    assert st_fake.parou is True


def test_guard_protege_a_funcao_inteira(st_fake):
    _, guard = build_error_handlers("teste_guard")

    @guard("renderizar os KPIs")
    def quebra():
        raise KeyError("coluna")

    assert quebra() is None
    assert "renderizar os KPIs" in st_fake.erros[0]


def test_guard_devolve_o_valor_no_caminho_feliz(st_fake):
    _, guard = build_error_handlers("teste_guard_ok")

    @guard("calcular")
    def soma(a, b):
        return a + b

    assert soma(2, 3) == 5


def test_guard_preserva_nome_e_docstring():
    _, guard = build_error_handlers("teste_meta")

    @guard("contexto")
    def minha_funcao():
        """Doc original."""

    assert minha_funcao.__name__ == "minha_funcao"
    assert minha_funcao.__doc__ == "Doc original."


def test_erro_vai_para_o_log_da_area(st_fake, caplog):
    error_boundary, _ = build_error_handlers("area_do_log")
    with caplog.at_level(logging.ERROR, logger="area_do_log"):
        with error_boundary("gravar o registro"):
            raise ValueError("falhou")
    assert any("gravar o registro" in r.message for r in caplog.records)


def test_cada_area_tem_seu_proprio_logger():
    """Logs separados por área é o motivo de a fábrica receber o nome."""
    build_error_handlers("area_a")
    build_error_handlers("area_b")
    assert logging.getLogger("area_a") is not logging.getLogger("area_b")


def test_handlers_nao_sao_duplicados_em_chamadas_repetidas():
    """Duas chamadas para a mesma área não podem dobrar as linhas de log."""
    build_error_handlers("area_repetida")
    build_error_handlers("area_repetida")
    assert len(logging.getLogger("area_repetida").handlers) == 1
