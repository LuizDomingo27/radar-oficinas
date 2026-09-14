from __future__ import annotations

import datetime
import unittest

from app_postos.core.config import Columns
from app_postos.core.record import (
    RecordValidationError,
    build_record_payload,
    validate_record_fields,
)


def _valid_kwargs(**overrides):
    base = dict(
        oficina="  Maria Confecções  ",
        mp="algodao",
        frete="  Rápido Brasil ",
        data_efetivos="2026-08-24",
        qtd_efetivos=100,
        data_trabalhados="2026-08-24",
        qtd_trabalhados=95,
        contratacoes=2,
        demissoes=1,
        semana=35,
    )
    base.update(overrides)
    return base


class BuildRecordPayloadTests(unittest.TestCase):
    def test_sanitizes_text_fields(self) -> None:
        payload = build_record_payload(**_valid_kwargs())
        self.assertEqual(payload[Columns.OFICINA], "Maria Confecções")
        self.assertEqual(payload[Columns.MP], "ALGODAO")  # upper
        self.assertEqual(payload[Columns.FRETE], "Rápido Brasil")

    def test_casts_quantities_and_week_to_int(self) -> None:
        payload = build_record_payload(**_valid_kwargs(qtd_efetivos="100", semana="35"))
        self.assertEqual(payload[Columns.QTD_EFETIVOS], 100)
        self.assertIsInstance(payload[Columns.QTD_EFETIVOS], int)
        self.assertEqual(payload[Columns.SEMANA], 35)

    def test_accepts_date_objects_and_formats_iso(self) -> None:
        payload = build_record_payload(
            **_valid_kwargs(
                data_efetivos=datetime.date(2026, 8, 24),
                data_trabalhados=datetime.date(2026, 8, 25),
            )
        )
        self.assertEqual(payload[Columns.DATA_EFETIVOS], "2026-08-24")
        self.assertEqual(payload[Columns.DATA_TRABALHADOS], "2026-08-25")

    def test_payload_has_exactly_the_persisted_columns(self) -> None:
        payload = build_record_payload(**_valid_kwargs())
        self.assertEqual(
            set(payload.keys()),
            {
                Columns.FRETE, Columns.MP, Columns.OFICINA,
                Columns.DATA_EFETIVOS, Columns.QTD_EFETIVOS,
                Columns.DATA_TRABALHADOS, Columns.QTD_TRABALHADOS,
                Columns.CONTRATACOES, Columns.DEMISSOES, Columns.SEMANA,
            },
        )


class ValidateRecordFieldsTests(unittest.TestCase):
    def test_accepts_valid_record(self) -> None:
        validate_record_fields(**_valid_kwargs())  # não deve levantar

    def test_rejects_empty_oficina(self) -> None:
        with self.assertRaises(RecordValidationError) as ctx:
            validate_record_fields(**_valid_kwargs(oficina="   "))
        self.assertTrue(any("Oficina" in e for e in ctx.exception.errors))

    def test_rejects_empty_mp(self) -> None:
        with self.assertRaises(RecordValidationError) as ctx:
            validate_record_fields(**_valid_kwargs(mp=""))
        self.assertTrue(any("Matéria-prima" in e for e in ctx.exception.errors))

    def test_rejects_empty_frete(self) -> None:
        with self.assertRaises(RecordValidationError) as ctx:
            validate_record_fields(**_valid_kwargs(frete="  "))
        self.assertTrue(any("Frete" in e for e in ctx.exception.errors))

    def test_rejects_week_out_of_range(self) -> None:
        for bad in (0, 54, -1):
            with self.assertRaises(RecordValidationError):
                validate_record_fields(**_valid_kwargs(semana=bad))

    def test_rejects_negative_quantities(self) -> None:
        with self.assertRaises(RecordValidationError) as ctx:
            validate_record_fields(**_valid_kwargs(qtd_efetivos=-1))
        self.assertTrue(any("negativ" in e.lower() for e in ctx.exception.errors))

    def test_rejects_invalid_date(self) -> None:
        with self.assertRaises(RecordValidationError):
            validate_record_fields(**_valid_kwargs(data_efetivos="24/08/2026"))

    def test_collects_multiple_errors_at_once(self) -> None:
        with self.assertRaises(RecordValidationError) as ctx:
            validate_record_fields(**_valid_kwargs(oficina="", mp="", semana=99))
        self.assertGreaterEqual(len(ctx.exception.errors), 3)


if __name__ == "__main__":
    unittest.main()
