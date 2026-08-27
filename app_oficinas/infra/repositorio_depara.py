"""Serialização do De-Para para disco (JSON para o frontend, CSV para humanos)."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from app_oficinas.domain.models import Oficina


def oficina_para_dict(oficina: Oficina) -> dict:
    """Projeta uma ``Oficina`` num dicionário serializável e estável."""
    return {
        "oficina_id": oficina.oficina_id,
        "nome_canonico": oficina.nome_canonico,
        "nome_base": oficina.nome_base,
        "fontes": sorted(oficina.fontes),
        "papeis": sorted(oficina.papeis),
        "unidades": sorted(oficina.unidades),
        "precisa_revisao": oficina.precisa_revisao,
        "revisao": list(oficina.revisao),
        "variantes": sorted(
            {v.nome_cru for v in oficina.variantes}
        ),
        "qtd_variantes": len({v.nome_cru for v in oficina.variantes}),
    }


def salvar_json(
    oficinas: list[Oficina], resumo: dict, caminho: Path, erros: list[str] | None = None
) -> None:
    """Grava o De-Para completo em JSON (consumido pela página de revisão)."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "resumo": resumo,
        "erros": erros or [],
        "oficinas": [oficina_para_dict(o) for o in oficinas],
    }
    caminho.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def salvar_csv(oficinas: list[Oficina], caminho: Path) -> None:
    """Grava uma visão tabular do De-Para para conferência em planilha."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8-sig", newline="") as arq:
        escritor = csv.writer(arq, delimiter=";")
        escritor.writerow(
            ["oficina_id", "nome_canonico", "papeis",
             "unidades", "precisa_revisao", "revisao", "variantes"]
        )
        for o in oficinas:
            d = oficina_para_dict(o)
            escritor.writerow([
                d["oficina_id"], d["nome_canonico"],
                "|".join(d["papeis"]), "|".join(d["unidades"]),
                "sim" if d["precisa_revisao"] else "nao",
                " / ".join(d["revisao"]), " | ".join(d["variantes"]),
            ])
