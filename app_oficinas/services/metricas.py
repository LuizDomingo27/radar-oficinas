"""Camada de métricas (Fase 3).

Transforma os fatos crus (Fase 2) nas três métricas por oficina/período, sem
inventar fórmula: usa exatamente o que as planilhas já calculam.

- **Produtividade** = Σpeças ÷ Σminutos (peças por minuto), com os totais.
- **Absenteísmo** = 1 − Σtrabalhados ÷ Σefetivos (razão agregada do período);
  rotatividade (Σcontratação/Σdemissão) vem de brinde.
- **Eficiência** = entrega ÷ capacidade, a regra das planilhas de estoque:
  JEANS divide a entrega semanal pela capacidade de peças que a planilha já
  computa, nas duas bases (100% e 70%); NÃO-JEANS já traz o efic% pronto por
  semana em duas versões distintas — por peças e por minutos.

Funções puras sobre listas de fatos; a granularidade (``"mes"`` ou ``"semana"``)
alimenta os filtros mês/semana/ano. Ano = soma/roll-up das linhas mensais.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from app_oficinas.domain.models import (
    FatoAbsenteismo,
    FatoEficiencia,
    FatoProducao,
)

# Granularidades temporais suportadas.
POR_MES = "mes"
POR_SEMANA = "semana"


def _chave_periodo(periodo, por: str) -> tuple | None:
    """Chave de agregação (ano[, mês|semana]); ``None`` se o dado não a tem."""
    if por == POR_MES:
        return (periodo.ano, periodo.mes) if periodo.mes else None
    if por == POR_SEMANA:
        return (periodo.ano, periodo.semana_iso) if periodo.semana_iso else None
    raise ValueError(f"granularidade inválida: {por!r}")


def _rotulo(por: str, chave: tuple) -> dict:
    """Campos de período serializáveis para uma chave de agregação."""
    ano, parte = chave
    return {"ano": ano, "mes": parte} if por == POR_MES else {"ano": ano, "semana": parte}


def _divisao_segura(numerador: float, denominador: float) -> float | None:
    """Divisão que devolve ``None`` (não zero) quando não há denominador."""
    return numerador / denominador if denominador else None


# --------------------------------------------------------------------------- #
# Produtividade                                                               #
# --------------------------------------------------------------------------- #

def serie_produtividade(
    fatos: Iterable[FatoProducao], por: str = POR_MES
) -> list[dict]:
    """Peças, minutos e peças/minuto por oficina e período."""
    acum: dict[tuple, dict] = defaultdict(
        lambda: {"pecas": 0.0, "minutos": 0.0}
    )
    for f in fatos:
        if f.oficina_id is None:
            continue
        chave = _chave_periodo(f.periodo, por)
        if chave is None:
            continue
        alvo = acum[(f.oficina_id, chave)]
        alvo["pecas"] += f.real_cortado
        alvo["minutos"] += f.minutos

    linhas = []
    for (oficina_id, chave), v in acum.items():
        linhas.append({
            "oficina_id": oficina_id, **_rotulo(por, chave),
            "pecas": round(v["pecas"], 2),
            "minutos": round(v["minutos"], 2),
            "pecas_por_minuto": _arredonda(_divisao_segura(v["pecas"], v["minutos"]), 4),
        })
    return _ordenar(linhas, por)


# --------------------------------------------------------------------------- #
# Absenteísmo                                                                 #
# --------------------------------------------------------------------------- #

def serie_absenteismo(
    fatos: Iterable[FatoAbsenteismo], por: str = POR_MES
) -> list[dict]:
    """Absenteísmo (1 − trab/efet) e rotatividade por oficina e período."""
    acum: dict[tuple, dict] = defaultdict(
        lambda: {"efet": 0.0, "trab": 0.0, "contr": 0.0, "demi": 0.0}
    )
    for f in fatos:
        if f.oficina_id is None:
            continue
        chave = _chave_periodo(f.periodo, por)
        if chave is None:
            continue
        alvo = acum[(f.oficina_id, chave)]
        alvo["efet"] += f.qtd_efetivos
        alvo["trab"] += f.qtd_trabalhados
        alvo["contr"] += f.contratacao
        alvo["demi"] += f.demissao

    linhas = []
    for (oficina_id, chave), v in acum.items():
        presenca = _divisao_segura(v["trab"], v["efet"])
        linhas.append({
            "oficina_id": oficina_id, **_rotulo(por, chave),
            "qtd_efetivos": round(v["efet"], 2),
            "qtd_trabalhados": round(v["trab"], 2),
            "absenteismo_pct": _arredonda(None if presenca is None else 1 - presenca, 4),
            "contratacao": round(v["contr"], 2),
            "demissao": round(v["demi"], 2),
        })
    return _ordenar(linhas, por)


# --------------------------------------------------------------------------- #
# Eficiência                                                                  #
# --------------------------------------------------------------------------- #

def serie_eficiencia(fatos: Iterable[FatoEficiencia]) -> list[dict]:
    """Eficiência oficial por oficina — a % que a própria planilha calcula.

    Um valor por oficina (``tipo_valor == "efic_oficial"``): Méd. das últimas 4
    semanas de entrega ÷ Cap Peças 100%. Não é série semanal — é o indicador
    atual que a equipe acompanha. Se a mesma oficina aparecer em mais de uma
    linha (raro), fica a média.
    """
    agreg: dict[str, dict] = defaultdict(lambda: {"soma": 0.0, "n": 0, "mp": None, "ano": None})
    for f in fatos:
        if f.oficina_id is None or f.tipo_valor != "efic_oficial":
            continue
        a = agreg[f.oficina_id]
        a["soma"] += f.valor
        a["n"] += 1
        a["mp"] = a["mp"] or f.mp
        a["ano"] = f.periodo.ano

    linhas = [
        {"oficina_id": oid, "ano": a["ano"], "mp": a["mp"],
         "base": "oficial", "eficiencia_pct": round(a["soma"] / a["n"], 4)}
        for oid, a in agreg.items()
    ]
    linhas.sort(key=lambda r: r["oficina_id"])
    return linhas


# --------------------------------------------------------------------------- #
# Auxiliares                                                                  #
# --------------------------------------------------------------------------- #

def _arredonda(valor: float | None, casas: int) -> float | None:
    return None if valor is None else round(valor, casas)


def _ordenar(linhas: list[dict], por: str) -> list[dict]:
    parte = "mes" if por == POR_MES else "semana"
    return sorted(linhas, key=lambda r: (r["oficina_id"], r["ano"], r[parte]))
