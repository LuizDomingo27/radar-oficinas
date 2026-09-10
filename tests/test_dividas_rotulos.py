"""Rótulos, ordem e formato da tela de Dívidas (guarda de regressão do front).

A troca foi só de apresentação — as chaves do payload (``divida_total``,
``tributos``, ``encargos``) seguem as mesmas, então os testes do serviço
(``test_dividas``) continuam valendo. O que muda é o que o operador lê:

- ``divida_total`` aparece como **Dívida**
- ``encargos``     aparece como **Descontos**
- ``tributos``     aparece como **Valor líquido**
- ordem dos cards/colunas: **Dívida · Descontos · Valor líquido**
- card "Oficinas com dívida" ganha o **percentual sobre o total da rede**
- os três cards de valor mostram **duas casas decimais** (``fmtBRL2``)

Como a SPA é estática (sem runner de JS), a checagem é no texto-fonte dos
arquivos servidos — mesmo estilo de ``test_motivo_falha`` sobre o HTML embutido.
"""

import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
INDEX = (RAIZ / "web" / "index.html").read_text(encoding="utf-8")
JS = (RAIZ / "web" / "assets" / "js" / "dashboard.js").read_text(encoding="utf-8")


class TestRotulosIndex(unittest.TestCase):
    def test_rotulos_novos_presentes(self):
        for rotulo in ("Descontos", "Valor líquido"):
            self.assertIn(rotulo, INDEX)

    def test_rotulos_antigos_de_exibicao_sumiram(self):
        # Não devem sobrar como texto de tela (as chaves de dados vivem no JS).
        for antigo in ("Tributos", "Encargos", "Dívida total"):
            self.assertNotIn(antigo, INDEX)

    def test_ordem_dos_cards_e_divida_descontos_liquido(self):
        i_div = INDEX.index('class="l">Dívida</div>')
        i_desc = INDEX.index("Descontos")
        i_liq = INDEX.index("Valor líquido")
        i_ofi = INDEX.index("Oficinas com dívida")
        self.assertLess(i_div, i_desc)
        self.assertLess(i_desc, i_liq)
        self.assertLess(i_liq, i_ofi)

    def test_card_oficinas_tem_rotulo_com_id_para_o_percentual(self):
        self.assertIn('id="div-kpi-oficinas-l"', INDEX)

    def test_cabecalhos_da_tabela_na_nova_ordem(self):
        i_div = INDEX.index('<th class="num">Dívida</th>')
        i_desc = INDEX.index('<th class="num">Descontos</th>')
        i_liq = INDEX.index('<th class="num">Valor líquido</th>')
        self.assertLess(i_div, i_desc)
        self.assertLess(i_desc, i_liq)


class TestComportamentoJs(unittest.TestCase):
    def test_formatador_de_duas_casas_existe(self):
        self.assertIn("const fmtBRL2", JS)

    def test_cards_usam_o_formatador_de_duas_casas(self):
        # O setter dos KPIs de valor passou a formatar com 2 casas decimais.
        self.assertIn("el.textContent = fmtBRL2(v)", JS)

    def test_percentual_sobre_o_total_da_rede(self):
        self.assertIn("estado.dados.oficinas.length", JS)
        self.assertIn("fmtPct(d.oficinas.length / totalRede)", JS)
        self.assertIn("da rede", JS)

    def test_tooltip_de_faturamento_reordenado_e_renomeado(self):
        i_desc = JS.index('{ rot: "Descontos", val: fmtBRL(d.encargos) }')
        i_liq = JS.index('{ rot: "Valor líquido", val: fmtBRL(d.tributos) }')
        self.assertLess(i_desc, i_liq)

    def test_tooltip_do_grafico_maiores_reordenado_e_renomeado(self):
        i_desc = JS.index('{ rot: "Descontos", val: fmtBRL(o.encargos) }')
        i_liq = JS.index('{ rot: "Valor líquido", val: fmtBRL(o.tributos) }')
        self.assertLess(i_desc, i_liq)

    def test_grafico_maiores_rotulado_como_divida(self):
        self.assertIn('rotulo: "Dívida" }', JS)


if __name__ == "__main__":
    unittest.main()
