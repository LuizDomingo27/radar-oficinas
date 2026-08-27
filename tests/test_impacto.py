"""Testes do motor de impacto (Fase 4) — janelas anuais e dif-em-dif."""

import unittest

from app_oficinas.services import impacto


def prod(oid, ano, pecas, minutos):
    return {"oficina_id": oid, "ano": ano, "mes": 1,
            "pecas": pecas, "minutos": minutos}


def absen(oid, ano, efet, trab, contr=0.0, demi=0.0):
    return {"oficina_id": oid, "ano": ano, "mes": 1, "qtd_efetivos": efet,
            "qtd_trabalhados": trab, "contratacao": contr, "demissao": demi}


def efic(oid, ano, pct, semana="WK1"):
    return {"oficina_id": oid, "ano": ano, "semana": semana,
            "base": "pecas_100", "mp": "JEANS", "eficiencia_pct": pct}


def treino(oid, modulo, ano):
    return {"oficina_id": oid, "modulo": modulo, "ano": ano}


class TestRollupAnual(unittest.TestCase):
    def test_produtividade_soma_pecas_e_minutos_por_ano(self):
        s = impacto.anual_produtividade(
            [prod("of", 2025, 100, 1000), prod("of", 2025, 50, 500),
             prod("of", 2026, 200, 1000)]
        )
        self.assertEqual(s["of"][2025], {"pecas": 150.0, "minutos": 1500.0})
        self.assertEqual(s["of"][2026], {"pecas": 200.0, "minutos": 1000.0})

    def test_absenteismo_agrega_efetivos_trabalhados(self):
        s = impacto.anual_absenteismo(
            [absen("of", 2024, 100, 90, contr=2, demi=1),
             absen("of", 2024, 100, 80, contr=0, demi=3)]
        )
        self.assertEqual(s["of"][2024]["efet"], 200.0)
        self.assertEqual(s["of"][2024]["trab"], 170.0)
        self.assertEqual(s["of"][2024]["contr"], 2.0)
        self.assertEqual(s["of"][2024]["demi"], 4.0)

    def test_eficiencia_ignora_pct_nulo(self):
        s = impacto.anual_eficiencia(
            [efic("of", 2026, 0.9), efic("of", 2026, 0.7),
             {"oficina_id": "of", "ano": 2026, "eficiencia_pct": None}]
        )
        self.assertEqual(s["of"][2026], {"soma": 1.6, "n": 2})


class TestJanelaPrePos(unittest.TestCase):
    def _series(self, prod_l=(), abs_l=(), efic_l=()):
        return impacto.montar_series(list(prod_l), list(abs_l), list(efic_l))

    def test_delta_ok_pre_e_pos_presentes(self):
        # absenteísmo 2024 (pré) 10% -> 2026 (pós) 4%; treino em 2025 é buffer.
        series = self._series(abs_l=[absen("of", 2024, 100, 90),
                                     absen("of", 2026, 100, 96)])
        linhas = impacto.impacto_por_oficina([("of", "TOC", 2025)], series)
        abs_linha = next(l for l in linhas if l["metrica"] == "absenteismo")
        self.assertEqual(abs_linha["status"], impacto.OK)
        self.assertAlmostEqual(abs_linha["pre_valor"], 0.10, places=4)
        self.assertAlmostEqual(abs_linha["pos_valor"], 0.04, places=4)
        self.assertAlmostEqual(abs_linha["delta"], -0.06, places=4)
        self.assertEqual(abs_linha["sentido"], -1)  # cair é bom

    def test_ano_do_treino_e_buffer_excluido(self):
        # dado só no ano do treino -> nem pré nem pós.
        series = self._series(abs_l=[absen("of", 2025, 100, 90)])
        linha = next(l for l in impacto.impacto_por_oficina(
            [("of", "TOC", 2025)], series) if l["metrica"] == "absenteismo")
        self.assertEqual(linha["status"], impacto.SEM_DADO)
        self.assertIsNone(linha["delta"])

    def test_sem_pre_quando_so_ha_pos(self):
        series = self._series(prod_l=[prod("of", 2026, 200, 1000)])
        linha = next(l for l in impacto.impacto_por_oficina(
            [("of", "TOC", 2025)], series) if l["metrica"] == "produtividade")
        self.assertEqual(linha["status"], impacto.SEM_PRE)
        self.assertIsNone(linha["delta"])
        self.assertEqual(linha["pos_anos"], [2026])

    def test_sem_pos_quando_so_ha_pre(self):
        series = self._series(abs_l=[absen("of", 2024, 100, 90)])
        linha = next(l for l in impacto.impacto_por_oficina(
            [("of", "TOC", 2026)], series) if l["metrica"] == "absenteismo")
        self.assertEqual(linha["status"], impacto.SEM_POS)
        self.assertEqual(linha["pre_anos"], [2024])

    def test_todas_as_metricas_geram_uma_linha(self):
        series = self._series()
        linhas = impacto.impacto_por_oficina([("of", "TOC", 2025)], series)
        self.assertEqual({l["metrica"] for l in linhas}, set(impacto.METRICAS))


