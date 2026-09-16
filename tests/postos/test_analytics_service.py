"""Testes da camada de análise (séries de evolução semanal e mensal).

Cobre a regra confirmada de que, na evolução MENSAL, efetivos e trabalhados
usam a fotografia da ÚLTIMA semana do mês (headcount é estoque, não fluxo),
enquanto os demais indicadores continuam somando/derivando dos totais do mês.
"""

from __future__ import annotations

import math
import unittest

import pandas as pd

from app_postos.core.config import Columns
from app_postos.services.analytics_service import (
    absenteismo_por_oficina,
    aggregate_by_mp,
    aggregate_by_oficina,
    media_absenteismo,
    monthly_evolution,
    ranking_absenteismo,
    weekly_evolution,
)


def _sample_dataframe() -> pd.DataFrame:
    """Dois meses com várias semanas/oficinas, para separar 'soma' de 'última semana'.

    Janeiro/2026 (semanas 1, 2, 3 — última = 3):
      efetivos por semana: 150, 200, 100  -> soma = 450, última = 100
      trabalhados por semana: 130, 180, 90 -> soma = 400, última = 90
      contratações por semana: 3, 4, 1     -> soma = 8
      demissões por semana: 1, 2, 1        -> soma = 4
    Fevereiro/2026 (semanas 5, 6 — última = 6):
      efetivos por semana: 300, 111        -> última = 111
    """
    rows = [
        # ano_mes,     mes_label,   semana, efetivos, trabalhados, contr, dem
        ("2026-01", "Jan/2026", 1, 100, 90, 2, 1),
        ("2026-01", "Jan/2026", 1, 50, 40, 1, 0),
        ("2026-01", "Jan/2026", 2, 200, 180, 4, 2),
        ("2026-01", "Jan/2026", 3, 90, 80, 1, 0),
        ("2026-01", "Jan/2026", 3, 10, 10, 0, 1),
        ("2026-02", "Fev/2026", 5, 300, 260, 5, 3),
        ("2026-02", "Fev/2026", 6, 111, 100, 2, 1),
    ]
    return pd.DataFrame(
        rows,
        columns=[
            Columns.ANO_MES,
            Columns.MES_LABEL,
            Columns.SEMANA,
            Columns.QTD_EFETIVOS,
            Columns.QTD_TRABALHADOS,
            Columns.CONTRATACOES,
            Columns.DEMISSOES,
        ],
    )


def _valor(serie: pd.DataFrame, ano_mes: str) -> float:
    return float(serie.loc[serie[Columns.ANO_MES] == ano_mes, "valor"].iloc[0])


class MonthlyEvolutionLastWeekTests(unittest.TestCase):
    def test_efetivos_usa_ultima_semana_do_mes(self) -> None:
        serie = monthly_evolution(_sample_dataframe(), "efetivos")
        self.assertEqual(_valor(serie, "2026-01"), 100)  # última semana (3), não a soma (450)
        self.assertEqual(_valor(serie, "2026-02"), 111)  # última semana (6)

    def test_trabalhados_usa_ultima_semana_do_mes(self) -> None:
        serie = monthly_evolution(_sample_dataframe(), "trabalhados")
        self.assertEqual(_valor(serie, "2026-01"), 90)  # última semana (3), não a soma (400)
        self.assertEqual(_valor(serie, "2026-02"), 100)

    def test_ausencia_continua_somando_o_mes(self) -> None:
        serie = monthly_evolution(_sample_dataframe(), "ausencia")
        # soma efetivos (450) - soma trabalhados (400)
        self.assertEqual(_valor(serie, "2026-01"), 50)

    def test_absenteismo_continua_derivando_das_somas(self) -> None:
        serie = monthly_evolution(_sample_dataframe(), "absenteismo")
        # (450 - 400) / 450 * 100
        self.assertTrue(math.isclose(_valor(serie, "2026-01"), 50 / 450 * 100, rel_tol=1e-9))

    def test_contratacoes_e_demissoes_continuam_somando(self) -> None:
        contratacoes = monthly_evolution(_sample_dataframe(), "contratacoes")
        demissoes = monthly_evolution(_sample_dataframe(), "demissoes")
        self.assertEqual(_valor(contratacoes, "2026-01"), 8)
        self.assertEqual(_valor(demissoes, "2026-01"), 4)

    def test_mantem_rotulo_do_mes(self) -> None:
        serie = monthly_evolution(_sample_dataframe(), "efetivos")
        rotulos = dict(zip(serie[Columns.ANO_MES], serie[Columns.MES_LABEL]))
        self.assertEqual(rotulos["2026-01"], "Jan/2026")
        self.assertEqual(rotulos["2026-02"], "Fev/2026")

    def test_nao_muta_o_dataframe_de_entrada(self) -> None:
        source = _sample_dataframe()
        original = source.copy(deep=True)
        monthly_evolution(source, "efetivos")
        pd.testing.assert_frame_equal(source, original)


