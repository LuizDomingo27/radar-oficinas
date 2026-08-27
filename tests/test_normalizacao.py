"""Testes da normalização de nomes, CNPJ e matéria-prima."""

import unittest

from app_oficinas.domain.models import RegistroNome
from app_oficinas.services import normalizacao as norm


class TestRemoverAcentos(unittest.TestCase):
    def test_remove_diacriticos(self):
        self.assertEqual(norm.remover_acentos("CONFECÇÕES ÁÀÃÂ"), "CONFECCOES AAAA")

    def test_texto_sem_acento_inalterado(self):
        self.assertEqual(norm.remover_acentos("ABC 123"), "ABC 123")


class TestLimpar(unittest.TestCase):
    def test_maiusculas_sem_acento_sem_pontuacao(self):
        self.assertEqual(norm.limpar("Confecções J.S. Ltda"), "CONFECCOES J S LTDA")

    def test_colapsa_espacos_e_e_comercial(self):
        self.assertEqual(norm.limpar("A  &  B"), "A B")

    def test_none_vira_vazio(self):
        self.assertEqual(norm.limpar(None), "")


class TestRuido(unittest.TestCase):
    def test_cabecalho_e_ruido(self):
        self.assertTrue(norm.eh_ruido("RAZAO SOCIAL"))
        self.assertTrue(norm.eh_ruido("DEVOLUCAO TROCA DE OFICINA"))

    def test_muito_curto_e_ruido(self):
        self.assertTrue(norm.eh_ruido("AB"))

    def test_nome_valido_nao_e_ruido(self):
        self.assertFalse(norm.eh_ruido("ACAUE CONFECCOES"))


class TestSepararBaseEUnidade(unittest.TestCase):
    def test_remove_unidade_do_fim(self):
        self.assertEqual(
            norm.separar_base_e_unidade("ACAUE CONFECCOES LTDA POLO"),
            ("ACAUE CONFECCOES", "POLO"),
        )

    def test_remove_juridico_sem_unidade(self):
        self.assertEqual(
            norm.separar_base_e_unidade("M K INDUSTRIA TEXTIL LTDA"),
            ("M K INDUSTRIA TEXTIL", None),
        )

    def test_matriz_e_unidade(self):
        base, unidade = norm.separar_base_e_unidade("F L AZEVEDO LTDA MATRIZ")
        self.assertEqual(base, "F L AZEVEDO")
        self.assertEqual(unidade, "MATRIZ")

    def test_nunca_esvazia_a_base(self):
        # Só tokens jurídicos: preserva ao menos um token.
        base, _ = norm.separar_base_e_unidade("LTDA")
        self.assertEqual(base, "LTDA")


class TestCriarVariante(unittest.TestCase):
    def _reg(self, nome):
        return RegistroNome(nome_cru=nome, fonte="f", papel="p")

    def test_variante_valida(self):
        v = norm.criar_variante(self._reg("Acauê Confecções LTDA POLO"))
        self.assertIsNotNone(v)
        self.assertEqual(v.nome_base, "ACAUE CONFECCOES")
        self.assertEqual(v.unidade, "POLO")
        self.assertEqual(v.nome_cru, "Acauê Confecções LTDA POLO")

    def test_ruido_retorna_none(self):
        self.assertIsNone(norm.criar_variante(self._reg("DEVOLUÇÃO - TROCA DE OFICINA")))

    def test_numerico_retorna_none(self):
        self.assertIsNone(norm.criar_variante(self._reg("0.94")))


class TestNormalizarMp(unittest.TestCase):
    def test_variacoes_de_caixa(self):
        self.assertEqual(norm.normalizar_mp("Malha"), "MALHA")
        self.assertEqual(norm.normalizar_mp("JEANS"), "JEANS")

    def test_desconhecido_vira_none(self):
        self.assertIsNone(norm.normalizar_mp("XPTO"))
        self.assertIsNone(norm.normalizar_mp(None))


if __name__ == "__main__":
    unittest.main()
