"""Testes da consolidação de fatos (Fase 2).

As fontes de I/O são substituídas por fixtures em memória, de modo que o teste
exercita só a lógica do serviço: resolução de ``oficina_id``, normalização de
período/MP e rastreio dos nomes não resolvidos.
"""

import unittest
from datetime import datetime
from unittest import mock

from app_oficinas.services import consolidacao


class TestConsolidar(unittest.TestCase):
    def setUp(self):
        # Índice: nome_base -> (oficina_id, nome_canonico).
        self.indice = {
            "ALFA TEXTIL": ("alfa-textil", "ALFA TEXTIL LTDA"),
            "BETA": ("beta", "BETA"),
        }
        self._prod = [
            {"nome": "Alfa Têxtil LTDA", "mp": "jeans",
             "data": datetime(2026, 1, 2), "real_cortado": 100.0, "minutos": 900.0},
            {"nome": "Fantasma SA", "mp": "TEAR",  # não está no índice
             "data": datetime(2026, 1, 3), "real_cortado": 5.0, "minutos": 50.0},
            {"nome": "Beta", "mp": "MALHA",
             "data": "sem data", "real_cortado": 1.0, "minutos": 1.0},  # descartado
        ]
        self._absen = [
            {"nome": "ALFA TEXTIL", "frete": "RA", "mp": "JEANS",
             "data": datetime(2025, 8, 1), "semana": "31", "efetivos": 10.0,
             "trabalhados": 9.0, "contratacao": 0.0, "demissao": 1.0},
        ]
        self._efic = [
            {"nome": "BETA", "mp": "POLO", "rotulo_semana": "W31",
             "tipo_valor": "efic_pecas", "valor": 0.61, "ano": 2026},
        ]
        self._treino_ep = [
            {"nome": "ALFA TEXTIL", "modulo": "TOC", "ch": 20.0, "ciclo": "2023/2024"},
        ]
        self._treino_lidera = [
            {"nome": "BETA", "modulo": "Lidera+", "data": datetime(2026, 5, 12),
             "polo": "Natal - 18/07"},
        ]

    def _consolidar(self):
        with mock.patch.multiple(
            consolidacao.leitor_fatos,
            ler_producao=mock.Mock(return_value=iter(self._prod)),
            ler_absenteismo=mock.Mock(return_value=iter(self._absen)),
            ler_eficiencia_jeans=mock.Mock(return_value=iter([])),
            ler_eficiencia_naojeans=mock.Mock(return_value=iter(self._efic)),
            ler_treino_ep=mock.Mock(return_value=iter(self._treino_ep)),
            ler_treino_lidera=mock.Mock(return_value=iter(self._treino_lidera)),
        ):
            return consolidacao.consolidar(self.indice)

    def test_resolve_id_e_normaliza(self):
        c = self._consolidar()
        alfa = next(f for f in c.producao if f.oficina_nome == "Alfa Têxtil LTDA")
        self.assertEqual(alfa.oficina_id, "alfa-textil")
        self.assertEqual(alfa.mp, "JEANS")
        self.assertEqual((alfa.periodo.ano, alfa.periodo.mes), (2026, 1))

    def test_nome_fora_do_indice_fica_sem_id_e_rastreado(self):
        c = self._consolidar()
        fantasma = next(f for f in c.producao if f.oficina_nome == "Fantasma SA")
        self.assertIsNone(fantasma.oficina_id)
        self.assertIn("Fantasma SA", c.nao_resolvidos)

    def test_linha_sem_data_e_descartada(self):
        c = self._consolidar()
        self.assertFalse(any(f.oficina_nome == "Beta" for f in c.producao))

    def test_treino_ep_usa_ano_do_ciclo(self):
        c = self._consolidar()
        toc = next(f for f in c.treino if f.modulo == "TOC")
        self.assertEqual(toc.periodo.ano, 2024)
        self.assertEqual(toc.ch, 20.0)

    def test_eficiencia_preserva_tipo_e_rotulo(self):
        c = self._consolidar()
        self.assertEqual(len(c.eficiencia), 1)
        e = c.eficiencia[0]
        self.assertEqual((e.tipo_valor, e.periodo.rotulo_semana), ("efic_pecas", "W31"))

    def test_resumo_conta_tudo(self):
        r = self._consolidar().resumo()
        self.assertEqual(r["producao"], 2)      # Alfa + Fantasma (Beta descartado)
        self.assertEqual(r["absenteismo"], 1)
        self.assertEqual(r["treino"], 2)
        self.assertEqual(r["nao_resolvidos"], 1)


if __name__ == "__main__":
    unittest.main()