class WeeklyEvolutionUnchangedTests(unittest.TestCase):
    def test_semanal_de_efetivos_soma_as_oficinas_da_semana(self) -> None:
        serie = weekly_evolution(_sample_dataframe(), "efetivos")
        por_semana = dict(zip(serie[Columns.SEMANA], serie["valor"]))
        self.assertEqual(por_semana[1], 150)  # 100 + 50
        self.assertEqual(por_semana[2], 200)
        self.assertEqual(por_semana[3], 100)  # 90 + 10


class EmptyInputTests(unittest.TestCase):
    def test_monthly_evolution_com_dataframe_vazio_nao_quebra(self) -> None:
        empty = _sample_dataframe().iloc[0:0]
        serie = monthly_evolution(empty, "efetivos")
        self.assertTrue(serie.empty)


def _dim_dataframe() -> pd.DataFrame:
    """Recorte com MP e oficina, para as agregações por dimensão.

    MALHA : efetivos 100+50=150, trabalhados 90+40=130 -> ausência 20, abs 13.33%
    JEANS : efetivos 200, trabalhados 180              -> ausência 20, abs 10.00%
    ZERO  : efetivo 0 -> taxa não calculável (NaN)
    """
    rows = [
        # mp,      oficina_mp,   semana, efetivos, trabalhados, contr, dem
        ("MALHA", "OF A MALHA", 1, 100, 90, 2, 1),
        ("MALHA", "OF B MALHA", 1, 50, 40, 1, 0),
        ("JEANS", "OF C JEANS", 2, 200, 180, 4, 2),
        ("ZERO", "OF D ZERO", 2, 0, 0, 0, 0),
    ]
    return pd.DataFrame(
        rows,
        columns=[
            Columns.MP,
            Columns.OFICINA_MP,
            Columns.SEMANA,
            Columns.QTD_EFETIVOS,
            Columns.QTD_TRABALHADOS,
            Columns.CONTRATACOES,
            Columns.DEMISSOES,
        ],
    )


class AggregateByMpTests(unittest.TestCase):
    def test_soma_por_mp_e_calcula_ausencia_e_taxa(self) -> None:
        grp = aggregate_by_mp(_dim_dataframe())
        malha = grp.loc[grp[Columns.MP] == "MALHA"].iloc[0]
        self.assertEqual(int(malha["efetivos"]), 150)
        self.assertEqual(int(malha["trabalhados"]), 130)
        self.assertEqual(int(malha["ausencia"]), 20)
        self.assertAlmostEqual(float(malha["absenteismo"]), 13.33, places=2)

    def test_taxa_e_razao_entre_somas_nao_media_de_taxas(self) -> None:
        # Médias das taxas de OF A (10%) e OF B (20%) daria 15%; o certo é 13,33%.
        grp = aggregate_by_mp(_dim_dataframe())
        malha = grp.loc[grp[Columns.MP] == "MALHA"].iloc[0]
        self.assertNotAlmostEqual(float(malha["absenteismo"]), 15.0, places=2)

    def test_efetivo_zero_vira_taxa_nan(self) -> None:
        grp = aggregate_by_mp(_dim_dataframe())
        zero = grp.loc[grp[Columns.MP] == "ZERO"].iloc[0]
        self.assertTrue(math.isnan(float(zero["absenteismo"])))

    def test_ordenado_por_mp(self) -> None:
        grp = aggregate_by_mp(_dim_dataframe())
        self.assertEqual(list(grp[Columns.MP]), sorted(grp[Columns.MP]))

    def test_vazio_devolve_contrato_de_colunas(self) -> None:
        grp = aggregate_by_mp(_dim_dataframe().iloc[0:0])
        self.assertTrue(grp.empty)
        for col in ("efetivos", "trabalhados", "ausencia", "absenteismo"):
            self.assertIn(col, grp.columns)


