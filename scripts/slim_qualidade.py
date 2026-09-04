"""Pré-extrai (e cacheia) só as abas de Qualidade do "Indicador geral".

O "Indicador geral" tem ~24 MB; o custo do build de Qualidade é iterar as abas
RESUMO (~41 mil linhas) e DEFEITOS (~144 mil linhas) pelo openpyxl (~22 s).
Este script lê o Excel UMA vez e grava só as colunas usadas em CSVs compactos
em ``Planilhas/.cache_qualidade/``. A partir daí o build lê os CSVs (~0,3 s).

O cache é validado pelo **hash do arquivo de origem**: enquanto o "Indicador
geral" não mudar, rodar de novo (ou um novo upload que mexa só em outras
planilhas) reaproveita o cache — nada é reprocessado.

    python -m scripts.slim_qualidade          # garante o cache (recria se mudou)
    python -m scripts.slim_qualidade --force  # recria mesmo se o hash bater

Não é um passo obrigatório do pipeline: o build de Qualidade já dispara o cache
sozinho na primeira leitura. Serve para pré-aquecer e conferir o efeito.
"""
from __future__ import annotations

import argparse
import sys
import time

from app_oficinas import config
from app_oficinas.errors import RadarError
from app_oficinas.infra import leitor_qualidade


def executar(forcar: bool = False) -> int:
    src = config.PLANILHAS_DIR / config.QUALIDADE_RESUMO.arquivo
    print(f"Fonte: {src}")
    try:
        inicio = time.time()
        resumo_csv, defeitos_csv = leitor_qualidade.garantir_cache(forcar=forcar)
        dur = time.time() - inicio
    except RadarError as exc:
        print(f"ERRO ao gerar o cache da Qualidade: {exc}", file=sys.stderr)
        return 1

    kb = lambda p: p.stat().st_size // 1024  # noqa: E731
    # dur alto = leu o Excel e recriou; dur baixo = cache válido reaproveitado.
    acao = "recriado (leu o Excel)" if dur > 1 else "reaproveitado (hash bateu)"
    print(f"Cache {acao} em {dur:.1f}s:")
    print(f"  {resumo_csv}  ({kb(resumo_csv)} KB)")
    print(f"  {defeitos_csv}  ({kb(defeitos_csv)} KB)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gera/valida o cache CSV das abas de Qualidade.")
    parser.add_argument("--force", action="store_true",
                        help="recria o cache mesmo se o hash da fonte não mudou")
    args = parser.parse_args()
    return executar(forcar=args.force)


if __name__ == "__main__":
    raise SystemExit(main())
