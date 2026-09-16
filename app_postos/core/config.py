"""
core/config.py
----------------
Configurações centrais da aplicação: caminhos, nomes de colunas,
paleta de cores do tema e metadados dos indicadores.

Manter TODAS as constantes "mágicas" aqui evita números/strings
espalhados pelo código e facilita manutenção futura (ex.: troca de
fonte de dados, ajuste de paleta de cores, novo indicador).
"""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_PATH = BASE_DIR / "Dataset" / "POSTOS.xlsx"
DATASET_SHEET_NAME = "Planilha1"

# ---------------------------------------------------------------------------
# Banco de dados — Neon (Postgres)
# ---------------------------------------------------------------------------
# Nome da tabela (schema `public`) que armazena os lançamentos. A string de
# conexão fica em `.streamlit/secrets.toml`, nunca aqui — ver
# `app_common/neon_client.py`.
DB_TABLE_POSTOS = "postos"

# ---------------------------------------------------------------------------
# Metadados da aplicação
# ---------------------------------------------------------------------------
APP_TITLE = "Gestão de Postos de Trabalho"
APP_SUBTITLE = "Acompanhamento de efetivos, produtividade e absenteísmo por oficina"

# ---------------------------------------------------------------------------
# Nomes das colunas BRUTAS, exatamente como vêm da planilha Excel original.
# Esse contrato é usado na importação em lote (upload de .xlsx) e no script
# `app_common/scripts/bootstrap_neon.py`. Centralizar aqui é o que permite
# que, se a planilha mudar o nome de uma coluna, o ajuste seja feito em UM
# único lugar.
# ---------------------------------------------------------------------------
class RawColumns:
    FRETE = "Frete"
    MP = "MP"
    OFICINA = "Oficinas"
    DATA_EFETIVOS = "Data Efetivos"
    QTD_EFETIVOS = "QTD Efetivos"
    DATA_TRABALHADOS = "Data Trabalhados"
    QTD_TRABALHADOS = "QTD Trabalhados"
    CONTRATACAO = "Contratatação"
    DEMISSAO = "Demissão"
    SEMANA = "Semana"


# ---------------------------------------------------------------------------
# Nomes das colunas já PADRONIZADAS (snake_case), usadas internamente em
# todo o restante da aplicação a partir da camada de limpeza de dados.
# ---------------------------------------------------------------------------
class Columns:
    FRETE = "frete"
    MP = "mp"
    OFICINA = "oficina"
    DATA_EFETIVOS = "data_efetivos"
    QTD_EFETIVOS = "qtd_efetivos"
    DATA_TRABALHADOS = "data_trabalhados"
    QTD_TRABALHADOS = "qtd_trabalhados"
    CONTRATACOES = "contratacoes"
    DEMISSOES = "demissoes"
    SEMANA = "semana"
    ANO_MES = "ano_mes"          # derivado: período mensal (YYYY-MM)
    MES_LABEL = "mes_label"      # derivado: rótulo amigável do mês
    OFICINA_MP = "oficina_mp"    # derivado: "<Oficina> <MP>", ex.: "DI3 CONFECCOES LTDA Malha"
    ANO = "ano"                  # derivado: ano da data de efetivos (YYYY)


# ---------------------------------------------------------------------------
# Tradução entre o contrato "bruto" (RawColumns, cabeçalhos da planilha
# Excel) e as colunas reais da tabela `postos` no Neon (snake_case,
# mesmos nomes de `Columns` para os campos persistidos). Um único lugar
# evita divergência entre `services/data_loader.py` (leitura) e
# `services/data_writer.py` (escrita).
# ---------------------------------------------------------------------------
RAW_TO_DB_COLUMNS: dict[str, str] = {
    RawColumns.FRETE: Columns.FRETE,
    RawColumns.MP: Columns.MP,
    RawColumns.OFICINA: Columns.OFICINA,
    RawColumns.DATA_EFETIVOS: Columns.DATA_EFETIVOS,
    RawColumns.QTD_EFETIVOS: Columns.QTD_EFETIVOS,
    RawColumns.DATA_TRABALHADOS: Columns.DATA_TRABALHADOS,
    RawColumns.QTD_TRABALHADOS: Columns.QTD_TRABALHADOS,
    RawColumns.CONTRATACAO: Columns.CONTRATACOES,
    RawColumns.DEMISSAO: Columns.DEMISSOES,
    RawColumns.SEMANA: Columns.SEMANA,
}
DB_TO_RAW_COLUMNS: dict[str, str] = {db: raw for raw, db in RAW_TO_DB_COLUMNS.items()}


# ---------------------------------------------------------------------------
# Indicadores (KPIs)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class IndicatorMeta:
    key: str
    label: str
    column: str | None   # None para indicadores calculados (ex.: absenteísmo)
    icon: str
    is_percentage: bool = False


# O campo `icon` é mantido por compatibilidade da dataclass, mas fica vazio:
# a identidade visual dos cards é feita pelo símbolo tipográfico ✦ (ver
# ui/components/cards.py), sem emojis — alinhado ao design text-only.
INDICATORS: dict[str, IndicatorMeta] = {
    "efetivos": IndicatorMeta("efetivos", "Total de Efetivos", Columns.QTD_EFETIVOS, ""),
    "trabalhados": IndicatorMeta("trabalhados", "Total Trabalhados", Columns.QTD_TRABALHADOS, ""),
    "ausencia": IndicatorMeta("ausencia", "Total de Ausências", None, ""),
    "contratacoes": IndicatorMeta("contratacoes", "Total de Contratações", Columns.CONTRATACOES, ""),
    "demissoes": IndicatorMeta("demissoes", "Total de Demissões", Columns.DEMISSOES, ""),
    "absenteismo": IndicatorMeta("absenteismo", "Taxa de Absenteísmo", None, "", is_percentage=True),
}

# Ordem de exibição dos cards de KPI
KPI_ORDER = ["efetivos", "trabalhados", "ausencia", "contratacoes", "demissoes", "absenteismo"]

# ---------------------------------------------------------------------------
# Outras constantes de negócio
# ---------------------------------------------------------------------------
# Mapeamento de normalização de categorias da coluna MP que vêm com
# inconsistências de digitação/acentuação na planilha de origem
# (ex.: "POLÓ" e "POLO" representam a mesma matéria-prima).
MP_NORMALIZATION_MAP = {
    "POLÓ": "POLO",
}

