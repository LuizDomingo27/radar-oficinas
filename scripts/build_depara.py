"""Entrypoint da Fase 1 — gera o De-Para das oficinas.

Uso:
    python -m scripts.build_depara            # lê da raiz do projeto
    python -m scripts.build_depara --tolerante  # pula fontes com erro

Orquestra as camadas (infra -> serviços -> infra) e grava ``data/depara.json``
e ``data/depara.csv``. Nunca deixa uma exceção esperada escapar sem mensagem.
"""

from __future__ import annotations

import argparse
import sys

from app_oficinas import config
from app_oficinas.errors import RadarError
from app_oficinas.infra import ler_todas
from app_oficinas.infra.repositorio_depara import salvar_csv, salvar_json
from app_oficinas.services.depara import construir_depara, resumo
from app_oficinas.services.normalizacao import criar_variante


def executar(tolerante: bool = False) -> int:
    """Roda o pipeline completo do De-Para. Retorna um código de saída."""
    try:
        registros, erros = ler_todas(tolerante=tolerante)
    except RadarError as exc:
        print(f"ERRO ao ler as planilhas: {exc}", file=sys.stderr)
        print("Dica: rode com --tolerante para pular fontes problemáticas.",
              file=sys.stderr)
        return 1

    variantes = [v for v in map(criar_variante, registros) if v is not None]
    oficinas = construir_depara(variantes)
    stats = resumo(oficinas)

    destino_json = config.DATA_OUT_DIR / "depara.json"
    destino_csv = config.DATA_OUT_DIR / "depara.csv"
    salvar_json(oficinas, stats, destino_json, erros)
    salvar_csv(oficinas, destino_csv)

    print(f"Registros lidos ........ {len(registros)}")
    print(f"Variantes válidas ...... {len(variantes)}")
    print(f"Oficinas canônicas ..... {stats['oficinas']}")
    print(f"  com produção ......... {stats['com_producao']}")
    print(f"  com absenteísmo ...... {stats['com_absenteismo']}")
    print(f"  com eficiência ....... {stats['com_eficiencia']}")
    print(f"  com treino ........... {stats['com_treino']}")
    print(f"  cobrem 3 métricas .... {stats['cobertura_3_metricas']}")
    print(f"  precisam revisão ..... {stats['precisam_revisao']}")
    for erro in erros:
        print(f"AVISO: {erro}", file=sys.stderr)
    print(f"\nGravado: {destino_json}\n         {destino_csv}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera o De-Para das oficinas.")
    parser.add_argument(
        "--tolerante", action="store_true",
        help="pula fontes com erro em vez de abortar",
    )
    args = parser.parse_args()
    return executar(tolerante=args.tolerante)


if __name__ == "__main__":
    raise SystemExit(main())
