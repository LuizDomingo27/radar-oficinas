"""Entrypoint da Fase 4 — motor de impacto antes × depois do treinamento.

Uso:
    python -m scripts.build_impacto

Lê as saídas já gravadas da Fase 3 (``data/metricas_*.json``), o De-Para
(``data/depara.json``, só para o nome de exibição) e os treinos
(``data/fato_treino.json``), e grava:

- ``data/impacto_por_oficina.json`` — uma linha por (oficina, treino, métrica)
  com pré, pós, Δ e o status da comparação (``ok`` ou o motivo da ausência).
- ``data/impacto_coorte.json`` — resumo por coorte (módulo × ano × métrica):
  Δ médio das treinadas × Δ médio do controle × diferença-em-diferenças.

Reaproveita as leituras cacheadas da Fase 3 em vez de reprocessar as planilhas
(frugalidade de I/O). Rode ``build_metricas`` antes se os JSONs não existirem.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from app_oficinas import config
from app_oficinas.infra.repositorio_fatos import salvar_tabela
from app_oficinas.services import impacto


def _registros(caminho: Path) -> list[dict]:
    """Lê a lista ``registros`` de um JSON gravado pela Fase 2/3."""
    payload = json.loads(caminho.read_text(encoding="utf-8"))
    return payload.get("registros", []) if isinstance(payload, dict) else payload


def _nomes_oficinas(caminho: Path) -> dict[str, str]:
    """Mapa ``oficina_id -> nome_canonico`` a partir do De-Para (se existir)."""
    if not caminho.exists():
        return {}
    payload = json.loads(caminho.read_text(encoding="utf-8"))
    return {o["oficina_id"]: o["nome_canonico"] for o in payload.get("oficinas", [])}


def executar() -> int:
    data = config.DATA_OUT_DIR
    faltando = [
        n for n in ("metricas_produtividade_mes", "metricas_absenteismo_mes",
                    "metricas_eficiencia", "fato_treino")
        if not (data / f"{n}.json").exists()
    ]
    if faltando:
        print("ERRO: faltam saídas da Fase 2/3: "
              + ", ".join(f"{n}.json" for n in faltando), file=sys.stderr)
        print("Dica: rode `python -m scripts.build_metricas` primeiro.",
              file=sys.stderr)
        return 1

    prod = _registros(data / "metricas_produtividade_mes.json")
    absent = _registros(data / "metricas_absenteismo_mes.json")
    efic = _registros(data / "metricas_eficiencia.json")
    treino_reg = _registros(data / "fato_treino.json")
    nomes = _nomes_oficinas(data / "depara.json")

    series = impacto.montar_series(prod, absent, efic)
    treinos = impacto.extrair_treinos(treino_reg)
    por_oficina = impacto.impacto_por_oficina(treinos, series, nomes)
    coorte = impacto.impacto_coorte(por_oficina, treinos, series)

    meta = {
        "janela": "anual; ano do treino excluído como buffer (carência)",
        "tratamento_sem_dado": "linha mantida com status sem_pre/sem_pos/sem_dado",
    }
    salvar_tabela(por_oficina, data / "impacto_por_oficina.json", meta)
    salvar_tabela(coorte, data / "impacto_coorte.json", meta)

    _relatorio(treinos, por_oficina, coorte)
    print(f"\nGravado em: {data}")
    return 0


def _relatorio(treinos, por_oficina, coorte) -> None:
    """Resumo legível no terminal — quanto do antes/depois realmente fecha."""
    ok = sum(1 for l in por_oficina if l["status"] == impacto.OK)
    print(f"Treinos (oficina x modulo x ano) .. {len(treinos)}")
    print(f"Linhas por oficina ................ {len(por_oficina)} "
          f"({ok} com delta, {len(por_oficina) - ok} sem registro numa das janelas)")
    coortes_ok = sum(1 for c in coorte if c["status"] == impacto.OK)
    print(f"Coortes (modulo x ano x metrica) .. {len(coorte)} ({coortes_ok} com delta medio)")
    for c in coorte:
        if c["status"] == impacto.OK and c["dif_em_dif"] is not None:
            print(f"  {c['ano_treino']} | {c['modulo'][:24]:24} | {c['metrica']:13} "
                  f"d_trein={c['delta_medio_treinadas']:+.4f} "
                  f"d_ctrl={c['delta_medio_controle']:+.4f} "
                  f"dif-em-dif={c['dif_em_dif']:+.4f}")


def main() -> int:
    return executar()


if __name__ == "__main__":
    raise SystemExit(main())
