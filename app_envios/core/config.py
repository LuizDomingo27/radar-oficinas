"""
core/config.py — configurações centrais da área "Envios".

Concentra caminhos, nome da tabela no Neon, contrato de colunas (bruto da
planilha ↔ snake_case do banco) e o descritor ``AREA``, que é o que liga esta
área ao núcleo compartilhado em ``app_common.movimentacao``.

Paleta, granularidades e nomes de coluna comuns NÃO são declarados aqui: eles
vivem em ``app_common`` e são importados, para que Envios e Recebimento não
possam divergir.
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
DATASET_PATH = REPO_DIR / "Planilhas" / "ENVIOS_OFICINAS.xlsx"
DATASET_SHEET_NAME = "ENVIOS_OFICINAS"

# ---------------------------------------------------------------------------
# Banco de dados — Neon (Postgres)
# ---------------------------------------------------------------------------
# Nome EXATO da tabela (case-sensitive). Criada pela migração
# db_migrations/migrations/20260915120000_create_envios_radar_table.sql.
DB_TABLE_ENVIOS = "Envios_Radar"

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
# Colunas PADRONIZADAS (snake_case) — usadas internamente e no banco.
# ---------------------------------------------------------------------------
class Columns(ColunasMovimentacao):
    """Colunas comuns da movimentação + as que só existem em Envios."""

    ORIGEM = "origem"
    ENVIO = "envio"            # data do envio
    PDV = "pdv"
    FRETE = "frete"
    SITUACAO = "situacao"


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

# Normalização de MP (planilha traz variações de caixa/valores inválidos).
MP_NORMALIZATION_MAP = {
    "00:00:00": "SEM MP INFORMADA",
}


# ---------------------------------------------------------------------------
# Descritor da área — o contrato lido pelo núcleo compartilhado.
# ---------------------------------------------------------------------------
AREA = AreaMovimentacao(
    chave="envios",
    titulo=APP_TITLE,
    subtitulo=APP_SUBTITLE,
    tabela=DB_TABLE_ENVIOS,
    coluna_data=Columns.ENVIO,
    colunas_persistidas=DB_COLUMNS_PERSISTED,
    vocabulario=VocabularioMovimentacao(
        singular="envio",
        plural="envios",
        pecas_participio="Enviadas",
        minutos_participio="Enviados",
        titulo_registros="Envios",
        verbo_oficina="receberam",
        rotulo_data="Envio",
        exemplo_ordem="300222101",
    ),
    top_n_oficinas=TOP_N_OFICINAS,
    page_size_tabela=PAGE_SIZE_TABLE,
)
