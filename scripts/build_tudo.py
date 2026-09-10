"""Roda todo o pipeline de uma vez, na ordem correta.

Uso:
    python -m scripts.build_tudo

Executa os oito passos em sequência — De-Para → Fatos → Métricas → Impacto →
Dashboard → Qualidade → Faturamento → Dívidas —, cada um lendo a saída do
anterior. Para na primeira falha (devolve o código de erro do passo). É o
comando para atualizar a aplicação depois de substituir as planilhas na raiz do
projeto.
"""

from __future__ import annotations

from app_oficinas.errors import RadarError
from scripts import (
    build_dashboard,
    build_depara,
    build_dividas,
    build_faturamento,
    build_fatos,
    build_impacto,
    build_metricas,
    build_qualidade,
)

# Ordem obrigatória: cada passo consome os JSONs gravados pelo anterior.
# Chamamos ``executar`` (não ``main``): ``main`` reprocessa ``argparse`` sobre o
# ``sys.argv`` do processo — inofensivo na CLI, mas frágil quando o app Streamlit
# chama o pipeline (o argv é o do Streamlit). ``executar`` roda o trabalho puro e
# devolve o código de saída (0 = ok). Qualidade, Faturamento e Dívidas são
# independentes (leem só a própria planilha), então fecham a fila.
PASSOS = (
    ("1/8 De-Para", build_depara.executar),
    ("2/8 Fatos (ETL)", build_fatos.executar),
    ("3/8 Métricas", build_metricas.executar),
    ("4/8 Impacto", build_impacto.executar),
    ("5/8 Dashboard", build_dashboard.executar),
    ("6/8 Qualidade", build_qualidade.executar),
    ("7/8 Faturamento", build_faturamento.executar),
    ("8/8 Dívidas", build_dividas.executar),
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
