"""
services/data_writer.py
-------------------------
Responsabilidade única: gravar novos registros na tabela `postos` do
Supabase. Isso mantém a lógica de escrita completamente isolada das
visualizações e filtros.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from app_postos.core.config import Columns, RAW_TO_DB_COLUMNS, RawColumns, SUPABASE_TABLE_POSTOS
from app_postos.core.record import build_record_payload
from app_postos.services.supabase_client import fetch_all_rows, get_supabase_client

if TYPE_CHECKING:  # apenas para type hints; não exige a lib em runtime/testes
    from supabase import Client

_BULK_INSERT_BATCH_SIZE = 500


def check_record_exists(
    oficina: str,
    mp: str,
    semana: int,
    data_efetivos: str,
    *,
    exclude_id: int | None = None,
    client: "Client | None" = None,
) -> bool:
    """
    Verifica se já existe um lançamento para a mesma Oficina + Matéria-prima
    na mesma Semana e no mesmo ANO na tabela `postos` do Supabase.

    Regra de negócio (formulário manual): uma oficina só pode ter UM
    lançamento por matéria-prima dentro de uma mesma semana,
    independentemente do dia exato informado em `data_efetivos`. Por isso a
    checagem NÃO compara a data exata — compara se existe qualquer registro
    daquela Oficina/MP/Semana dentro do intervalo do ano da data informada.
    (Oficinas que processam mais de uma MP continuam podendo ter um
    lançamento por MP na mesma semana, pois a MP faz parte da chave.)

    O ANO permanece na chave (derivado de `data_efetivos`) porque o número
    da semana se repete a cada ano — ex.: a Semana 35 existe tanto em 2025
    quanto em 2026. Sem o recorte por ano, um lançamento novo de um ano
    seria erroneamente bloqueado por já existir a mesma Oficina/MP/Semana em
    outro ano.

    `exclude_id`: ao EDITAR um registro, informe o id dele para que a própria
    linha não seja contada como duplicata de si mesma — assim a checagem só
    acusa conflito se OUTRO registro tiver a mesma chave.

    `client`: injeção de dependência opcional (usada nos testes). Em produção
    fica `None` e a conexão real do Supabase é obtida sob demanda.
    """
    oficina_clean = str(oficina).strip()
    mp_clean = str(mp).strip().upper()
    ano = str(data_efetivos)[:4]  # "YYYY-MM-DD" -> "YYYY" (ano-calendário)

    client = client or get_supabase_client()
    try:
        query = (
            client.table(SUPABASE_TABLE_POSTOS)
            .select("id")
            .eq(Columns.OFICINA, oficina_clean)
            .eq(Columns.MP, mp_clean)
            .eq(Columns.SEMANA, int(semana))
            .gte(Columns.DATA_EFETIVOS, f"{ano}-01-01")
            .lte(Columns.DATA_EFETIVOS, f"{ano}-12-31")
        )
        if exclude_id is not None:
            query = query.neq("id", exclude_id)
        response = query.limit(1).execute()
        return len(response.data or []) > 0
    except Exception as exc:
        raise RuntimeError(f"Erro ao verificar existência de registro no Supabase: {exc}") from exc


def insert_record(
    frete: str,
    mp: str,
    oficina: str,
    data_efetivos: str,
    qtd_efetivos: int,
    data_trabalhados: str,
    qtd_trabalhados: int,
    contratacoes: int,
    demissoes: int,
    semana: int,
    client: "Client | None" = None,
) -> None:
    """
    Insere um único registro de posto de trabalho na tabela `postos` do
    Supabase. A sanitização/montagem do payload é delegada ao domínio
    (`core.record.build_record_payload`), garantindo o mesmo contrato usado
    pela edição. `client` permite injeção de dependência nos testes.
    """
    payload = build_record_payload(
        frete=frete,
        mp=mp,
        oficina=oficina,
        data_efetivos=data_efetivos,
        qtd_efetivos=qtd_efetivos,
        data_trabalhados=data_trabalhados,
        qtd_trabalhados=qtd_trabalhados,
        contratacoes=contratacoes,
        demissoes=demissoes,
        semana=semana,
    )

    client = client or get_supabase_client()
    try:
        client.table(SUPABASE_TABLE_POSTOS).insert(payload).execute()
    except Exception as exc:
        raise RuntimeError(f"Erro ao inserir registro no Supabase: {exc}") from exc


def insert_bulk_records(df: pd.DataFrame) -> int:
    """
    Insere múltiplos registros na tabela `postos` do Supabase, ignorando
    qualquer linha cuja combinação (Oficinas, MP, Semana, Data Efetivos) já
    exista no banco. Retorna o número de linhas novas inseridas com sucesso.

    A Data Efetivos entra na chave de deduplicação porque o número da
    semana se repete a cada ano — sem a data, um lançamento novo de um ano
    seria confundido com o de outro ano para a mesma Oficina/MP/Semana e
    seria erroneamente ignorado como duplicado (bug corrigido: 92
    registros da Semana 28/2026 nunca foram inseridos por esse motivo,
    pois colidiam com registros da Semana 28/2025 já existentes).

    `df` deve conter as colunas BRUTAS (cabeçalhos originais da planilha
    Excel, ver `core.config.RawColumns`) — mesmo contrato usado pelo upload
    manual na tela de Lançamento de Dados.
    """
    required_cols = list(RAW_TO_DB_COLUMNS.keys())

    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"O arquivo importado está sem as seguintes colunas obrigatórias: {missing}")

    # Cópia e limpeza básica
    df_clean = df[required_cols].copy()
    df_clean[RawColumns.FRETE] = df_clean[RawColumns.FRETE].astype(str).str.strip()
    df_clean[RawColumns.MP] = df_clean[RawColumns.MP].astype(str).str.strip().str.upper()
    df_clean[RawColumns.OFICINA] = df_clean[RawColumns.OFICINA].astype(str).str.strip()

    # Formatação de datas para string ISO
    df_clean[RawColumns.DATA_EFETIVOS] = pd.to_datetime(
        df_clean[RawColumns.DATA_EFETIVOS]
    ).dt.strftime("%Y-%m-%d")
    df_clean[RawColumns.DATA_TRABALHADOS] = pd.to_datetime(
        df_clean[RawColumns.DATA_TRABALHADOS]
    ).dt.strftime("%Y-%m-%d")

    # Tratamento de inteiros e nulos
    int_cols = [
        RawColumns.QTD_EFETIVOS,
        RawColumns.QTD_TRABALHADOS,
        RawColumns.CONTRATACAO,
        RawColumns.DEMISSAO,
        RawColumns.SEMANA,
    ]
    for col in int_cols:
        df_clean[col] = df_clean[col].fillna(0).astype(int)

    client = get_supabase_client()
    try:
        # 1. Carrega as chaves (Oficina, MP, Semana, Data Efetivos) já existentes no Supabase
        existing_rows = fetch_all_rows(
            client,
            SUPABASE_TABLE_POSTOS,
            columns=f"{Columns.OFICINA},{Columns.MP},{Columns.SEMANA},{Columns.DATA_EFETIVOS}",
        )
        existing_keys = {
            (
                str(r[Columns.OFICINA]).strip(),
                str(r[Columns.MP]).strip().upper(),
                int(r[Columns.SEMANA]),
                str(r[Columns.DATA_EFETIVOS])[:10],
            )
            for r in existing_rows
        }

        # 2. Cria chaves temporárias para as novas linhas do lote
        df_clean["_key"] = list(
            zip(
                df_clean[RawColumns.OFICINA],
                df_clean[RawColumns.MP],
                df_clean[RawColumns.SEMANA],
                df_clean[RawColumns.DATA_EFETIVOS],
            )
        )

        # 3. Filtra apenas registros que não existem no banco e remove duplicados do próprio lote
        df_to_insert = df_clean[~df_clean["_key"].isin(existing_keys)].drop(columns=["_key"])
        df_to_insert = df_to_insert.drop_duplicates(
            subset=[RawColumns.OFICINA, RawColumns.MP, RawColumns.SEMANA, RawColumns.DATA_EFETIVOS]
        )

        if len(df_to_insert) == 0:
            return 0

        # 4. Traduz para as colunas do Supabase e grava em blocos (o PostgREST
        #    aceita lotes grandes, mas dividir evita payloads excessivos).
        payload = df_to_insert.rename(columns=RAW_TO_DB_COLUMNS).to_dict(orient="records")
        for i in range(0, len(payload), _BULK_INSERT_BATCH_SIZE):
            client.table(SUPABASE_TABLE_POSTOS).insert(
                payload[i : i + _BULK_INSERT_BATCH_SIZE]
            ).execute()

        return len(df_to_insert)
    except Exception as exc:
        raise RuntimeError(f"Erro ao importar dados em lote para o Supabase: {exc}") from exc
