"""Testes do leitor de Qualidade — foco no cache CSV validado por hash.

Constrói um "Indicador geral" mínimo em disco (abas RESUMO e DEFEITOS nas
posições de coluna reais do config) e verifica: (1) a leitura via cache devolve
os mesmos dados da extração direta; (2) o cache é criado; (3) reaproveita
enquanto o arquivo não muda e recria quando o conteúdo muda.
"""
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import openpyxl

from app_oficinas import config
from app_oficinas.infra import leitor_qualidade as Q


def _linha(tamanho: int, valores: dict) -> list:
    linha = [None] * tamanho
    for i, v in valores.items():
        linha[i] = v
    return linha


def _montar_indicador(pasta: Path, data_resumo=datetime(2026, 6, 15)) -> None:
    wb = openpyxl.Workbook()
    r = config.QUALIDADE_RESUMO
    ws = wb.active
    ws.title = r.aba  # "RESUMO"
    ws.append(_linha(29, {}))                                   # linha 1 (vazia)
    ws.append(_linha(29, {r.col_oficina: "OFICINA"}))          # linha 2 (cabeçalho)
    ws.append(_linha(29, {r.col_oficina: "ARARA", r.col_status: "REPROVADO",
                          r.col_2qa: 2, r.col_prod: 100, r.col_data3: data_resumo}))
    ws.append(_linha(29, {r.col_oficina: "ARARA", r.col_status: "APROVADO",
                          r.col_2qa: 0, r.col_prod: 50, r.col_data3: data_resumo}))
    ws.append(_linha(29, {r.col_oficina: "", r.col_status: "APROVADO"}))  # sem oficina: ignorada

    d = config.QUALIDADE_DEFEITOS
    wsd = wb.create_sheet(d.aba)  # "DEFEITOS"
    wsd.append(_linha(20, {}))
    wsd.append(_linha(20, {d.col_defeito: "DESCRICAO"}))
    wsd.append(_linha(20, {d.col_defeito: "ESCAPAMENTO",
                           d.col_tipo: "INSPECAO DA SEGUNDA QUALIDADE",
                           d.col_setor: "COSTURA", d.col_mes: 6, d.col_ano: 2026,
                           d.col_qntd: 12}))
    wb.save(pasta / config.QUALIDADE_RESUMO.arquivo)


class TestCacheQualidade(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        _montar_indicador(self.base)

    def tearDown(self):
        self._tmp.cleanup()

    def test_le_inspecoes_via_cache_e_cria_os_csvs(self):
        insp = list(Q.ler_inspecoes(base_dir=self.base))
        self.assertEqual(len(insp), 2)                      # linha sem oficina ignorada
        self.assertEqual(insp[0]["oficina"], "ARARA")
        self.assertEqual((insp[0]["ano"], insp[0]["mes"]), (2026, 6))
        self.assertEqual(insp[0]["prod"], 100.0)
        self.assertTrue((self.base / ".cache_qualidade" / "resumo.csv").exists())

    def test_le_defeitos_via_cache(self):
        defs = list(Q.ler_defeitos(base_dir=self.base))
        self.assertEqual(len(defs), 1)
        self.assertEqual(defs[0]["defeito"], "ESCAPAMENTO")
        self.assertEqual((defs[0]["ano"], defs[0]["mes"], defs[0]["qntd"]),
                         (2026, 6, 12.0))

    def test_cache_reaproveita_enquanto_fonte_nao_muda(self):
        r1, _ = Q.garantir_cache(base_dir=self.base)
        m1 = r1.stat().st_mtime_ns
        r2, _ = Q.garantir_cache(base_dir=self.base)      # hash igual: não recria
        self.assertEqual(r1, r2)
        self.assertEqual(m1, r2.stat().st_mtime_ns)

    def test_cache_recria_quando_fonte_muda(self):
        r1, _ = Q.garantir_cache(base_dir=self.base)
        m1 = r1.stat().st_mtime_ns
        _montar_indicador(self.base, data_resumo=datetime(2026, 7, 20))  # muda conteúdo
        Q.garantir_cache(base_dir=self.base)
        insp = list(Q.ler_inspecoes(base_dir=self.base))
        self.assertEqual(insp[0]["mes"], 7)               # cache refletiu a mudança
        self.assertNotEqual(m1, (self.base / ".cache_qualidade" / "resumo.csv").stat().st_mtime_ns)

    def test_cache_indisponivel_cai_para_leitura_direta(self):
        # Sem o arquivo de origem, a leitura direta levanta o erro esperado.
        (self.base / config.QUALIDADE_RESUMO.arquivo).unlink()
        from app_oficinas.errors import PlanilhaNaoEncontrada
        with self.assertRaises(PlanilhaNaoEncontrada):
            list(Q.ler_inspecoes(base_dir=self.base))


if __name__ == "__main__":
    unittest.main()
