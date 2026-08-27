"""Configuração central: caminhos, fontes de dados e vocabulário de normalização.

Manter tudo o que é "dado sobre os dados" aqui deixa as camadas de infra e
serviço agnósticas a nomes de arquivo e a peculiaridades das planilhas.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Raiz do projeto (a pasta que contém as planilhas .xlsx).
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_OUT_DIR = BASE_DIR / "data"


# --------------------------------------------------------------------------- #
# Papéis (domínios de métrica) que cada fonte alimenta.                        #
# --------------------------------------------------------------------------- #
PAPEL_PRODUCAO = "producao"        # produtividade  (RECEBIMENTO)
PAPEL_ABSENTEISMO = "absenteismo"  # absenteísmo    (postos)
PAPEL_EFICIENCIA = "eficiencia"    # eficiência     (estoque oficinas)
PAPEL_TREINO = "treino"            # treinamentos   (histórico EP / Lidera+)

PAPEIS = (PAPEL_PRODUCAO, PAPEL_ABSENTEISMO, PAPEL_EFICIENCIA, PAPEL_TREINO)

# Fonte cuja grafia é a referência para o nome de exibição da oficina. A
# planilha de postos é a lista oficial de parceiros, então seus nomes viram o
# padrão; oficinas ausentes dela caem no desempate por frequência.
FONTE_NOME_PADRAO = "postos"


@dataclass(frozen=True)
class FonteNomes:
    """Descreve onde encontrar nomes de oficina numa planilha.

    Attributes:
        chave: identificador curto e estável da fonte.
        arquivo: nome do arquivo .xlsx na raiz do projeto.
        aba: nome da worksheet.
        col_nome: índice (base 0) da coluna com a razão social.
        primeira_linha: primeira linha de dados (base 1), pulando cabeçalhos.
        papel: domínio de métrica alimentado pela fonte.
    """

    chave: str
    arquivo: str
    aba: str
    col_nome: int
    primeira_linha: int
    papel: str


# Registro das fontes de nomes de oficina. A planilha "Indicador geral" é
# intencionalmente ignorada. Colunas/linhas foram conferidas na análise inicial.
FONTES: tuple[FonteNomes, ...] = (
    FonteNomes("recebimento", "RECEBIMENTO.xlsx", "RECEBIMENTO", 1, 2, PAPEL_PRODUCAO),
    FonteNomes("postos", "postos.xlsx", "Dados", 2, 2, PAPEL_ABSENTEISMO),
    FonteNomes(
        "estoque_jeans_aux",
        "ESTOQUE OFICINAS - JEANS - 2026.xlsx", "AUX", 0, 2, PAPEL_EFICIENCIA,
    ),
    FonteNomes(
        "estoque_jeans",
        "ESTOQUE OFICINAS - JEANS - 2026.xlsx", "ESTOQUE", 0, 6, PAPEL_EFICIENCIA,
    ),
    FonteNomes(
        "estoque_naojeans_aux",
        "ESTOQUE OFICINA NÃO JEANS.xlsx", "AUX", 0, 2, PAPEL_EFICIENCIA,
    ),
    FonteNomes(
        "estoque_naojeans_efic",
        "ESTOQUE OFICINA NÃO JEANS.xlsx", "HISTÓRICO EFIC", 1, 3, PAPEL_EFICIENCIA,
    ),
    FonteNomes(
        "treino_ep",
        "Histórico de Atendimento EP.xlsx", "Planilha1", 0, 2, PAPEL_TREINO,
    ),
    FonteNomes(
        "lidera",
        "Inscrições Lidera+ Gestão de Pessoas.xlsx", "Sheet1", 6, 2, PAPEL_TREINO,
    ),
)


# --------------------------------------------------------------------------- #
# Fontes de FATO (Fase 2) — colunas de valor/data de cada planilha.            #
# Índices base 0; ``primeira_linha`` base 1 (pula cabeçalhos). Conferidos na   #
# sondagem das planilhas. A "Indicador geral" continua fora, por decisão.      #
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class FonteProducao:
    arquivo: str = "RECEBIMENTO.xlsx"
    aba: str = "RECEBIMENTO"
    primeira_linha: int = 2
    col_data: int = 0
    col_nome: int = 1
    col_mp: int = 3
    col_real_cortado: int = 4
    col_minutos: int = 5


@dataclass(frozen=True)
class FonteAbsenteismo:
    arquivo: str = "postos.xlsx"
    aba: str = "Dados"
    primeira_linha: int = 2
    col_frete: int = 0
    col_mp: int = 1
    col_nome: int = 2
    # Data Efetivos é a referência: em ~110 linhas a Data Trabalhados vem como
    # placeholder 1990-12-31 (semana ainda não fechada), enquanto Efetivos traz
    # a data real. Ver services/consolidacao e o build da Fase 2.
    col_data: int = 3
    col_efetivos: int = 4
    col_trabalhados: int = 6
    col_contratacao: int = 7
    col_demissao: int = 8
    col_semana: int = 9


@dataclass(frozen=True)
class FonteTreinoEP:
    arquivo: str = "Histórico de Atendimento EP.xlsx"
    aba: str = "Planilha1"
    primeira_linha: int = 2
    col_nome: int = 0
    col_modulo: int = 2
    col_ch: int = 3
    col_ciclo: int = 4


@dataclass(frozen=True)
class FonteTreinoLidera:
    arquivo: str = "Inscrições Lidera+ Gestão de Pessoas.xlsx"
    aba: str = "Sheet1"
    primeira_linha: int = 2
    col_data: int = 1          # Hora de início
    col_nome: int = 6
    col_polo: int = 8
    modulo: str = "Lidera+ Gestão de Pessoas"


# Eficiência = a **% oficial da própria planilha** (decisão do usuário: "os
# valores corretos são aqueles"). Ambas as planilhas de estoque trazem, por
# oficina, a mesma coluna-resumo: **Méd. das últimas 4 semanas de entrega
# (peças) ÷ Cap Peças 100%** — um único valor atual por oficina. Lemos essa
# coluna direto; não recalculamos nem usamos a base 70% (só referência interna).

# A coluna da % oficial é localizada pelo **cabeçalho**, não por posição fixa —
# as planilhas de estoque são largas e ganham colunas de semana a cada carga, o
# que deslocaria um índice fixo. Rótulos aceitos (a 1ª coluna que casar vence, e
# é sempre a de PEÇAS, que vem antes da de minutos). Se nenhuma casar, o leitor
# levanta ``FonteInvalida`` — falha alto em vez de ler a coluna errada.
ROTULOS_EFIC_OFICIAL = ("% 4WK", "MÉDIA 4W")


# JEANS (aba ESTOQUE): cabeçalho na linha 5; a coluna oficial é "% 4WK".
@dataclass(frozen=True)
class FonteEficienciaJeans:
    arquivo: str = "ESTOQUE OFICINAS - JEANS - 2026.xlsx"
    aba: str = "ESTOQUE"
    linha_cabecalho: int = 5
    primeira_linha: int = 6
    col_nome: int = 0
    mp: str = "JEANS"
    ano: int = 2026


# NÃO-JEANS (aba ESTOQUE OFICINAS): cabeçalho na linha 8; coluna "MÉDIA 4W".
# A MP vem por linha (MALHA/POLO/TEAR). A aba HISTÓRICO EFIC (2 semanas soltas)
# foi abandonada em favor deste resumo oficial de 4 semanas.
@dataclass(frozen=True)
class FonteEficienciaNaoJeans:
    arquivo: str = "ESTOQUE OFICINA NÃO JEANS.xlsx"
    aba: str = "ESTOQUE OFICINAS"
    linha_cabecalho: int = 8
    primeira_linha: int = 9
    col_mp: int = 0
    col_nome: int = 1
    ano: int = 2026


PRODUCAO = FonteProducao()
ABSENTEISMO = FonteAbsenteismo()
TREINO_EP = FonteTreinoEP()
TREINO_LIDERA = FonteTreinoLidera()
EFIC_JEANS = FonteEficienciaJeans()
EFIC_NAOJEANS = FonteEficienciaNaoJeans()


# --------------------------------------------------------------------------- #
# Fontes de QUALIDADE — aba GRÁFICOS do "Indicador geral".                     #
# --------------------------------------------------------------------------- #
# Exceção deliberada: para as métricas de qualidade (nota, 2ª qualidade e
# principais causas) a "Indicador geral" É usada. Duas tabelas alimentam os
# gráficos: RESUMO (tabela RES, 1 linha = 1 inspeção/OM) e DEFEITOS (tabela DEF,
# 1 linha = 1 defeito). Índices base 0 a partir da coluna A da aba; as tabelas
# começam na coluna B, por isso os índices "pulam" a coluna A vazia.
PAPEL_QUALIDADE = "qualidade"

# Status de inspeção que entram no denominador da nota (os demais são ignorados).
STATUS_APROVADO = "APROVADO"
STATUS_REPROVADO = "REPROVADO"
STATUS_CONCESSAO = "APROVADO COM CONCESSAO"  # comparado já sem acento

# Pesos da Nota de Qualidade (idênticos à planilha: BD = BA*.6 + BB*.3 + BC*.1).
# Quanto MAIOR a nota, PIOR — é um índice de demérito ponderado.
PESO_REPROVADO = 0.6
PESO_CONCESSAO = 0.3
PESO_2QA = 0.1

# Filtros que definem "Principais Causas - 2ª Qualidade" na planilha.
CAUSAS_TIPO_CONTEM = "SEGUNDA"   # TIPO DE INSPEÇÃO contém "SEGUNDA"
CAUSAS_SETOR_PADRAO = "COSTURA"  # SETOR selecionado no gráfico original


@dataclass(frozen=True)
class FonteQualidadeResumo:
    arquivo: str = "Indicador geral_Junho.xlsx"
    aba: str = "RESUMO"
    primeira_linha: int = 3   # tabela RES: cabeçalho na linha 2, dados a partir da 3
    col_oficina: int = 5      # F
    col_status: int = 11      # L
    col_2qa: int = 21         # V  (peças de 2ª qualidade)
    col_prod: int = 22        # W  (produção)
    col_data3: int = 28       # AC (data usada no filtro de período)


@dataclass(frozen=True)
class FonteQualidadeDefeitos:
    arquivo: str = "Indicador geral_Junho.xlsx"
    aba: str = "DEFEITOS"
    primeira_linha: int = 3   # tabela DEF: cabeçalho na linha 2, dados a partir da 3
    col_qntd: int = 6         # G
    col_defeito: int = 8      # I  (descrição do defeito)
    col_tipo: int = 11        # L  (tipo de inspeção)
    col_setor: int = 15       # P
    col_mes: int = 18         # S
    col_ano: int = 19         # T


QUALIDADE_RESUMO = FonteQualidadeResumo()
QUALIDADE_DEFEITOS = FonteQualidadeDefeitos()


# --------------------------------------------------------------------------- #
# Vocabulário de normalização de nomes de oficina.                            #
# --------------------------------------------------------------------------- #

# Tokens de UNIDADE / linha de produto: removidos do nome-base, mas preservados
# como atributo da variante (uma mesma razão social pode ter POLO, CARGO etc.).
TOKENS_UNIDADE = frozenset({
    "POLO", "CARGO", "BASICO", "ELABORADO", "MATRIZ", "FILIAL",
    "JEANS", "MALHA", "TEAR", "PLUS", "PREMIUM",
})

# Tokens de natureza jurídica: removidos e descartados do nome-base.
TOKENS_JURIDICOS = frozenset({
    "LTDA", "ME", "EPP", "EIRELI", "MEI", "CIA", "SA", "S/A", "EI",
})

# Valores que não são oficinas (ruído / cabeçalhos vazados) — comparados já
# normalizados (sem acento, maiúsculas).
RUIDO = frozenset({
    "DEVOLUCAO TROCA DE OFICINA",
    "RAZAO SOCIAL", "OFICINA", "OFICINAS", "FORNECEDOR", "TOTAL",
    "EMPRESA", "PRODUTO",
})

# Comprimento mínimo do nome-base para ser considerado uma oficina válida.
MIN_TAMANHO_BASE = 3

# Similaridade (0..1) acima da qual dois nomes-base distintos viram candidatos
# a duplicata para revisão humana.
LIMIAR_DUPLICATA = 0.90


# --------------------------------------------------------------------------- #
# Normalização de matéria-prima (MP).                                          #
# --------------------------------------------------------------------------- #
MP_CANONICO: dict[str, str] = {
    "jeans": "JEANS",
    "malha": "MALHA",
    "tear": "TEAR",
    "polo": "POLO",
    "ecobags": "ECOBAGS",
    "comart": "COMART",
}

# MPs presentes na produção que não têm capacidade nas planilhas de eficiência.
MP_SEM_EFICIENCIA = frozenset({"ECOBAGS", "COMART"})
