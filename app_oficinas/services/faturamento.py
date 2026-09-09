"""Consolidação do faturamento (produção → payload da tela de Faturamento).

Funções puras (sem I/O nem relógio): recebem os títulos crus lidos da planilha
(``{"nome", "data", "valor"}``) e devolvem um payload enxuto pronto para o
frontend filtrar por ano/mês sem refazer contas pesadas.

Definição de **semana**: semana-do-mês por calendário — dias 1–7 = semana 1,
8–14 = semana 2, 15–21 = 3, 22–28 = 4, 29–fim = 5. É a partição que casa com o
pedido "semanas de acordo com o mês" (cada título cai em exatamente uma semana
de um mês, sem semana atravessando a virada), e torna a "maior semana" sempre
comparável entre meses e entre todo o período.

Tudo é feito em uma única passagem pelos títulos (o arquivo tem dezenas de
milhares de linhas), agregando em dicionários e materializando as listas
ordenadas só no fim.
"""

from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import date
from typing import Iterable

from app_oficinas.errors import FonteInvalida
from app_oficinas.services.periodos import para_data


def _semana_do_mes(dia: int) -> int:
    """Semana-do-mês (1..5) de um dia do mês pela regra de blocos de 7 dias."""
    return (dia - 1) // 7 + 1


def _intervalo_semana(ano: int, mes: int, semana: int) -> tuple[str, str]:
    """Datas (ISO) de início e fim da semana-do-mês, com o fim preso ao mês."""
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    ini_dia = (semana - 1) * 7 + 1
    fim_dia = min(semana * 7, ultimo_dia)
    return date(ano, mes, ini_dia).isoformat(), date(ano, mes, fim_dia).isoformat()


def consolidar(registros: Iterable[dict]) -> dict:
    """Agrega os títulos de faturamento no payload da tela.

    Args:
        registros: iterável de ``{"nome": str, "data": date|datetime|str,
            "valor": float|None}`` (saída de ``infra.leitor_fatos.ler_faturamento``).

    Returns:
        Dicionário com:
          - ``moeda``: rótulo da moeda (``"R$"``);
          - ``anos``: anos com dado, crescente;
          - ``meses``: ``[{ano, mes, total}]`` por (ano, mês), cronológico;
          - ``semanas``: ``[{ano, mes, semana, ini, fim, total}]``, cronológico;
          - ``oficinas``: ``{"todos": [...], "<ano>": [...]}`` cada lista com
            ``{nome, total}`` em ordem decrescente de total;
          - ``oficinas_mes``: ``{"<ano>-<mm>": [...]}`` para atualizar os
            rankings quando o usuário filtra um mês;
          - ``linhas``: nº de títulos válidos considerados.

    Raises:
        FonteInvalida: se nenhum título válido (com data e valor) for encontrado
            — falha alto em vez de publicar uma tela vazia sem explicação.
    """
    por_mes: dict[tuple[int, int], float] = defaultdict(float)
    por_semana: dict[tuple[int, int, int], float] = defaultdict(float)
    por_oficina_total: dict[str, float] = defaultdict(float)
    por_oficina_ano: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    por_oficina_mes: dict[tuple[int, int], dict[str, float]] = defaultdict(
        lambda: defaultdict(float)
    )
    validos = 0

    for reg in registros:
        nome = reg.get("nome")
        valor = reg.get("valor")
        d = para_data(reg.get("data"))
        # Ignora títulos sem oficina, sem data reconhecível ou sem valor numérico.
        if not nome or d is None or valor is None:
            continue
        validos += 1
        ano, mes = d.year, d.month
        semana = _semana_do_mes(d.day)
        por_mes[(ano, mes)] += valor
        por_semana[(ano, mes, semana)] += valor
        por_oficina_total[nome] += valor
        por_oficina_ano[ano][nome] += valor
        por_oficina_mes[(ano, mes)][nome] += valor

    if validos == 0:
        raise FonteInvalida(
            "Nenhum título de faturamento válido (com oficina, data e valor) foi "
            "encontrado na planilha. Confira a aba e as colunas de "
            f"{__name__.split('.')[-1]}."
        )

    anos = sorted({ano for ano, _ in por_mes})

    meses = [
        {"ano": ano, "mes": mes, "total": round(por_mes[(ano, mes)], 2)}
        for ano, mes in sorted(por_mes)
    ]

    semanas = []
    for ano, mes, semana in sorted(por_semana):
        ini, fim = _intervalo_semana(ano, mes, semana)
        semanas.append({
            "ano": ano, "mes": mes, "semana": semana,
            "ini": ini, "fim": fim,
            "total": round(por_semana[(ano, mes, semana)], 2),
        })

    def _ordenar(mapa: dict[str, float]) -> list[dict]:
        itens = [{"nome": n, "total": round(v, 2)} for n, v in mapa.items()]
        itens.sort(key=lambda x: x["total"], reverse=True)
        return itens

    oficinas: dict[str, list[dict]] = {"todos": _ordenar(por_oficina_total)}
    for ano in anos:
        oficinas[str(ano)] = _ordenar(por_oficina_ano[ano])

    oficinas_mes = {
        f"{ano}-{mes:02d}": _ordenar(por_oficina_mes[(ano, mes)])
        for ano, mes in sorted(por_oficina_mes)
    }

    return {
        "moeda": "R$",
        "anos": anos,
        "meses": meses,
        "semanas": semanas,
        "oficinas": oficinas,
        "oficinas_mes": oficinas_mes,
        "linhas": validos,
    }
