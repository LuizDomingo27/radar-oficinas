"""Consolidação para o dashboard (Fase 5) — as três telas em um só payload.

Reúne, num único objeto enxuto, tudo o que o frontend precisa para as três
telas do plano:

- **Ranking geral** — cada oficina nas métricas, com um valor representativo
  (roll-up do ano mais recente com dado). Produtividade é lida como **volume**:
  média de peças/mês e média de peças/semana (duas colunas, sem semáforo).
- **Ficha da oficina** — a série temporal de cada métrica (produtividade em
  duas linhas do tempo: peças/mês e peças/semana; absenteísmo mensal) e os
  marcos de treino.
- **Impacto do treinamento** — repassa as tabelas já prontas da Fase 4
  (``impacto_por_oficina`` e ``impacto_coorte``), sem recalcular.

Funções puras sobre as listas ``registros`` já periodizadas da Fase 3 e sobre o
De-Para/treinos. Não faz I/O — o orquestrador ``scripts/build_dashboard.py``
injeta os dados lidos e grava a saída. Reaproveita as leituras cacheadas em vez
de reabrir as planilhas (frugalidade de I/O, como a Fase 4).

Decisões de projeto:

- **Valor de ranking = roll-up do ano mais recente com dado**, seguindo as
  fórmulas da Fase 3: produtividade = Σpeças ÷ Σminutos, absenteísmo =
  1 − Σtrab ÷ Σefetivos, eficiência = média das semanas representativas.
- **Eficiência representativa por semana**: base ``pecas_100`` no JEANS (a
  capacidade real, mais rígida) e ``pecas`` no não-jeans (o % já pronto).
  Duplicatas na mesma semana entram por média.
- **Semáforo**: só nas métricas com meta absoluta — eficiência contra a meta de
  65% (piso: ok ≥ 65%, alerta ≥ 55%, senão crítico) e absenteísmo (ok ≤ 5%,
  alerta ≤ 10%, senão crítico). Produtividade agora é **volume de peças** e
  depende do tamanho da oficina — não leva semáforo, mostra só o número.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

# Sentido de cada métrica: +1 se subir é bom, -1 se subir é ruim.
SENTIDO = {"eficiencia": +1, "absenteismo": -1}

# Faixas absolutas de semáforo (fração 0..1). Ordem: (ok_ate/ok_desde, alerta).
# Absenteísmo é "menor é melhor"; eficiência é "maior é melhor".
FAIXA_ABSENTEISMO = (0.05, 0.10)   # <=5% ok, <=10% alerta, senão crítico
FAIXA_EFICIENCIA = (0.65, 0.55)    # >=65% ok, >=55% alerta, senão crítico


def _mes_periodo(reg: dict) -> str:
    """Rótulo de período mensal ``AAAA-MM`` a partir de um registro."""
    return f"{reg['ano']:04d}-{reg['mes']:02d}"


def _serie_mensal(registros: Iterable[dict], campo_valor: str) -> list[dict]:
    """Série ordenada ``[{periodo, valor}]`` a partir de registros mensais."""
    itens = [
        {"periodo": _mes_periodo(r), "valor": round(r[campo_valor], 4)}
        for r in registros
        if r.get(campo_valor) is not None
    ]
    return sorted(itens, key=lambda x: x["periodo"])


def _semana_periodo(reg: dict) -> str:
    """Rótulo de período semanal ``AAAA-Www`` a partir de um registro."""
    return f"{reg['ano']:04d}-W{reg['semana']:02d}"


def _serie_semanal(registros: Iterable[dict], campo_valor: str) -> list[dict]:
    """Série ordenada ``[{periodo, valor}]`` a partir de registros semanais."""
    itens = [
        {"periodo": _semana_periodo(r), "valor": round(r[campo_valor], 4)}
        for r in registros
        if r.get(campo_valor) is not None
    ]
    return sorted(itens, key=lambda x: x["periodo"])


def _media_volume(registros: list[dict]) -> tuple[float, int] | None:
    """Média de peças produzidas por período (mês ou semana) do conjunto.

    A produtividade passou a ser lida como **volume**: a média das peças
    entregues em cada período com dado, por oficina — visão mais direta que o
    antigo peças/minuto. Devolve ``(media, n_periodos)``.
    """
    pecas = [r["pecas"] for r in registros if r.get("pecas") is not None]
    if not pecas:
        return None
    return round(sum(pecas) / len(pecas), 1), len(pecas)


def _rollup_absenteismo(registros: list[dict]) -> tuple[float, int] | None:
    """1 − Σtrabalhados ÷ Σefetivos (razão agregada da Fase 3)."""
    efetivos = sum(r["qtd_efetivos"] for r in registros)
    trabalhados = sum(r["qtd_trabalhados"] for r in registros)
    if efetivos <= 0:
        return None
    return round(1 - trabalhados / efetivos, 4), len(registros)


def _rollup_eficiencia(registros: list[dict]) -> tuple[float, int] | None:
    """% oficial da planilha (Méd. últimas 4 sem ÷ Cap 100%) — um valor por oficina."""
    valores = [r["eficiencia_pct"] for r in registros if r.get("eficiencia_pct") is not None]
    if not valores:
        return None
    return round(sum(valores) / len(valores), 4), len(valores)


def _ultimo_ano(registros: list[dict]) -> int | None:
    """Ano mais recente presente nos registros (None se vazio)."""
    anos = [r["ano"] for r in registros]
    return max(anos) if anos else None


def _total_periodo_recente(
    registros: list[dict], campo_periodo: str
) -> tuple[float, str] | None:
    """Volume de peças do período (mês/semana) mais recente com dado.

    Diferente da média, mostra o **ritmo atual**: o total do último mês ou da
    última semana com produção registrada. Devolve ``(valor, rotulo_periodo)``.
    """
    comdado = [r for r in registros if r.get("pecas") is not None]
    if not comdado:
        return None
    alvo = max(comdado, key=lambda r: r[campo_periodo])
    rotulo = _mes_periodo(alvo) if campo_periodo == "mes" else _semana_periodo(alvo)
    return round(alvo["pecas"], 1), rotulo


def _ranking_metricas(
    prod_mes: dict[str, list[dict]],
    prod_sem: dict[str, list[dict]],
    absent: dict[str, list[dict]],
    efic: dict[str, list[dict]],
) -> dict[str, dict]:
    """Valor de ranking por oficina/métrica: roll-up do ano mais recente.

    Devolve ``{oficina_id: {metrica: {valor, ano, n}}}``. Produtividade entra em
    quatro métricas de volume: ``pecas_mes``/``pecas_semana`` (média de peças por
    período) e ``pecas_mes_total``/``pecas_semana_total`` (total do mês/semana
    mais recente com dado — o ritmo atual). O semáforo (só para eficiência e
    absenteísmo) é aplicado depois, em :func:`_aplicar_semaforo`.
    """
    ranking: dict[str, dict] = defaultdict(dict)

    def preencher(fonte: dict[str, list[dict]], metrica: str, rollup) -> None:
        for oid, regs in fonte.items():
            ano = _ultimo_ano(regs)
            if ano is None:
                continue
            calc = rollup([r for r in regs if r["ano"] == ano])
            if calc is None:
                continue
            valor, n = calc
            ranking[oid][metrica] = {"valor": valor, "ano": ano, "n": n}

    def preencher_total(
        fonte: dict[str, list[dict]], metrica: str, campo_periodo: str
    ) -> None:
        for oid, regs in fonte.items():
            ano = _ultimo_ano(regs)
            if ano is None:
                continue
            calc = _total_periodo_recente(
                [r for r in regs if r["ano"] == ano], campo_periodo
            )
            if calc is None:
                continue
            valor, periodo = calc
            ranking[oid][metrica] = {"valor": valor, "ano": ano, "periodo": periodo}

    preencher(prod_mes, "pecas_mes", _media_volume)
    preencher(prod_sem, "pecas_semana", _media_volume)
    preencher_total(prod_mes, "pecas_mes_total", "mes")
    preencher_total(prod_sem, "pecas_semana_total", "semana")
    preencher(absent, "absenteismo", _rollup_absenteismo)
    preencher(efic, "eficiencia", _rollup_eficiencia)
    return ranking


def _semaforo_absoluto(metrica: str, valor: float) -> str:
    """Semáforo ok/alerta/critico por faixa absoluta (efic e absenteísmo)."""
    if metrica == "eficiencia":
        ok, alerta = FAIXA_EFICIENCIA
        if valor >= ok:
            return "ok"
        return "alerta" if valor >= alerta else "critico"
    if metrica == "absenteismo":
        ok, alerta = FAIXA_ABSENTEISMO
        if valor <= ok:
            return "ok"
        return "alerta" if valor <= alerta else "critico"
    return "neutro"


def _aplicar_semaforo(ranking: dict[str, dict]) -> None:
    """Escreve ``semaforo`` nas células com meta absoluta (mutação in-place).

    Só eficiência e absenteísmo têm semáforo. As métricas de volume
    (``pecas_mes``/``pecas_semana``) ficam sem cor — volume não é qualidade.
    """
    for celulas in ranking.values():
        for metrica, cel in celulas.items():
            if metrica in ("eficiencia", "absenteismo"):
                cel["semaforo"] = _semaforo_absoluto(metrica, cel["valor"])


def _agrupar_por_oficina(registros: Iterable[dict]) -> dict[str, list[dict]]:
    """Indexa uma lista de registros por ``oficina_id``."""
    grupos: dict[str, list[dict]] = defaultdict(list)
    for r in registros:
        grupos[r["oficina_id"]].append(r)
    return grupos


def _treinos_por_oficina(treino_reg: Iterable[dict]) -> dict[str, list[dict]]:
    """Marcos de treino por oficina: ``{modulo, ano, ciclo}`` sem duplicatas."""
    vistos: dict[str, set] = defaultdict(set)
    saida: dict[str, list[dict]] = defaultdict(list)
    for r in treino_reg:
        oid = r["oficina_id"]
        chave = (r.get("modulo"), r.get("ano"), r.get("ciclo"))
        if chave in vistos[oid]:
            continue
        vistos[oid].add(chave)
        saida[oid].append(
            {"modulo": r.get("modulo"), "ano": r.get("ano"), "ciclo": r.get("ciclo")}
        )
    for lista in saida.values():
        lista.sort(key=lambda t: (t["ano"] or 0, t["modulo"] or ""))
    return saida


def montar_oficinas(
    depara_oficinas: list[dict],
    prod_mes: list[dict],
    prod_sem: list[dict],
    absent: list[dict],
    efic: list[dict],
    treino_reg: list[dict],
) -> list[dict]:
    """Monta a lista de oficinas do dashboard (ranking + série + treinos).

    Percorre o De-Para (a dimensão canônica) para não perder oficinas sem
    métrica — elas aparecem no ranking com célula vazia, honrando a regra de
    nunca omitir uma linha por falta de dado.
    """
    prod_mes_g = _agrupar_por_oficina(prod_mes)
    prod_sem_g = _agrupar_por_oficina(prod_sem)
    absent_g = _agrupar_por_oficina(absent)
    efic_g = _agrupar_por_oficina(efic)
    treinos_g = _treinos_por_oficina(treino_reg)

    ranking = _ranking_metricas(prod_mes_g, prod_sem_g, absent_g, efic_g)
    _aplicar_semaforo(ranking)

    oficinas = []
    for o in depara_oficinas:
        oid = o["oficina_id"]
        oficinas.append({
            "oficina_id": oid,
            "nome": o["nome_canonico"],
            "papeis": o.get("papeis", []),
            "ranking": ranking.get(oid, {}),
            # Eficiência não tem série: é a % oficial atual da planilha (fica no
            # ranking). Produtividade vira volume em duas linhas do tempo
            # (peças/mês e peças/semana); absenteísmo é mensal.
            "series": {
                "pecas_mes": _serie_mensal(prod_mes_g.get(oid, []), "pecas"),
                "pecas_semana": _serie_semanal(prod_sem_g.get(oid, []), "pecas"),
                "absenteismo": _serie_mensal(absent_g.get(oid, []), "absenteismo_pct"),
            },
            "treinos": treinos_g.get(oid, []),
        })
    oficinas.sort(key=lambda x: x["nome"])
    return oficinas


def montar_payload(
    depara_oficinas: list[dict],
    resumo: dict,
    prod_mes: list[dict],
    prod_sem: list[dict],
    absent: list[dict],
    efic: list[dict],
    treino_reg: list[dict],
    impacto_por_oficina: list[dict],
    impacto_coorte: list[dict],
) -> dict:
    """Payload completo do dashboard, pronto para gravar como ``dashboard.json``."""
    oficinas = montar_oficinas(
        depara_oficinas, prod_mes, prod_sem, absent, efic, treino_reg
    )
    return {
        "resumo": resumo,
        "sentido": SENTIDO,
        "faixas": {
            "eficiencia": FAIXA_EFICIENCIA,
            "absenteismo": FAIXA_ABSENTEISMO,
            "pecas_mes": "sem semáforo (volume de produção)",
            "pecas_semana": "sem semáforo (volume de produção)",
            "pecas_mes_total": "sem semáforo (total do mês recente)",
            "pecas_semana_total": "sem semáforo (total da semana recente)",
        },
        "oficinas": oficinas,
        "impacto_por_oficina": impacto_por_oficina,
        "impacto_coorte": impacto_coorte,
    }
