"""Testes da leitura de fatos — foco na eficiência achada pelo cabeçalho."""

import tempfile
import unittest
from pathlib import Path

import openpyxl

from app_oficinas import config
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


class TestLerEndividamento(unittest.TestCase):
    """A leitura de dívidas ignora o rodapé de totais (linha sem razão social)."""

    def _planilha(self, dir_, linhas):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = config.ENDIVIDAMENTO.aba
        ws.append(("Razão Social", "Dívida Total (R$)", "Encargos (R$)", "Tributos (R$)"))
        for linha in linhas:
            ws.append(linha)
        caminho = Path(dir_) / config.ENDIVIDAMENTO.arquivo
        wb.save(caminho)
        return caminho

    def test_ignora_rodape_sem_nome_e_le_valores(self):
        with tempfile.TemporaryDirectory() as d:
            self._planilha(d, [
                ("OFICINA A", 100, 30, 70),
                ("OFICINA B", 500, 100, 400),
                (None, 600, 130, 470),  # rodapé de totais: sem razão social
            ])
            regs = list(L.ler_endividamento(base_dir=Path(d)))
        self.assertEqual(len(regs), 2)  # o rodapé NÃO vira oficina
        self.assertEqual(regs[0], {"nome": "OFICINA A", "divida_total": 100.0,
                                   "encargos": 30.0, "tributos": 70.0})
        self.assertEqual(regs[1]["nome"], "OFICINA B")


if __name__ == "__main__":
    unittest.main()
