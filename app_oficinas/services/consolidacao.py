"""Consolidação dos fatos (Fase 2).

Recebe o índice canônico do De-Para (``nome_base`` -> ``oficina_id``) e as
linhas cruas lidas pela infra, e produz listas de fatos tipados já com
``oficina_id`` e ``Periodo``. Funções puras sobre as linhas — o I/O fica na
infra e é injetado pelo orquestrador ``consolidar``.

Regra de resolução: normaliza-se o nome cru do fato para o mesmo ``nome_base``
usado na Fase 1 e consulta-se o índice. Sem correspondência, o fato é mantido
com ``oficina_id = None`` (registrado em ``nao_resolvidos``) — nunca se descarta
silenciosamente uma observação de métrica.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable

from app_oficinas import config
from app_oficinas.domain.models import (
    FatoAbsenteismo,
    FatoEficiencia,
    FatoProducao,
    FatoTreino,
    Periodo,
)
from app_oficinas.infra import leitor_fatos
from app_oficinas.services import periodos
from app_oficinas.services.normalizacao import nome_base_de, normalizar_mp

Indice = dict[str, tuple[str, str]]


class Consolidado:
    """Agregado dos quatro fatos + diagnóstico de resolução de nomes."""

    def __init__(self) -> None:
        self.producao: list[FatoProducao] = []
        self.absenteismo: list[FatoAbsenteismo] = []
        self.eficiencia: list[FatoEficiencia] = []
        self.treino: list[FatoTreino] = []
        self.nao_resolvidos: set[str] = set()  # nomes crus sem match no De-Para

    def resumo(self) -> dict[str, int]:
        return {
            "producao": len(self.producao),
            "absenteismo": len(self.absenteismo),
            "eficiencia": len(self.eficiencia),
            "treino": len(self.treino),
            "nao_resolvidos": len(self.nao_resolvidos),
        }


def _mp(valor: object) -> str | None:
    """Normaliza a MP; se não estiver no vocabulário, mantém em caixa-alta."""
    if valor is None:
        return None
    return normalizar_mp(valor) or str(valor).strip().upper() or None


def _resolver(nome: str, indice: Indice, consolidado: Consolidado) -> str | None:
    """Devolve o ``oficina_id`` do nome, registrando os não resolvidos."""
    base = nome_base_de(nome)
    achado = indice.get(base) if base else None
    if achado is None:
        consolidado.nao_resolvidos.add(nome)
        return None
    return achado[0]


def _consumir(
    linhas: Iterable[dict], construir: Callable[[dict], object | None]
) -> None:
    """Aplica ``construir`` a cada linha, ignorando as que devolvem ``None``."""
    for linha in linhas:
        fato = construir(linha)
        if fato is not None:
            yield fato


def consolidar(indice: Indice, base_dir: Path | None = None) -> Consolidado:
    """Lê todas as fontes de valor e devolve os fatos consolidados."""
    c = Consolidado()

    def prod(linha: dict) -> FatoProducao | None:
        periodo = periodos.periodo_de_data(linha["data"])
        if periodo is None:
            return None
        return FatoProducao(
            oficina_id=_resolver(linha["nome"], indice, c),
            oficina_nome=linha["nome"],
            mp=_mp(linha["mp"]),
            periodo=periodo,
            fonte="recebimento",
            real_cortado=linha["real_cortado"],
            minutos=linha["minutos"],
        )

    def absen(linha: dict) -> FatoAbsenteismo | None:
        periodo = periodos.periodo_de_data(linha["data"], linha["semana"])
        if periodo is None:
            return None
        return FatoAbsenteismo(
            oficina_id=_resolver(linha["nome"], indice, c),
            oficina_nome=linha["nome"],
            mp=_mp(linha["mp"]),
            periodo=periodo,
            fonte="postos",
            qtd_efetivos=linha["efetivos"],
            qtd_trabalhados=linha["trabalhados"],
            contratacao=linha["contratacao"],
            demissao=linha["demissao"],
            frete=linha["frete"],
        )

    def efic(fonte: str):
        def construir(linha: dict) -> FatoEficiencia:
            return FatoEficiencia(
                oficina_id=_resolver(linha["nome"], indice, c),
                oficina_nome=linha["nome"],
                mp=_mp(linha["mp"]),
                periodo=Periodo(ano=linha["ano"], rotulo_semana=linha["rotulo_semana"]),
                fonte=fonte,
                tipo_valor=linha["tipo_valor"],
                valor=linha["valor"],
            )
        return construir

    def treino_ep(linha: dict) -> FatoTreino:
        return FatoTreino(
            oficina_id=_resolver(linha["nome"], indice, c),
            oficina_nome=linha["nome"],
            mp=None,
            periodo=periodos.periodo_de_ciclo(linha["ciclo"]) or Periodo(ano=0),
            fonte="treino_ep",
            modulo=linha["modulo"],
            ch=linha["ch"],
            ciclo=linha["ciclo"],
            polo=None,
        )

    def treino_lidera(linha: dict) -> FatoTreino:
        periodo = periodos.periodo_de_data(linha["data"]) or Periodo(ano=2026)
        return FatoTreino(
            oficina_id=_resolver(linha["nome"], indice, c),
            oficina_nome=linha["nome"],
            mp=None,
            periodo=periodo,
            fonte="lidera",
            modulo=linha["modulo"],
            ch=None,
            ciclo=None,
            polo=linha["polo"],
        )

    c.producao = list(_consumir(leitor_fatos.ler_producao(base_dir), prod))
    c.absenteismo = list(_consumir(leitor_fatos.ler_absenteismo(base_dir), absen))
    c.eficiencia = list(_consumir(
        leitor_fatos.ler_eficiencia_jeans(base_dir), efic("estoque_jeans")
    )) + list(_consumir(
        leitor_fatos.ler_eficiencia_naojeans(base_dir), efic("estoque_naojeans")
    ))
    c.treino = list(_consumir(leitor_fatos.ler_treino_ep(base_dir), treino_ep)) \
        + list(_consumir(leitor_fatos.ler_treino_lidera(base_dir), treino_lidera))
    return c
