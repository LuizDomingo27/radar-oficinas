from __future__ import annotations

import unittest

from app_postos.core.config import Columns, SUPABASE_TABLE_POSTOS
from app_postos.core.record import RecordValidationError
from app_postos.services.record_service import (
    RecordDuplicateError,
    RecordNotFoundError,
    RecordServiceError,
    get_record,
    list_records,
    update_record,
)
from tests.postos.fakes import FakeSupabaseClient


def _row(rid, oficina="MARIA", mp="ALGODAO", semana=35, data="2026-08-24", qtd_efetivos=100):
    return {
        "id": rid,
        Columns.FRETE: "RAPIDO",
        Columns.OFICINA: oficina,
        Columns.MP: mp,
        Columns.SEMANA: semana,
        Columns.DATA_EFETIVOS: data,
        Columns.QTD_EFETIVOS: qtd_efetivos,
        Columns.DATA_TRABALHADOS: data,
        Columns.QTD_TRABALHADOS: 90,
        Columns.CONTRATACOES: 0,
        Columns.DEMISSOES: 0,
        "created_at": "2026-08-24T00:00:00",
    }


def _client(rows=None):
    return FakeSupabaseClient({SUPABASE_TABLE_POSTOS: rows if rows is not None else []})


def _update_kwargs(**overrides):
    base = dict(
        frete="RAPIDO", mp="ALGODAO", oficina="MARIA",
        data_efetivos="2026-08-24", qtd_efetivos=120,
        data_trabalhados="2026-08-24", qtd_trabalhados=110,
        contratacoes=1, demissoes=0, semana=35,
    )
    base.update(overrides)
    return base


class _BoomClient:
    def table(self, *_args, **_kwargs):
        raise ConnectionError("sem rede")


class _WriteBoomClient:
    """Leituras funcionam; qualquer UPDATE falha (simula queda na escrita)."""

    def __init__(self, rows):
        self._fake = FakeSupabaseClient({SUPABASE_TABLE_POSTOS: rows})

    def table(self, name):
        t = self._fake.table(name)

        def boom_update(_payload):
            raise ConnectionError("falha de escrita")

        t.update = boom_update  # type: ignore[method-assign]
        return t

    def rows(self, name):
        return self._fake.rows(name)


class ListRecordsTests(unittest.TestCase):
    def test_returns_all_rows_with_id(self) -> None:
        client = _client([_row(1), _row(2, oficina="JOAO")])
        result = list_records(client=client)
        self.assertEqual({r["id"] for r in result}, {1, 2})

    def test_wraps_backend_error(self) -> None:
        with self.assertRaises(RecordServiceError):
            list_records(client=_BoomClient())


class GetRecordTests(unittest.TestCase):
    def test_returns_matching_record(self) -> None:
        client = _client([_row(1), _row(2)])
        self.assertEqual(get_record(2, client=client)["id"], 2)

    def test_raises_not_found_for_missing_id(self) -> None:
        with self.assertRaises(RecordNotFoundError):
            get_record(999, client=_client([_row(1)]))


class UpdateRecordTests(unittest.TestCase):
    def test_overwrites_existing_record(self) -> None:
        client = _client([_row(1, qtd_efetivos=100)])
        update_record(1, client=client, **_update_kwargs(qtd_efetivos=120))
        row = client.rows(SUPABASE_TABLE_POSTOS)[0]
        self.assertEqual(row[Columns.QTD_EFETIVOS], 120)
        self.assertEqual(row[Columns.QTD_TRABALHADOS], 110)

    def test_allows_saving_same_record_without_changing_key(self) -> None:
        client = _client([_row(1)])
        update_record(1, client=client, **_update_kwargs())  # não deve levantar
        self.assertEqual(client.rows(SUPABASE_TABLE_POSTOS)[0][Columns.QTD_TRABALHADOS], 110)

    def test_blocks_when_key_collides_with_another_record(self) -> None:
        client = _client([_row(1, oficina="MARIA"), _row(2, oficina="JOAO")])
        with self.assertRaises(RecordDuplicateError):
            update_record(2, client=client, **_update_kwargs(oficina="MARIA"))

    def test_allows_same_oficina_with_different_mp(self) -> None:
        client = _client(
            [_row(1, oficina="MARIA", mp="ALGODAO"), _row(2, oficina="MARIA", mp="POLIESTER")]
        )
        update_record(
            2, client=client, **_update_kwargs(oficina="MARIA", mp="POLIESTER", qtd_efetivos=50)
        )
        self.assertEqual(client.rows(SUPABASE_TABLE_POSTOS)[1][Columns.QTD_EFETIVOS], 50)

    def test_raises_not_found_when_editing_missing_record(self) -> None:
        with self.assertRaises(RecordNotFoundError):
            update_record(999, client=_client([_row(1)]), **_update_kwargs())

    def test_rejects_invalid_input_without_writing(self) -> None:
        client = _client([_row(1)])
        with self.assertRaises(RecordValidationError):
            update_record(1, client=client, **_update_kwargs(oficina="", semana=99))
        self.assertEqual(client.rows(SUPABASE_TABLE_POSTOS)[0][Columns.OFICINA], "MARIA")

    def test_wraps_backend_error_on_write(self) -> None:
        client = _WriteBoomClient([_row(1)])
        with self.assertRaises(RecordServiceError):
            update_record(1, client=client, **_update_kwargs())


if __name__ == "__main__":
    unittest.main()
