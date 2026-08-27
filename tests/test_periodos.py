"""Testes da normalização de período (Fase 2)."""

import unittest
from datetime import date, datetime

from app_oficinas.services import periodos


class TestParaData(unittest.TestCase):
    def test_datetime_vira_date(self):
        self.assertEqual(periodos.para_data(datetime(2026, 1, 2, 9, 30)), date(2026, 1, 2))

    def test_string_iso(self):
        self.assertEqual(periodos.para_data("2024-01-10 00:00:00"), date(2024, 1, 10))

    def test_invalidos_viram_none(self):
        for v in (None, "", "sem data", 42):
            self.assertIsNone(periodos.para_data(v))


class TestPeriodoDeData(unittest.TestCase):
    def test_deriva_ano_mes_semana_iso(self):
        p = periodos.periodo_de_data(datetime(2026, 1, 2), rotulo_semana="2")
        self.assertEqual((p.ano, p.mes, p.semana_iso, p.rotulo_semana), (2026, 1, 1, "2"))

    def test_sem_data_retorna_none(self):
        self.assertIsNone(periodos.periodo_de_data("xx"))

    def test_rotulo_vazio_vira_none(self):
        p = periodos.periodo_de_data(date(2025, 8, 1), rotulo_semana="  ")
        self.assertIsNone(p.rotulo_semana)


class TestCiclo(unittest.TestCase):
    def test_intervalo_usa_ano_final(self):
        self.assertEqual(periodos.ano_do_ciclo("2021/2022"), 2022)

    def test_ano_unico(self):
        self.assertEqual(periodos.ano_do_ciclo("2025"), 2025)

    def test_sem_ano(self):
        self.assertIsNone(periodos.ano_do_ciclo("sem ano"))
        self.assertIsNone(periodos.ano_do_ciclo(None))

    def test_periodo_de_ciclo(self):
        p = periodos.periodo_de_ciclo("2023/2024")
        self.assertEqual(p.ano, 2024)
        self.assertIsNone(p.mes)


if __name__ == "__main__":
    unittest.main()
