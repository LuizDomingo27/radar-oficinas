"""Serialização dos fatos consolidados (Fase 2) para JSON.

Um arquivo por fato em ``data/`` — consumidos pela camada de métricas (Fase 3)
e pelo frontend. O ``Periodo`` é achatado em campos de topo (``ano``, ``mes``,
``semana_iso``, ``rotulo_semana``) para facilitar os filtros mês/semana/ano.
"""

from __future__ import annotations

import json
from dataclasses import asdict, fields
from datetime import datetime, timezone
from pathlib import Path

from app_oficinas.domain.models import Periodo


def _achatar(fato) -> dict:
    """Projeta um fato em dicionário, elevando os campos de ``Periodo``."""
    dados = {}
    for campo in fields(fato):
        valor = getattr(fato, campo.name)
        if isinstance(valor, Periodo):
            dados.update(asdict(valor))
        else:
            dados[campo.name] = valor
    return dados


def salvar_fato(fatos: list, caminho: Path, meta: dict | None = None) -> None:
    """Grava uma lista de fatos num JSON com metadados de geração."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total": len(fatos),
        "meta": meta or {},
        "registros": [_achatar(f) for f in fatos],
    }
    caminho.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def salvar_tabela(registros: list[dict], caminho: Path, meta: dict | None = None) -> None:
    """Grava uma lista de dicionários já prontos (ex.: séries de métrica)."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total": len(registros),
        "meta": meta or {},
        "registros": registros,
    }
    caminho.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def salvar_consolidado(consolidado, destino: Path) -> dict[str, Path]:
    """Grava os quatro fatos em ``destino`` e devolve os caminhos escritos."""
    mapa = {
        "fato_producao": consolidado.producao,
        "fato_absenteismo": consolidado.absenteismo,
        "fato_eficiencia": consolidado.eficiencia,
        "fato_treino": consolidado.treino,
    }
    escritos: dict[str, Path] = {}
    for nome, fatos in mapa.items():
        caminho = destino / f"{nome}.json"
        salvar_fato(fatos, caminho)
        escritos[nome] = caminho
    # Diagnóstico dos nomes que não casaram com o De-Para (conferência humana).
    diag = destino / "fatos_nao_resolvidos.json"
    diag.write_text(
        json.dumps(
            {
                "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "total": len(consolidado.nao_resolvidos),
                "nomes": sorted(consolidado.nao_resolvidos),
            },
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )
    escritos["nao_resolvidos"] = diag
    return escritos
