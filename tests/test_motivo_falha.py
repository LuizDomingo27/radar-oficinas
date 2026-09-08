"""O motivo mostrado ao usuário precisa ser a CAUSA, não o passo que parou.

Bug original: o log do pipeline termina com "FALHOU em '1/7 De-Para'. Abortando
o restante." — uma linha que só diz onde parou. O app varria o log de trás para
frente e mostrava justamente essa, escondendo a causa real ("Aba 'Dados' não
existe em postos.xlsx"). O usuário via só "os dados não puderam ser
atualizados" e não tinha como corrigir nada.
"""

import unittest

import streamlit_app

LOG_ABA_RENOMEADA = """
========================================================
== 1/7 De-Para
========================================================
ERRO ao ler as planilhas: Aba 'Dados' não existe em postos.xlsx e nenhuma outra aba tem o cabeçalho esperado. Disponíveis: ['Planilha1', 'Planilha2']
Dica: rode com --tolerante para pular fontes problemáticas.

FALHOU em '1/7 De-Para' (código 1). Abortando o restante.
"""

LOG_PLANILHA_AUSENTE = """
== 2/7 Fatos (ETL)
FALHOU em '2/7 Fatos (ETL)': Planilha não encontrada: D:\\x\\Planilhas\\postos.xlsx
Corrija a fonte e rode de novo.
"""


class TestMontarHtml(unittest.TestCase):
    """A SPA embutida não pode quebrar o build do HTML.

    Regressão: o conteúdo de JS/CSS ia como STRING de reposição do ``re.sub``,
    que interpreta escapes (``\\d``, ``\\n``…). Uma regex ``/\\d{4}/`` no
    graficos_dashboard.js virava "bad escape" e derrubava o app. A reposição
    passou a ser função (texto literal, sem interpretar escape).
    """

    def test_embute_js_e_injeta_dados_sem_bad_escape(self):
        html = streamlit_app.montar_html()
        # Scripts locais trocados pelo conteúdo embutido + dados injetados.
        self.assertNotIn('src="assets/js/graficos_dashboard.js', html)
        self.assertNotIn('src="assets/js/dashboard.js', html)
        self.assertIn("window.__DASHBOARD__", html)
        # Trechos do JS com escapes de regex chegam literais ao HTML.
        self.assertIn("tituloPeriodo", html)


class TestUltimoMotivo(unittest.TestCase):
    def test_prefere_a_causa_ao_passo_que_abortou(self):
        motivo = streamlit_app._ultimo_motivo(LOG_ABA_RENOMEADA)
        self.assertIn("postos.xlsx", motivo)
        self.assertNotIn("Abortando", motivo)

    def test_planilha_ausente_tem_a_maior_prioridade(self):
        motivo = streamlit_app._ultimo_motivo(LOG_PLANILHA_AUSENTE)
        self.assertIn("Planilha não encontrada", motivo)

    def test_log_sem_pista_devolve_orientacao_generica(self):
        motivo = streamlit_app._ultimo_motivo("tudo certo por aqui\nnada demais")
        self.assertIn("planilhas", motivo)


if __name__ == "__main__":
    unittest.main()
