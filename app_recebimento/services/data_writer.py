"""
services/data_writer.py — gravação de novos recebimentos em ``Recebimento_Radar``.

Regra anti-duplicação (mesma decisão de Envios): cada linha recebe uma impressão
digital (``row_hash`` = SHA-1 do conteúdo + índice de ocorrência no arquivo). Só
entram no banco as linhas cujo hash ainda NÃO existe — re-subir a mesma planilha
não insere nada (idempotente), e linhas 100% idênticas do mesmo arquivo são ambas
preservadas. Nada é apagado ou sobrescrito: a gravação é insert-only.
"""

from __future__ import annotations

import pandas as pd

from app_common.formatting import build_row_hash
from app_common.neon_client import fetch_all_rows, get_db_client
from app_recebimento.core.config import (
    Columns,
    DB_COLUMNS_PERSISTED,
    DB_TABLE_RECEBIMENTO,
)
from app_recebimento.services.data_cleaning import standardize_raw

_BULK_INSERT_BATCH_SIZE = 500

# Campos de conteúdo que compõem a impressão digital da linha (ordem fixa).
_HASH_FIELDS = [
    Columns.ORDEM, Columns.OFICINA, Columns.QTD, Columns.MINUTOS,
    Columns.RECEBIMENTO, Columns.MP,
]


def _data_iso(value) -> str | None:
    """Data de recebimento como 'YYYY-MM-DD' (ou None quando ausente/inválida)."""
    if value is None or pd.isna(value):
        return None
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def prepare_dataframe_for_insert(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Padroniza a planilha bruta e acrescenta ``row_hash`` (com índice de
    ocorrência para preservar linhas idênticas). Devolve um DataFrame com
    exatamente as colunas persistidas em ``Recebimento_Radar``.
    """
    df = standardize_raw(df_raw)

    # Índice de ocorrência: para linhas idênticas dentro do arquivo, 0,1,2…
    ocorrencia = df.groupby(_HASH_FIELDS, dropna=False).cumcount()

    df[Columns.ROW_HASH] = [
        build_row_hash(
            [row[Columns.ORDEM], row[Columns.OFICINA], row[Columns.QTD],
             row[Columns.MINUTOS], _data_iso(row[Columns.RECEBIMENTO]) or "",
             row[Columns.MP]],
            occurrence=int(occ),
        )
        for (_, row), occ in zip(df.iterrows(), ocorrencia)
    ]
    return df[DB_COLUMNS_PERSISTED]


def _row_to_payload(row: pd.Series) -> dict:
    return {
        Columns.ROW_HASH: str(row[Columns.ROW_HASH]),
        Columns.ORDEM: str(row[Columns.ORDEM]),
        Columns.OFICINA: str(row[Columns.OFICINA]),
        Columns.QTD: int(row[Columns.QTD]),
        Columns.MINUTOS: float(row[Columns.MINUTOS]),
        Columns.RECEBIMENTO: _data_iso(row[Columns.RECEBIMENTO]),
        Columns.MP: str(row[Columns.MP]),
    }


def insert_bulk_records(df_raw: pd.DataFrame, client=None) -> int:
    """
    Insere na tabela ``Recebimento_Radar`` apenas os recebimentos ainda não
    existentes (dedup por ``row_hash``). Retorna o número de linhas novas.

    `client`: injeção de dependência opcional (testes). Em produção fica None e
    a conexão real é obtida sob demanda.
    """
    df = prepare_dataframe_for_insert(df_raw)

    client = client or get_db_client()
    try:
        existentes = fetch_all_rows(client, DB_TABLE_RECEBIMENTO, columns=Columns.ROW_HASH)
        hashes_existentes = {str(r[Columns.ROW_HASH]) for r in existentes}

        # Remove os já existentes no banco e eventuais repetições no próprio lote.
        df_novos = df[~df[Columns.ROW_HASH].isin(hashes_existentes)]
        df_novos = df_novos.drop_duplicates(subset=[Columns.ROW_HASH])

        if df_novos.empty:
            return 0

        payload = [_row_to_payload(row) for _, row in df_novos.iterrows()]
        for i in range(0, len(payload), _BULK_INSERT_BATCH_SIZE):
            client.table(DB_TABLE_RECEBIMENTO).insert(
                payload[i : i + _BULK_INSERT_BATCH_SIZE]
            ).execute()

        return len(df_novos)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Erro ao importar recebimentos para o banco: {exc}") from exc
