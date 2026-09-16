"""Leitura da fonte de POSTOS a partir do Neon (Fase 2 — I/O isolado).

Substitui a antiga planilha ``postos.xlsx`` como fonte ÚNICA de absenteísmo e de
nomes canônicos das oficinas. A tabela ``postos`` do Neon é a MESMA
alimentada pelo módulo "Gestão de Postos": o Radar passa a LER dela o que o
Postos ESCREVE, unificando a origem (o objetivo da Fase 2).

Duas costuras consomem esta fonte, ambas preservando o contrato antigo do
``postos.xlsx`` para que as camadas de serviço não precisem mudar:

- :func:`ler_absenteismo` → dicts crus de fato, no MESMO shape que o antigo
  ``leitor_fatos.ler_absenteismo`` emitia (``nome, frete, mp, data, semana,
  efetivos, trabalhados, contratacao, demissao``).
- :func:`registros_nome` → ``RegistroNome`` com ``fonte="postos"``, mantendo a
  autoridade de nome (``config.FONTE_NOME_PADRAO == "postos"`` continua elegendo
  a grafia de postos como o nome de exibição padrão da oficina).

O I/O de rede fica ISOLADO aqui: qualquer falha (credenciais ausentes, rede,
resposta inesperada) vira :class:`~app_oficinas.errors.FonteIndisponivel`, uma
``RadarError``, para o pipeline reportar a causa e o app nunca quebrar.
"""

from __future__ import annotations

from typing import Iterator

from app_oficinas import config
from app_oficinas.domain.models import RegistroNome
from app_oficinas.errors import FonteIndisponivel

# Tabela e colunas da fonte no Neon (schema estável — o mesmo escrito pelo
# módulo de Postos). É o CONTRATO desta fonte; se a tabela mudar de coluna, o
# ajuste é feito só aqui.
TABELA = "postos"
COL_OFICINA = "oficina"
COL_FRETE = "frete"
COL_MP = "mp"
# Data Efetivos é a referência (a Data Trabalhados às vezes vem como placeholder
# quando a semana não fechou), decisão herdada do build anterior via xlsx.
COL_DATA = "data_efetivos"
COL_EFETIVOS = "qtd_efetivos"
COL_TRABALHADOS = "qtd_trabalhados"
COL_CONTRATACAO = "contratacoes"
COL_DEMISSAO = "demissoes"
COL_SEMANA = "semana"

# Chave/papel herdados do postos.xlsx (preservam o comportamento do De-Para).
FONTE = "postos"


def _num(valor: object) -> float:
    """Converte para ``float`` de forma tolerante; ``0.0`` se nulo/ inválido.

    Paridade com o leitor de planilha antigo: ausência de valor vira 0.0 (não
    ``None``), pois o serviço de consolidação soma esses campos diretamente.
    """
    if valor is None or isinstance(valor, bool):
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip()
    if not texto:
        return 0.0
    try:
        return float(texto.replace(",", "."))
    except ValueError:
        return 0.0


def _texto(valor: object) -> str | None:
    if valor is None:
        return None
    t = str(valor).strip()
    return t or None


def _obter_linhas(client: object | None = None) -> list[dict]:
    """Busca TODAS as linhas da tabela ``postos``, traduzindo falhas em domínio.

    Args:
        client: client do banco já pronto (injetável nos testes). Por padrão usa
            o client compartilhado do módulo de Postos, que lê as credenciais de
            ``.streamlit/secrets.toml`` / Secrets do Streamlit Cloud.

    Raises:
        FonteIndisponivel: credenciais ausentes/incompletas, rede indisponível ou
            resposta inesperada do banco.
    """
    try:
        if client is None:
            from app_common.neon_client import get_db_client
            client = get_db_client()
        from app_common.neon_client import fetch_all_rows
        return fetch_all_rows(client, TABELA)
    except Exception as exc:  # DbConfigError, rede, SQL, etc.
        raise FonteIndisponivel(
            f"Não foi possível ler os postos do banco: {exc}. Confira a seção "
            "[neon] em .streamlit/secrets.toml (campo dsn) ou nos Secrets do "
            "Streamlit Cloud."
        ) from exc


def ler_absenteismo(client: object | None = None) -> Iterator[dict]:
    """Emite um dict cru de absenteísmo por linha da tabela ``postos``.

    Mesmo shape do antigo ``leitor_fatos.ler_absenteismo`` — a consolidação
    (``services.consolidacao``) consome sem saber que a origem mudou. Linhas sem
    nome de oficina são ignoradas.
    """
    for row in _obter_linhas(client):
        nome = _texto(row.get(COL_OFICINA))
        if not nome:
            continue
        yield {
            "nome": nome,
            "frete": _texto(row.get(COL_FRETE)),
            "mp": _texto(row.get(COL_MP)),
            "data": row.get(COL_DATA),  # ISO 'YYYY-MM-DD'; periodos.para_data aceita
            "semana": _texto(row.get(COL_SEMANA)),
            "efetivos": _num(row.get(COL_EFETIVOS)),
            "trabalhados": _num(row.get(COL_TRABALHADOS)),
            "contratacao": _num(row.get(COL_CONTRATACAO)),
            "demissao": _num(row.get(COL_DEMISSAO)),
        }


def registros_nome(client: object | None = None) -> Iterator[RegistroNome]:
    """Emite um ``RegistroNome`` por oficina da tabela ``postos`` (fonte de nome).

    Mantém ``fonte="postos"`` e ``papel=PAPEL_ABSENTEISMO`` — é o que faz o
    De-Para reconhecer estes nomes como a fonte-padrão de grafia. Linhas sem nome
    são ignoradas.
    """
    for row in _obter_linhas(client):
        nome = _texto(row.get(COL_OFICINA))
        if not nome:
            continue
        yield RegistroNome(
            nome_cru=nome, fonte=FONTE, papel=config.PAPEL_ABSENTEISMO
        )
