"""Testes da leitura de planilhas (infra), incluindo tratamento de erros."""

import tempfile
import unittest
from pathlib import Path

import openpyxl

from app_oficinas.config import FonteNomes
from app_oficinas.errors import AbaNaoEncontrada, PlanilhaNaoEncontrada
from app_oficinas.infra import leitor_planilha as leitor


class TestLerFonte(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Dados"
        ws.append(["OFICINA", "CNPJ"])          # cabeçalho (linha 1)
        ws.append(["Alfa Confecções LTDA", "17.160.212/0001-39"])
        ws.append([None, None])                  # linha vazia -> ignorada
        ws.append(["   ", "x"])                   # nome em branco -> ignorada
        ws.append(["Beta Malhas", None])
        wb.save(self.base / "arq.xlsx")

    def tearDown(self):
        self.tmp.cleanup()

    def _fonte(self, **kw):
        base = dict(chave="t", arquivo="arq.xlsx", aba="Dados",
                    col_nome=0, primeira_linha=2, papel="p")
        base.update(kw)
        return FonteNomes(**base)

    def test_le_apenas_linhas_validas(self):
        regs = list(leitor.ler_fonte(self._fonte(), self.base))
        nomes = [r.nome_cru for r in regs]
        self.assertEqual(nomes, ["Alfa Confecções LTDA", "Beta Malhas"])

    def test_arquivo_inexistente(self):
        with self.assertRaises(PlanilhaNaoEncontrada):
            list(leitor.ler_fonte(self._fonte(arquivo="nao_existe.xlsx"), self.base))

    def test_aba_inexistente(self):
        with self.assertRaises(AbaNaoEncontrada):
            list(leitor.ler_fonte(self._fonte(aba="Fantasma"), self.base))


class TestLerTodas(unittest.TestCase):
    def test_modo_tolerante_coleta_erros_e_continua(self):
        tmp = tempfile.TemporaryDirectory()
        base = Path(tmp.name)
        wb = openpyxl.Workbook()
        wb.active.title = "Dados"
        wb.active.append(["OFICINA"])
        wb.active.append(["Alfa"])
        wb.save(base / "ok.xlsx")
        boa = FonteNomes("ok", "ok.xlsx", "Dados", 0, 2, "p")
        ruim = FonteNomes("ruim", "sumiu.xlsx", "Dados", 0, 2, "p")

        regs, erros = leitor.ler_todas((boa, ruim), base, tolerante=True)
        self.assertEqual(len(regs), 1)
        self.assertEqual(len(erros), 1)
        self.assertIn("ruim", erros[0])
        tmp.cleanup()

    def test_modo_estrito_propaga(self):
        ruim = FonteNomes("ruim", "sumiu.xlsx", "Dados", 0, 2, "p")
        with self.assertRaises(PlanilhaNaoEncontrada):
            leitor.ler_todas((ruim,), Path("."), tolerante=False)


if __name__ == "__main__":
    unittest.main()
