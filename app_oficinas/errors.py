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


class FonteIndisponivel(RadarError):
    """Uma fonte externa (ex.: a tabela de postos no Supabase) não pôde ser lida.

    Diferente de ``FonteInvalida`` (configuração local errada), sinaliza falha de
    acesso ao dado em si: credenciais ausentes, rede indisponível ou resposta
    inesperada do serviço. É ``RadarError`` para o pipeline reportar a causa e o
    app nunca quebrar.
    """


class ColunaInvalida(RadarError):
    """O índice de coluna configurado está fora do intervalo da aba."""
