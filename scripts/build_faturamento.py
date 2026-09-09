"""Entrypoint da tela de Faturamento — gera ``data/faturamento.json``.

Uso:
    python -m scripts.build_faturamento

Lê a planilha consolidada de faturamento (fornecedor, data de vencimento e
montante), agrega por oficina, mês e semana-do-mês e grava um JSON enxuto que o
frontend filtra ao vivo por ano/mês. É um passo independente (não depende das
outras fases), tal como a Qualidade — só precisa da própria planilha.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from app_oficinas import config
from app_oficinas.errors import RadarError
from app_oficinas.infra.leitor_fatos import ler_faturamento
from app_oficinas.services import faturamento


def executar() -> int:
    try:
        payload = faturamento.consolidar(ler_faturamento())
    except RadarError as exc:
        print(f"ERRO ao gerar o faturamento: {exc}", file=sys.stderr)
        print("Dica: confira se a planilha "
              f"'{config.FATURAMENTO.arquivo}' está em {config.PLANILHAS_DIR} "
              "com a aba e as colunas esperadas.", file=sys.stderr)
        return 1

    payload["gerado_em"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    caminho = config.DATA_OUT_DIR / "faturamento.json"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Títulos válidos ... {payload['linhas']}")
    print(f"Anos .............. {', '.join(map(str, payload['anos']))}")
    print(f"Meses ............. {len(payload['meses'])}")
    print(f"Semanas ........... {len(payload['semanas'])}")
    print(f"Oficinas .......... {len(payload['oficinas']['todos'])}")
    print(f"\nGravado em: {caminho}")
    return 0


def main() -> int:
    return executar()


if __name__ == "__main__":
    raise SystemExit(main())
