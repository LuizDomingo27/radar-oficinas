"""Testes de app_envios.services.data_writer — deduplicação por row_hash."""
from __future__ import annotations

import pandas as pd

from app_envios.core.config import Columns, RawColumns, DB_TABLE_ENVIOS
from app_envios.services.data_writer import insert_bulk_records, prepare_dataframe_for_insert
from tests.postos.fakes import FakeNeonClient


def _raw_df(rows: list[dict]) -> pd.DataFrame:
    base = []
    for r in rows:
        base.append({
            RawColumns.ORIGEM: r.get("origem", "JEANS"),
            RawColumns.ORDEM: r["ordem"],
            RawColumns.OFICINA: r["oficina"],
            RawColumns.QTD: r.get("qtd", 100),
            RawColumns.MINUTOS: r.get("minutos", 1000.0),
            RawColumns.ENVIO: r.get("envio", "2026-01-02"),
            RawColumns.MP: r.get("mp", "JEANS"),
            RawColumns.PDV: r.get("pdv", "NAO_PDV"),
            RawColumns.FRETE: r.get("frete", "R.A"),
            RawColumns.SITUACAO: r.get("situacao", "Enviado"),
        })
    return pd.DataFrame(base)


def test_prepare_gera_row_hash_unico_por_linha():
    df = prepare_dataframe_for_insert(_raw_df([
        {"ordem": "1", "oficina": "A"},
        {"ordem": "2", "oficina": "B"},
    ]))
    assert df[Columns.ROW_HASH].nunique() == 2


def test_linhas_identicas_preservadas_por_ocorrencia():
    df = prepare_dataframe_for_insert(_raw_df([
        {"ordem": "1", "oficina": "A"},
        {"ordem": "1", "oficina": "A"},  # idêntica
    ]))
    # Duas linhas idênticas geram hashes diferentes (occurrence 0 e 1).
    assert df[Columns.ROW_HASH].nunique() == 2


def test_insert_conta_novos_e_ignora_existentes():
    client = FakeNeonClient({DB_TABLE_ENVIOS: []})
    df = _raw_df([{"ordem": "1", "oficina": "A"}, {"ordem": "2", "oficina": "B"}])

    inseridos = insert_bulk_records(df, client=client)
    assert inseridos == 2
    assert len(client.rows(DB_TABLE_ENVIOS)) == 2

    # Re-subir a MESMA planilha não insere nada (idempotente).
    inseridos2 = insert_bulk_records(df, client=client)
    assert inseridos2 == 0
    assert len(client.rows(DB_TABLE_ENVIOS)) == 2


def test_insert_apenas_linhas_novas_no_reupload():
    client = FakeNeonClient({DB_TABLE_ENVIOS: []})
    insert_bulk_records(_raw_df([{"ordem": "1", "oficina": "A"}]), client=client)

    # Segundo arquivo: uma repetida + uma nova → só a nova entra.
    novos = insert_bulk_records(
        _raw_df([{"ordem": "1", "oficina": "A"}, {"ordem": "3", "oficina": "C"}]),
        client=client,
    )
    assert novos == 1
    assert len(client.rows(DB_TABLE_ENVIOS)) == 2


def test_insert_preserva_duas_linhas_identicas_na_carga():
    client = FakeNeonClient({DB_TABLE_ENVIOS: []})
    novos = insert_bulk_records(
        _raw_df([{"ordem": "9", "oficina": "Z"}, {"ordem": "9", "oficina": "Z"}]),
        client=client,
    )
    assert novos == 2
