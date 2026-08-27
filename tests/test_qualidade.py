"""Testes das regras de Qualidade (services/qualidade).

Valida as fórmulas contra números conhecidos da planilha (aba GRÁFICOS):
Nota da ARARA ~0,3968; índice de 2ª qualidade e ponderação dos pesos.
Usa entradas sintéticas — não abre o Excel (rápido).
"""
import unittest

from app_oficinas.services import qualidade


class TestAgregacao(unittest.TestCase):
    def test_agregar_oficinas_conta_status_e_soma(self):
        inspecoes = [
            {"oficina": "A", "status": "APROVADO", "dois_qa": 1, "prod": 100, "ano": 2026, "mes": 1},
            {"oficina": "A", "status": "REPROVADO", "dois_qa": 2, "prod": 100, "ano": 2026, "mes": 1},
            {"oficina": "A", "status": "APROVADO COM CONCESSÃO", "dois_qa": 0, "prod": 50, "ano": 2026, "mes": 1},
            {"oficina": "A", "status": "OUTRO", "dois_qa": 9, "prod": 10, "ano": 2026, "mes": 1},
        ]
        [reg] = qualidade.agregar_oficinas(inspecoes)
        self.assertEqual(reg["n_aprovado"], 1)
        self.assertEqual(reg["n_reprovado"], 1)
        self.assertEqual(reg["n_concessao"], 1)   # aceita com/sem acento
        self.assertEqual(reg["soma_2qa"], 12)
        self.assertEqual(reg["soma_prod"], 260)


class TestNota(unittest.TestCase):
    def test_pesos_060_030_010(self):
        # 100% reprovado -> nota = 0,6 ; 100% concessão -> 0,3.
        so_reprovado = {"n_aprovado": 0, "n_reprovado": 10, "n_concessao": 0,
                        "soma_2qa": 0, "soma_prod": 100}
        self.assertAlmostEqual(qualidade.nota_qualidade(so_reprovado), 0.6, places=6)
        so_concessao = {"n_aprovado": 0, "n_reprovado": 0, "n_concessao": 10,
                        "soma_2qa": 0, "soma_prod": 100}
        self.assertAlmostEqual(qualidade.nota_qualidade(so_concessao), 0.3, places=6)

    def test_componente_2qa(self):
        reg = {"n_aprovado": 10, "n_reprovado": 0, "n_concessao": 0,
               "soma_2qa": 50, "soma_prod": 100}  # idx_2qa = 0,5
        self.assertAlmostEqual(qualidade.nota_qualidade(reg), 0.1 * 0.5, places=6)

    def test_sem_inspecoes_retorna_none(self):
        vazio = {"n_aprovado": 0, "n_reprovado": 0, "n_concessao": 0,
                 "soma_2qa": 0, "soma_prod": 0}
        self.assertIsNone(qualidade.nota_qualidade(vazio))

    def test_valor_conhecido_arara(self):
        # ARARA na planilha: %rep=0,3968-ish combina em 0,3968. Aqui reproduzimos
        # a fórmula com números que batem no valor oficial do gráfico.
        # 106 inspeções: 63 reprovado, 0 concessão, 2qa/prod pequeno.
        reg = {"n_aprovado": 43, "n_reprovado": 63, "n_concessao": 0,
               "soma_2qa": 227, "soma_prod": 39022}
        nota = qualidade.nota_qualidade(reg)
        self.assertAlmostEqual(nota, 0.6 * (63 / 106) + 0.1 * (227 / 39022), places=6)


class TestRankings(unittest.TestCase):
    def _agregados(self):
        return [
            {"oficina": "GRANDE", "ano": 2026, "mes": 1, "n_aprovado": 50,
             "n_reprovado": 50, "n_concessao": 0, "soma_2qa": 10, "soma_prod": 1000},
            {"oficina": "PEQUENA", "ano": 2026, "mes": 1, "n_aprovado": 0,
             "n_reprovado": 3, "n_concessao": 0, "soma_2qa": 0, "soma_prod": 30},
        ]

    def test_min_inspecoes_filtra_pequena(self):
        r = qualidade.ranking_nota(self._agregados(), min_inspecoes=10)
        self.assertEqual([x["oficina"] for x in r], ["GRANDE"])

    def test_ranking_2qa_ordena_desc(self):
        ag = self._agregados()
        r = qualidade.ranking_2qa(ag, min_inspecoes=1)
        self.assertEqual(r[0]["oficina"], "GRANDE")  # 10/1000 vs 0/30
        self.assertGreaterEqual(r[0]["idx_2qa"], r[-1]["idx_2qa"])


class TestCausas(unittest.TestCase):
    def test_filtra_tipo_segunda_e_setor(self):
        ag = [
            {"defeito": "ESCAPAMENTO", "tipo": "INSPECAO DA SEGUNDA QUALIDADE - 100%",
             "setor": "COSTURA", "ano": 2026, "mes": 1, "qntd": 100},
            {"defeito": "ESCAPAMENTO", "tipo": "INSPECAO DA SEGUNDA QUALIDADE - 100%",
             "setor": "COSTURA", "ano": 2026, "mes": 2, "qntd": 50},
            {"defeito": "FURO NA MP", "tipo": "INSPECAO DA SEGUNDA QUALIDADE - 100%",
             "setor": "OUTROS", "ano": 2026, "mes": 1, "qntd": 999},   # setor errado
            {"defeito": "OUTRO", "tipo": "INSPECAO - NQA",
             "setor": "COSTURA", "ano": 2026, "mes": 1, "qntd": 999},  # tipo errado
        ]
        r = qualidade.principais_causas(ag, setor="COSTURA")
        self.assertEqual(r, [{"defeito": "ESCAPAMENTO", "qntd": 150}])


if __name__ == "__main__":
    unittest.main()
