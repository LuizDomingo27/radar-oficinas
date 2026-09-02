"""Build da Explicação (Fase 6) — gera ``docs/explicacao_oficinas.html``.

Lê o ``data/dashboard.json`` (o JSON já criado a partir das planilhas) e escreve
um documento navegável que, para CADA oficina, explica **por que** e **como** ela
chegou a cada resultado do ranking: a fórmula, os insumos (ano e nº de períodos)
e o motivo do semáforo. Não abre nenhuma planilha — descreve o que a Fase 5 já
consolidou, então o texto nunca diverge do número exibido no dashboard.

    python -m scripts.build_explicacao

É regenerado a cada "Atualizar dados", junto com os JSONs.
"""
from __future__ import annotations

import html
import json
import sys
from datetime import datetime, timezone

from app_oficinas import config
from app_oficinas.errors import RadarError
from app_oficinas.services import explicacao

ENTRADA = config.DATA_OUT_DIR / "dashboard.json"
SAIDA = config.BASE_DIR / "docs" / "explicacao_oficinas.html"

_CLASSE_SEM = {"ok": "ok", "alerta": "alerta", "critico": "critico"}


def _card_metrica(m: dict) -> str:
    sem = m.get("semaforo")
    selo = ""
    if sem in _CLASSE_SEM:
        selo = (f'<span class="selo {_CLASSE_SEM[sem]}">'
                f'{html.escape(m["semaforo_txt"])}</span>')
    return (
        '<div class="metrica">'
        f'<div class="m-topo"><span class="m-rotulo">{html.escape(m["rotulo"])}</span>'
        f'<span class="m-valor">{html.escape(m["valor"])}</span>{selo}</div>'
        f'<div class="m-como"><b>Como:</b> {html.escape(m["como"])}</div>'
        f'<div class="m-porque"><b>Por quê:</b> {html.escape(m["porque"])}</div>'
        '</div>'
    )


def _card_oficina(o: dict) -> str:
    metricas = "".join(_card_metrica(m) for m in o["metricas"]) or \
        '<div class="vazio">Sem métricas registradas para esta oficina.</div>'
    papeis = ", ".join(html.escape(p) for p in o["papeis"]) or "—"
    sem_dado = ""
    if o["sem_dado"]:
        itens = ", ".join(html.escape(s) for s in o["sem_dado"])
        sem_dado = f'<div class="sem-dado">Sem dado em: {itens}.</div>'
    treinos = ""
    if o["treinos"]:
        linhas = "".join(
            f'<li>{html.escape(t["modulo"])}'
            + (f' — {t["ano"]}' if t["ano"] else "")
            + (f' (ciclo {html.escape(str(t["ciclo"]))})' if t["ciclo"] else "")
            + "</li>"
            for t in o["treinos"]
        )
        treinos = f'<div class="treinos"><b>Treinamentos:</b><ul>{linhas}</ul></div>'
    nome = html.escape(o["nome"] or "(sem nome)")
    return (
        f'<article class="oficina" data-nome="{nome.lower()}">'
        f'<h2>{nome}</h2>'
        f'<div class="papeis">Papéis com dado: {papeis}</div>'
        f'{sem_dado}{metricas}{treinos}'
        '</article>'
    )


