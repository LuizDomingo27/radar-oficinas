"""Construção do De-Para: agrupa variantes de nome em oficinas canônicas.

Regra de agrupamento: **apenas o nome** — variantes com o mesmo ``nome_base``
pertencem à mesma oficina. O único mecanismo de revisão é a detecção de
nomes-base quase idênticos (possíveis duplicatas a decidir manualmente).
"""

from __future__ import annotations

import re
from collections import Counter
from difflib import SequenceMatcher
from itertools import combinations
from typing import Iterable

from app_oficinas import config
from app_oficinas.domain.models import Oficina, VarianteNome

_SLUG_INVALIDO = re.compile(r"[^a-z0-9]+")


def _slug(nome_base: str) -> str:
    """Gera um identificador estável e legível a partir do nome-base."""
    return _SLUG_INVALIDO.sub("-", nome_base.lower()).strip("-")


def _nome_para_exibir(variantes: list[VarianteNome]) -> str:
    """Escolhe o rótulo de exibição da oficina.

    Prioriza a grafia da planilha de postos (``config.FONTE_NOME_PADRAO``), que
    é a lista oficial de parceiros. Só quando a oficina não aparece em postos é
    que se recorre à grafia crua mais frequente entre as demais fontes.

    Desempate determinístico em ambos os casos: mais frequente, depois mais
    longa, depois alfabética — assim o resultado não depende da ordem de leitura.
    """
    padrao = [v for v in variantes if v.fonte == config.FONTE_NOME_PADRAO]
    candidatas = padrao or variantes
    contagem = Counter(v.nome_cru for v in candidatas)
    return max(contagem, key=lambda n: (contagem[n], len(n), n))


def _agrupar(variantes: list[VarianteNome]) -> list[list[VarianteNome]]:
    """Agrupa variantes exclusivamente pelo ``nome_base``."""
    grupos: dict[str, list[VarianteNome]] = {}
    for variante in variantes:
        grupos.setdefault(variante.nome_base, []).append(variante)
    return list(grupos.values())


def _sinalizar_duplicatas(oficinas: list[Oficina]) -> None:
    """Marca pares de oficinas cujos nomes-base são quase idênticos.

    Atua in-place adicionando avisos em ``Oficina.revisao``. Comparação apenas
    entre bases distintas — igualdade já teria fundido as variantes.
    """
    for a, b in combinations(oficinas, 2):
        similaridade = SequenceMatcher(None, a.nome_base, b.nome_base).ratio()
        if similaridade >= config.LIMIAR_DUPLICATA:
            pct = round(similaridade * 100)
            a.revisao.append(f"Possível duplicata de '{b.nome_canonico}' ({pct}%)")
            b.revisao.append(f"Possível duplicata de '{a.nome_canonico}' ({pct}%)")


def construir_depara(variantes: Iterable[VarianteNome]) -> list[Oficina]:
    """Constrói a lista de oficinas canônicas a partir das variantes.

    Args:
        variantes: variantes já normalizadas (ver ``services.normalizacao``).

    Returns:
        Oficinas ordenadas por nome de exibição, com identificadores únicos,
        procedência consolidada e sinalizações de revisão preenchidas.
    """
    grupos = _agrupar(list(variantes))
    oficinas: list[Oficina] = []
    ids_usados: set[str] = set()

    for grupo in grupos:
        nome_base = grupo[0].nome_base  # todas as variantes do grupo compartilham a base

        base_id = _slug(nome_base) or "oficina"
        oficina_id = base_id
        contador = 2
        while oficina_id in ids_usados:  # colisão de slug: desambigua
            oficina_id = f"{base_id}-{contador}"
            contador += 1
        ids_usados.add(oficina_id)

        oficina = Oficina(
            oficina_id=oficina_id,
            nome_canonico=_nome_para_exibir(grupo),
            nome_base=nome_base,
            variantes=list(grupo),
            fontes={v.fonte for v in grupo},
            papeis={v.papel for v in grupo},
            unidades={v.unidade for v in grupo if v.unidade},
        )
        oficinas.append(oficina)

    oficinas.sort(key=lambda o: o.nome_canonico)
    _sinalizar_duplicatas(oficinas)
    return oficinas


def indexar_por_nome(oficinas: list[Oficina]) -> dict[str, tuple[str, str]]:
    """Mapeia cada ``nome_base`` para ``(oficina_id, nome_canonico)``.

    É a ponte da Fase 2: dado o nome cru de um fato, normaliza-se para o
    nome-base (ver ``normalizacao.nome_base_de``) e consulta-se este índice para
    obter a chave canônica da oficina. Bases distintas nunca colidem porque o
    agrupamento do De-Para é justamente por base.
    """
    return {
        o.nome_base: (o.oficina_id, o.nome_canonico) for o in oficinas
    }


def resumo(oficinas: list[Oficina]) -> dict[str, int]:
    """Métricas agregadas do De-Para para relatório e conferência."""
    return {
        "oficinas": len(oficinas),
        "precisam_revisao": sum(1 for o in oficinas if o.precisa_revisao),
        "com_producao": sum(1 for o in oficinas if o.cobre_papel(config.PAPEL_PRODUCAO)),
        "com_absenteismo": sum(
            1 for o in oficinas if o.cobre_papel(config.PAPEL_ABSENTEISMO)
        ),
        "com_eficiencia": sum(
            1 for o in oficinas if o.cobre_papel(config.PAPEL_EFICIENCIA)
        ),
        "com_treino": sum(1 for o in oficinas if o.cobre_papel(config.PAPEL_TREINO)),
        "cobertura_3_metricas": sum(
            1
            for o in oficinas
            if o.cobre_papel(config.PAPEL_PRODUCAO)
            and o.cobre_papel(config.PAPEL_ABSENTEISMO)
            and o.cobre_papel(config.PAPEL_EFICIENCIA)
        ),
    }
