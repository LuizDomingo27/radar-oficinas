"""
services/record_service.py
----------------------------
Recurso de EDIÇÃO de registros da tabela `postos` (camada de aplicação).

Responsabilidade única: ler registros existentes (com `id`) para seleção e
SOBRESCREVER um registro após validar as invariantes do domínio
(`core.record`) e a regra de duplicidade (`data_writer.check_record_exists`).
Mantém o recurso de edição isolado da inserção e das telas.

Todas as funções aceitam `client` (injeção de dependência) para permitir
testes com um fake, sem tocar o banco remoto de produção.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app_postos.core.config import Columns, DB_TABLE_POSTOS
from app_postos.core.record import RecordValidationError, build_record_payload, validate_record_fields
from app_postos.services.data_writer import check_record_exists
from app_common.neon_client import fetch_all_rows, get_db_client

if TYPE_CHECKING:  # apenas para type hints
    from app_common.neon_client import NeonClient as Client

__all__ = [
    "RecordServiceError",
    "RecordNotFoundError",
    "RecordDuplicateError",
    "RecordValidationError",
    "list_records",
    "get_record",
    "update_record",
]


class RecordServiceError(Exception):
    """Falha de I/O no recurso de edição de registros."""


class RecordNotFoundError(RecordServiceError):
    """O registro solicitado (por `id`) não existe na tabela `postos`."""


class RecordDuplicateError(RecordServiceError):
    """
    A edição criaria uma duplicata: OUTRO registro já tem a mesma
    Oficina + Matéria-prima + Semana + Ano.
    """


def list_records(*, client: "Client | None" = None) -> list[dict]:
    """Lê todos os registros (com `id`) para popular a seleção de edição."""
    client = client or get_db_client()
    try:
        return fetch_all_rows(client, DB_TABLE_POSTOS)
    except Exception as exc:
        raise RecordServiceError(f"Erro ao listar os registros no banco: {exc}") from exc


def get_record(record_id: int, *, client: "Client | None" = None) -> dict:
    """Busca um registro por `id`; levanta RecordNotFoundError se não existir."""
    client = client or get_db_client()
    try:
        response = (
            client.table(DB_TABLE_POSTOS)
            .select("*")
            .eq("id", record_id)
            .limit(1)
            .execute()
        )
        data = response.data or []
    except Exception as exc:
        raise RecordServiceError(f"Erro ao buscar o registro no banco: {exc}") from exc

    if not data:
        raise RecordNotFoundError(f"Registro id={record_id} não encontrado.")
    return data[0]


def update_record(
    record_id: int,
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
    client: "Client | None" = None,
) -> None:
    """
    Sobrescreve um registro existente.

    Ordem (falha cedo, sem escrever se algo estiver errado):
      1. valida invariantes do domínio  -> RecordValidationError
      2. confirma que o registro existe  -> RecordNotFoundError
      3. checa duplicidade ignorando o próprio id -> RecordDuplicateError
      4. grava a sobrescrita
    """
    # 1. Invariantes do domínio (deixa RecordValidationError propagar para a UI).
    validate_record_fields(
        oficina=oficina,
        mp=mp,
        frete=frete,
        data_efetivos=data_efetivos,
        qtd_efetivos=qtd_efetivos,
        data_trabalhados=data_trabalhados,
        qtd_trabalhados=qtd_trabalhados,
        contratacoes=contratacoes,
        demissoes=demissoes,
        semana=semana,
    )

    client = client or get_db_client()

    # 2. Registro precisa existir (mensagem clara em vez de UPDATE silencioso).
    get_record(record_id, client=client)

    payload = build_record_payload(
        frete=frete,
        mp=mp,
        oficina=oficina,
        data_efetivos=data_efetivos,
        qtd_efetivos=qtd_efetivos,
        data_trabalhados=data_trabalhados,
        qtd_trabalhados=qtd_trabalhados,
        contratacoes=contratacoes,
        demissoes=demissoes,
        semana=semana,
    )

    # 3. Duplicidade: bloqueia apenas se OUTRO registro (id != este) já tem a
    #    mesma Oficina/MP/Semana/Ano. Editar o próprio registro sem mudar a
    #    chave é permitido (exclude_id remove ele mesmo da checagem).
    if check_record_exists(
        payload[Columns.OFICINA],
        payload[Columns.MP],
        payload[Columns.SEMANA],
        payload[Columns.DATA_EFETIVOS],
        exclude_id=record_id,
        client=client,
    ):
        raise RecordDuplicateError(
            f"Já existe outro lançamento para a Oficina '{payload[Columns.OFICINA]}' "
            f"com a Matéria-prima '{payload[Columns.MP]}' na Semana {payload[Columns.SEMANA]} "
            f"desse mesmo ano."
        )

    # 4. Sobrescreve o registro.
    try:
        client.table(DB_TABLE_POSTOS).update(payload).eq("id", record_id).execute()
    except Exception as exc:
        raise RecordServiceError(f"Erro ao atualizar o registro no banco: {exc}") from exc
