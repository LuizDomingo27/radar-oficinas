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
from app_postos.services.analytics_service import monthly_evolution, weekly_evolution


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


if __name__ == "__main__":
    unittest.main()
