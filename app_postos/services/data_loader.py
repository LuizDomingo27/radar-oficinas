"""
services/data_loader.py
-------------------------
Responsabilidade única: ler os dados BRUTOS da fonte (tabela `postos` no
Neon) e validar sua estrutura, devolvendo-os no contrato de colunas
histórico da planilha Excel (`RawColumns`). Isso mantém toda a camada de
limpeza (`services/data_cleaning.py`) e o restante da aplicação alheios à
troca de fonte de dados (SQLite → Neon).
"""

from __future__ import annotations

import pandas as pd

from app_postos.core.config import DB_TO_RAW_COLUMNS, RawColumns, DB_TABLE_POSTOS
from app_common.neon_client import DbConfigError, fetch_all_rows, get_db_client

REQUIRED_RAW_COLUMNS = [
    RawColumns.FRETE,
    RawColumns.MP,
    RawColumns.OFICINA,
    RawColumns.DATA_EFETIVOS,
    RawColumns.QTD_EFETIVOS,
    RawColumns.DATA_TRABALHADOS,
    RawColumns.QTD_TRABALHADOS,
    RawColumns.CONTRATACAO,
    RawColumns.DEMISSAO,
    RawColumns.SEMANA,
]


class DataLoadError(Exception):
    """Erro de domínio para falhas na leitura/validação da fonte de dados."""


class EmptyDataError(DataLoadError):
    """
    A tabela `postos` está acessível e com o schema correto, mas ainda não
    tem nenhum registro (cenário legítimo de primeiro uso — antes da
    importação inicial). Distinta de `DataLoadError` genérica para que
    `app.py` possa tratá-la como recuperável (deixar o usuário chegar até a
    página de Lançamento de Dados) em vez de bloquear o app inteiro.
    """


def load_raw_dataframe() -> pd.DataFrame:
    """
    Lê todos os registros da tabela `postos` no Neon e devolve um
    DataFrame no contrato de colunas "bruto" (nomes originais da planilha
    Excel), para consumo pela camada de limpeza.
    """
    try:
        client = get_db_client()
    except DbConfigError as exc:
        raise DataLoadError(str(exc)) from exc

    try:
        rows = fetch_all_rows(client, DB_TABLE_POSTOS)
    except Exception as exc:
        raise DataLoadError(f"Falha ao ler os dados do banco: {exc}") from exc

    if not rows:
        raise EmptyDataError(
            f"A tabela '{DB_TABLE_POSTOS}' no banco não contém nenhum registro. "
            "Use a página de Lançamento de Dados para importar a planilha inicial."
        )

    # Descarta colunas de infraestrutura da tabela (id, created_at) e renomeia
    # as colunas snake_case do banco para o contrato "bruto" (RawColumns),
    # mantendo a camada de limpeza (services/data_cleaning.py) inalterada.
    df = pd.DataFrame(rows).drop(columns=["id", "created_at"], errors="ignore")
    df = df.rename(columns=DB_TO_RAW_COLUMNS)

    # Converte as colunas de data (vindas como texto ISO da API) para
    # datetime64, garantindo retrocompatibilidade com toda a pipeline.
    try:
        df[RawColumns.DATA_EFETIVOS] = pd.to_datetime(df[RawColumns.DATA_EFETIVOS])
        df[RawColumns.DATA_TRABALHADOS] = pd.to_datetime(df[RawColumns.DATA_TRABALHADOS])
    except Exception as exc:
        raise DataLoadError(f"Erro ao converter formatos de data do banco: {exc}") from exc

    _validate_schema(df)
    return df


def _validate_schema(df: pd.DataFrame) -> None:
    """Garante que as colunas mínimas esperadas existem no DataFrame carregado."""
    faltantes = [col for col in REQUIRED_RAW_COLUMNS if col not in df.columns]
    if faltantes:
        raise DataLoadError(
            f"Os dados da tabela '{DB_TABLE_POSTOS}' estão sem as colunas obrigatórias: "
            f"{faltantes}. Colunas encontradas: {list(df.columns)}"
        )
    if df.empty:
        raise DataLoadError(f"A tabela '{DB_TABLE_POSTOS}' não contém nenhuma linha.")

