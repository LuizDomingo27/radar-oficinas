"""
core/record.py
----------------
Domínio do "registro de posto de trabalho": invariantes de negócio e
montagem/sanitização do payload de persistência.

Camada PURA (sem I/O). Concentra as regras do agregado "registro" para que
tanto a inserção (`services/data_writer`) quanto a edição
(`services/record_service`) compartilhem exatamente as mesmas regras, sem
duplicação.
"""

from __future__ import annotations

import datetime
from typing import Any

from app_postos.core.config import Columns

_MIN_SEMANA = 1
_MAX_SEMANA = 53


class RecordValidationError(Exception):
    """
    Erro de domínio: um ou mais campos do registro violam as invariantes de
    negócio. `errors` guarda TODAS as mensagens (a UI pode exibir uma a uma).
    """

    def __init__(self, errors: list[str]):
        self.errors = list(errors)
        super().__init__(" ".join(self.errors) or "Registro inválido.")


def _to_iso_date(value: Any) -> str:
    """
    Normaliza uma data (`date`/`datetime`/str ISO) para 'YYYY-MM-DD'.
    Levanta ValueError/TypeError se o valor não for uma data ISO válida.
    """
    if isinstance(value, datetime.datetime):
        return value.date().isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    text = str(value).strip()
    # `fromisoformat` aceita apenas datas no formato ISO (ex.: '2026-08-24').
    return datetime.date.fromisoformat(text).isoformat()


def build_record_payload(
    *,
    frete: Any,
    mp: Any,
    oficina: Any,
    data_efetivos: Any,
    qtd_efetivos: Any,
    data_trabalhados: Any,
    qtd_trabalhados: Any,
    contratacoes: Any,
    demissoes: Any,
    semana: Any,
) -> dict:
    """
    Monta o dict sanitizado pronto para persistir na tabela `postos`
    (mesmo contrato de colunas usado por inserção e edição). Não valida — a
    validação de invariantes é responsabilidade de `validate_record_fields`,
    que deve ser chamada antes quando a origem dos dados não é confiável.
    """
    return {
        Columns.FRETE: str(frete).strip(),
        Columns.MP: str(mp).strip().upper(),
        Columns.OFICINA: str(oficina).strip(),
        Columns.DATA_EFETIVOS: _to_iso_date(data_efetivos),
        Columns.QTD_EFETIVOS: int(qtd_efetivos),
        Columns.DATA_TRABALHADOS: _to_iso_date(data_trabalhados),
        Columns.QTD_TRABALHADOS: int(qtd_trabalhados),
        Columns.CONTRATACOES: int(contratacoes),
        Columns.DEMISSOES: int(demissoes),
        Columns.SEMANA: int(semana),
    }


def validate_record_fields(
    *,
    oficina: Any,
    mp: Any,
    frete: Any,
    data_efetivos: Any,
    qtd_efetivos: Any,
    data_trabalhados: Any,
    qtd_trabalhados: Any,
    contratacoes: Any,
    demissoes: Any,
    semana: Any,
) -> None:
    """
    Valida as invariantes de um registro. Acumula TODOS os problemas e, se
    houver algum, levanta `RecordValidationError` com a lista completa (em vez
    de falhar no primeiro), para que o usuário veja tudo de uma vez.
    """
    errors: list[str] = []

    if not str(oficina).strip():
        errors.append("O campo 'Oficina' é obrigatório.")
    if not str(mp).strip():
        errors.append("O campo 'Matéria-prima (MP)' é obrigatório.")
    if not str(frete).strip():
        errors.append("O campo 'Frete' é obrigatório.")

    # Semana: inteiro dentro do intervalo ISO (1..53).
    try:
        semana_int = int(semana)
        if not (_MIN_SEMANA <= semana_int <= _MAX_SEMANA):
            errors.append(f"A 'Semana' deve estar entre {_MIN_SEMANA} e {_MAX_SEMANA}.")
    except (TypeError, ValueError):
        errors.append("A 'Semana' deve ser um número inteiro.")

    # Quantidades: inteiras e não-negativas.
    for label, value in (
        ("QTD Efetivos", qtd_efetivos),
        ("QTD Trabalhados", qtd_trabalhados),
        ("Contratações", contratacoes),
        ("Demissões", demissoes),
    ):
        try:
            if int(value) < 0:
                errors.append(f"O campo '{label}' não pode ser negativo.")
        except (TypeError, ValueError):
            errors.append(f"O campo '{label}' deve ser um número inteiro.")

    # Datas: precisam ser datas ISO válidas.
    for label, value in (
        ("Data Efetivos", data_efetivos),
        ("Data Trabalhados", data_trabalhados),
    ):
        try:
            _to_iso_date(value)
        except (TypeError, ValueError):
            errors.append(f"O campo '{label}' contém uma data inválida.")

    if errors:
        raise RecordValidationError(errors)
