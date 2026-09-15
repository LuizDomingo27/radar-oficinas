"""
core/utils.py — utilitários genéricos da área "Envios" (sem Streamlit).

Formatação numérica pt-BR e a função de impressão digital de linha (``row_hash``)
usada como chave anti-duplicação nas gravações.
"""

from __future__ import annotations

import hashlib
import math
from typing import Optional


# ---------------------------------------------------------------------------
# Formatação numérica (padrão pt-BR)
# ---------------------------------------------------------------------------
def format_int_br(value: Optional[float]) -> str:
    """Inteiro no padrão brasileiro (1.234). Retorna '—' para nulo/NaN."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    return f"{int(round(value)):,}".replace(",", ".")


def format_minutos_br(value: Optional[float]) -> str:
    """Minutos com 1 casa decimal no padrão brasileiro (1.234,5)."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    inteiro, _, decimal = f"{value:,.1f}".partition(".")
    return inteiro.replace(",", ".") + "," + decimal


def safe_div(numerator: float, denominator: float) -> float:
    """Divisão segura: NaN quando o denominador é 0/None/NaN."""
    if denominator in (0, None) or (isinstance(denominator, float) and math.isnan(denominator)):
        return float("nan")
    return numerator / denominator


# ---------------------------------------------------------------------------
# Impressão digital da linha (chave anti-duplicação)
# ---------------------------------------------------------------------------
def build_row_hash(fields: list, occurrence: int = 0) -> str:
    """
    SHA-1 determinístico do conteúdo de uma linha de envio + índice de ocorrência.

    O ``occurrence`` distingue linhas 100% idênticas dentro do MESMO arquivo
    (ex.: dois envios físicos iguais): a 1ª recebe occurrence=0, a 2ª occurrence=1,
    gerando hashes diferentes — assim ambas são preservadas na carga inicial.
    Re-subir o MESMO arquivo gera exatamente o mesmo conjunto de hashes, então
    nada é reinserido (idempotente).
    """
    partes = [str(f).strip() for f in fields] + [f"#{occurrence}"]
    chave = "|".join(partes)
    return hashlib.sha1(chave.encode("utf-8")).hexdigest()
