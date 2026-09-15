"""
core/config.py — configurações centrais da área "Recebimento".

Concentra caminhos, nome da tabela no Neon, contrato de colunas (bruto da
planilha ↔ snake_case do banco), paleta de tema e metadados dos indicadores.
Espelha ``app_envios/core/config.py`` — mesmos indicadores, fonte diferente:
a planilha RECEBIMENTO.xlsx traz as peças CORTADAS/recebidas das oficinas.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
# Raiz do repositório (…/radar-oficinas), para achar a pasta Planilhas.
REPO_DIR = BASE_DIR.parent
DATASET_PATH = REPO_DIR / "Planilhas" / "RECEBIMENTO.xlsx"
DATASET_SHEET_NAME = "RECEBIMENTO"

# ---------------------------------------------------------------------------
# Banco de dados — Neon (Postgres)
# ---------------------------------------------------------------------------
# Nome EXATO da tabela (case-sensitive). Criada pela migração
# db_migrations/migrations/20260916120000_create_recebimento_radar_table.sql.
DB_TABLE_RECEBIMENTO = "Recebimento_Radar"

# ---------------------------------------------------------------------------
# Metadados da aplicação
# ---------------------------------------------------------------------------
APP_TITLE = "Recebimento de Peças"
APP_SUBTITLE = "Acompanhamento de peças e minutos recebidos das oficinas"

# Tamanho de página da tabela de consulta (requisito: 15 por página).
PAGE_SIZE_TABLE = 15
# Nº de oficinas no gráfico de colunas de "quem mais entregou peças".
TOP_N_OFICINAS = 10

# ---------------------------------------------------------------------------
# Colunas BRUTAS — cabeçalhos exatos da planilha RECEBIMENTO.xlsx.
# ---------------------------------------------------------------------------
class RawColumns:
    DIA = "DIA"
    OFICINA = "OFICINA"
    ORDEM = "ORDEM MESTRE"
    MP = "MP"
    QTD = "REAL CORTADO"
    MINUTOS = "MINUTOS"


# ---------------------------------------------------------------------------
# Colunas PADRONIZADAS (snake_case) — usadas internamente e no banco.
# ---------------------------------------------------------------------------
class Columns:
    ORDEM = "ordem"
    OFICINA = "oficina"
    QTD = "qtd"
    MINUTOS = "minutos"
    RECEBIMENTO = "recebimento"   # data do recebimento (a coluna "DIA" da planilha)
    MP = "mp"
    ROW_HASH = "row_hash"
    # Derivadas (não persistidas)
    ANO = "ano"                # ano do recebimento (YYYY)
    ANO_MES = "ano_mes"        # período mensal (YYYY-MM)
    MES_LABEL = "mes_label"    # rótulo amigável do mês (ex.: "Jan/2026")
    SEMANA = "semana"          # semana ISO do recebimento
    DIA = "dia"                # data do recebimento (date, para agrupar por dia)
    DIA_LABEL = "dia_label"    # rótulo amigável do dia (ex.: "02/01/2026")


# Tradução bruto → banco (as colunas persistidas na tabela Recebimento_Radar).
RAW_TO_DB_COLUMNS: dict[str, str] = {
    RawColumns.ORDEM: Columns.ORDEM,
    RawColumns.OFICINA: Columns.OFICINA,
    RawColumns.QTD: Columns.QTD,
    RawColumns.MINUTOS: Columns.MINUTOS,
    RawColumns.DIA: Columns.RECEBIMENTO,
    RawColumns.MP: Columns.MP,
}

# Colunas persistidas na tabela (ordem lógica), sem id/created_at.
DB_COLUMNS_PERSISTED: list[str] = [
    Columns.ROW_HASH,
    Columns.ORDEM,
    Columns.OFICINA,
    Columns.QTD,
    Columns.MINUTOS,
    Columns.RECEBIMENTO,
    Columns.MP,
]


# ---------------------------------------------------------------------------
# Granularidades disponíveis na análise (requisito do produto).
# ---------------------------------------------------------------------------
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

# Normalização de MP. A planilha traz variações apenas de caixa (ex.: "Malha"
# vs "MALHA"), resolvidas pelo ``.upper()`` da limpeza; o mapa abaixo cobre,
# por segurança, o mesmo valor-hora inválido tratado em Envios.
MP_NORMALIZATION_MAP = {
    "00:00:00": "SEM MP INFORMADA",
}


# ---------------------------------------------------------------------------
# Paleta de cores — tema ESCURO, alinhado ao Radar (mesmos tokens do Postos).
# ---------------------------------------------------------------------------
class Theme:
    BG_PRIMARY = "#0d1015"
    BG_SECONDARY = "#161b22"
    CARD_BG = "#161b22"
    CARD_BORDER = "#2a323d"

    ACCENT = "#4fd0c3"
    ACCENT_SOFT = "rgba(79,208,195,0.16)"
    ACCENT_GLOW = "rgba(79,208,195,0.20)"

    POSITIVE = "#6cc596"
    NEGATIVE = "#ec7063"
    NEUTRAL = "#a3adbc"

    TEXT_PRIMARY = "#e8ecf2"
    TEXT_MUTED = "#a3adbc"

    FONT_HEADING = "'Sora', sans-serif"
    FONT_BODY = "'Inter', sans-serif"
