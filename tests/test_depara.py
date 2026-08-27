"""Testes da construção do De-Para (agrupamento e sinalização de revisão)."""

import unittest

from app_oficinas import config
from app_oficinas.domain.models import VarianteNome
from app_oficinas.services import depara


def variante(base, fonte="recebimento", papel=config.PAPEL_PRODUCAO,
             cru=None, unidade=None):
    return VarianteNome(
        nome_cru=cru or base, nome_base=base, unidade=unidade,
        fonte=fonte, papel=papel,
    )


class TestAgrupamentoPorBase(unittest.TestCase):
    def test_mesma_base_vira_uma_oficina(self):
        ofs = depara.construir_depara([
            variante("ACAUE CONFECCOES", cru="Acauê Confecções POLO", unidade="POLO"),
            variante("ACAUE CONFECCOES", fonte="postos",
                     papel=config.PAPEL_ABSENTEISMO, cru="ACAUE CONFECCOES LTDA"),
        ])
        self.assertEqual(len(ofs), 1)
        self.assertEqual(ofs[0].papeis, {config.PAPEL_PRODUCAO, config.PAPEL_ABSENTEISMO})
        self.assertEqual(ofs[0].fontes, {"recebimento", "postos"})

    def test_ids_unicos(self):
        ofs = depara.construir_depara([
            variante("ALFA"), variante("BETA"), variante("GAMA"),
        ])
        ids = [o.oficina_id for o in ofs]
        self.assertEqual(len(ids), len(set(ids)))


class TestAgrupamentoSoNome(unittest.TestCase):
    def test_bases_distintas_nao_fundem(self):
        # Sem CNPJ no agrupamento: nomes-base diferentes ficam separados.
        ofs = depara.construir_depara([
            variante("F L AZEVEDO", cru="F & L Azevedo Matriz"),
            variante("FEL AZEVEDO CONFECCAO", cru="Fel Azevedo Confecção"),
        ])
        self.assertEqual(len(ofs), 2)

    def test_mesma_base_grafias_diferentes_fundem(self):
        ofs = depara.construir_depara([
            variante("EBENEZER", cru="Ebenezer Industria Textil LTDA"),
            variante("EBENEZER", cru="EBENEZER LTDA", fonte="postos",
                     papel=config.PAPEL_ABSENTEISMO),
        ])
        self.assertEqual(len(ofs), 1)
        self.assertEqual(len(ofs[0].variantes), 2)


class TestNomeDeExibicao(unittest.TestCase):
    def test_grafia_de_postos_vira_o_padrao(self):
        # Mesmo minoritária, a grafia de postos é a escolhida.
        ofs = depara.construir_depara([
            variante("ACAUE CONFECCOES", cru="Acauê Confecções POLO", unidade="POLO"),
            variante("ACAUE CONFECCOES", cru="Acauê Confecções CARGO", unidade="CARGO"),
            variante("ACAUE CONFECCOES", fonte="postos",
                     papel=config.PAPEL_ABSENTEISMO, cru="ACAUE CONFECCOES LTDA"),
        ])
        self.assertEqual(len(ofs), 1)
        self.assertEqual(ofs[0].nome_canonico, "ACAUE CONFECCOES LTDA")

    def test_sem_postos_usa_mais_frequente(self):
        ofs = depara.construir_depara([
            variante("BETA", cru="Beta Textil"),
            variante("BETA", cru="Beta Textil"),
            variante("BETA", fonte="estoque_jeans",
                     papel=config.PAPEL_EFICIENCIA, cru="BETA TEXTIL LTDA"),
        ])
        self.assertEqual(ofs[0].nome_canonico, "Beta Textil")


class TestSinalizacaoDuplicata(unittest.TestCase):
    def test_bases_muito_parecidas_sao_sinalizadas(self):
        ofs = depara.construir_depara([
            variante("CONFECCOES JS"),
            variante("CONFECCOES J S"),
        ])
        # Sem CNPJ para unir; ficam separadas mas sinalizadas mutuamente.
        self.assertEqual(len(ofs), 2)
        self.assertTrue(all(o.precisa_revisao for o in ofs))

    def test_bases_distintas_nao_sinalizam(self):
        ofs = depara.construir_depara([variante("ALFA TEXTIL"), variante("ZEBRA MALHAS")])
        self.assertFalse(any(o.precisa_revisao for o in ofs))


class TestResumo(unittest.TestCase):
    def test_contagens_por_papel(self):
        ofs = depara.construir_depara([
            variante("ALFA", papel=config.PAPEL_PRODUCAO),
            variante("ALFA", fonte="postos", papel=config.PAPEL_ABSENTEISMO),
            variante("ALFA", fonte="estoque_jeans", papel=config.PAPEL_EFICIENCIA),
            variante("BETA", papel=config.PAPEL_PRODUCAO),
        ])
        r = depara.resumo(ofs)
        self.assertEqual(r["oficinas"], 2)
        self.assertEqual(r["com_producao"], 2)
        self.assertEqual(r["com_absenteismo"], 1)
        self.assertEqual(r["cobertura_3_metricas"], 1)


if __name__ == "__main__":
    unittest.main()
