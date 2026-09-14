"""Testes do leitor de POSTOS via Supabase (Fase 2).

O I/O de rede é substituído injetando as linhas cruas (``_obter_linhas``), de
modo que os testes exercitam só o mapeamento e o contrato de erro — nunca tocam
o Supabase de verdade.
"""

import unittest
from unittest import mock

from app_oficinas import config
from app_oficinas.errors import FonteIndisponivel
from app_oficinas.infra import leitor_postos


def _linha(**kw) -> dict:
    """Linha crua no formato da tabela ``postos`` do Supabase."""
    base = {
        "oficina": "ALFA TEXTIL LTDA",
        "frete": "RA",
        "mp": "JEANS",
        "data_efetivos": "2026-07-10",
        "qtd_efetivos": 17,
        "qtd_trabalhados": 16,
        "contratacoes": 0,
        "demissoes": 1,
        "semana": 28,
    }
    base.update(kw)
    return base


class TestLerAbsenteismo(unittest.TestCase):
    def test_mapeia_colunas_para_o_shape_antigo(self):
        with mock.patch.object(leitor_postos, "_obter_linhas", return_value=[_linha()]):
            regs = list(leitor_postos.ler_absenteismo())
        self.assertEqual(regs, [{
            "nome": "ALFA TEXTIL LTDA", "frete": "RA", "mp": "JEANS",
            "data": "2026-07-10", "semana": "28", "efetivos": 17.0,
            "trabalhados": 16.0, "contratacao": 0.0, "demissao": 1.0,
        }])

    def test_quantidades_nulas_viram_zero(self):
        linha = _linha(qtd_efetivos=None, qtd_trabalhados=None,
                       contratacoes=None, demissoes=None)
        with mock.patch.object(leitor_postos, "_obter_linhas", return_value=[linha]):
            reg = next(iter(leitor_postos.ler_absenteismo()))
        self.assertEqual(
            (reg["efetivos"], reg["trabalhados"], reg["contratacao"], reg["demissao"]),
            (0.0, 0.0, 0.0, 0.0),
        )

    def test_semana_vira_texto(self):
        with mock.patch.object(leitor_postos, "_obter_linhas", return_value=[_linha(semana=31)]):
            reg = next(iter(leitor_postos.ler_absenteismo()))
        self.assertEqual(reg["semana"], "31")

    def test_linha_sem_oficina_e_ignorada(self):
        linhas = [_linha(oficina=None), _linha(oficina="   "), _linha()]
        with mock.patch.object(leitor_postos, "_obter_linhas", return_value=linhas):
            regs = list(leitor_postos.ler_absenteismo())
        self.assertEqual(len(regs), 1)
        self.assertEqual(regs[0]["nome"], "ALFA TEXTIL LTDA")


class TestRegistrosNome(unittest.TestCase):
    def test_emite_registro_com_fonte_postos(self):
        with mock.patch.object(leitor_postos, "_obter_linhas", return_value=[_linha()]):
            regs = list(leitor_postos.registros_nome())
        self.assertEqual(len(regs), 1)
        self.assertEqual(regs[0].nome_cru, "ALFA TEXTIL LTDA")
        self.assertEqual(regs[0].fonte, "postos")
        self.assertEqual(regs[0].papel, config.PAPEL_ABSENTEISMO)

    def test_ignora_linhas_sem_nome(self):
        linhas = [_linha(oficina=""), _linha(oficina="BETA")]
        with mock.patch.object(leitor_postos, "_obter_linhas", return_value=linhas):
            regs = list(leitor_postos.registros_nome())
        self.assertEqual([r.nome_cru for r in regs], ["BETA"])


class TestErroDeFonte(unittest.TestCase):
    def test_falha_de_conexao_vira_fonte_indisponivel(self):
        class ClienteQuebrado:
            def table(self, *_a, **_k):
                raise RuntimeError("sem rede")

        with self.assertRaises(FonteIndisponivel):
            list(leitor_postos.ler_absenteismo(client=ClienteQuebrado()))

    def test_mensagem_orienta_configurar_secrets(self):
        class ClienteQuebrado:
            def table(self, *_a, **_k):
                raise RuntimeError("boom")

        with self.assertRaises(FonteIndisponivel) as ctx:
            list(leitor_postos.registros_nome(client=ClienteQuebrado()))
        self.assertIn("supabase", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
