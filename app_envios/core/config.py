"""
core/config.py — configurações centrais da área "Envios".

Concentra caminhos, nome da tabela no Supabase, contrato de colunas (bruto da
planilha ↔ snake_case do banco), paleta de tema e metadados dos indicadores.
Espelha ``app_postos/core/config.py``.
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
DATASET_PATH = REPO_DIR / "Planilhas" / "ENVIOS_OFICINAS.xlsx"
DATASET_SHEET_NAME = "ENVIOS_OFICINAS"

# ---------------------------------------------------------------------------
# Banco de dados — Supabase
# ---------------------------------------------------------------------------
# Nome EXATO da tabela (case-sensitive no PostgREST). Criada pela migração
# db_migrations/migrations/20260915120000_create_envios_radar_table.sql.
SUPABASE_TABLE_ENVIOS = "Envios_Radar"

# ---------------------------------------------------------------------------
# Metadados da aplicação
# ---------------------------------------------------------------------------
APP_TITLE = "Envios de Peças"
APP_SUBTITLE = "Acompanhamento de peças e minutos enviados às oficinas"

# Tamanho de página da tabela de consulta (requisito: 15 por página).
PAGE_SIZE_TABLE = 15
# Nº de oficinas no gráfico de colunas de "quem mais recebeu peças".
TOP_N_OFICINAS = 10

# ---------------------------------------------------------------------------
# Colunas BRUTAS — cabeçalhos exatos da planilha ENVIOS_OFICINAS.xlsx.
# ---------------------------------------------------------------------------
class RawColumns:
    ORIGEM = "ORIGEM"
    ORDEM = "ORDEM"
    OFICINA = "OFICINA"
    QTD = "QTD"
    MINUTOS = "MINUTOS"
    ENVIO = "ENVIO"
    MP = "MP"
    PDV = "PDV"
    FRETE = "FRETE"
    SITUACAO = "SITUAÇÃO"


# ---------------------------------------------------------------------------
# Colunas PADRONIZADAS (snake_case) — usadas internamente e no Supabase.
# ---------------------------------------------------------------------------
class Columns:
    ORIGEM = "origem"
    ORDEM = "ordem"
    OFICINA = "oficina"
    QTD = "qtd"
    MINUTOS = "minutos"
    ENVIO = "envio"
    MP = "mp"
    PDV = "pdv"
    FRETE = "frete"
    SITUACAO = "situacao"
    ROW_HASH = "row_hash"
    # Derivadas (não persistidas)
    ANO = "ano"                # ano do envio (YYYY)
    ANO_MES = "ano_mes"        # período mensal (YYYY-MM)
    MES_LABEL = "mes_label"    # rótulo amigável do mês (ex.: "Jan/2026")
    SEMANA = "semana"          # semana ISO do envio
    DIA = "dia"                # data do envio (date, para agrupar por dia)
    DIA_LABEL = "dia_label"    # rótulo amigável do dia (ex.: "02/01")


# Tradução bruto → banco (as colunas persistidas na tabela Envios_Radar).
RAW_TO_DB_COLUMNS: dict[str, str] = {
    RawColumns.ORIGEM: Columns.ORIGEM,
    RawColumns.ORDEM: Columns.ORDEM,
    RawColumns.OFICINA: Columns.OFICINA,
    RawColumns.QTD: Columns.QTD,
    RawColumns.MINUTOS: Columns.MINUTOS,
    RawColumns.ENVIO: Columns.ENVIO,
    RawColumns.MP: Columns.MP,
    RawColumns.PDV: Columns.PDV,
    RawColumns.FRETE: Columns.FRETE,
    RawColumns.SITUACAO: Columns.SITUACAO,
}
DB_TO_RAW_COLUMNS: dict[str, str] = {db: raw for raw, db in RAW_TO_DB_COLUMNS.items()}

# Colunas persistidas na tabela (ordem lógica), sem id/created_at.
DB_COLUMNS_PERSISTED: list[str] = [
    Columns.ROW_HASH,
    Columns.ORIGEM,
    Columns.ORDEM,
    Columns.OFICINA,
    Columns.QTD,
    Columns.MINUTOS,
    Columns.ENVIO,
    Columns.MP,
    Columns.PDV,
    Columns.FRETE,
    Columns.SITUACAO,
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

# Normalização de MP (planilha traz variações de caixa/valores inválidos).
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
