from __future__ import annotations

import unittest

from app_postos.core.config import Columns, SUPABASE_TABLE_POSTOS
from app_postos.services.data_writer import check_record_exists, insert_record
from tests.postos.fakes import FakeSupabaseClient


def _row(rid: int, oficina="MARIA", mp="ALGODAO", semana=35, data="2026-08-24") -> dict:
    return {
        "id": rid,
        Columns.OFICINA: oficina,
        Columns.MP: mp,
        Columns.SEMANA: semana,
        Columns.DATA_EFETIVOS: data,
    }


def _client(rows=None) -> FakeSupabaseClient:
    return FakeSupabaseClient({SUPABASE_TABLE_POSTOS: rows or []})


class _BoomClient:
    """Client que falha em qualquer acesso — simula queda de conexão."""

    def table(self, *_args, **_kwargs):
        raise ConnectionError("sem rede")


class CheckRecordExistsTests(unittest.TestCase):
    def test_true_when_same_oficina_mp_week_year(self) -> None:
        client = _client([_row(1)])
        self.assertTrue(check_record_exists("MARIA", "ALGODAO", 35, "2026-08-24", client=client))

    def test_false_when_week_differs(self) -> None:
        client = _client([_row(1, semana=35)])
        self.assertFalse(check_record_exists("MARIA", "ALGODAO", 36, "2026-08-24", client=client))

    def test_false_when_mp_differs(self) -> None:
        client = _client([_row(1, mp="ALGODAO")])
        self.assertFalse(check_record_exists("MARIA", "POLIESTER", 35, "2026-08-24", client=client))

    def test_false_when_same_week_but_different_year(self) -> None:
        # O ano faz parte da chave: Semana 35/2025 não colide com Semana 35/2026.
        client = _client([_row(1, data="2025-08-25")])
        self.assertFalse(check_record_exists("MARIA", "ALGODAO", 35, "2026-08-24", client=client))

    def test_true_when_same_week_and_year_but_different_day(self) -> None:
        # Independe do dia dentro da mesma semana/ano (regra do formulário manual).
        client = _client([_row(1, data="2026-08-24")])
        self.assertTrue(check_record_exists("MARIA", "ALGODAO", 35, "2026-08-28", client=client))

    def test_normalizes_mp_uppercase_and_trims(self) -> None:
        client = _client([_row(1, oficina="MARIA", mp="ALGODAO")])
        self.assertTrue(check_record_exists(" MARIA ", " algodao ", 35, "2026-08-24", client=client))

    def test_exclude_id_ignores_the_record_being_edited(self) -> None:
        client = _client([_row(1)])
        self.assertFalse(
            check_record_exists("MARIA", "ALGODAO", 35, "2026-08-24", exclude_id=1, client=client)
        )

    def test_exclude_id_still_detects_other_duplicate(self) -> None:
        client = _client([_row(1), _row(2)])
        self.assertTrue(
            check_record_exists("MARIA", "ALGODAO", 35, "2026-08-24", exclude_id=1, client=client)
        )

    def test_wraps_backend_error_in_runtime_error(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "verificar"):
            check_record_exists("MARIA", "ALGODAO", 35, "2026-08-24", client=_BoomClient())


class InsertRecordTests(unittest.TestCase):
    def test_inserts_sanitized_payload(self) -> None:
        client = _client([])
        insert_record(
            frete=" Rapido ", mp="algodao", oficina=" Maria ",
            data_efetivos="2026-08-24", qtd_efetivos=10,
            data_trabalhados="2026-08-24", qtd_trabalhados=9,
            contratacoes=1, demissoes=0, semana=35, client=client,
        )
        rows = client.rows(SUPABASE_TABLE_POSTOS)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][Columns.MP], "ALGODAO")
        self.assertEqual(rows[0][Columns.OFICINA], "Maria")
        self.assertEqual(rows[0][Columns.FRETE], "Rapido")
        self.assertEqual(rows[0][Columns.SEMANA], 35)

    def test_wraps_backend_error_in_runtime_error(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "inserir"):
            insert_record(
                frete="R", mp="M", oficina="O", data_efetivos="2026-08-24",
                qtd_efetivos=1, data_trabalhados="2026-08-24", qtd_trabalhados=1,
                contratacoes=0, demissoes=0, semana=35, client=_BoomClient(),
            )


if __name__ == "__main__":
    unittest.main()
