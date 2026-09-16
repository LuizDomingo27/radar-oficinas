"""
app_common/movimentacao/area.py — contrato das áreas de movimentação de peças.

Reúne o que Envios e Recebimento têm em comum (nomes de coluna padronizados e
granularidades) e o descritor ``AreaMovimentacao``, que é como cada área conta
ao núcleo compartilhado quem ela é: sua tabela no Neon, sua coluna de data e o
vocabulário que aparece na tela.
"""

from __future__ import annotations

from dataclasses import dataclass


class ColunasMovimentacao:
    """
    Colunas snake_case comuns às duas áreas.

    Cada área herda desta classe e acrescenta o que é só dela (a coluna de data
    e, no caso de Envios, os campos de origem/PDV/frete/situação). Herdar — em
    vez de repetir as strings — é o que garante que "oficina" signifique a mesma
    coluna nos dois lados.
    """

    ORDEM = "ordem"
    OFICINA = "oficina"
    QTD = "qtd"
    MINUTOS = "minutos"
    MP = "mp"
    ROW_HASH = "row_hash"
    # Derivadas da data da movimentação (não persistidas).
    ANO = "ano"                # ano (YYYY)
    ANO_MES = "ano_mes"        # período mensal (YYYY-MM)
    MES_LABEL = "mes_label"    # rótulo amigável do mês (ex.: "Jan/2026")
    SEMANA = "semana"          # semana ISO
    DIA = "dia"                # data normalizada (para agrupar por dia)
    DIA_LABEL = "dia_label"    # rótulo amigável do dia (ex.: "02/01")


# Nome da coluna de contagem produzida pelas agregações. É "registros" nas duas
# áreas de propósito: o rótulo que o usuário vê ("Envios"/"Recebimentos") vem do
# vocabulário, e o dado não precisa mudar de nome junto com ele.
COLUNA_REGISTROS = "registros"
COLUNA_ROTULO = "rotulo"


@dataclass(frozen=True)
class Granularity:
    key: str
    label: str


GRANULARITIES: dict[str, Granularity] = {
    "mp": Granularity("mp", "Matéria-prima"),
    "oficina": Granularity("oficina", "Oficinas"),
    "mes": Granularity("mes", "Mês"),
    "semana": Granularity("semana", "Semana"),
    "dia": Granularity("dia", "Dia"),
}
GRANULARITY_ORDER = ["mp", "oficina", "mes", "semana", "dia"]

# Dimensões temporais: linhas sem data não têm período onde ser posicionadas.
GRANULARIDADES_TEMPORAIS = {"mes", "semana", "dia"}


@dataclass(frozen=True)
class VocabularioMovimentacao:
    """
    As palavras que diferenciam as duas telas.

    Ficam reunidas num objeto só (e não espalhadas em literais dentro da UI)
    porque são a ÚNICA coisa que muda entre Envios e Recebimento no que o
    usuário lê — juntá-las torna a diferença auditável de relance.
    """

    singular: str            # "envio"      → "Nenhum envio encontrado…"
    plural: str              # "envios"     → "linhas de envio"
    pecas_participio: str    # "Enviadas"   → card "Peças Enviadas"
    minutos_participio: str  # "Enviados"   → card "Minutos Enviados"
    titulo_registros: str    # "Envios"     → coluna da tabela e "Envios por mês"
    verbo_oficina: str       # "receberam"  → "Top oficinas que mais receberam peças"
    rotulo_data: str         # "Envio"      → cabeçalho da coluna de data
    exemplo_ordem: str       # "300222101"  → placeholder da busca


@dataclass(frozen=True)
class AreaMovimentacao:
    """Descritor completo de uma área de movimentação, montado em ``core/config.py``."""

    chave: str                      # prefixo das keys de widget ("envios", "receb")
    titulo: str                     # título exibido na navbar
    subtitulo: str
    tabela: str                     # nome EXATO da tabela no Neon
    coluna_data: str                # coluna de data da movimentação
    colunas_persistidas: list[str]
    vocabulario: VocabularioMovimentacao
    top_n_oficinas: int = 10
    page_size_tabela: int = 15

    def key(self, sufixo: str) -> str:
        """Key de widget namespaceada pela área (evita colisão entre as abas)."""
        return f"{self.chave}_{sufixo}"
