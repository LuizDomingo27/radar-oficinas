"""Consolidação do endividamento (planilha → payload da tela de Dívidas).

Função pura (sem I/O nem relógio): recebe os registros crus lidos da planilha
(``{"nome", "divida_total", "encargos", "tributos"}``) e devolve um payload
enxuto, pronto para o frontend montar a tabela, os KPIs e o gráfico das maiores
dívidas — sem refazer contas.

Regras de negócio:

- Uma linha da planilha = uma oficina na tela. Cada oficina da planilha vira uma
  linha própria (mesmo quando duas trazem a mesma razão social), para que a
  contagem exibida bata exatamente com as oficinas listadas na planilha.
- Valores ausentes contam como zero (a decomposição tributos/encargos nem sempre
  vem preenchida), mas a dívida total é sempre considerada.
- Nomes que são ruído (cabeçalho/marcador vazado, ou o rótulo "TOTAL" do rodapé)
  são descartados — o rodapé de totais já vem sem nome do leitor, esta é só uma
  segunda barreira.
"""

from __future__ import annotations

from typing import Iterable

from app_oficinas import config
from app_oficinas.errors import FonteInvalida
from app_oficinas.services.normalizacao import limpar


def _v(valor: object) -> float:
    """Valor numérico da célula, tratando ausência (``None``) como zero."""
    return float(valor) if isinstance(valor, (int, float)) else 0.0


def consolidar(registros: Iterable[dict]) -> dict:
    """Monta o payload da tela de dívidas a partir dos registros crus.

    Args:
        registros: iterável de ``{"nome": str, "divida_total": float|None,
            "encargos": float|None, "tributos": float|None}`` (saída de
            ``infra.leitor_fatos.ler_endividamento``).

    Returns:
        Dicionário com:
          - ``moeda``: rótulo da moeda (``"R$"``);
          - ``total_divida`` / ``total_tributos`` / ``total_encargos``: somas
            gerais (o ``total_divida`` confere com o rodapé da planilha);
          - ``oficinas``: ``[{nome, divida_total, tributos, encargos}]`` em
            ordem decrescente de dívida total — uma entrada por linha da planilha;
          - ``linhas``: nº de linhas de oficina lidas (= nº de oficinas).

    Raises:
        FonteInvalida: se nenhuma oficina válida for encontrada — falha alto em
            vez de publicar uma tela vazia sem explicação.
    """
    oficinas = []

    for reg in registros:
        nome = reg.get("nome")
        if not nome:
            continue
        limpo = limpar(nome)
        # Segunda barreira contra ruído (o rodapé sem nome já foi descartado no
        # leitor): descarta cabeçalho vazado e o rótulo "TOTAL".
        if not limpo or limpo in config.RUIDO:
            continue
        oficinas.append({
            "nome": nome,
            "divida_total": round(_v(reg.get("divida_total")), 2),
            "tributos": round(_v(reg.get("tributos")), 2),
            "encargos": round(_v(reg.get("encargos")), 2),
        })

    if not oficinas:
        raise FonteInvalida(
            "Nenhuma oficina com dívida válida foi encontrada na planilha. "
            "Confira a aba e as colunas de endividamento."
        )

    oficinas.sort(key=lambda x: x["divida_total"], reverse=True)

    total_divida = round(sum(o["divida_total"] for o in oficinas), 2)
    total_tributos = round(sum(o["tributos"] for o in oficinas), 2)
    total_encargos = round(sum(o["encargos"] for o in oficinas), 2)

    return {
        "moeda": "R$",
        "total_divida": total_divida,
        "total_tributos": total_tributos,
        "total_encargos": total_encargos,
        "oficinas": oficinas,
        "linhas": len(oficinas),
    }
