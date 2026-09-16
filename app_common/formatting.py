"""
app_common/formatting.py — formatação pt-BR, matemática segura e impressão
digital de linha, compartilhadas por todas as áreas do app.

Sem dependência de Streamlit nem de regra de negócio: qualquer camada pode
importar. Ficam aqui (e não em cada ``core/utils.py``) porque um "1.234,5"
formatado de jeito diferente entre Postos, Envios e Recebimento é exatamente o
tipo de divergência que a regra "uma fonte de verdade" existe para impedir.
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


def format_percent_br(value: Optional[float], decimals: int = 1) -> str:
    """Percentual no padrão brasileiro (12,3%). Retorna '—' para nulo/NaN."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    return f"{value:.{decimals}f}%".replace(".", ",")


def format_delta_br(value: Optional[float], decimals: int = 1) -> str:
    """
    Variação percentual com sinal explícito (+3,2% / -1,5%).

    O sinal é explícito porque estes valores aparecem como indicador de
    diferença entre semanas/meses, onde "3,2%" sozinho seria ambíguo.
    """
    if value is None or (isinstance(value, float) and math.isnan(value)) or math.isinf(value):
        return "—"
    sinal = "+" if value > 0 else ""
    return f"{sinal}{value:.{decimals}f}%".replace(".", ",")


# ---------------------------------------------------------------------------
# Matemática segura
# ---------------------------------------------------------------------------
def safe_div(numerator: float, denominator: float) -> float:
    """Divisão segura: NaN quando o denominador é 0/None/NaN."""
    if denominator in (0, None) or (isinstance(denominator, float) and math.isnan(denominator)):
        return float("nan")
    return numerator / denominator


# ---------------------------------------------------------------------------
# Seleção (padrão "selecionar todos" dos filtros)
# ---------------------------------------------------------------------------
def all_or_selected(selected: list, full_options: list) -> list:
    """
    Quando nada está selecionado em um multiselect, a convenção do app é tratar
    como "todos selecionados" (evita dashboards vazios por engano).
    """
    if not selected:
        return list(full_options)
    return selected


# ---------------------------------------------------------------------------
# Impressão digital da linha (chave anti-duplicação)
# ---------------------------------------------------------------------------
def build_row_hash(fields: list, occurrence: int = 0) -> str:
    """
    SHA-1 determinístico do conteúdo de uma linha + índice de ocorrência.

    O ``occurrence`` distingue linhas 100% idênticas dentro do MESMO arquivo
    (ex.: duas movimentações físicas iguais): a 1ª recebe occurrence=0, a 2ª
    occurrence=1, gerando hashes diferentes — assim ambas são preservadas na
    carga inicial. Re-subir o MESMO arquivo gera exatamente o mesmo conjunto de
    hashes, então nada é reinserido (idempotente).
    """
    partes = [str(f).strip() for f in fields] + [f"#{occurrence}"]
    chave = "|".join(partes)
    return hashlib.sha1(chave.encode("utf-8")).hexdigest()