class TestExtrairTreinos(unittest.TestCase):
    def test_dedup_e_descarta_ano_invalido(self):
        treinos = impacto.extrair_treinos([
            treino("of", "TOC", 2025), treino("of", "TOC", 2025),
            treino("of", "Lean", 2022),
            {"oficina_id": "of", "modulo": "X", "ano": None},  # descartado
            {"oficina_id": None, "modulo": "X", "ano": 2025},  # descartado
        ])
        self.assertEqual(treinos, [("of", "Lean", 2022), ("of", "TOC", 2025)])


class TestCoorteControle(unittest.TestCase):
    def test_dif_em_dif_treinadas_menos_controle(self):
        # Treinada melhora 6pp; controle melhora 2pp -> dif-em-dif -0.04.
        abs_l = [
            absen("trein", 2024, 100, 90), absen("trein", 2026, 100, 96),
            absen("ctrl", 2024, 100, 90), absen("ctrl", 2026, 100, 92),
        ]
        series = impacto.montar_series([], abs_l, [])
        treinos = [("trein", "TOC", 2025)]
        por_of = impacto.impacto_por_oficina(treinos, series)
        coorte = impacto.impacto_coorte(por_of, treinos, series)
        c = next(r for r in coorte if r["metrica"] == "absenteismo")
        self.assertEqual(c["n_treinadas"], 1)
        self.assertEqual(c["n_delta_treinadas"], 1)
        self.assertAlmostEqual(c["delta_medio_treinadas"], -0.06, places=4)
        self.assertEqual(c["n_controle"], 1)
        self.assertAlmostEqual(c["delta_medio_controle"], -0.02, places=4)
        self.assertAlmostEqual(c["dif_em_dif"], -0.04, places=4)
        self.assertEqual(c["status"], impacto.OK)

    def test_controle_exclui_quem_treinou_no_ano(self):
        # duas oficinas treinam no mesmo ano -> nenhuma é controle uma da outra.
        abs_l = [
            absen("a", 2024, 100, 90), absen("a", 2026, 100, 95),
            absen("b", 2024, 100, 90), absen("b", 2026, 100, 95),
        ]
        series = impacto.montar_series([], abs_l, [])
        treinos = [("a", "TOC", 2025), ("b", "TOC", 2025)]
        por_of = impacto.impacto_por_oficina(treinos, series)
        coorte = impacto.impacto_coorte(por_of, treinos, series)
        c = next(r for r in coorte if r["metrica"] == "absenteismo")
        self.assertEqual(c["n_controle"], 0)
        self.assertIsNone(c["delta_medio_controle"])
        self.assertIsNone(c["dif_em_dif"])

    def test_coorte_sem_delta_reporta_motivo(self):
        # só há pós -> coorte sem Δ médio, status = sem_pre.
        series = impacto.montar_series([prod("of", 2026, 200, 1000)], [], [])
        treinos = [("of", "TOC", 2025)]
        por_of = impacto.impacto_por_oficina(treinos, series)
        coorte = impacto.impacto_coorte(por_of, treinos, series)
        c = next(r for r in coorte if r["metrica"] == "produtividade")
        self.assertIsNone(c["delta_medio_treinadas"])
        self.assertEqual(c["status"], impacto.SEM_PRE)


if __name__ == "__main__":
    unittest.main()
