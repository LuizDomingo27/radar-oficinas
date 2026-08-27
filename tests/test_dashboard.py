"""Testes da consolidação do dashboard (Fase 5) — ranking, série e semáforo.

Produtividade é lida como **volume**: média de peças/mês e de peças/semana por
oficina (duas métricas, sem semáforo). Eficiência e absenteísmo mantêm o
semáforo por faixa absoluta.
"""

import unittest

from app_oficinas.services import dashboard


def prod_mes(oid, ano, mes, pecas, minutos=1000):
    return {"oficina_id": oid, "ano": ano, "mes": mes,
            "pecas": pecas, "minutos": minutos,
            "pecas_por_minuto": round(pecas / minutos, 4)}


def prod_sem(oid, ano, semana, pecas, minutos=1000):
    return {"oficina_id": oid, "ano": ano, "semana": semana,
            "pecas": pecas, "minutos": minutos,
            "pecas_por_minuto": round(pecas / minutos, 4)}


def absen(oid, ano, mes, efet, trab):
    return {"oficina_id": oid, "ano": ano, "mes": mes, "qtd_efetivos": efet,
            "qtd_trabalhados": trab, "absenteismo_pct": round(1 - trab / efet, 4)}


def efic(oid, ano, pct, mp="JEANS"):
    # % oficial da planilha: um valor por oficina (sem semana).
    return {"oficina_id": oid, "ano": ano, "base": "oficial",
            "mp": mp, "eficiencia_pct": pct}


def oficina(oid, nome, papeis):
    return {"oficina_id": oid, "nome_canonico": nome, "papeis": papeis}


def treino(oid, modulo, ano, ciclo="2025"):
    return {"oficina_id": oid, "modulo": modulo, "ano": ano, "ciclo": ciclo}


class TestRankingVolume(unittest.TestCase):
    def test_pecas_mes_e_media_do_ano_mais_recente(self):
        ofs = dashboard.montar_oficinas(
            [oficina("of", "OF", ["producao"])],
            [prod_mes("of", 2025, 1, 100), prod_mes("of", 2026, 1, 300),
             prod_mes("of", 2026, 2, 500)],
            [], [], [], [],
        )
        cel = ofs[0]["ranking"]["pecas_mes"]
        self.assertEqual(cel["ano"], 2026)
        # média das peças/mês do ano 2026 = (300 + 500) / 2 = 400
        self.assertEqual(cel["valor"], 400.0)
        self.assertEqual(cel["n"], 2)

    def test_pecas_semana_e_media_por_semana(self):
        ofs = dashboard.montar_oficinas(
            [oficina("of", "OF", ["producao"])],
            [], [prod_sem("of", 2026, 1, 200), prod_sem("of", 2026, 2, 400)],
            [], [], [],
        )
        cel = ofs[0]["ranking"]["pecas_semana"]
        self.assertEqual(cel["valor"], 300.0)
        self.assertEqual(cel["n"], 2)

    def test_pecas_mes_total_e_do_mes_mais_recente(self):
        # Total = volume do mês mais recente com dado (não a média).
        ofs = dashboard.montar_oficinas(
            [oficina("of", "OF", ["producao"])],
            [prod_mes("of", 2026, 1, 300), prod_mes("of", 2026, 2, 500)],
            [], [], [], [],
        )
        cel = ofs[0]["ranking"]["pecas_mes_total"]
        self.assertEqual(cel["valor"], 500.0)      # mês 2 é o mais recente
        self.assertEqual(cel["periodo"], "2026-02")
        self.assertNotIn("semaforo", cel)          # volume não tem semáforo

    def test_pecas_semana_total_e_da_semana_mais_recente(self):
        ofs = dashboard.montar_oficinas(
            [oficina("of", "OF", ["producao"])],
            [], [prod_sem("of", 2026, 1, 200), prod_sem("of", 2026, 3, 450)],
            [], [], [],
        )
        cel = ofs[0]["ranking"]["pecas_semana_total"]
        self.assertEqual(cel["valor"], 450.0)      # semana 3 é a mais recente
        self.assertEqual(cel["periodo"], "2026-W03")

    def test_absenteismo_e_razao_agregada(self):
        ofs = dashboard.montar_oficinas(
            [oficina("of", "OF", ["absenteismo"])],
            [], [], [absen("of", 2024, 1, 100, 90), absen("of", 2024, 2, 100, 80)],
            [], [],
        )
        cel = ofs[0]["ranking"]["absenteismo"]
        # 1 - (90+80)/(100+100) = 1 - 0.85 = 0.15
        self.assertEqual(cel["valor"], 0.15)

    def test_eficiencia_e_a_pct_oficial(self):
        ofs = dashboard.montar_oficinas(
            [oficina("of", "OF", ["eficiencia"])],
            [], [], [], [efic("of", 2026, 0.7921)], [],
        )
        cel = ofs[0]["ranking"]["eficiencia"]
        self.assertEqual(cel["valor"], 0.7921)


