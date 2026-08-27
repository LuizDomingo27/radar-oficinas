"""Regras de negócio da Qualidade (puras, sem I/O).

Reproduz os critérios da aba GRÁFICOS do "Indicador geral":

* Nota de Qualidade (índice de demérito ponderado, maior = pior):
      Nota = 0,6*%Reprovado + 0,3*%Concessão + 0,1*(Σ2QA / ΣProd)
* Índice de 2ª Qualidade por oficina: Σ2QA / ΣProd.
* Principais Causas - 2ª Qualidade: Σ QNTD por defeito, inspeção de 2ª
  qualidade, setor de costura.

As funções de agregação devolvem "crus" por (oficina/defeito × ano × mês) para
que o frontend aplique os filtros de período (mês/ano). As funções de ranking
são a referência testada do cálculo — o frontend replica a mesma fórmula.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from app_oficinas import config


def agregar_oficinas(inspecoes: Iterable[dict]) -> list[dict]:
    """Agrega inspeções por (oficina, ano, mês) com contagens e somas."""
    acc: dict[tuple, dict] = defaultdict(lambda: {
        "n_aprovado": 0, "n_reprovado": 0, "n_concessao": 0,
        "soma_2qa": 0.0, "soma_prod": 0.0,
    })
    for ins in inspecoes:
        reg = acc[(ins["oficina"], ins["ano"], ins["mes"])]
        status = _sem_acento(ins["status"])
        if status == config.STATUS_APROVADO:
            reg["n_aprovado"] += 1
        elif status == config.STATUS_REPROVADO:
            reg["n_reprovado"] += 1
        elif status == config.STATUS_CONCESSAO:
            reg["n_concessao"] += 1
        reg["soma_2qa"] += ins["dois_qa"]
        reg["soma_prod"] += ins["prod"]
    return [
        {"oficina": of, "ano": ano, "mes": mes, **reg}
        for (of, ano, mes), reg in acc.items()
    ]


def agregar_causas(defeitos: Iterable[dict]) -> list[dict]:
    """Agrega defeitos por (defeito, tipo, setor, ano, mês) somando QNTD."""
    acc: dict[tuple, float] = defaultdict(float)
    for d in defeitos:
        acc[(d["defeito"], d["tipo"], d["setor"], d["ano"], d["mes"])] += d["qntd"]
    return [
        {"defeito": de, "tipo": ti, "setor": se, "ano": an, "mes": me, "qntd": q}
        for (de, ti, se, an, me), q in acc.items()
    ]


def nota_qualidade(reg: dict) -> float | None:
    """Índice de demérito ponderado de uma oficina (soma de linhas agregadas)."""
    total = reg["n_aprovado"] + reg["n_reprovado"] + reg["n_concessao"]
    if total <= 0:
        return None
    pct_rep = reg["n_reprovado"] / total
    pct_conc = reg["n_concessao"] / total
    idx_2qa = reg["soma_2qa"] / reg["soma_prod"] if reg["soma_prod"] > 0 else 0.0
    return (config.PESO_REPROVADO * pct_rep
            + config.PESO_CONCESSAO * pct_conc
            + config.PESO_2QA * idx_2qa)


def indice_2qa(reg: dict) -> float:
    """Índice de 2ª qualidade: Σ2QA / ΣProd."""
    return reg["soma_2qa"] / reg["soma_prod"] if reg["soma_prod"] > 0 else 0.0


def _somar_por_oficina(agregados: Iterable[dict]) -> dict[str, dict]:
    somas: dict[str, dict] = defaultdict(lambda: {
        "n_aprovado": 0, "n_reprovado": 0, "n_concessao": 0,
        "soma_2qa": 0.0, "soma_prod": 0.0,
    })
    for reg in agregados:
        s = somas[reg["oficina"]]
        for chave in s:
            s[chave] += reg[chave]
    return somas


def ranking_nota(agregados: Iterable[dict], min_inspecoes: int = 10,
                 top: int = 20) -> list[dict]:
    """Top oficinas por Nota de Qualidade (maior = pior)."""
    linhas = []
    for oficina, s in _somar_por_oficina(agregados).items():
        total = s["n_aprovado"] + s["n_reprovado"] + s["n_concessao"]
        if total < min_inspecoes:
            continue
        nota = nota_qualidade(s)
        if nota is None:
            continue
        linhas.append({"oficina": oficina, "nota": nota,
                       "inspecoes": total, "idx_2qa": indice_2qa(s)})
    linhas.sort(key=lambda x: x["nota"], reverse=True)
    return linhas[:top]


def ranking_2qa(agregados: Iterable[dict], min_inspecoes: int = 10,
                top: int = 20) -> list[dict]:
    """Top oficinas por índice de 2ª qualidade (maior = pior)."""
    linhas = []
    for oficina, s in _somar_por_oficina(agregados).items():
        total = s["n_aprovado"] + s["n_reprovado"] + s["n_concessao"]
        if total < min_inspecoes:
            continue
        linhas.append({"oficina": oficina, "idx_2qa": indice_2qa(s),
                       "inspecoes": total})
    linhas.sort(key=lambda x: x["idx_2qa"], reverse=True)
    return linhas[:top]


def principais_causas(agregados: Iterable[dict],
                      setor: str = config.CAUSAS_SETOR_PADRAO,
                      top: int = 10) -> list[dict]:
    """Top defeitos das inspeções de 2ª qualidade (por setor), somando QNTD."""
    somas: dict[str, float] = defaultdict(float)
    for reg in agregados:
        if config.CAUSAS_TIPO_CONTEM not in reg["tipo"]:
            continue
        if setor and reg["setor"] != setor:
            continue
        somas[reg["defeito"]] += reg["qntd"]
    linhas = [{"defeito": d, "qntd": q} for d, q in somas.items()]
    linhas.sort(key=lambda x: x["qntd"], reverse=True)
    return linhas[:top]


def _sem_acento(texto: str) -> str:
    return (texto.replace("Ã", "A").replace("Á", "A").replace("À", "A")
                 .replace("Â", "A").replace("Ç", "C"))
