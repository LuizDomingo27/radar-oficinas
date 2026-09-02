"""Explicação por oficina (Fase 6) — o *porquê* de cada número do ranking.

Funções puras que transformam uma oficina já consolidada no ``dashboard.json``
(ranking + treinos) numa explicação legível: para cada métrica, **como** o valor
foi calculado (a fórmula e os insumos: ano e nº de períodos) e **por que** ele
recebeu aquele semáforo (a faixa que a colocou em ok/alerta/crítico).

Não faz I/O nem recalcula nada — apenas descreve o que a Fase 5 já decidiu, para
que o texto NUNCA divirja do número mostrado no dashboard. O orquestrador
``scripts/build_explicacao.py`` lê o JSON, chama estas funções e grava o HTML.
"""

from __future__ import annotations

from typing import Any

# Rótulo de exibição de cada métrica do ranking.
ROTULOS = {
    "eficiencia": "Eficiência",
    "absenteismo": "Absenteísmo",
    "pecas_mes": "Produtividade — média de peças/mês",
    "pecas_semana": "Produtividade — média de peças/semana",
    "pecas_mes_total": "Produtividade — total do mês mais recente",
    "pecas_semana_total": "Produtividade — total da semana mais recente",
}

# Ordem em que as métricas aparecem na explicação.
ORDEM = ("eficiencia", "absenteismo", "pecas_mes", "pecas_semana",
         "pecas_mes_total", "pecas_semana_total")

# Como cada métrica é obtida (o "como", independente do valor).
COMO = {
    "eficiencia": ("% oficial da planilha de estoque: média das últimas 4 semanas "
                   "de entrega (peças) ÷ capacidade a 100%. Um único valor atual "
                   "por oficina, lido direto da coluna-resumo (não recalculado)."),
    "absenteismo": ("1 − (Σ trabalhados ÷ Σ efetivos) no roll-up do ano mais "
                    "recente com dado. Agrega todos os postos/semanas da oficina "
                    "no ano antes de dividir."),
    "pecas_mes": ("Média das peças entregues por mês, considerando os meses do "
                  "ano mais recente que têm produção registrada."),
    "pecas_semana": ("Média das peças entregues por semana, considerando as "
                     "semanas do ano mais recente com produção registrada."),
    "pecas_mes_total": ("Total de peças do mês mais recente com produção — o "
                        "ritmo atual, sem média."),
    "pecas_semana_total": ("Total de peças da semana mais recente com produção — "
                           "o ritmo atual, sem média."),
}

# Texto amigável de cada semáforo.
_SEMAFORO_TXT = {"ok": "OK", "alerta": "Alerta", "critico": "Crítico"}


def _fmt_pct(valor: float) -> str:
    """Fração 0..1 → percentual com 1 casa (0.7759 → '77,6%')."""
    return f"{valor * 100:.1f}%".replace(".", ",")


def _fmt_num(valor: float) -> str:
    """Número de peças com separador de milhar em pt-BR (4975.5 → '4.975,5')."""
    inteiro = valor == int(valor)
    texto = f"{valor:,.0f}" if inteiro else f"{valor:,.1f}"
    return texto.replace(",", "·").replace(".", ",").replace("·", ".")


def _porque_eficiencia(valor: float, semaforo: str, faixas: list[float]) -> str:
    ok, alerta = faixas
    v = _fmt_pct(valor)
    if semaforo == "ok":
        return (f"{v} está no verde porque é ≥ {_fmt_pct(ok)} (meta de eficiência). "
                f"Quanto maior, melhor.")
    if semaforo == "alerta":
        return (f"{v} ficou em alerta: está abaixo da meta de {_fmt_pct(ok)}, mas "
                f"ainda ≥ {_fmt_pct(alerta)} (piso do alerta).")
    return (f"{v} é crítico porque está abaixo de {_fmt_pct(alerta)} — bem longe "
            f"da meta de {_fmt_pct(ok)}.")


def _porque_absenteismo(valor: float, semaforo: str, faixas: list[float]) -> str:
    ok, alerta = faixas
    v = _fmt_pct(valor)
    if semaforo == "ok":
        return (f"{v} está no verde porque é ≤ {_fmt_pct(ok)} (teto aceitável). "
                f"Aqui, quanto menor, melhor.")
    if semaforo == "alerta":
        return (f"{v} ficou em alerta: passou de {_fmt_pct(ok)}, mas ainda "
                f"≤ {_fmt_pct(alerta)}.")
    return f"{v} é crítico porque passou de {_fmt_pct(alerta)}."


def _explicar_metrica(chave: str, cel: dict, faixas: dict) -> dict[str, Any]:
    """Monta a explicação de uma célula do ranking."""
    valor = cel["valor"]
    percentual = chave in ("eficiencia", "absenteismo")
    valor_fmt = _fmt_pct(valor) if percentual else _fmt_num(valor) + " peças"

    # O "como" ganha os insumos concretos (ano, nº de períodos ou período-alvo).
    como = COMO[chave]
    if "n" in cel:
        unidade = {"absenteismo": "meses", "pecas_mes": "meses",
                   "pecas_semana": "semanas", "eficiencia": "valor(es) de resumo"}
        como += f" Base: {cel['n']} {unidade.get(chave, 'períodos')} de {cel['ano']}."
    elif "periodo" in cel:
        como += f" Período usado: {cel['periodo']}."

    semaforo = cel.get("semaforo")
    if semaforo == "ok" or semaforo == "alerta" or semaforo == "critico":
        if chave == "eficiencia":
            porque = _porque_eficiencia(valor, semaforo, faixas["eficiencia"])
        else:
            porque = _porque_absenteismo(valor, semaforo, faixas["absenteismo"])
    else:
        porque = ("Volume de produção não recebe semáforo — depende do tamanho "
                  "da oficina; serve para comparar ritmo, não qualidade.")

    return {
        "chave": chave,
        "rotulo": ROTULOS.get(chave, chave),
        "valor": valor_fmt,
        "semaforo": semaforo,
        "semaforo_txt": _SEMAFORO_TXT.get(semaforo, "—"),
        "como": como,
        "porque": porque,
    }


def explicar_oficina(oficina: dict, faixas: dict) -> dict[str, Any]:
    """Explicação completa de uma oficina do ``dashboard.json``.

    Percorre as métricas na ordem canônica; lista à parte as que não têm dado,
    honrando a regra de nunca esconder uma lacuna.
    """
    ranking = oficina.get("ranking", {})
    metricas = [
        _explicar_metrica(chave, ranking[chave], faixas)
        for chave in ORDEM
        if chave in ranking
    ]
    sem_dado = [ROTULOS[c] for c in ("eficiencia", "absenteismo", "pecas_mes")
                if c not in ranking]

    treinos = [
        {"modulo": t.get("modulo") or "—", "ano": t.get("ano"),
         "ciclo": t.get("ciclo")}
        for t in oficina.get("treinos", [])
    ]
    return {
        "oficina_id": oficina.get("oficina_id"),
        "nome": oficina.get("nome"),
        "papeis": oficina.get("papeis", []),
        "metricas": metricas,
        "sem_dado": sem_dado,
        "treinos": treinos,
    }


def explicar_todas(oficinas: list[dict], faixas: dict) -> list[dict]:
    """Explica todas as oficinas, ordenadas por nome (como no dashboard)."""
    saida = [explicar_oficina(o, faixas) for o in oficinas]
    saida.sort(key=lambda x: (x["nome"] or "").upper())
    return saida
