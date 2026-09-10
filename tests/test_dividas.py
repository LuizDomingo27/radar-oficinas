"""Testes da consolidação do endividamento (tela de Dívidas)."""

import unittest

from app_oficinas.errors import FonteInvalida
from app_oficinas.services import dividas


def _reg(nome, divida, encargos, tributos):
    return {"nome": nome, "divida_total": divida,
            "encargos": encargos, "tributos": tributos}


class TestConsolidar(unittest.TestCase):
    def setUp(self):
        self.registros = [
            _reg("OFICINA A", 100.0, 30.0, 70.0),
            _reg("OFICINA B", 500.0, 100.0, 400.0),
            _reg("OFICINA C", 50.0, 0.0, 50.0),
        ]

    def test_oficinas_ordenadas_desc_por_divida(self):
        p = dividas.consolidar(self.registros)
        self.assertEqual([o["nome"] for o in p["oficinas"]],
                         ["OFICINA B", "OFICINA A", "OFICINA C"])

    def test_totais_gerais(self):
        p = dividas.consolidar(self.registros)
        self.assertEqual(p["total_divida"], 650.0)
        self.assertEqual(p["total_encargos"], 130.0)
        self.assertEqual(p["total_tributos"], 520.0)

    def test_razao_social_repetida_conta_como_duas_oficinas(self):
        # Cada linha da planilha é uma oficina: a razão social repetida NÃO é
        # somada numa só — a contagem exibida bate com as linhas da planilha.
        p = dividas.consolidar([
            _reg("J M CONFECCOES & CIA LTDA", 1.0, 0.0, 1.0),
            _reg("J M CONFECCOES & CIA LTDA", 379802.0, 0.0, 379802.0),
        ])
        self.assertEqual(len(p["oficinas"]), 2)
        self.assertEqual(p["total_divida"], 379803.0)
        self.assertEqual(p["linhas"], 2)

    def test_valores_ausentes_contam_zero(self):
        p = dividas.consolidar([_reg("OFICINA A", 100.0, None, None)])
        o = p["oficinas"][0]
        self.assertEqual((o["divida_total"], o["encargos"], o["tributos"]),
                         (100.0, 0.0, 0.0))

    def test_ignora_linhas_sem_nome_ou_ruido(self):
        # Rodapé de total (sem nome) e um rótulo "TOTAL" são descartados.
        p = dividas.consolidar([
            _reg(None, 999.0, 0.0, 999.0),
            _reg("TOTAL", 888.0, 0.0, 888.0),
            _reg("OFICINA A", 100.0, 30.0, 70.0),
        ])
        self.assertEqual(len(p["oficinas"]), 1)
        self.assertEqual(p["total_divida"], 100.0)
        self.assertEqual(p["linhas"], 1)

    def test_linhas_conta_registros_lidos(self):
        p = dividas.consolidar(self.registros)
        self.assertEqual(p["linhas"], 3)

    def test_moeda_no_payload(self):
        self.assertEqual(dividas.consolidar(self.registros)["moeda"], "R$")

    def test_sem_registros_validos_levanta(self):
        with self.assertRaises(FonteInvalida):
            dividas.consolidar([])
        with self.assertRaises(FonteInvalida):
            dividas.consolidar([_reg(None, 1.0, 1.0, 1.0)])


if __name__ == "__main__":
    unittest.main()
