"""Exceções de domínio da aplicação.

Uma hierarquia própria permite que a camada de apresentação capture
``RadarError`` e trate qualquer falha esperada sem quebrar a aplicação,
enquanto erros inesperados continuam propagando.
"""

from __future__ import annotations


class RadarError(Exception):
    """Erro base da aplicação Radar de Oficinas."""


class PlanilhaNaoEncontrada(RadarError):
    """O arquivo .xlsx de uma fonte configurada não existe no disco."""


class AbaNaoEncontrada(RadarError):
    """A aba (worksheet) esperada não existe na planilha."""


class FonteInvalida(RadarError):
    """A configuração de uma fonte está incompleta ou inconsistente."""


class ColunaInvalida(RadarError):
    """O índice de coluna configurado está fora do intervalo da aba."""
