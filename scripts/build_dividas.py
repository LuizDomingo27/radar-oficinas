"""Entrypoint da tela de Dívidas — gera ``data/dividas.json``.

Uso:
    python -m scripts.build_dividas

Lê a planilha de endividamento (razão social, dívida total, encargos e
tributos), soma por oficina e grava um JSON enxuto que o frontend usa para a
tabela, os KPIs e o gráfico das maiores dívidas. É um passo independente (não
depende das outras fases), tal como a Qualidade e o Faturamento — só precisa da
própria planilha.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from app_oficinas import config
from app_oficinas.errors import RadarError
from app_oficinas.infra.leitor_fatos import ler_endividamento
from app_oficinas.services import dividas


def executar() -> int:
    try:
        payload = dividas.consolidar(ler_endividamento())
    except RadarError as exc:
        print(f"ERRO ao gerar as dívidas: {exc}", file=sys.stderr)
        print("Dica: confira se a planilha "
              f"'{config.ENDIVIDAMENTO.arquivo}' está em {config.PLANILHAS_DIR} "
              "com a aba e as colunas esperadas.", file=sys.stderr)
        return 1

    payload["gerado_em"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    caminho = config.DATA_OUT_DIR / "dividas.json"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Linhas de oficina .. {payload['linhas']}")
    print(f"Oficinas ........... {len(payload['oficinas'])}")
    print(f"Dívida total ....... R$ {payload['total_divida']:,.2f}")
    print(f"Tributos ........... R$ {payload['total_tributos']:,.2f}")
    print(f"Encargos ........... R$ {payload['total_encargos']:,.2f}")
    print(f"\nGravado em: {caminho}")
    return 0


def main() -> int:
    return executar()


if __name__ == "__main__":
    raise SystemExit(main())
