"""Motor de impacto (Fase 4) — antes × depois do treinamento.

Responde à pergunta central do projeto: *a oficina que participou de um
treinamento melhorou nas três métricas?* Compara, para cada oficina treinada, a
métrica **antes** e **depois** do treino e contrasta com um **grupo de controle**
de oficinas não treinadas no mesmo período (separa o efeito do treino da
sazonalidade — o clássico diferença-em-diferenças).

Decisões de projeto (fechadas com o usuário):

- **Marco anual, ano do treino como buffer.** O treino só tem ano/ciclo (sem
  mês). A janela *pré* são os anos com dado ANTES do ano do treino; a *pós*, os
  anos DEPOIS. O próprio ano do treino é excluído (carência/maturação).
- **Calcular o que dá + flag explícita.** Onde falta a janela pré ou pós, a
  linha não é omitida: recebe ``status`` = ``sem_pre``/``sem_pos``/``sem_dado``.
  Honra a regra de alertar comparações sem registro. Dada a cobertura curta
  (produtividade e eficiência só têm 2026), a maioria dos pares fica incompleta
  hoje — a máquina fica pronta e preenche conforme o histórico acumula.

Funções puras sobre as séries já periodizadas da Fase 3 (as listas ``registros``
dos ``data/metricas_*.json``) e sobre os treinos (``data/fato_treino.json``). Não
faz I/O; o orquestrador ``scripts/build_impacto.py`` injeta os dados lidos.

Fórmulas de roll-up anual seguem a Fase 3: produtividade = Σpeças ÷ Σminutos,
absenteísmo = 1 − Σtrab ÷ Σefetivos (razão agregada), eficiência = média das
semanas (indicador combinado das bases). Δ = valor_pós − valor_pré; o
``sentido`` diz se subir é bom (+1) ou ruim (−1).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Callable, Iterable

# Sentido de cada métrica: sinal de um Δ "bom" (melhora real da oficina).
SENTIDO = {
    "produtividade": +1,   # peças/minuto — subir é bom
    "eficiencia": +1,      # eficiência % — subir é bom
    "absenteismo": -1,     # absenteísmo % — subir é ruim
}
METRICAS = ("produtividade", "absenteismo", "eficiencia")

# Status de um par pré/pós.
OK = "ok"
SEM_PRE = "sem_pre"
SEM_POS = "sem_pos"
SEM_DADO = "sem_dado"

Bucket = dict
SerieAnual = dict[str, dict[int, Bucket]]  # {oficina_id: {ano: bucket}}
Reducer = Callable[[list[Bucket]], float | None]


# --------------------------------------------------------------------------- #
# Roll-up anual por oficina (a partir das séries mensais/semanais da Fase 3)   #
# --------------------------------------------------------------------------- #

def anual_produtividade(linhas: Iterable[dict]) -> SerieAnual:
    """{oficina_id: {ano: {'pecas', 'minutos'}}} somando as linhas mensais."""
    out: SerieAnual = defaultdict(lambda: defaultdict(lambda: {"pecas": 0.0, "minutos": 0.0}))
    for r in linhas:
        b = out[r["oficina_id"]][r["ano"]]
        b["pecas"] += r.get("pecas") or 0.0
        b["minutos"] += r.get("minutos") or 0.0
    return _congelar(out)


def anual_absenteismo(linhas: Iterable[dict]) -> SerieAnual:
    """{oficina_id: {ano: {'efet', 'trab', 'contr', 'demi'}}} somando os meses."""
    out: SerieAnual = defaultdict(
        lambda: defaultdict(lambda: {"efet": 0.0, "trab": 0.0, "contr": 0.0, "demi": 0.0})
    )
    for r in linhas:
        b = out[r["oficina_id"]][r["ano"]]
        b["efet"] += r.get("qtd_efetivos") or 0.0
        b["trab"] += r.get("qtd_trabalhados") or 0.0
        b["contr"] += r.get("contratacao") or 0.0
        b["demi"] += r.get("demissao") or 0.0
    return _congelar(out)


def anual_eficiencia(linhas: Iterable[dict]) -> SerieAnual:
    """{oficina_id: {ano: {'soma', 'n'}}} — média das semanas de todas as bases.

    A eficiência combina bases de escalas diferentes (JEANS peças 100/70,
    NÃO-JEANS peças/min); aqui vira um indicador único por média simples das
    semanas. Como só há dados de 2026, o par pré/pós ainda não fecha na prática —
    o valor serve de base para quando o histórico crescer.
    """
    out: SerieAnual = defaultdict(lambda: defaultdict(lambda: {"soma": 0.0, "n": 0}))
    for r in linhas:
        efic = r.get("eficiencia_pct")
        if efic is None:
            continue
        b = out[r["oficina_id"]][r["ano"]]
        b["soma"] += efic
        b["n"] += 1
    return _congelar(out)


def _congelar(out: SerieAnual) -> SerieAnual:
    """Converte os defaultdicts aninhados em dicts comuns."""
    return {oid: dict(anos) for oid, anos in out.items()}


# --------------------------------------------------------------------------- #
# Redutores: lista de buckets anuais -> valor da métrica (ou None)             #
# --------------------------------------------------------------------------- #

def _reduz_produtividade(buckets: list[Bucket]) -> float | None:
    pe = sum(b["pecas"] for b in buckets)
    mi = sum(b["minutos"] for b in buckets)
    return round(pe / mi, 4) if mi else None


def _reduz_absenteismo(buckets: list[Bucket]) -> float | None:
    ef = sum(b["efet"] for b in buckets)
    tr = sum(b["trab"] for b in buckets)
    return round(1 - tr / ef, 4) if ef else None


def _reduz_eficiencia(buckets: list[Bucket]) -> float | None:
    n = sum(b["n"] for b in buckets)
    s = sum(b["soma"] for b in buckets)
    return round(s / n, 4) if n else None


def montar_series(prod: Iterable[dict], absent: Iterable[dict],
                  efic: Iterable[dict]) -> dict[str, tuple[SerieAnual, Reducer]]:
    """Empacota as três séries anuais com o redutor de cada métrica."""
    return {
        "produtividade": (anual_produtividade(prod), _reduz_produtividade),
        "absenteismo": (anual_absenteismo(absent), _reduz_absenteismo),
        "eficiencia": (anual_eficiencia(efic), _reduz_eficiencia),
    }


# --------------------------------------------------------------------------- #
# Núcleo: janela pré/pós de uma oficina em torno de um ano de treino          #
# --------------------------------------------------------------------------- #

def _janela(por_ano: dict[int, Bucket], ano_treino: int, reduz: Reducer):
    """Valores pré/pós e Δ para uma oficina, com o ano do treino como buffer.

    Devolve ``(pre_valor, pos_valor, pre_anos, pos_anos, delta, status)``.
    """
    pre_anos = sorted(a for a in por_ano if a < ano_treino)
    pos_anos = sorted(a for a in por_ano if a > ano_treino)
    pre = reduz([por_ano[a] for a in pre_anos]) if pre_anos else None
    pos = reduz([por_ano[a] for a in pos_anos]) if pos_anos else None
    if pre is None and pos is None:
        status, delta = SEM_DADO, None
    elif pre is None:
        status, delta = SEM_PRE, None
    elif pos is None:
        status, delta = SEM_POS, None
    else:
        status, delta = OK, round(pos - pre, 4)
    return pre, pos, pre_anos, pos_anos, delta, status


def extrair_treinos(registros: Iterable[dict]) -> list[tuple[str, str, int]]:
    """Marcos de treino distintos ``(oficina_id, modulo, ano)`` com ano válido."""
    vistos: set[tuple[str, str, int]] = set()
    for r in registros:
        oid, modulo, ano = r.get("oficina_id"), r.get("modulo"), r.get("ano")
        if oid and modulo and ano:
            vistos.add((oid, modulo, int(ano)))
    return sorted(vistos)


def impacto_por_oficina(
    treinos: list[tuple[str, str, int]],
    series: dict[str, tuple[SerieAnual, Reducer]],
    nomes: dict[str, str] | None = None,
) -> list[dict]:
    """Uma linha por (oficina, treino, métrica): pré, pós, Δ e status."""
    nomes = nomes or {}
    linhas: list[dict] = []
    for oid, modulo, ano in treinos:
        for metrica, (por_of, reduz) in series.items():
            pre, pos, pre_anos, pos_anos, delta, status = _janela(
                por_of.get(oid, {}), ano, reduz
            )
            linhas.append({
                "oficina_id": oid,
                "oficina_nome": nomes.get(oid, oid),
                "modulo": modulo,
                "ano_treino": ano,
                "metrica": metrica,
                "sentido": SENTIDO[metrica],
                "pre_valor": pre,
                "pos_valor": pos,
                "pre_anos": pre_anos,
                "pos_anos": pos_anos,
                "delta": delta,
                "status": status,
            })
    return linhas


# --------------------------------------------------------------------------- #
# Grupo de controle e diferença-em-diferenças por coorte (módulo × ano)       #
# --------------------------------------------------------------------------- #

def _treinadas_por_ano(treinos: list[tuple[str, str, int]]) -> dict[int, set[str]]:
    """{ano: {oficina_id, ...}} — quem treinou em cada ano (qualquer módulo)."""
    out: dict[int, set[str]] = defaultdict(set)
    for oid, _modulo, ano in treinos:
        out[ano].add(oid)
    return out


def _deltas_controle(
    ano: int,
    excluidas: set[str],
    series: dict[str, tuple[SerieAnual, Reducer]],
) -> dict[str, list[float]]:
    """Δ das oficinas NÃO treinadas em ``ano``, pela mesma janela pré/pós.

    Depende só do ano-marco (a janela é a mesma para qualquer módulo), então é
    calculado uma vez por ano e reaproveitado por todas as coortes daquele ano.
    """
    out: dict[str, list[float]] = {}
    for metrica, (por_of, reduz) in series.items():
        deltas: list[float] = []
        for oid, por_ano in por_of.items():
            if oid in excluidas:
                continue
            *_, delta, status = _janela(por_ano, ano, reduz)
            if status == OK:
                deltas.append(delta)
        out[metrica] = deltas
    return out


def _media(valores: list[float]) -> float | None:
    return round(sum(valores) / len(valores), 4) if valores else None


def impacto_coorte(
    linhas_oficina: list[dict],
    treinos: list[tuple[str, str, int]],
    series: dict[str, tuple[SerieAnual, Reducer]],
) -> list[dict]:
    """Resumo por coorte (módulo × ano × métrica): treinadas × controle × dif-em-dif."""
    treinadas_ano = _treinadas_por_ano(treinos)
    controle_cache: dict[int, dict[str, list[float]]] = {}

    # Agrupa as linhas por (módulo, ano, métrica) preservando o total de treinadas.
    grupos: dict[tuple[str, int, str], list[dict]] = defaultdict(list)
    for l in linhas_oficina:
        grupos[(l["modulo"], l["ano_treino"], l["metrica"])].append(l)

    resumo: list[dict] = []
    for (modulo, ano, metrica), grupo in grupos.items():
        if ano not in controle_cache:
            controle_cache[ano] = _deltas_controle(ano, treinadas_ano[ano], series)
        deltas_trein = [l["delta"] for l in grupo if l["status"] == OK]
        deltas_ctrl = controle_cache[ano][metrica]
        media_trein = _media(deltas_trein)
        media_ctrl = _media(deltas_ctrl)
        dif = (round(media_trein - media_ctrl, 4)
               if media_trein is not None and media_ctrl is not None else None)
        resumo.append({
            "modulo": modulo,
            "ano_treino": ano,
            "metrica": metrica,
            "sentido": SENTIDO[metrica],
            "n_treinadas": len(grupo),
            "n_delta_treinadas": len(deltas_trein),
            "delta_medio_treinadas": media_trein,
            "n_controle": len(deltas_ctrl),
            "delta_medio_controle": media_ctrl,
            "dif_em_dif": dif,
            "status": OK if media_trein is not None else _motivo_coorte(grupo),
        })
    resumo.sort(key=lambda r: (r["ano_treino"], r["modulo"], r["metrica"]))
    return resumo


def _motivo_coorte(grupo: list[dict]) -> str:
    """Por que a coorte não tem Δ médio — o status pré/pós mais comum."""
    contagem: dict[str, int] = defaultdict(int)
    for l in grupo:
        contagem[l["status"]] += 1
    return max(contagem, key=contagem.get)
