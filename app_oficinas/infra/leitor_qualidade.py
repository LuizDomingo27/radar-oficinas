"""Leitura das abas de qualidade do "Indicador geral" (I/O isolado).

Emite dicionários crus, sem regra de negócio: ``ler_inspecoes`` (aba RESUMO)
e ``ler_defeitos`` (aba DEFEITOS). A agregação e as fórmulas ficam no serviço
``services/qualidade.py``. As abas são grandes (~41 mil e ~144 mil linhas),
então são lidas em modo streaming (``read_only`` + ``iter_rows``).
"""
from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Iterator

import openpyxl

from app_oficinas import config
from app_oficinas.errors import PlanilhaNaoEncontrada
from app_oficinas.infra import abas

_EPOCA_EXCEL = _dt.datetime(1899, 12, 30)


def _abrir(caminho: Path):
    if not caminho.exists():
        raise PlanilhaNaoEncontrada(f"Planilha não encontrada: {caminho}")
    try:
        return openpyxl.load_workbook(caminho, read_only=True, data_only=True)
    except Exception as exc:  # arquivo corrompido / não-xlsx
        raise PlanilhaNaoEncontrada(
            f"Falha ao abrir a planilha {caminho.name}: {exc}"
        ) from exc


def _aba(wb, nome_aba: str, arquivo: str):
    """Aba pedida, tolerando renomeação (ver ``infra.abas``)."""
    return abas.abrir_aba(wb, nome_aba, arquivo)


def _texto(valor) -> str:
    return "" if valor is None else str(valor).replace("\t", " ").strip()


def _int(valor) -> int:
    try:
        return int(round(float(valor)))
    except (TypeError, ValueError):
        return 0


def _float(valor) -> float:
    if isinstance(valor, bool) or valor is None:
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    try:
        return float(str(valor).strip().replace(",", "."))
    except ValueError:
        return 0.0


def _ano_mes(valor) -> tuple[int | None, int | None]:
    """(ano, mês) a partir de um datetime ou serial Excel; (None, None) se vazio."""
    if isinstance(valor, (_dt.datetime, _dt.date)):
        return valor.year, valor.month
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        d = _EPOCA_EXCEL + _dt.timedelta(days=int(valor))
        return d.year, d.month
    return None, None


def ler_inspecoes(base_dir: Path | None = None) -> Iterator[dict]:
    """Cada inspeção da aba RESUMO: {oficina, status, dois_qa, prod, ano, mes}."""
    fonte = config.QUALIDADE_RESUMO
    base = base_dir or config.PLANILHAS_DIR
    wb = _abrir(base / fonte.arquivo)
    try:
        ws = _aba(wb, fonte.aba, fonte.arquivo)
        for row in ws.iter_rows(min_row=fonte.primeira_linha, values_only=True):
            oficina = _texto(row[fonte.col_oficina]) if len(row) > fonte.col_oficina else ""
            if not oficina:
                continue
            ano, mes = _ano_mes(row[fonte.col_data3])
            if ano is None:
                continue
            yield {
                "oficina": oficina,
                "status": _texto(row[fonte.col_status]).upper(),
                "dois_qa": _float(row[fonte.col_2qa]),
                "prod": _float(row[fonte.col_prod]),
                "ano": ano,
                "mes": mes,
            }
    finally:
        wb.close()


def ler_defeitos(base_dir: Path | None = None) -> Iterator[dict]:
    """Cada defeito da aba DEFEITOS: {defeito, tipo, setor, ano, mes, qntd}."""
    fonte = config.QUALIDADE_DEFEITOS
    base = base_dir or config.PLANILHAS_DIR
    wb = _abrir(base / fonte.arquivo)
    try:
        ws = _aba(wb, fonte.aba, fonte.arquivo)
        for row in ws.iter_rows(min_row=fonte.primeira_linha, values_only=True):
            defeito = _texto(row[fonte.col_defeito]) if len(row) > fonte.col_defeito else ""
            if not defeito:
                continue
            yield {
                "defeito": defeito,
                "tipo": _texto(row[fonte.col_tipo]).upper(),
                "setor": _texto(row[fonte.col_setor]).upper(),
                "ano": _int(row[fonte.col_ano]) or None,
                "mes": _int(row[fonte.col_mes]) or None,
                "qntd": _float(row[fonte.col_qntd]),
            }
    finally:
        wb.close()
