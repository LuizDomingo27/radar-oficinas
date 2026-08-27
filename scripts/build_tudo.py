"""Roda todo o pipeline de uma vez, na ordem correta.

Uso:
    python -m scripts.build_tudo

Executa os cinco passos em sequência — De-Para → Fatos → Métricas → Impacto →
Dashboard —, cada um lendo a saída do anterior. Para na primeira falha (devolve
o código de erro do passo). É o comando para atualizar a aplicação depois de
substituir as planilhas na raiz do projeto.
"""

from __future__ import annotations

from app_oficinas.errors import RadarError
from scripts import (
    build_dashboard,
    build_depara,
    build_fatos,
    build_impacto,
    build_metricas,
    build_qualidade,
)

# Ordem obrigatória: cada passo consome os JSONs gravados pelo anterior.
# Qualidade é independente (lê o "Indicador geral"), então roda por último.
PASSOS = (
    ("1/6 De-Para", build_depara.main),
    ("2/6 Fatos (ETL)", build_fatos.main),
    ("3/6 Métricas", build_metricas.main),
    ("4/6 Impacto", build_impacto.main),
    ("5/6 Dashboard", build_dashboard.main),
    ("6/6 Qualidade", build_qualidade.main),
)


def main() -> int:
    for nome, executar in PASSOS:
        print(f"\n{'=' * 56}\n== {nome}\n{'=' * 56}")
        try:
            codigo = executar()
        except RadarError as erro:
            print(f"\nFALHOU em '{nome}': {erro}")
            print("Corrija a fonte e rode de novo.")
            return 1
        if codigo:
            print(f"\nFALHOU em '{nome}' (código {codigo}). Abortando o restante.")
            return codigo

    print(f"\n{'=' * 56}")
    print("Pipeline completo. Sirva com `python -m http.server 8756` e abra /web/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
