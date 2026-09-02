"""Build da Qualidade — gera ``data/qualidade.json`` para o dashboard.

Lê as abas RESUMO e DEFEITOS do "Indicador geral" (infra/leitor_qualidade),
agrega por (oficina/defeito × ano × mês) (services/qualidade) e grava um JSON
compacto — a única coisa que sobe para a hospedagem, no lugar do Excel de 24 MB.

    python -m scripts.build_qualidade

O frontend (aba Qualidade) aplica os filtros de período e reproduz as fórmulas
de ranking já validadas no serviço.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from app_oficinas import config
from app_oficinas.errors import RadarError
from app_oficinas.infra import leitor_qualidade
from app_oficinas.services import qualidade

SAIDA = config.DATA_OUT_DIR / "qualidade.json"


def _compactar_oficinas(agregados: list[dict]) -> list[list]:
    # Ordem: oficina, ano, mes, n_aprovado, n_reprovado, n_concessao, 2qa, prod.
    return [[r["oficina"], r["ano"], r["mes"], r["n_aprovado"], r["n_reprovado"],
             r["n_concessao"], round(r["soma_2qa"], 2), round(r["soma_prod"], 2)]
            for r in agregados]


def _compactar_causas(agregados: list[dict]) -> list[list]:
    # Ordem: defeito, tipo, setor, ano, mes, qntd.
    return [[r["defeito"], r["tipo"], r["setor"], r["ano"], r["mes"],
             round(r["qntd"], 2)] for r in agregados]


def main() -> None:
    print("Lendo abas RESUMO e DEFEITOS (pode levar ~1 min)...")
    oficinas = qualidade.agregar_oficinas(leitor_qualidade.ler_inspecoes())
    causas = qualidade.agregar_causas(leitor_qualidade.ler_defeitos())
    print(f"  {len(oficinas)} linhas de oficina, {len(causas)} linhas de causa")

    anos = sorted({r["ano"] for r in oficinas}
                  | {r["ano"] for r in causas if r["ano"]})
    meses = sorted({r["mes"] for r in oficinas if r["mes"]})
    setores = sorted({r["setor"] for r in causas if r["setor"]})

    meta = {
        "fonte": config.QUALIDADE_RESUMO.arquivo,
        "anos": anos,
        "meses": meses,
        "setores": setores,
        "setor_padrao": config.CAUSAS_SETOR_PADRAO,
        "pesos": {"reprovado": config.PESO_REPROVADO,
                  "concessao": config.PESO_CONCESSAO, "2qa": config.PESO_2QA},
        "colunas_oficinas": ["oficina", "ano", "mes", "n_aprovado", "n_reprovado",
                             "n_concessao", "soma_2qa", "soma_prod"],
        "colunas_causas": ["defeito", "tipo", "setor", "ano", "mes", "qntd"],
    }
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "meta": meta,
        "oficinas": _compactar_oficinas(oficinas),
        "causas": _compactar_causas(causas),
    }
    SAIDA.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"OK -> {SAIDA}  ({SAIDA.stat().st_size // 1024} KB)")
    print(f"  anos={anos} meses={meses} setores={setores}")


def executar() -> int:
    """Wrapper com código de saída para o orquestrador (0 = ok, 1 = falhou).

    ``main()`` continua levantando ``RadarError`` — o fallback "Qualidade-só" do
    app depende disso. Aqui traduzimos a exceção em código de saída, para que o
    ``build_tudo`` trate todos os passos do mesmo jeito.
    """
    try:
        main()
    except RadarError as exc:
        print(f"ERRO ao gerar a Qualidade: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(executar())