def _montar_html(explicacoes: list[dict], gerado_em: str, total: int) -> str:
    cards = "".join(_card_oficina(o) for o in explicacoes)
    return f"""<!doctype html>
<html lang="pt-BR" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Explicação por oficina — Radar de Oficinas</title>
<style>
  :root {{ color-scheme: dark; --bg:#0f141b; --card:#182230; --txt:#e6edf3;
    --sub:#9fb0c3; --linha:#25313f; --ok:#2ea043; --alerta:#d29922; --crit:#f85149; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--txt);
    font:15px/1.5 system-ui,Segoe UI,Roboto,Arial,sans-serif; }}
  header {{ padding:24px 20px; border-bottom:1px solid var(--linha);
    position:sticky; top:0; background:var(--bg); z-index:2; }}
  h1 {{ margin:0 0 6px; font-size:22px; }}
  .intro {{ color:var(--sub); max-width:70ch; }}
  .intro ul {{ margin:8px 0 0; padding-left:18px; }}
  .busca {{ margin-top:14px; width:min(420px,100%); padding:10px 12px;
    border-radius:8px; border:1px solid var(--linha); background:var(--card);
    color:var(--txt); font-size:15px; }}
  main {{ padding:20px; display:grid; gap:16px;
    grid-template-columns:repeat(auto-fill,minmax(340px,1fr)); }}
  .oficina {{ background:var(--card); border:1px solid var(--linha);
    border-radius:12px; padding:16px; }}
  .oficina h2 {{ margin:0 0 4px; font-size:17px; }}
  .papeis, .sem-dado {{ color:var(--sub); font-size:13px; margin-bottom:8px; }}
  .sem-dado {{ color:var(--alerta); }}
  .metrica {{ border-top:1px solid var(--linha); padding:10px 0; }}
  .m-topo {{ display:flex; align-items:baseline; gap:8px; flex-wrap:wrap; }}
  .m-rotulo {{ font-weight:600; }}
  .m-valor {{ margin-left:auto; font-variant-numeric:tabular-nums; font-weight:700; }}
  .selo {{ font-size:11px; padding:2px 8px; border-radius:999px; font-weight:700; }}
  .selo.ok {{ background:rgba(46,160,67,.18); color:var(--ok); }}
  .selo.alerta {{ background:rgba(210,153,34,.18); color:var(--alerta); }}
  .selo.critico {{ background:rgba(248,81,73,.18); color:var(--crit); }}
  .m-como, .m-porque {{ color:var(--sub); font-size:13px; margin-top:4px; }}
  .m-porque {{ color:var(--txt); }}
  .treinos {{ margin-top:10px; font-size:13px; color:var(--sub); }}
  .treinos ul {{ margin:4px 0 0; padding-left:18px; }}
  .vazio {{ color:var(--sub); font-style:italic; }}
  footer {{ padding:16px 20px; color:var(--sub); font-size:12px; }}
</style>
</head>
<body>
<header>
  <h1>Explicação por oficina</h1>
  <div class="intro">
    Por que cada oficina chegou a cada resultado do ranking. Para cada métrica há
    <b>Como</b> (a fórmula e os insumos) e <b>Por quê</b> (o motivo do semáforo).
    <ul>
      <li><b>Eficiência</b> — % oficial da planilha (média das últimas 4 semanas de
        entrega ÷ capacidade 100%). Verde ≥ 65%, alerta ≥ 55%, senão crítico.</li>
      <li><b>Absenteísmo</b> — 1 − (trabalhados ÷ efetivos) no ano recente.
        Verde ≤ 5%, alerta ≤ 10%, senão crítico.</li>
      <li><b>Produtividade</b> — volume de peças (média por mês/semana e total do
        período mais recente). Sem semáforo: depende do tamanho da oficina.</li>
    </ul>
  </div>
  <input id="busca" class="busca" type="search"
    placeholder="Filtrar por nome da oficina…" aria-label="Filtrar oficinas">
</header>
<main id="lista">
{cards}
</main>
<footer>Gerado em {html.escape(gerado_em)} · {total} oficinas · fonte: data/dashboard.json</footer>
<script>
  const b = document.getElementById('busca'), lista = document.getElementById('lista');
  b.addEventListener('input', () => {{
    const q = b.value.trim().toLowerCase();
    for (const el of lista.children)
      el.style.display = !q || el.dataset.nome.includes(q) ? '' : 'none';
  }});
</script>
</body>
</html>
"""


def executar() -> int:
    """Gera o HTML de explicação a partir do dashboard.json. 0 = ok, 1 = falhou."""
    if not ENTRADA.exists():
        print(f"ERRO: {ENTRADA} não existe. Rode o build do dashboard antes.",
              file=sys.stderr)
        return 1
    try:
        doc = json.loads(ENTRADA.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERRO ao ler {ENTRADA.name}: {exc}", file=sys.stderr)
        return 1

    oficinas = doc.get("oficinas", [])
    faixas = doc.get("faixas", {})
    # Normaliza as faixas (podem vir como lista no JSON) para (ok, alerta).
    faixas = {
        "eficiencia": list(faixas.get("eficiencia", (0.65, 0.55)))[:2],
        "absenteismo": list(faixas.get("absenteismo", (0.05, 0.10)))[:2],
    }
    explicacoes = explicacao.explicar_todas(oficinas, faixas)

    gerado = datetime.now(timezone.utc).astimezone().strftime("%d/%m/%Y %H:%M")
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(_montar_html(explicacoes, gerado, len(explicacoes)),
                     encoding="utf-8")
    print(f"OK -> {SAIDA}  ({len(explicacoes)} oficinas, "
          f"{SAIDA.stat().st_size // 1024} KB)")
    return 0


def main() -> int:
    return executar()


if __name__ == "__main__":
    raise SystemExit(main())
