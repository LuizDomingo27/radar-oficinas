"""O botão "Atualizar dados" não pode derrubar a página — nem no erro imprevisto.

Bug original (Streamlit Cloud): o pipeline morreu com ``AttributeError`` em
``config.FATURAMENTO`` e o traceback subiu até a página, apagando o resultado do
upload. Só ``RadarError`` era tratado; qualquer outra exceção escapava.

O ``AttributeError`` daquele dia veio de o processo estar com módulos de
commits diferentes na memória (o ``/mount/src`` é atualizado por trás do app já
rodando). Por isso o pipeline passou a ser importado junto com o ``config``, no
topo do módulo — ver ``test_pipeline_importado_junto_com_o_config``.
"""

import unittest
from unittest.mock import patch

import streamlit_app
from app_oficinas.errors import FonteInvalida


class TestRodarBuild(unittest.TestCase):
    def test_pipeline_ok_relata_sucesso(self):
        with patch.object(streamlit_app.build_tudo, "main", return_value=0):
            ok, msg = streamlit_app._rodar_build()
        self.assertTrue(ok)
        self.assertIn("Pipeline completo", msg)

    def test_erro_inesperado_vira_mensagem_e_nao_excecao(self):
        erro = AttributeError("module 'app_oficinas.config' has no attribute "
                              "'FATURAMENTO'")
        with patch.object(streamlit_app.build_tudo, "main", side_effect=erro):
            ok, msg = streamlit_app._rodar_build()
        self.assertFalse(ok)
        self.assertIn("FATURAMENTO", msg)
        self.assertIn("Reboot", msg)          # dica específica do AttributeError
        self.assertIn("nada foi alterado", msg)

    def test_erro_inesperado_generico_mostra_o_tipo(self):
        with patch.object(streamlit_app.build_tudo, "main",
                          side_effect=ZeroDivisionError("division by zero")):
            ok, msg = streamlit_app._rodar_build()
        self.assertFalse(ok)
        self.assertIn("ZeroDivisionError", msg)

    def test_pipeline_falha_mas_qualidade_e_regerada(self):
        with patch.object(streamlit_app.build_tudo, "main", return_value=1), \
             patch.object(streamlit_app.build_qualidade, "main", return_value=0):
            ok, msg = streamlit_app._rodar_build()
        self.assertTrue(ok)
        self.assertIn("Apenas a Qualidade", msg)

    def test_qualidade_com_erro_previsto_nao_relata_sucesso(self):
        with patch.object(streamlit_app.build_tudo, "main", return_value=1), \
             patch.object(streamlit_app.build_qualidade, "main",
                          side_effect=FonteInvalida("aba sumiu")):
            ok, msg = streamlit_app._rodar_build()
        self.assertFalse(ok)
        self.assertIn("aba sumiu", msg)

    def test_qualidade_com_erro_imprevisto_nao_relata_sucesso(self):
        with patch.object(streamlit_app.build_tudo, "main", return_value=1), \
             patch.object(streamlit_app.build_qualidade, "main",
                          side_effect=RuntimeError("boom")):
            ok, msg = streamlit_app._rodar_build()
        self.assertFalse(ok)
        self.assertIn("RuntimeError", msg)


class TestCoerenciaDeImports(unittest.TestCase):
    """O pipeline tem de ser importado no mesmo instante que o ``config``.

    Com o import tardio (dentro da função) o processo podia misturar um
    ``config`` antigo, já em memória, com um ``scripts``/``infra`` novo, lido do
    disco depois de um pull — foi essa mistura que gerou o ``AttributeError``.
    """

    def test_pipeline_importado_junto_com_o_config(self):
        self.assertTrue(hasattr(streamlit_app, "build_tudo"))
        self.assertTrue(hasattr(streamlit_app, "build_qualidade"))
        self.assertTrue(hasattr(streamlit_app, "config"))


if __name__ == "__main__":
    unittest.main()
