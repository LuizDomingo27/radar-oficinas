"""Entrypoint da Fase 3 — calcula as métricas a partir dos fatos.

Uso:
    python -m scripts.build_metricas              # lê da raiz do projeto
    python -m scripts.build_metricas --tolerante  # pula fontes de nome com erro

Fluxo: reconstrói o De-Para (Fase 1), consolida os fatos (Fase 2) e aplica as
fórmulas de métrica (Fase 3), gravando as séries mensais e semanais em
``data/metricas_*.json``. Produtividade e absenteísmo saem em mês e semana;
eficiência é semanal (as planilhas de estoque são semanais).
"""

from __future__ import annotations

import argparse
import sys

from app_oficinas import config
from app_oficinas.errors import RadarError
from app_oficinas.infra import ler_todas
from app_oficinas.infra.repositorio_fatos import salvar_tabela
from app_oficinas.services import metricas
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
    indice = indexar_por_nome(construir_depara(variantes))
    dados = consolidar(indice)

    prod_mes = metricas.serie_produtividade(dados.producao, metricas.POR_MES)
    prod_sem = metricas.serie_produtividade(dados.producao, metricas.POR_SEMANA)
    abs_mes = metricas.serie_absenteismo(dados.absenteismo, metricas.POR_MES)
    abs_sem = metricas.serie_absenteismo(dados.absenteismo, metricas.POR_SEMANA)
    efic = metricas.serie_eficiencia(dados.eficiencia)

    saidas = {
        "metricas_produtividade_mes": prod_mes,
        "metricas_produtividade_semana": prod_sem,
        "metricas_absenteismo_mes": abs_mes,
        "metricas_absenteismo_semana": abs_sem,
        "metricas_eficiencia": efic,
    }
    for nome, linhas in saidas.items():
        salvar_tabela(linhas, config.DATA_OUT_DIR / f"{nome}.json")

    print(f"Produtividade .... {len(prod_mes)} linhas/mês · {len(prod_sem)} linhas/semana")
    print(f"Absenteísmo ...... {len(abs_mes)} linhas/mês · {len(abs_sem)} linhas/semana")
    print(f"Eficiência ....... {len(efic)} oficinas (% oficial da planilha)")
    for erro in erros:
        print(f"AVISO: {erro}", file=sys.stderr)
    print(f"\nGravado em: {config.DATA_OUT_DIR}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Calcula as métricas (Fase 3).")
    parser.add_argument("--tolerante", action="store_true",
                        help="pula fontes de nome com erro em vez de abortar")
    args = parser.parse_args()
    return executar(tolerante=args.tolerante)


if __name__ == "__main__":
    raise SystemExit(main())
