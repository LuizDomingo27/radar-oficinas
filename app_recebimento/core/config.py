"""
core/config.py — configurações centrais da área "Recebimento".

Concentra caminhos, nome da tabela no Neon, contrato de colunas (bruto da
planilha ↔ snake_case do banco) e o descritor ``AREA``, que é o que liga esta
área ao núcleo compartilhado em ``app_common.movimentacao``.

Espelha ``app_envios/core/config.py`` — mesmos indicadores, fonte diferente: a
planilha RECEBIMENTO.xlsx traz as peças CORTADAS/recebidas das oficinas.
"""

from __future__ import annotations

from pathlib import Path

from app_common.movimentacao.area import (
    AreaMovimentacao,
    ColunasMovimentacao,
    VocabularioMovimentacao,
)

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
class Columns(ColunasMovimentacao):
    """Colunas comuns da movimentação + a data que só existe em Recebimento."""

    RECEBIMENTO = "recebimento"   # data do recebimento (a coluna "DIA" da planilha)


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

# Normalização de MP. A planilha traz variações apenas de caixa (ex.: "Malha"
# vs "MALHA"), resolvidas pelo ``.upper()`` da limpeza; o mapa abaixo cobre,
# por segurança, o mesmo valor-hora inválido tratado em Envios.
MP_NORMALIZATION_MAP = {
    "00:00:00": "SEM MP INFORMADA",
}


# ---------------------------------------------------------------------------
# Descritor da área — o contrato lido pelo núcleo compartilhado.
# ---------------------------------------------------------------------------
AREA = AreaMovimentacao(
    chave="receb",
    titulo=APP_TITLE,
    subtitulo=APP_SUBTITLE,
    tabela=DB_TABLE_RECEBIMENTO,
    coluna_data=Columns.RECEBIMENTO,
    colunas_persistidas=DB_COLUMNS_PERSISTED,
    vocabulario=VocabularioMovimentacao(
        singular="recebimento",
        plural="recebimentos",
        pecas_participio="Recebidas",
        minutos_participio="Recebidos",
        titulo_registros="Recebimentos",
        verbo_oficina="entregaram",
        rotulo_data="Recebimento",
        exemplo_ordem="300222936",
    ),
    top_n_oficinas=TOP_N_OFICINAS,
    page_size_tabela=PAGE_SIZE_TABLE,
)
