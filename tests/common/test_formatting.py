"""Testes de app_common.formatting — formatação pt-BR, divisão segura e row_hash."""
from __future__ import annotations

import math

from app_common.formatting import (
    all_or_selected,
    build_row_hash,
    format_delta_br,
    format_int_br,
    format_minutos_br,
    format_percent_br,
    safe_div,
)


def test_format_int_br():
    assert format_int_br(1234) == "1.234"
    assert format_int_br(0) == "0"
    assert format_int_br(1234.6) == "1.235"  # arredonda


def test_format_int_br_nulo_e_nan():
    assert format_int_br(None) == "—"
    assert format_int_br(float("nan")) == "—"


def test_format_minutos_br():
    assert format_minutos_br(1234.5) == "1.234,5"
    assert format_minutos_br(0.0) == "0,0"
    assert format_minutos_br(None) == "—"
    assert format_minutos_br(float("nan")) == "—"


def test_format_percent_br():
    assert format_percent_br(12.34) == "12,3%"
    assert format_percent_br(12.34, decimals=2) == "12,34%"
    assert format_percent_br(None) == "—"


def test_format_delta_br_sinal_explicito():
    assert format_delta_br(3.2) == "+3,2%"
    assert format_delta_br(-1.5) == "-1,5%"
    assert format_delta_br(0.0) == "0,0%"


def test_format_delta_br_sem_base():
    assert format_delta_br(None) == "—"
    assert format_delta_br(float("nan")) == "—"
    assert format_delta_br(float("inf")) == "—"


def test_safe_div():
    assert safe_div(10, 2) == 5
    assert math.isnan(safe_div(10, 0))
    assert math.isnan(safe_div(10, None))
    assert math.isnan(safe_div(10, float("nan")))


def test_all_or_selected():
    assert all_or_selected([], ["A", "B"]) == ["A", "B"]
    assert all_or_selected(["A"], ["A", "B"]) == ["A"]


def test_all_or_selected_devolve_copia():
    """A lista devolvida no caso 'todos' não pode ser a mesma instância das opções."""
    opcoes = ["A", "B"]
    resultado = all_or_selected([], opcoes)
    resultado.append("C")
    assert opcoes == ["A", "B"]


def test_build_row_hash_deterministico():
    assert build_row_hash(["A", 1, "X"]) == build_row_hash(["A", 1, "X"])


def test_build_row_hash_ignora_espacos_nas_bordas():
    assert build_row_hash([" A ", 1]) == build_row_hash(["A", 1])


def test_build_row_hash_ocorrencia_diferencia_linhas_identicas():
    """Duas linhas 100% iguais no mesmo arquivo precisam sobreviver às duas."""
    assert build_row_hash(["A", 1], occurrence=0) != build_row_hash(["A", 1], occurrence=1)


def test_build_row_hash_muda_com_o_conteudo():
    assert build_row_hash(["A", 1]) != build_row_hash(["A", 2])
