"""Testes de app_envios.core.utils — hash de linha e formatação pt-BR."""
from __future__ import annotations

from app_envios.core.utils import build_row_hash, format_int_br, format_minutos_br, safe_div


def test_row_hash_deterministico():
    campos = ["JEANS", "300222101", "OFICINA X", 238, 4360.16, "2026-01-02", "JEANS", "NAO_PDV", "R.A", "Enviado"]
    assert build_row_hash(campos, 0) == build_row_hash(campos, 0)


def test_row_hash_muda_com_ocorrencia():
    campos = ["JEANS", "300222101", "OFICINA X", 238, 4360.16, "2026-01-02", "JEANS", "NAO_PDV", "R.A", "Enviado"]
    assert build_row_hash(campos, 0) != build_row_hash(campos, 1)


def test_row_hash_muda_com_conteudo():
    a = build_row_hash(["300222101", "OFICINA X", 238], 0)
    b = build_row_hash(["300222101", "OFICINA Y", 238], 0)
    assert a != b


def test_format_int_br():
    assert format_int_br(1234567) == "1.234.567"
    assert format_int_br(None) == "—"
    assert format_int_br(float("nan")) == "—"


def test_format_minutos_br():
    assert format_minutos_br(1234.5) == "1.234,5"
    assert format_minutos_br(None) == "—"


def test_safe_div():
    assert safe_div(10, 2) == 5
    assert safe_div(10, 0) != safe_div(10, 0)  # NaN
