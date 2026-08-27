"""Entrypoint da Fase 2 — consolida as planilhas nos fatos.

Uso:
    python -m scripts.build_fatos              # lê da raiz do projeto
    python -m scripts.build_fatos --tolerante  # pula fontes de nome com erro

Fluxo: reconstrói o índice canônico do De-Para (Fase 1) em memória, lê as
colunas de valor de cada planilha, resolve o ``oficina_id`` de cada observação
e grava ``data/fato_*.json``. A "Indicador geral" permanece fora, por decisão.
"""

from __future__ import annotations

import argparse
import sys

from app_oficinas import config
from app_oficinas.errors import RadarError
from app_oficinas.infra import ler_todas
from app_oficinas.infra.repositorio_fatos import salvar_consolidado
from app_oficinas.services.consolidacao import consolidar
from app_oficinas.services.depara import construir_depara, indexar_por_nome
from app_oficinas.services.normalizacao import criar_variante


def executar(tolerante: bool = False) -> int:
    try:
        registros, erros = ler_todas(tolerante=tolerante)
    except RadarError as exc:
        print(f"ERRO ao ler as planilhas: {exc}", file=sys.stderr)
        print("Dica: rode com --tolerante para pular fontes problemáticas.",
              file=sys.stderr)
        return 1

    variantes = [v for v in map(criar_variante, registros) if v is not None]
    oficinas = construir_depara(variantes)
    indice = indexar_por_nome(oficinas)

    consolidado = consolidar(indice)
    escritos = salvar_consolidado(consolidado, config.DATA_OUT_DIR)
    stats = consolidado.resumo()

    print(f"Oficinas no De-Para .... {len(oficinas)}")
    print(f"Fatos de produção ...... {stats['producao']}")
    print(f"Fatos de absenteísmo ... {stats['absenteismo']}")
    print(f"Fatos de eficiência .... {stats['eficiencia']}")
    print(f"Fatos de treino ........ {stats['treino']}")
    print(f"Nomes não resolvidos ... {stats['nao_resolvidos']}")
    for erro in erros:
        print(f"AVISO: {erro}", file=sys.stderr)
    print("\nGravado:")
    for nome, caminho in escritos.items():
        print(f"  {nome:20} {caminho}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Consolida os fatos (Fase 2).")
    parser.add_argument(
        "--tolerante", action="store_true",
        help="pula fontes de nome com erro em vez de abortar",
    )
    args = parser.parse_args()
    return executar(tolerante=args.tolerante)


if __name__ == "__main__":
    raise SystemExit(main())
