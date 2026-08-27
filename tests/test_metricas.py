"""Testes das fórmulas de métrica (Fase 3)."""

import unittest

from app_oficinas.domain.models import (
    FatoAbsenteismo,
    FatoEficiencia,
    FatoProducao,
    Periodo,
)
from app_oficinas.services import metricas


def prod(oid, ano, mes, semana, pecas, minutos):
    return FatoProducao(
        oficina_id=oid, oficina_nome=oid or "?", mp="JEANS",
        periodo=Periodo(ano=ano, mes=mes, semana_iso=semana),
        fonte="recebimento", real_cortado=pecas, minutos=minutos,
    )


def absen(oid, ano, mes, efet, trab, contr=0.0, demi=0.0):
    return FatoAbsenteismo(
        oficina_id=oid, oficina_nome=oid or "?", mp="JEANS",
        periodo=Periodo(ano=ano, mes=mes, semana_iso=1),
        fonte="postos", qtd_efetivos=efet, qtd_trabalhados=trab,
        contratacao=contr, demissao=demi, frete=None,
    )


def efic(oid, semana, tipo, valor, mp="JEANS", ano=2026):
    return FatoEficiencia(
        oficina_id=oid, oficina_nome=oid or "?", mp=mp,
        periodo=Periodo(ano=ano, rotulo_semana=semana),
        fonte="estoque", tipo_valor=tipo, valor=valor,
    )


class TestProdutividade(unittest.TestCase):
    def test_soma_e_taxa(self):
        linhas = metricas.serie_produtividade([
            prod("a", 2026, 1, 1, 100, 1000),
            prod("a", 2026, 1, 2, 50, 1000),
        ], metricas.POR_MES)
        self.assertEqual(len(linhas), 1)
        r = linhas[0]
        self.assertEqual((r["pecas"], r["minutos"]), (150.0, 2000.0))
        self.assertEqual(r["pecas_por_minuto"], 0.075)

    def test_separa_por_semana(self):
        linhas = metricas.serie_produtividade([
            prod("a", 2026, 1, 1, 100, 1000),
            prod("a", 2026, 1, 2, 50, 1000),
        ], metricas.POR_SEMANA)
        self.assertEqual(len(linhas), 2)

    def test_ignora_sem_oficina_id(self):
        self.assertEqual(metricas.serie_produtividade([prod(None, 2026, 1, 1, 1, 1)]), [])


class TestAbsenteismo(unittest.TestCase):
    def test_razao_agregada(self):
        linhas = metricas.serie_absenteismo([
            absen("a", 2024, 1, 30, 27),
            absen("a", 2024, 1, 20, 20),
        ], metricas.POR_MES)
        # 1 - (27+20)/(30+20) = 1 - 47/50 = 0.06
        self.assertAlmostEqual(linhas[0]["absenteismo_pct"], 0.06)

    def test_efetivos_zero_nao_quebra(self):
        linhas = metricas.serie_absenteismo([absen("a", 2024, 1, 0, 0)])
        self.assertIsNone(linhas[0]["absenteismo_pct"])


class TestEficiencia(unittest.TestCase):
    def test_passa_a_pct_oficial_por_oficina(self):
        # A eficiência é a % que a planilha já calcula — um valor por oficina.
        linhas = metricas.serie_eficiencia([
            efic("a", None, "efic_oficial", 0.7921),
            efic("b", None, "efic_oficial", 0.5523, mp="POLO"),
        ])
        por_id = {r["oficina_id"]: r for r in linhas}
        self.assertEqual(por_id["a"]["eficiencia_pct"], 0.7921)
        self.assertEqual(por_id["a"]["base"], "oficial")
        self.assertEqual(por_id["b"]["mp"], "POLO")

    def test_uma_linha_por_oficina(self):
        linhas = metricas.serie_eficiencia([
            efic("a", None, "efic_oficial", 0.6),
            efic("b", None, "efic_oficial", 0.7),
        ])
        self.assertEqual(len(linhas), 2)

    def test_duplicatas_da_mesma_oficina_sao_mediadas(self):
        linhas = metricas.serie_eficiencia([
            efic("a", None, "efic_oficial", 0.4),
            efic("a", None, "efic_oficial", 0.6),
        ])
        self.assertEqual(len(linhas), 1)
        self.assertEqual(linhas[0]["eficiencia_pct"], 0.5)

    def test_ignora_tipo_que_nao_e_oficial(self):
        linhas = metricas.serie_eficiencia([efic("a", "WK18", "entrega_pecas", 500.0)])
        self.assertEqual(linhas, [])


if __name__ == "__main__":
    unittest.main()
