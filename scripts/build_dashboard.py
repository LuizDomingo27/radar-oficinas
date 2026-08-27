"""Entrypoint da Fase 5 — consolida o payload único do dashboard.

Uso:
    python -m scripts.build_dashboard

Lê as saídas já gravadas das fases anteriores (o De-Para, as métricas da Fase 3
e as tabelas de impacto da Fase 4) e grava ``data/dashboard.json`` — o objeto
enxuto que alimenta as três telas do frontend (Ranking, Ficha, Impacto).

Reaproveita as leituras cacheadas em vez de reprocessar as planilhas
(frugalidade de I/O). Rode as fases anteriores antes se os JSONs não existirem.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from app_oficinas import config
from app_oficinas.infra.repositorio_fatos import salvar_tabela
from app_oficinas.services import dashboard

# Saídas das fases anteriores das quais o dashboard depende.
FONTES = (
    "depara",
    "metricas_produtividade_mes",
    "metricas_produtividade_semana",
    "metricas_absenteismo_mes",
    "metricas_eficiencia",
    "fato_treino",
    "impacto_por_oficina",
    "impacto_coorte",
)


def _registros(caminho: Path) -> list[dict]:
    """Lê a lista ``registros`` (ou a própria lista) de um JSON gravado."""
    payload = json.loads(caminho.read_text(encoding="utf-8"))
    return payload.get("registros", []) if isinstance(payload, dict) else payload


def executar() -> int:
    data = config.DATA_OUT_DIR
    faltando = [n for n in FONTES if not (data / f"{n}.json").exists()]
    if faltando:
        print("ERRO: faltam saídas das fases anteriores: "
              + ", ".join(f"{n}.json" for n in faltando), file=sys.stderr)
        print("Dica: rode build_depara, build_fatos, build_metricas e "
              "build_impacto primeiro.", file=sys.stderr)
        return 1

    depara = json.loads((data / "depara.json").read_text(encoding="utf-8"))
    payload = dashboard.montar_payload(
        depara_oficinas=depara.get("oficinas", []),
        resumo=depara.get("resumo", {}),
        prod_mes=_registros(data / "metricas_produtividade_mes.json"),
        prod_sem=_registros(data / "metricas_produtividade_semana.json"),
        absent=_registros(data / "metricas_absenteismo_mes.json"),
        efic=_registros(data / "metricas_eficiencia.json"),
        treino_reg=_registros(data / "fato_treino.json"),
        impacto_por_oficina=_registros(data / "impacto_por_oficina.json"),
        impacto_coorte=_registros(data / "impacto_coorte.json"),
    )

    meta = {
        "descricao": "payload único das três telas do dashboard (Fase 5)",
        "valor_ranking": "roll-up do ano mais recente com dado (fórmulas da Fase 3)",
    }
    # Reusa o serializador padrão: grava a lista de oficinas + anexa o resto.
    caminho = data / "dashboard.json"
    salvar_tabela(payload["oficinas"], caminho, meta)
    # Reabre para anexar as seções que não são "registros" de oficina.
    doc = json.loads(caminho.read_text(encoding="utf-8"))
    doc["oficinas"] = doc.pop("registros")
    doc["resumo"] = payload["resumo"]
    doc["sentido"] = payload["sentido"]
    doc["faixas"] = payload["faixas"]
    doc["impacto_por_oficina"] = payload["impacto_por_oficina"]
    doc["impacto_coorte"] = payload["impacto_coorte"]
    caminho.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    _relatorio(payload)
    print(f"\nGravado em: {caminho}")
    return 0


def _relatorio(payload: dict) -> None:
    """Resumo legível no terminal — cobertura de cada tela."""
    oficinas = payload["oficinas"]
    com_rank = sum(1 for o in oficinas if o["ranking"])
    com_serie = sum(
        1 for o in oficinas if any(o["series"][m] for m in o["series"])
    )
    com_treino = sum(1 for o in oficinas if o["treinos"])
    coortes_ok = sum(
        1 for c in payload["impacto_coorte"] if c.get("dif_em_dif") is not None
    )
    print(f"Oficinas ..................... {len(oficinas)}")
    print(f"  com ranking (>=1 metrica) .. {com_rank}")
    print(f"  com serie temporal ......... {com_serie}")
    print(f"  com marco de treino ........ {com_treino}")
    print(f"Coortes com dif-em-dif ....... {coortes_ok}")


def main() -> int:
    return executar()


if __name__ == "__main__":
    raise SystemExit(main())
