"""
services/data_writer.py — gravação de novos envios na tabela ``Envios_Radar``.

Regra anti-duplicação (decisão do time): cada linha recebe uma impressão digital
(``row_hash`` = SHA-1 do conteúdo + índice de ocorrência no arquivo). Só entram
no banco as linhas cujo hash ainda NÃO existe — re-subir a mesma planilha não
insere nada (idempotente), e linhas 100% idênticas do mesmo arquivo são ambas
preservadas. Nada é apagado ou sobrescrito: a gravação é insert-only.
"""

from __future__ import annotations

import pandas as pd

from app_envios.core.config import (
    Columns,
    DB_COLUMNS_PERSISTED,
    SUPABASE_TABLE_ENVIOS,
)
from app_envios.core.utils import build_row_hash
from app_envios.services.data_cleaning import standardize_raw
from app_envios.services.supabase_client import fetch_all_rows, get_supabase_client

_BULK_INSERT_BATCH_SIZE = 500

# Campos de conteúdo que compõem a impressão digital da linha (ordem fixa).
_HASH_FIELDS = [
    Columns.ORIGEM, Columns.ORDEM, Columns.OFICINA, Columns.QTD, Columns.MINUTOS,
    Columns.ENVIO, Columns.MP, Columns.PDV, Columns.FRETE, Columns.SITUACAO,
]


def _envio_iso(value) -> str | None:
    """Data de envio como 'YYYY-MM-DD' (ou None quando ausente/ inválida)."""
    if value is None or pd.isna(value):
        return None
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def prepare_dataframe_for_insert(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Padroniza a planilha bruta e acrescenta ``row_hash`` (com índice de
    ocorrência para preservar linhas idênticas). Devolve um DataFrame com
    exatamente as colunas persistidas em ``Envios_Radar``.
    """
    df = standardize_raw(df_raw)

    # Índice de ocorrência: para linhas idênticas dentro do arquivo, 0,1,2…
    ocorrencia = df.groupby(_HASH_FIELDS, dropna=False).cumcount()

    df[Columns.ROW_HASH] = [
        build_row_hash(
            [row[Columns.ORIGEM], row[Columns.ORDEM], row[Columns.OFICINA],
             row[Columns.QTD], row[Columns.MINUTOS], _envio_iso(row[Columns.ENVIO]) or "",
             row[Columns.MP], row[Columns.PDV], row[Columns.FRETE], row[Columns.SITUACAO]],
            occurrence=int(occ),
        )
        for (_, row), occ in zip(df.iterrows(), ocorrencia)
    ]
    return df[DB_COLUMNS_PERSISTED]


def _row_to_payload(row: pd.Series) -> dict:
    return {
        Columns.ROW_HASH: str(row[Columns.ROW_HASH]),
        Columns.ORIGEM: str(row[Columns.ORIGEM]),
        Columns.ORDEM: str(row[Columns.ORDEM]),
        Columns.OFICINA: str(row[Columns.OFICINA]),
        Columns.QTD: int(row[Columns.QTD]),
        Columns.MINUTOS: float(row[Columns.MINUTOS]),
        Columns.ENVIO: _envio_iso(row[Columns.ENVIO]),
        Columns.MP: str(row[Columns.MP]),
        Columns.PDV: str(row[Columns.PDV]),
        Columns.FRETE: str(row[Columns.FRETE]),
        Columns.SITUACAO: str(row[Columns.SITUACAO]),
    }


def insert_bulk_records(df_raw: pd.DataFrame, client=None) -> int:
    """
    Insere na tabela ``Envios_Radar`` apenas os envios ainda não existentes
    (dedup por ``row_hash``). Retorna o número de linhas novas inseridas.

    `client`: injeção de dependência opcional (testes). Em produção fica None e
    a conexão real é obtida sob demanda.
    """
    df = prepare_dataframe_for_insert(df_raw)

    client = client or get_supabase_client()
    try:
        existentes = fetch_all_rows(client, SUPABASE_TABLE_ENVIOS, columns=Columns.ROW_HASH)
        hashes_existentes = {str(r[Columns.ROW_HASH]) for r in existentes}

        # Remove os já existentes no banco e eventuais repetições no próprio lote.
        df_novos = df[~df[Columns.ROW_HASH].isin(hashes_existentes)]
        df_novos = df_novos.drop_duplicates(subset=[Columns.ROW_HASH])

        if df_novos.empty:
            return 0

        payload = [_row_to_payload(row) for _, row in df_novos.iterrows()]
        for i in range(0, len(payload), _BULK_INSERT_BATCH_SIZE):
            client.table(SUPABASE_TABLE_ENVIOS).insert(
                payload[i : i + _BULK_INSERT_BATCH_SIZE]
            ).execute()

        return len(df_novos)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Erro ao importar envios para o Supabase: {exc}") from exc