class AggregateByOficinaTests(unittest.TestCase):
    def test_ordena_do_menor_para_o_maior_absenteismo(self) -> None:
        grp = aggregate_by_oficina(_dim_dataframe())
        taxas = [t for t in grp["absenteismo_%"] if t == t]  # ignora NaN
        self.assertEqual(taxas, sorted(taxas))

    def test_uma_casa_decimal(self) -> None:
        grp = aggregate_by_oficina(_dim_dataframe())
        linha = grp.loc[grp[Columns.OFICINA_MP] == "OF A MALHA"].iloc[0]
        self.assertEqual(float(linha["absenteismo_%"]), 10.0)

    def test_vazio_devolve_contrato_de_colunas(self) -> None:
        grp = aggregate_by_oficina(_dim_dataframe().iloc[0:0])
        self.assertTrue(grp.empty)
        self.assertIn("absenteismo_%", grp.columns)


class RankingAbsenteismoTests(unittest.TestCase):
    def test_usa_apenas_as_ultimas_semanas_da_janela(self) -> None:
        agregado, semanas = absenteismo_por_oficina(_dim_dataframe(), semanas=1)
        # Só a semana 2 entra; as oficinas de MALHA (semana 1) ficam de fora.
        self.assertEqual(semanas, 1)
        self.assertNotIn("OF A MALHA", list(agregado[Columns.OFICINA_MP]))

    def test_descarta_oficina_sem_taxa_calculavel(self) -> None:
        agregado, _ = absenteismo_por_oficina(_dim_dataframe())
        self.assertNotIn("OF D ZERO", list(agregado[Columns.OFICINA_MP]))

    def test_piores_traz_as_maiores_taxas(self) -> None:
        agregado, _ = absenteismo_por_oficina(_dim_dataframe())
        top = ranking_absenteismo(agregado, mode="piores", top_n=1)
        self.assertEqual(top.iloc[0][Columns.OFICINA_MP], "OF B MALHA")  # 20%

    def test_melhores_traz_as_menores_taxas(self) -> None:
        agregado, _ = absenteismo_por_oficina(_dim_dataframe())
        top = ranking_absenteismo(agregado, mode="melhores", top_n=1)
        self.assertEqual(top.iloc[0][Columns.OFICINA_MP], "OF A MALHA")  # 10%

    def test_resultado_sempre_ordenado_de_forma_crescente(self) -> None:
        agregado, _ = absenteismo_por_oficina(_dim_dataframe())
        for modo in ("piores", "melhores"):
            top = ranking_absenteismo(agregado, mode=modo, top_n=10)
            self.assertEqual(list(top["absenteismo"]), sorted(top["absenteismo"]))

    def test_modo_desconhecido_falha_explicitamente(self) -> None:
        agregado, _ = absenteismo_por_oficina(_dim_dataframe())
        with self.assertRaises(ValueError):
            ranking_absenteismo(agregado, mode="qualquer", top_n=5)

    def test_media_do_ranking(self) -> None:
        agregado, _ = absenteismo_por_oficina(_dim_dataframe())
        top = ranking_absenteismo(agregado, mode="piores", top_n=10)
        self.assertAlmostEqual(media_absenteismo(top), 13.33, places=1)

    def test_vazio_nao_quebra(self) -> None:
        vazio = _dim_dataframe().iloc[0:0]
        agregado, semanas = absenteismo_por_oficina(vazio)
        self.assertTrue(agregado.empty)
        self.assertEqual(semanas, 0)
        self.assertTrue(ranking_absenteismo(agregado, mode="piores", top_n=5).empty)
        self.assertTrue(math.isnan(media_absenteismo(agregado)))


if __name__ == "__main__":
    unittest.main()
