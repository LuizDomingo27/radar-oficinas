"""Leitura de nomes de oficina a partir das planilhas .xlsx.

Único ponto de I/O da Fase 1. Isola o openpyxl do resto do sistema e converte
falhas de arquivo/aba/coluna em exceções de domínio, para que as camadas
superiores nunca vejam um ``KeyError``/``FileNotFoundError`` cru.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import openpyxl

from app_oficinas import config
from app_oficinas.config import FonteNomes
from app_oficinas.domain.models import RegistroNome
from app_oficinas.errors import PlanilhaNaoEncontrada
from app_oficinas.infra import abas


def _abrir(caminho: Path):
    """Abre a planilha em modo somente-leitura, traduzindo falhas de I/O."""
    if not caminho.exists():
        raise PlanilhaNaoEncontrada(f"Planilha não encontrada: {caminho}")
    try:
        return openpyxl.load_workbook(caminho, read_only=True, data_only=True)
    except Exception as exc:  # arquivo corrompido / não-xlsx
        raise PlanilhaNaoEncontrada(
            f"Falha ao abrir a planilha {caminho.name}: {exc}"
        ) from exc


def ler_fonte(
    fonte: FonteNomes, base_dir: Path | None = None
) -> Iterator[RegistroNome]:
    """Emite um ``RegistroNome`` por linha de dados válida de uma fonte.

    Linhas vazias ou sem nome de oficina são ignoradas silenciosamente; a
    validação semântica (ruído, normalização) fica a cargo dos serviços.

    Raises:
        PlanilhaNaoEncontrada: arquivo ausente ou ilegível.
        AbaNaoEncontrada: a aba configurada não existe.
        ColunaInvalida: índice de coluna fora do intervalo da aba.
    """
    base_dir = base_dir or config.PLANILHAS_DIR
    caminho = base_dir / fonte.arquivo
    wb = _abrir(caminho)
    try:
        ws = abas.abrir_aba(wb, fonte.aba, fonte.arquivo)
        for linha in ws.iter_rows(min_row=fonte.primeira_linha, values_only=True):
            if len(linha) <= fonte.col_nome:
                continue
            valor = linha[fonte.col_nome]
            if valor is None or not str(valor).strip():
                continue
            yield RegistroNome(
                nome_cru=str(valor).strip(),
                fonte=fonte.chave,
                papel=fonte.papel,
            )
    finally:
        wb.close()


def ler_todas(
    fontes: tuple[FonteNomes, ...] | None = None,
    base_dir: Path | None = None,
    tolerante: bool = False,
) -> tuple[list[RegistroNome], list[str]]:
    """Lê todas as fontes configuradas.

    Args:
        fontes: fontes a ler; usa ``config.FONTES`` por padrão.
        base_dir: raiz onde estão os .xlsx.
        tolerante: se ``True``, uma fonte com erro é registrada e pulada em vez
            de interromper a leitura das demais.

    Returns:
        Uma tupla ``(registros, erros)`` — a lista de registros lidos e a lista
        de mensagens de erro das fontes que falharam (vazia se ``tolerante`` é
        ``False``, pois nesse caso a primeira falha é propagada).
    """
    fontes = fontes or config.FONTES
    registros: list[RegistroNome] = []
    erros: list[str] = []
    for fonte in fontes:
        try:
            registros.extend(ler_fonte(fonte, base_dir))
        except Exception as exc:
            if not tolerante:
                raise
            erros.append(f"[{fonte.chave}] {exc}")
    return registros, erros
