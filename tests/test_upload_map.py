"""Testes do mapeamento de upload → nome canônico (config).

Blinda o app contra o 2º modo de falha do "sincronizado sem mudança": um arquivo
enviado com nome ligeiramente diferente (ano/mês/acento) que fazia a base
esperada "sumir".
"""

import unittest

from app_oficinas import config


class TestNomeCanonicoUpload(unittest.TestCase):
    def test_nome_exato_mantido(self):
        self.assertEqual(
            config.nome_canonico_upload("RECEBIMENTO.xlsx"), "RECEBIMENTO.xlsx")

    def test_recebimento_com_sufixo(self):
        self.assertEqual(
            config.nome_canonico_upload("recebimento agosto 2026.xlsx"),
            config.PRODUCAO.arquivo)

    def test_posto_singular(self):
        self.assertEqual(
            config.nome_canonico_upload("Postos_novo.xlsx"), config.ABSENTEISMO.arquivo)

    def test_jeans_ano_diferente(self):
        # Ano no nome muda (2027), mas ainda mapeia para o canônico do pipeline.
        self.assertEqual(
            config.nome_canonico_upload("estoque jeans 2027.xlsx"),
            config.EFIC_JEANS.arquivo)

    def test_nao_jeans_vence_jeans(self):
        # Regra mais específica ("nao jeans") tem prioridade sobre "jeans".
        self.assertEqual(
            config.nome_canonico_upload("estoque oficina nao jeans agosto.xlsx"),
            config.EFIC_NAOJEANS.arquivo)

    def test_nao_jeans_com_acento(self):
        self.assertEqual(
            config.nome_canonico_upload("ESTOQUE OFICINA NÃO JEANS.xlsx"),
            config.EFIC_NAOJEANS.arquivo)

    def test_indicador_mes_diferente(self):
        self.assertEqual(
            config.nome_canonico_upload("Indicador geral_Julho.xlsx"),
            config.QUALIDADE_RESUMO.arquivo)

    def test_lidera(self):
        self.assertEqual(
            config.nome_canonico_upload("Inscrições Lidera+ Gestão de Pessoas.xlsx"),
            config.TREINO_LIDERA.arquivo)

    def test_atendimento_ep(self):
        self.assertEqual(
            config.nome_canonico_upload("Histórico de Atendimento EP.xlsx"),
            config.TREINO_EP.arquivo)

    def test_ep_2025(self):
        self.assertEqual(
            config.nome_canonico_upload("EP 2025 atualizada.xlsx"),
            config.TREINO_EP2025_CM.arquivo)

    def test_ep_2025_nao_colide_com_atendimento_ep(self):
        # "Atendimento EP" tem "ep" mas não "2025": continua no histórico antigo.
        self.assertEqual(
            config.nome_canonico_upload("Histórico de Atendimento EP.xlsx"),
            config.TREINO_EP.arquivo)

    def test_sem_correspondencia_retorna_none(self):
        self.assertIsNone(config.nome_canonico_upload("planilha aleatoria.xlsx"))


class TestArquivosEsperados(unittest.TestCase):
    def test_cobre_oito_fontes_distintas(self):
        self.assertEqual(len(config.ARQUIVOS_ESPERADOS), 8)
        self.assertEqual(len(set(config.ARQUIVOS_ESPERADOS)), 8)

    def test_toda_regra_aponta_para_arquivo_esperado(self):
        for _tokens, canonico in config.REGRAS_UPLOAD:
            self.assertIn(canonico, config.ARQUIVOS_ESPERADOS)


if __name__ == "__main__":
    unittest.main()
