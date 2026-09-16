"""
Testes de app_common.neon_client — o acesso único ao banco.

Focam no que dá para testar sem rede: a montagem do SQL pela API fluente, a
quotação de identificadores (a tabela ``Envios_Radar`` tem maiúsculas), o
divisor de instruções das migrações e a leitura da configuração dos Secrets.
Nenhum teste abre conexão.
"""
from __future__ import annotations

import pytest

from app_common.neon_client import (
    DbConfigError,
    NeonClient,
    _qi,
    _read_dsn,
    _split_sql_statements,
    fetch_all_rows,
)


def _sql(query) -> tuple[str, list]:
    """Monta o SQL sem executar — é o que queremos inspecionar."""
    return query._build()


# ---------------------------------------------------------------------------
# Quotação de identificadores
# ---------------------------------------------------------------------------
def test_qi_preserva_maiusculas():
    """Sem aspas, o Postgres rebaixa 'Envios_Radar' para minúsculas e não acha."""
    assert _qi("Envios_Radar") == '"Envios_Radar"'


def test_qi_escapa_aspas_no_identificador():
    assert _qi('tab"ela') == '"tab""ela"'


# ---------------------------------------------------------------------------
# SELECT
# ---------------------------------------------------------------------------
def test_select_todas_as_colunas():
    sql, params = _sql(NeonClient("dsn").table("postos").select("*"))
    assert sql == 'SELECT * FROM "postos"'
    assert params == []


def test_select_colunas_nomeadas_sao_quotadas():
    sql, _ = _sql(NeonClient("dsn").table("postos").select("oficina, mp"))
    assert sql == 'SELECT "oficina", "mp" FROM "postos"'


def test_select_com_filtros_usa_parametros():
    sql, params = _sql(
        NeonClient("dsn").table("postos").select("*").eq("oficina", "A").neq("mp", "X")
    )
    assert sql == 'SELECT * FROM "postos" WHERE "oficina" = %s AND "mp" <> %s'
    assert params == ["A", "X"]


def test_select_gte_lte():
    sql, params = _sql(
        NeonClient("dsn").table("postos").select("*").gte("semana", 10).lte("semana", 20)
    )
    assert '"semana" >= %s' in sql and '"semana" <= %s' in sql
    assert params == [10, 20]


def test_select_range_e_inclusivo():
    """`range(0, 999)` veio do PostgREST: intervalo fechado, 1000 linhas."""
    sql, _ = _sql(NeonClient("dsn").table("postos").select("*").range(0, 999))
    assert "LIMIT 1000" in sql
    assert "OFFSET" not in sql  # offset 0 não precisa aparecer


def test_select_range_com_offset():
    sql, _ = _sql(NeonClient("dsn").table("postos").select("*").range(100, 199))
    assert "LIMIT 100" in sql and "OFFSET 100" in sql


def test_select_limit():
    sql, _ = _sql(NeonClient("dsn").table("postos").select("*").limit(5))
    assert sql.endswith("LIMIT 5")


# ---------------------------------------------------------------------------
# INSERT
# ---------------------------------------------------------------------------
def test_insert_uma_linha():
    sql, params = _sql(NeonClient("dsn").table("postos").insert({"oficina": "A", "mp": "X"}))
    assert sql == 'INSERT INTO "postos" ("oficina", "mp") VALUES (%s, %s) RETURNING *'
    assert params == ["A", "X"]


def test_insert_em_lote_repete_os_placeholders():
    sql, params = _sql(
        NeonClient("dsn").table("postos").insert([{"a": 1}, {"a": 2}, {"a": 3}])
    )
    assert "VALUES (%s), (%s), (%s)" in sql
    assert params == [1, 2, 3]


def test_insert_lista_vazia_nao_gera_sql():
    sql, params = _sql(NeonClient("dsn").table("postos").insert([]))
    assert sql == "" and params == []


def test_insert_completa_chave_ausente_com_none():
    """A 1ª linha define as colunas; linha sem uma delas entra como NULL."""
    _, params = _sql(NeonClient("dsn").table("postos").insert([{"a": 1, "b": 2}, {"a": 3}]))
    assert params == [1, 2, 3, None]


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------
def test_update_com_filtro():
    sql, params = _sql(
        NeonClient("dsn").table("postos").update({"qtd": 10}).eq("id", 7)
    )
    assert sql == 'UPDATE "postos" SET "qtd" = %s WHERE "id" = %s RETURNING *'
    assert params == [10, 7]


def test_operacao_desconhecida():
    query = NeonClient("dsn").table("postos")
    query._op = "delete"
    with pytest.raises(ValueError, match="não suportada"):
        query._build()


# ---------------------------------------------------------------------------
# Divisor de SQL das migrações
# ---------------------------------------------------------------------------
def test_split_remove_comentarios_e_divide_por_ponto_e_virgula():
    script = """
-- comentário de cabeçalho
create table if not exists a (id int);
create index if not exists i on a (id);
"""
    assert _split_sql_statements(script) == [
        "create table if not exists a (id int)",
        "create index if not exists i on a (id)",
    ]


def test_split_ignora_instrucao_vazia_no_fim():
    assert _split_sql_statements("select 1;;\n") == ["select 1"]


def test_split_de_script_so_com_comentarios():
    assert _split_sql_statements("-- nada aqui\n-- nem aqui\n") == []


# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
def test_read_dsn_sem_secrets_da_mensagem_acionavel(monkeypatch):
    import app_common.neon_client as mod

    class _SemSecrets:
        def __getitem__(self, chave):
            raise KeyError(chave)

    monkeypatch.setattr(mod.st, "secrets", _SemSecrets())
    with pytest.raises(DbConfigError) as ctx:
        _read_dsn()
    assert "[neon]" in str(ctx.value)
    assert "secrets.toml" in str(ctx.value)


def test_read_dsn_secao_sem_dsn(monkeypatch):
    import app_common.neon_client as mod

    monkeypatch.setattr(mod.st, "secrets", {"neon": {}})
    with pytest.raises(DbConfigError, match="falta o campo 'dsn'"):
        _read_dsn()


def test_read_dsn_direct_cai_para_o_pooled_quando_ausente(monkeypatch):
    import app_common.neon_client as mod

    monkeypatch.setattr(mod.st, "secrets", {"neon": {"dsn": "pooled://x"}})
    assert _read_dsn(direct=True) == "pooled://x"


def test_read_dsn_direct_prefere_o_endpoint_sem_pool(monkeypatch):
    import app_common.neon_client as mod

    monkeypatch.setattr(
        mod.st, "secrets", {"neon": {"dsn": "pooled://x", "dsn_direct": "direto://y"}}
    )
    assert _read_dsn(direct=True) == "direto://y"
    assert _read_dsn() == "pooled://x"


# ---------------------------------------------------------------------------
# fetch_all_rows
# ---------------------------------------------------------------------------
def test_fetch_all_rows_delega_ao_client():
    from tests.postos.fakes import FakeNeonClient

    client = FakeNeonClient({"postos": [{"id": 1, "oficina": "A"}]})
    assert fetch_all_rows(client, "postos") == [{"id": 1, "oficina": "A"}]


def test_fetch_all_rows_com_coluna_unica():
    from tests.postos.fakes import FakeNeonClient

    client = FakeNeonClient({"postos": [{"id": 1, "oficina": "A"}]})
    assert fetch_all_rows(client, "postos", "oficina") == [{"oficina": "A"}]
