"""Regressão do orquestrador: um passo que falha NÃO pode virar sucesso.

Bug original: ``build_tudo`` engolia o erro e devolvia código 1, mas o app só
tratava exceção e ignorava o código — relatava "sincronizado" sem regerar nada.
Aqui fixamos o contrato: ``main()`` devolve o código do primeiro passo que
falha, e para de rodar os seguintes.
"""

import io
import unittest
from contextlib import redirect_stdout
from unittest import mock

from scripts import build_tudo


class TestOrquestrador(unittest.TestCase):
    def test_passos_usam_executar_nao_main(self):
        # Evita reprocessar argparse sobre o argv do Streamlit.
        for nome, fn in build_tudo.PASSOS:
            self.assertEqual(fn.__name__, "executar", nome)

    def test_falha_propaga_codigo_e_interrompe(self):
        chamados = []

        def passo_ok():
            chamados.append("ok")
            return 0

        def passo_ruim():
            chamados.append("ruim")
            return 1

        def passo_nao_alcancado():
            chamados.append("nunca")
            return 0

        passos = (("A", passo_ok), ("B", passo_ruim), ("C", passo_nao_alcancado))
        with mock.patch.object(build_tudo, "PASSOS", passos):
            with redirect_stdout(io.StringIO()):
                codigo = build_tudo.main()

        self.assertEqual(codigo, 1)
        self.assertEqual(chamados, ["ok", "ruim"])  # C nunca roda

    def test_sucesso_total_retorna_zero(self):
        passos = (("A", lambda: 0), ("B", lambda: 0))
        with mock.patch.object(build_tudo, "PASSOS", passos):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(build_tudo.main(), 0)


if __name__ == "__main__":
    unittest.main()
