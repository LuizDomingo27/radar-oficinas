"""
services/data_cleaning.py
---------------------------
Responsabilidade única: transformar o DataFrame BRUTO (colunas e valores
exatamente como vêm da planilha) em um DataFrame PADRONIZADO, pronto para
ser consumido pelas camadas de indicadores e analytics.

Regras de qualidade de dados aplicadas (e o motivo de cada uma):

1. Colunas renomeadas para snake_case (`core.config.Columns`) — desacopla
   o restante do app do nome literal das colunas na planilha.
2. Strings (frete, mp, oficina) têm espaços extras removidos — a planilha
   de origem tem variações como "MANSOUR " (com espaço) e "MANSOUR".
3. Categorias de MP normalizadas via `MP_NORMALIZATION_MAP` — a planilha
   contém "POLÓ" e "POLO" como a mesma matéria-prima (mesmo padrão usado
   no projeto APP_POLO).
4. Colunas numéricas (qtd_efetivos, qtd_trabalhados) têm nulos tratados
   como 0 — ausência de lançamento naquela semana/oficina é tratada como
   "não houve quantidade reportada", e não como dado ausente que quebra
   somas/médias.
5. A coluna `data_trabalhados` da planilha de origem contém uma data
   sentinela inválida (31/12/1990) para todas as linhas da Semana 31 —
   por isso NUNCA usamos essa coluna para derivar mês/período. O mês de
   referência é sempre derivado de `data_efetivos`, que é consistente em
   toda a base (uma única data por número de semana).
6. Uma mesma oficina pode ter mais de um lançamento na mesma semana
   quando ela produz mais de uma matéria-prima (ex.: a oficina
   "DI3 CONFECCOES LTDA" tem uma linha para JEANS e outra para MALHA na
   mesma semana — isso é um dado legítimo, não duplicidade). Para deixar
   essa distinção visível na interface, é derivada a coluna
   `oficina_mp`, no formato "<Oficina> <MP>" (ex.: "DI3 CONFECCOES LTDA
   Malha"), usada nos filtros e no ranking por oficina.
"""

from __future__ import annotations

import pandas as pd

from app_postos.core.config import Columns, INVALID_SENTINEL_DATE_YEAR, MP_NORMALIZATION_MAP, RawColumns

_RAW_TO_STANDARD = {
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

_MESES_PT = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}

_STRING_COLUMNS = [Columns.FRETE, Columns.MP, Columns.OFICINA]
_NUMERIC_FILL_ZERO_COLUMNS = [
    Columns.QTD_EFETIVOS,
    Columns.QTD_TRABALHADOS,
    Columns.CONTRATACOES,
    Columns.DEMISSOES,
]


def clean_dataframe(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Aplica toda a pipeline de limpeza e devolve um novo DataFrame padronizado."""
    df = df_raw.rename(columns=_RAW_TO_STANDARD).copy()

    df = _strip_string_columns(df)
    df = _normalize_mp(df)
    df = _fill_missing_numeric(df)
    df = _enforce_dtypes(df)
    df = _derive_month_period(df)
    df = _derive_oficina_mp_label(df)
    df = df.sort_values([Columns.SEMANA, Columns.OFICINA]).reset_index(drop=True)

    return df


def _strip_string_columns(df: pd.DataFrame) -> pd.DataFrame:
    for col in _STRING_COLUMNS:
        df[col] = df[col].astype(str).str.strip()
    return df


def _normalize_mp(df: pd.DataFrame) -> pd.DataFrame:
    df[Columns.MP] = df[Columns.MP].str.upper().replace(MP_NORMALIZATION_MAP)
    return df


def _fill_missing_numeric(df: pd.DataFrame) -> pd.DataFrame:
    for col in _NUMERIC_FILL_ZERO_COLUMNS:
        df[col] = df[col].fillna(0)
    return df


def _enforce_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    for col in _NUMERIC_FILL_ZERO_COLUMNS:
        df[col] = df[col].astype("int64")
    df[Columns.SEMANA] = df[Columns.SEMANA].astype("int64")
    df[Columns.DATA_EFETIVOS] = pd.to_datetime(df[Columns.DATA_EFETIVOS])
    return df


def _derive_month_period(df: pd.DataFrame) -> pd.DataFrame:
    """
    Deriva o período mensal SEMPRE a partir de `data_efetivos` (coluna
    confiável). A coluna `data_trabalhados` é mantida no DataFrame apenas
    como informação complementar, mas não é usada para cálculos de tempo.
    Também deriva o ano correspondente para filtragem.
    """
    periodo = df[Columns.DATA_EFETIVOS].dt.to_period("M")
    df[Columns.ANO_MES] = periodo.astype(str)  # ex.: "2025-07"
    df[Columns.MES_LABEL] = periodo.apply(lambda p: f"{_MESES_PT[p.month]}/{p.year}")
    df[Columns.ANO] = df[Columns.DATA_EFETIVOS].dt.year.astype("int64")
    return df


def _derive_oficina_mp_label(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cria o rótulo "<Oficina> <MP>" (ex.: "DI3 CONFECCOES LTDA Malha"),
    usado para distinguir, em filtros e tabelas, os múltiplos lançamentos
    de uma mesma oficina que produz mais de uma matéria-prima.
    """
    df[Columns.OFICINA_MP] = df[Columns.OFICINA] + " " + df[Columns.MP].str.title()
    return df


def build_data_quality_report(df_raw: pd.DataFrame) -> dict:
    """
    Gera um pequeno relatório (não bloqueante) sobre as inconsistências
    encontradas na planilha de origem. Útil para auditoria e para a seção
    de transparência exibida na interface.
    """
    df = df_raw.rename(columns=_RAW_TO_STANDARD)

    mp_variantes = sorted(df[Columns.MP].dropna().astype(str).str.strip().unique().tolist())
    frete_variantes = sorted(df[Columns.FRETE].dropna().astype(str).unique().tolist())

    linhas_sentinela = df[
        pd.to_datetime(df[Columns.DATA_TRABALHADOS], errors="coerce").dt.year
        == INVALID_SENTINEL_DATE_YEAR
    ]

    return {
        "linhas_totais": len(df),
        "qtd_efetivos_nulos": int(df[Columns.QTD_EFETIVOS].isna().sum()),
        "qtd_trabalhados_nulos": int(df[Columns.QTD_TRABALHADOS].isna().sum()),
        "mp_variantes_brutas": mp_variantes,
        "frete_variantes_brutas": frete_variantes,
        "linhas_data_trabalhados_invalida": int(len(linhas_sentinela)),
        "semanas_afetadas_data_invalida": sorted(
            linhas_sentinela[Columns.SEMANA].unique().tolist()
        ),
    }
