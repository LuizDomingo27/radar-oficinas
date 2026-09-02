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
    build_explicacao,
    build_fatos,
    build_impacto,
    build_metricas,
    build_qualidade,
)

# Ordem obrigatória: cada passo consome os JSONs gravados pelo anterior.
# Chamamos ``executar`` (não ``main``): ``main`` reprocessa ``argparse`` sobre o
# ``sys.argv`` do processo — inofensivo na CLI, mas frágil quando o app Streamlit
# chama o pipeline (o argv é o do Streamlit). ``executar`` roda o trabalho puro e
# devolve o código de saída (0 = ok). Qualidade é independente (lê o "Indicador
# geral"); Explicação lê o dashboard.json, então fecham a fila.
PASSOS = (
    ("1/7 De-Para", build_depara.executar),
    ("2/7 Fatos (ETL)", build_fatos.executar),
    ("3/7 Métricas", build_metricas.executar),
    ("4/7 Impacto", build_impacto.executar),
    ("5/7 Dashboard", build_dashboard.executar),
    ("6/7 Qualidade", build_qualidade.executar),
    ("7/7 Explicação", build_explicacao.executar),
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
