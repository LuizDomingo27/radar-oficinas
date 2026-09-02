"""Testes do serviço de explicação por oficina (Fase 6)."""

import unittest

from app_oficinas.services import explicacao

FAIXAS = {"eficiencia": [0.65, 0.55], "absenteismo": [0.05, 0.10]}


class TestFormatacao(unittest.TestCase):
    def test_pct_uma_casa_virgula(self):
        self.assertEqual(explicacao._fmt_pct(0.7759), "77,6%")

    def test_num_milhar_ptbr_inteiro(self):
        self.assertEqual(explicacao._fmt_num(4975.0), "4.975")

    def test_num_milhar_ptbr_decimal(self):
        self.assertEqual(explicacao._fmt_num(1474.2), "1.474,2")


class TestPorque(unittest.TestCase):
    def test_eficiencia_ok_cita_meta(self):
        txt = explicacao._porque_eficiencia(0.7759, "ok", FAIXAS["eficiencia"])
        self.assertIn("≥ 65,0%", txt)
        self.assertIn("77,6%", txt)

    def test_absenteismo_alerta(self):
        txt = explicacao._porque_absenteismo(0.0644, "alerta", FAIXAS["absenteismo"])
        self.assertIn("alerta", txt.lower())
        self.assertIn("6,4%", txt)

    def test_absenteismo_critico(self):
        txt = explicacao._porque_absenteismo(0.20, "critico", FAIXAS["absenteismo"])
        self.assertIn("crítico", txt.lower())


class TestExplicarOficina(unittest.TestCase):
    def _oficina(self):
        return {
            "oficina_id": "of1",
            "nome": "OFICINA TESTE",
            "papeis": ["eficiencia", "absenteismo", "producao"],
            "ranking": {
                "eficiencia": {"valor": 0.7759, "ano": 2026, "n": 1, "semaforo": "ok"},
                "absenteismo": {"valor": 0.0644, "ano": 2026, "n": 6,
                                "semaforo": "alerta"},
                "pecas_mes": {"valor": 4975.5, "ano": 2026, "n": 8},
                "pecas_mes_total": {"valor": 5290.0, "ano": 2026, "periodo": "2026-08"},
            },
            "treinos": [{"modulo": "Lidera+", "ano": 2026, "ciclo": None}],
        }

    def test_ordem_e_conteudo(self):
        r = explicacao.explicar_oficina(self._oficina(), FAIXAS)
        chaves = [m["chave"] for m in r["metricas"]]
        self.assertEqual(chaves, ["eficiencia", "absenteismo", "pecas_mes",
                                  "pecas_mes_total"])

    def test_valor_percentual_e_semaforo(self):
        r = explicacao.explicar_oficina(self._oficina(), FAIXAS)
        efic = next(m for m in r["metricas"] if m["chave"] == "eficiencia")
        self.assertEqual(efic["valor"], "77,6%")
        self.assertEqual(efic["semaforo_txt"], "OK")

    def test_volume_sem_semaforo(self):
        r = explicacao.explicar_oficina(self._oficina(), FAIXAS)
        vol = next(m for m in r["metricas"] if m["chave"] == "pecas_mes")
        self.assertIsNone(vol["semaforo"])
        self.assertIn("peças", vol["valor"])
        self.assertIn("8 meses de 2026", vol["como"])

    def test_como_usa_periodo_quando_sem_n(self):
        r = explicacao.explicar_oficina(self._oficina(), FAIXAS)
        tot = next(m for m in r["metricas"] if m["chave"] == "pecas_mes_total")
        self.assertIn("2026-08", tot["como"])

    def test_lista_metricas_sem_dado(self):
        of = self._oficina()
        del of["ranking"]["absenteismo"]
        r = explicacao.explicar_oficina(of, FAIXAS)
        self.assertIn("Absenteísmo", r["sem_dado"])

    def test_oficina_sem_ranking_nao_quebra(self):
        r = explicacao.explicar_oficina(
            {"oficina_id": "x", "nome": "VAZIA", "papeis": [], "ranking": {},
             "treinos": []}, FAIXAS)
        self.assertEqual(r["metricas"], [])
        self.assertEqual(len(r["sem_dado"]), 3)


class TestExplicarTodas(unittest.TestCase):
    def test_ordena_por_nome(self):
        ofs = [{"nome": "ZETA", "ranking": {}, "treinos": []},
               {"nome": "alfa", "ranking": {}, "treinos": []}]
        r = explicacao.explicar_todas(ofs, FAIXAS)
        self.assertEqual([o["nome"] for o in r], ["alfa", "ZETA"])


if __name__ == "__main__":
    unittest.main()
