"""Normalização de período para os filtros mês/semana/ano.

Funções puras (sem I/O) que traduzem datas e rótulos de ciclo das planilhas em
um ``Periodo`` estável. A semana usa o padrão ISO 8601 (``date.isocalendar``),
comparável entre fontes; o rótulo de semana original da planilha é preservado à
parte, no próprio ``Periodo.rotulo_semana``.
"""

from __future__ import annotations

import re
from datetime import date, datetime

from app_oficinas.domain.models import Periodo

_ANO_NO_TEXTO = re.compile(r"(19|20)\d{2}")


def para_data(valor: object) -> date | None:
    """Converte um valor de célula em ``date``; ``None`` se não for data.

    Aceita ``datetime``/``date`` (como o openpyxl entrega com ``data_only``) e
    strings ISO ``YYYY-MM-DD`` (com ou sem hora). Qualquer outra coisa vira
    ``None`` — cabe ao chamador decidir se descarta a linha.
    """
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str):
        texto = valor.strip()[:10]
        try:
            return date.fromisoformat(texto)
        except ValueError:
            return None
    return None


def periodo_de_data(
    valor: object, rotulo_semana: object = None
) -> Periodo | None:
    """Deriva ``ano/mes/semana_iso`` de uma data; ``None`` se não houver data."""
    d = para_data(valor)
    if d is None:
        return None
    _, semana_iso, _ = d.isocalendar()
    return Periodo(
        ano=d.year,
        mes=d.month,
        semana_iso=semana_iso,
        rotulo_semana=_texto_ou_none(rotulo_semana),
    )


def ano_do_ciclo(ciclo: object) -> int | None:
    """Extrai o ano de referência de um ciclo de treinamento.

    Para intervalos como ``"2021/2022"`` usa o último ano (o de conclusão);
    para ``"2025"`` usa o próprio ano. ``None`` se nenhum ano for reconhecível.
    """
    if ciclo is None:
        return None
    anos = [m.group(0) for m in _ANO_NO_TEXTO.finditer(str(ciclo))]
    return int(anos[-1]) if anos else None


def periodo_de_ciclo(ciclo: object, rotulo: object = None) -> Periodo | None:
    """``Periodo`` só com o ano do ciclo (sem mês/semana)."""
    ano = ano_do_ciclo(ciclo)
    if ano is None:
        return None
    return Periodo(ano=ano, rotulo_semana=_texto_ou_none(rotulo))


def _texto_ou_none(valor: object) -> str | None:
    """Normaliza um rótulo de semana para texto limpo, ou ``None`` se vazio."""
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None