class TestSemaforo(unittest.TestCase):
    def test_eficiencia_absoluta_meta_65(self):
        self.assertEqual(dashboard._semaforo_absoluto("eficiencia", 0.70), "ok")
        self.assertEqual(dashboard._semaforo_absoluto("eficiencia", 0.60), "alerta")
        self.assertEqual(dashboard._semaforo_absoluto("eficiencia", 0.40), "critico")

    def test_absenteismo_menor_e_melhor(self):
        self.assertEqual(dashboard._semaforo_absoluto("absenteismo", 0.03), "ok")
        self.assertEqual(dashboard._semaforo_absoluto("absenteismo", 0.08), "alerta")
        self.assertEqual(dashboard._semaforo_absoluto("absenteismo", 0.15), "critico")

    def test_volume_nao_tem_semaforo(self):
        # Peças/mês e peças/semana são volume — não levam semáforo (não é meta).
        ofs = dashboard.montar_oficinas(
            [oficina("of", "OF", ["producao"])],
            [prod_mes("of", 2026, 1, 100)], [prod_sem("of", 2026, 1, 100)],
            [], [], [],
        )
        self.assertNotIn("semaforo", ofs[0]["ranking"]["pecas_mes"])
        self.assertNotIn("semaforo", ofs[0]["ranking"]["pecas_semana"])


class TestSeriesETreinos(unittest.TestCase):
    def test_serie_mensal_de_pecas_ordenada(self):
        ofs = dashboard.montar_oficinas(
            [oficina("of", "OF", ["producao"])],
            [prod_mes("of", 2026, 3, 150), prod_mes("of", 2026, 1, 100)],
            [], [], [], [],
        )
        serie = ofs[0]["series"]["pecas_mes"]
        self.assertEqual([p["periodo"] for p in serie], ["2026-01", "2026-03"])
        self.assertEqual([p["valor"] for p in serie], [100.0, 150.0])

    def test_serie_semanal_de_pecas_ordenada(self):
        ofs = dashboard.montar_oficinas(
            [oficina("of", "OF", ["producao"])],
            [], [prod_sem("of", 2026, 3, 150), prod_sem("of", 2026, 1, 100)],
            [], [], [],
        )
        serie = ofs[0]["series"]["pecas_semana"]
        self.assertEqual([p["periodo"] for p in serie], ["2026-W01", "2026-W03"])
        self.assertEqual([p["valor"] for p in serie], [100.0, 150.0])

    def test_eficiencia_nao_tem_serie(self):
        # A eficiência é um valor único (KPI), não série temporal.
        ofs = dashboard.montar_oficinas(
            [oficina("of", "OF", ["eficiencia"])],
            [], [], [], [efic("of", 2026, 0.6)], [],
        )
        self.assertNotIn("eficiencia", ofs[0]["series"])

    def test_treinos_sem_duplicata_e_ordenados(self):
        ofs = dashboard.montar_oficinas(
            [oficina("of", "OF", ["treino"])],
            [], [], [], [],
            [treino("of", "TOC", 2025), treino("of", "TOC", 2025),
             treino("of", "Lean", 2022)],
        )
        treinos = ofs[0]["treinos"]
        self.assertEqual(len(treinos), 2)
        self.assertEqual([t["ano"] for t in treinos], [2022, 2025])


class TestNaoOmiteOficina(unittest.TestCase):
    def test_oficina_sem_metrica_entra_com_ranking_vazio(self):
        ofs = dashboard.montar_oficinas(
            [oficina("of", "OF", [])], [], [], [], [], [],
        )
        self.assertEqual(ofs[0]["ranking"], {})
        self.assertEqual(ofs[0]["series"]["pecas_mes"], [])
        self.assertEqual(ofs[0]["series"]["pecas_semana"], [])


if __name__ == "__main__":
    unittest.main()
