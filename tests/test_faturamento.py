"""Testes da consolidação do faturamento (tela de Faturamento)."""

import unittest
from datetime import date, datetime

from app_oficinas.errors import FonteInvalida
from app_oficinas.services import faturamento


def _reg(nome, data, valor):
    return {"nome": nome, "data": data, "valor": valor}


class TestConsolidar(unittest.TestCase):
    def setUp(self):
        # Dois meses, duas oficinas, semanas variadas. Datas cobrem semana 1
        # (dia 3), semana 2 (dia 10) e semana 5 (dia 31).
        self.registros = [
            _reg("OFICINA A", datetime(2025, 1, 3), 100.0),
            _reg("OFICINA A", datetime(2025, 1, 10), 50.0),
            _reg("OFICINA B", datetime(2025, 1, 31), 200.0),
            _reg("OFICINA A", datetime(2025, 2, 5), 30.0),
            _reg("OFICINA B", datetime(2026, 3, 3), 400.0),
        ]

    def test_meses_agregados_e_ordenados(self):
        p = faturamento.consolidar(self.registros)
        self.assertEqual(p["anos"], [2025, 2026])
        self.assertEqual(
            p["meses"],
            [
                {"ano": 2025, "mes": 1, "total": 350.0},
                {"ano": 2025, "mes": 2, "total": 30.0},
                {"ano": 2026, "mes": 3, "total": 400.0},
            ],
        )

    def test_semana_do_mes_por_bloco_de_7_dias(self):
        p = faturamento.consolidar(self.registros)
        jan = [s for s in p["semanas"] if s["ano"] == 2025 and s["mes"] == 1]
        # dia 3 -> semana 1; dia 10 -> semana 2; dia 31 -> semana 5.
        semanas = {s["semana"]: s["total"] for s in jan}
        self.assertEqual(semanas, {1: 100.0, 2: 50.0, 5: 200.0})
        s1 = next(s for s in jan if s["semana"] == 1)
        self.assertEqual((s1["ini"], s1["fim"]), ("2025-01-01", "2025-01-07"))
        s5 = next(s for s in jan if s["semana"] == 5)
        # A semana 5 de janeiro (31 dias) vai do dia 29 ao 31.
        self.assertEqual((s5["ini"], s5["fim"]), ("2025-01-29", "2025-01-31"))

    def test_oficinas_por_ano_e_total_ordenadas_desc(self):
        p = faturamento.consolidar(self.registros)
        self.assertEqual(
            p["oficinas"]["todos"],
            [
                {"nome": "OFICINA B", "total": 600.0},
                {"nome": "OFICINA A", "total": 180.0},
            ],
        )
        # Em 2025, A soma 180 e B soma 200 (B na frente).
        self.assertEqual(
            p["oficinas"]["2025"],
            [
                {"nome": "OFICINA B", "total": 200.0},
                {"nome": "OFICINA A", "total": 180.0},
            ],
        )
        self.assertEqual(p["oficinas"]["2026"], [{"nome": "OFICINA B", "total": 400.0}])

    def test_oficinas_por_mes_permite_atualizar_ranking_com_o_filtro(self):
        p = faturamento.consolidar(self.registros)
        self.assertEqual(
            p["oficinas_mes"]["2025-01"],
            [
                {"nome": "OFICINA B", "total": 200.0},
                {"nome": "OFICINA A", "total": 150.0},
            ],
        )
        self.assertEqual(
            p["oficinas_mes"]["2025-02"],
            [{"nome": "OFICINA A", "total": 30.0}],
        )

    def test_ignora_linhas_sem_data_valor_ou_nome(self):
        registros = [
            _reg("OFICINA A", datetime(2025, 1, 3), 100.0),
            _reg("OFICINA A", None, 999.0),          # sem data
            _reg("OFICINA A", datetime(2025, 1, 4), None),  # sem valor
            _reg(None, datetime(2025, 1, 5), 999.0),  # sem nome
        ]
        p = faturamento.consolidar(registros)
        self.assertEqual(p["linhas"], 1)
        self.assertEqual(p["meses"], [{"ano": 2025, "mes": 1, "total": 100.0}])

    def test_aceita_data_em_string_iso(self):
        p = faturamento.consolidar([_reg("OFICINA A", "2025-06-15", 10.0)])
        self.assertEqual(p["meses"], [{"ano": 2025, "mes": 6, "total": 10.0}])

    def test_sem_registros_validos_levanta(self):
        with self.assertRaises(FonteInvalida):
            faturamento.consolidar([])
        with self.assertRaises(FonteInvalida):
            faturamento.consolidar([_reg("OFICINA A", None, None)])

    def test_moeda_no_payload(self):
        p = faturamento.consolidar(self.registros)
        self.assertEqual(p["moeda"], "R$")


if __name__ == "__main__":
    unittest.main()
