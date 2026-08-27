"""Modelos de domínio da dimensão de oficinas (De-Para).

Fluxo: a infra emite ``RegistroNome`` (nome cru + procedência). O serviço de
normalização transforma cada um em ``VarianteNome`` (com nome-base e unidade).
O serviço de De-Para agrupa variantes em ``Oficina`` (entidade canônica).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RegistroNome:
    """Um nome de oficina cru, como aparece numa fonte.

    Attributes:
        nome_cru: texto exatamente como lido da planilha.
        fonte: chave da fonte (ver ``config.FONTES``).
        papel: domínio de métrica alimentado pela fonte.
    """

    nome_cru: str
    fonte: str
    papel: str


@dataclass(frozen=True)
class VarianteNome:
    """Um ``RegistroNome`` após normalização.

    Attributes:
        nome_cru: texto original preservado para auditoria.
        nome_base: forma canônica sem acento, unidade nem natureza jurídica.
        unidade: token de linha/unidade removido (ex.: ``POLO``), ou ``None``.
        fonte, papel: procedência herdada do registro de origem.
    """

    nome_cru: str
    nome_base: str
    unidade: str | None
    fonte: str
    papel: str


@dataclass
class Oficina:
    """Entidade canônica de oficina — o alvo do De-Para.

    Reúne todas as variantes de nome que se referem à mesma razão social,
    registrando em quais fontes/papéis a oficina aparece e sinalizando casos
    que merecem revisão humana.
    """

    oficina_id: str
    nome_canonico: str
    nome_base: str
    variantes: list[VarianteNome] = field(default_factory=list)
    fontes: set[str] = field(default_factory=set)
    papeis: set[str] = field(default_factory=set)
    unidades: set[str] = field(default_factory=set)
    revisao: list[str] = field(default_factory=list)

    @property
    def precisa_revisao(self) -> bool:
        """True se há qualquer sinalização pendente de revisão humana."""
        return bool(self.revisao)

    def cobre_papel(self, papel: str) -> bool:
        """Indica se a oficina possui dados no domínio de métrica informado."""
        return papel in self.papeis


# --------------------------------------------------------------------------- #
# Fatos (Fase 2) — observações brutas já ligadas ao ``oficina_id`` do De-Para  #
# e com o período normalizado. As fórmulas de métrica ficam para a Fase 3.     #
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Periodo:
    """Recorte temporal de uma observação, para os filtros mês/semana/ano.

    Attributes:
        ano: ano de referência (ex.: 2026).
        mes: mês 1..12, ou ``None`` quando a fonte só informa ano/ciclo.
        semana_iso: semana ISO 1..53 derivada da data, ou ``None``.
        rotulo_semana: rótulo de semana da própria planilha (ex.: ``WK18``,
            ``W31``, ``"2"``), preservado para auditoria; ``None`` se ausente.
    """

    ano: int
    mes: int | None = None
    semana_iso: int | None = None
    rotulo_semana: str | None = None


@dataclass(frozen=True)
class _FatoBase:
    """Campos comuns a todo fato: procedência canônica e período."""

    oficina_id: str | None      # ``None`` quando o nome não casou com o De-Para
    oficina_nome: str           # nome cru como veio da fonte (auditoria)
    mp: str | None
    periodo: Periodo
    fonte: str


@dataclass(frozen=True)
class FatoProducao(_FatoBase):
    """Produção diária (RECEBIMENTO): peças cortadas e minutos."""

    real_cortado: float
    minutos: float


@dataclass(frozen=True)
class FatoAbsenteismo(_FatoBase):
    """Efetivos vs. trabalhados por dia (postos), com rotatividade de brinde."""

    qtd_efetivos: float
    qtd_trabalhados: float
    contratacao: float
    demissao: float
    frete: str | None


@dataclass(frozen=True)
class FatoEficiencia(_FatoBase):
    """Uma célula da série semanal de eficiência, em formato longo.

    ``tipo_valor`` distingue a natureza do número (ex.: ``entrega_pecas``,
    ``cap_pecas_70``, ``efic_pecas``, ``efic_min``), permitindo unificar as duas
    planilhas de estoque sem impor uma fórmula ainda (isso é Fase 3).
    """

    tipo_valor: str
    valor: float


@dataclass(frozen=True)
class FatoTreino(_FatoBase):
    """Participação de uma oficina num módulo de treinamento."""

    modulo: str
    ch: float | None
    ciclo: str | None
    polo: str | None
