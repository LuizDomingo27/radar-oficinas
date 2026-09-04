"""Testes da leitura de fatos — foco na eficiência achada pelo cabeçalho."""

import unittest

from app_oficinas.errors import FonteInvalida
from app_oficinas.infra import leitor_fatos as L


class TestModuloProgramaCM(unittest.TestCase):
    def test_prefixa_programa_preservando_sufixo(self):
        self.assertEqual(
            L._modulo_programa("PRODUZA+ - MÓDULO 1", "Costura e Mecânica"),
            "Costura e Mecânica - MÓDULO 1")

    def test_sem_sufixo_usa_so_programa(self):
        self.assertEqual(
            L._modulo_programa("PRODUZA+", "Costura e Mecânica"),
            "Costura e Mecânica")

    def test_none_usa_programa(self):
        self.assertEqual(
            L._modulo_programa(None, "Costura e Mecânica"), "Costura e Mecânica")


class TestColunaEficienciaPorCabecalho(unittest.TestCase):
    def test_acha_coluna_pelo_rotulo_jeans(self):
        cab = ("Fornecedor", "Postos", "Cap Peças 100%", "WK32", "WK33",
               "Méd. últimas 4W", "% 4WK", "WK32")
        self.assertEqual(L._achar_col_efic(cab, "x.xlsx", "ESTOQUE"), 6)

    def test_acha_coluna_pelo_rotulo_naojeans(self):
        cab = ("PRODUTO", "OFICINA", "WK33", "WK34", "Méd. últimas 4W", "MÉDIA 4W")
        self.assertEqual(L._achar_col_efic(cab, "y.xlsx", "ESTOQUE OFICINAS"), 5)

    def test_ignora_acento_e_caixa(self):
        # "media 4w" (sem acento, minúsculo) ainda casa com "MÉDIA 4W".
        cab = ("OFICINA", "media 4w")
        self.assertEqual(L._achar_col_efic(cab, "y.xlsx", "aba"), 1)

    def test_pega_a_primeira_ocorrencia_pecas_antes_de_minutos(self):
        # A % de peças vem antes da de minutos; deve vencer a primeira.
        cab = ("OFICINA", "% 4WK", "Entrega Minutos", "% 4WK")
        self.assertEqual(L._achar_col_efic(cab, "x.xlsx", "aba"), 1)

    def test_falha_alto_quando_rotulo_some(self):
        # Layout mudou e o rótulo não existe mais: erro claro, não coluna errada.
        cab = ("OFICINA", "Méd. últimas 4W", "Situação")
        with self.assertRaises(FonteInvalida):
            L._achar_col_efic(cab, "x.xlsx", "ESTOQUE")


if __name__ == "__main__":
    unittest.main()
