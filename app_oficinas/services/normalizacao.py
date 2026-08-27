"""Normalização de nomes de oficina, CNPJ e matéria-prima.

Funções puras e determinísticas — sem I/O — para serem exaustivamente
testadas. O objetivo é reduzir cada nome cru a um ``nome_base`` estável que
sirva de chave de agrupamento no De-Para, preservando a unidade/linha.
"""

from __future__ import annotations

import re
import unicodedata

from app_oficinas import config
from app_oficinas.domain.models import RegistroNome, VarianteNome

_NAO_ALFANUM = re.compile(r"[^0-9A-Z ]+")
_ESPACOS = re.compile(r"\s+")
_TEM_LETRA = re.compile(r"[A-Z]")


def remover_acentos(texto: str) -> str:
    """Remove diacríticos preservando as letras-base (ç -> c, ã -> a)."""
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def limpar(texto: str) -> str:
    """Coloca em caixa-alta, remove acentos/pontuação e colapsa espaços."""
    if texto is None:
        return ""
    base = remover_acentos(str(texto)).upper()
    base = _NAO_ALFANUM.sub(" ", base)
    return _ESPACOS.sub(" ", base).strip()


def eh_ruido(nome_limpo: str) -> bool:
    """True se o valor não representa uma oficina (cabeçalho, marcador, vazio)."""
    if len(nome_limpo) < config.MIN_TAMANHO_BASE:
        return True
    if not _TEM_LETRA.search(nome_limpo):  # puramente numérico (ex.: "0 94", "524")
        return True
    return nome_limpo in config.RUIDO


def separar_base_e_unidade(nome_limpo: str) -> tuple[str, str | None]:
    """Remove tokens de unidade e de natureza jurídica do fim do nome.

    Retorna ``(nome_base, unidade)`` onde ``unidade`` é o token de linha/unidade
    removido mais próximo do fim (ex.: ``POLO``), ou ``None``. Preserva ao menos
    um token para nunca devolver base vazia.
    """
    tokens = nome_limpo.split()
    unidade: str | None = None
    while len(tokens) > 1:
        ultimo = tokens[-1]
        if ultimo in config.TOKENS_UNIDADE:
            if unidade is None:
                unidade = ultimo
            tokens.pop()
        elif ultimo in config.TOKENS_JURIDICOS:
            tokens.pop()
        else:
            break
    return " ".join(tokens), unidade


def base_e_unidade_de(nome_cru: object) -> tuple[str, str | None] | None:
    """Reduz um nome cru a ``(nome_base, unidade)`` ou ``None`` se for ruído.

    Núcleo compartilhado por ``criar_variante`` (Fase 1) e pela resolução de
    ``oficina_id`` dos fatos (Fase 2), para que ambas apliquem exatamente a
    mesma regra de agrupamento por nome.
    """
    limpo = limpar(nome_cru)
    if eh_ruido(limpo):
        return None
    nome_base, unidade = separar_base_e_unidade(limpo)
    if eh_ruido(nome_base):
        return None
    return nome_base, unidade


def nome_base_de(nome_cru: object) -> str | None:
    """Chave de agrupamento (nome-base) de um nome cru, ou ``None`` se ruído."""
    resultado = base_e_unidade_de(nome_cru)
    return resultado[0] if resultado else None


def criar_variante(registro: RegistroNome) -> VarianteNome | None:
    """Converte um ``RegistroNome`` cru em ``VarianteNome`` normalizada.

    Devolve ``None`` quando o valor é ruído ou não é uma oficina válida, de
    modo que a camada chamadora simplesmente o descarta.
    """
    resultado = base_e_unidade_de(registro.nome_cru)
    if resultado is None:
        return None
    nome_base, unidade = resultado
    return VarianteNome(
        nome_cru=str(registro.nome_cru).strip(),
        nome_base=nome_base,
        unidade=unidade,
        fonte=registro.fonte,
        papel=registro.papel,
    )


def normalizar_mp(valor: object) -> str | None:
    """Normaliza a matéria-prima para uma forma canônica (ver ``config``)."""
    if valor is None:
        return None
    return config.MP_CANONICO.get(str(valor).strip().lower())
