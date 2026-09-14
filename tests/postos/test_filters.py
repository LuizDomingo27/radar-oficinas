from __future__ import annotations

import unittest

import pandas as pd

from app_postos.core.config import Columns
from app_postos.services.filter_service import FilterSelection, apply_filters


class ApplyFiltersTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = pd.DataFrame(
            {
                Columns.ANO: [2025, 2026, 2026, 2026],
                Columns.ANO_MES: ["2025-07", "2026-07", "2026-07", "2026-08"],
                Columns.MP: ["MALHA", "MALHA", "JEANS", "MALHA"],
                Columns.OFICINA_MP: ["A Malha", "A Malha", "B Jeans", "A Malha"],
                Columns.SEMANA: [30, 30, 30, 31],
            }
        )

    def test_without_month_keeps_all_weeks_from_selected_year(self) -> None:
        selection = FilterSelection(
            ano=2026,
            mp=["MALHA", "JEANS"],
            oficinas=["A Malha", "B Jeans"],
            semanas=[30, 31],
            ano_mes=None,
        )

        result = apply_filters(self.data, selection)

        self.assertEqual(result.index.tolist(), [1, 2, 3])

    def test_selected_month_keeps_only_weeks_from_that_month(self) -> None:
        selection = FilterSelection(
            ano=2026,
            mp=["MALHA", "JEANS"],
            oficinas=["A Malha", "B Jeans"],
            semanas=[30, 31],
            ano_mes="2026-07",
        )

        result = apply_filters(self.data, selection)

        self.assertEqual(result.index.tolist(), [1, 2])


if __name__ == "__main__":
    unittest.main()
