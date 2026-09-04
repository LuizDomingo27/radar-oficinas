/* Controlador do dashboard (Fase 5).
   Responsabilidades: carregar data/dashboard.json, alternar entre as três telas
   e renderizar tabelas/controles, delegando os gráficos a GraficosDash. Sem
   regra de negócio — o backend (build_dashboard) já consolidou tudo. */

// Papéis exibidos como tags na ficha (quais dados a oficina tem).
const PAPEIS = [
  { chave: "producao", rotulo: "Produção" },
  { chave: "absenteismo", rotulo: "Absenteísmo" },
  { chave: "eficiencia", rotulo: "Eficiência" },
  { chave: "treino", rotulo: "Treino" },
];

const estado = {
  dados: null,
  view: "ranking",
  rank: { termo: "", ordena: "nome", metricaGrafico: "pecas_mes" },
  fichaId: null,
};

const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);
const norm = (t) => (t || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
const escapar = (t) => String(t).replace(/[&<>"]/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const icone = (id, cls = "icon") => `<svg class="${cls}" aria-hidden="true"><use href="#ic-${id}"></use></svg>`;
const fmtPct = (v) => v == null ? "—" : (v * 100).toFixed(1) + "%";
const fmtInt = (v) => v == null ? "—" : Math.round(v).toLocaleString("pt-BR");
// Eficiência e absenteísmo são frações (%); produção é volume de peças (inteiro).
const PCT_METRICAS = new Set(["absenteismo", "eficiencia"]);
const fmtValor = (metrica, v) =>
  v == null ? "—" : PCT_METRICAS.has(metrica) ? fmtPct(v) : fmtInt(v);

/* ---------------- carga ---------------- */
async function carregar() {
  // Quando embutido (ex.: shell Streamlit), os dados vêm injetados no HTML para
  // evitar fetch relativo dentro do iframe. Fora disso, busca o JSON servido.
  if (window.__DASHBOARD__) return window.__DASHBOARD__;
  const candidatos = ["../data/dashboard.json", "data/dashboard.json", "/data/dashboard.json"];
  for (const url of candidatos) {
    try {
      const r = await fetch(url, { cache: "no-store" });
      if (r.ok) return await r.json();
    } catch (_) { /* tenta o próximo */ }
  }
  throw new Error("Não foi possível carregar data/dashboard.json");
}

/* ---------------- navegação entre telas ---------------- */
function mostrarView(nome) {
  estado.view = nome;
  $$(".view").forEach((v) => v.classList.toggle("ativa", v.id === `view-${nome}`));
  $$(".nav-tab[data-view]").forEach((t) => {
    const ativa = t.dataset.view === nome;
    t.classList.toggle("ativa", ativa);
    ativa ? t.setAttribute("aria-current", "page") : t.removeAttribute("aria-current");
  });
  // Os gráficos precisam ser desenhados/medidos com a tela visível.
  if (nome === "ranking") desenharGraficoRanking();
  if (nome === "ficha") desenharFicha();
  if (nome === "qualidade") desenharQualidade();
  requestAnimationFrame(() => GraficosDash.redimensionar());
}

/* ---------------- Tela 1: Ranking ---------------- */
function celulaMetrica(o, metrica) {
  const cel = o.ranking[metrica];
  if (!cel) return `<td class="cel-metrica vazio">—</td>`;
  const txt = fmtValor(metrica, cel.valor);
  // Volume (peças/mês, peças/sem) não tem semáforo — só eficiência e absenteísmo.
  const semaforo = cel.semaforo
    ? `<span class="semaforo ${cel.semaforo}" title="${cel.semaforo} · ano ${cel.ano}"></span>`
    : "";
  // Totais mostram o período de origem (mês/semana mais recente) no tooltip.
  const titulo = cel.periodo ? ` title="${escapar(cel.periodo)}"`
    : cel.ano ? ` title="ano ${cel.ano}"` : "";
  return `<td class="cel-metrica"${titulo}><span class="val">${txt}</span>${semaforo}</td>`;
}

function oficinasOrdenadas() {
  const termo = norm(estado.rank.termo);
  let lista = estado.dados.oficinas.filter((o) => !termo || norm(o.nome).includes(termo));
  const ord = estado.rank.ordena;
  if (ord === "nome") {
    lista = [...lista].sort((a, b) => a.nome.localeCompare(b.nome, "pt"));
  } else {
    const menorMelhor = ord === "absenteismo";
    lista = [...lista].sort((a, b) => {
      const va = a.ranking[ord]?.valor, vb = b.ranking[ord]?.valor;
      if (va == null && vb == null) return a.nome.localeCompare(b.nome, "pt");
      if (va == null) return 1;            // sem dado vai para o fim
      if (vb == null) return -1;
      return menorMelhor ? va - vb : vb - va;
    });
  }
  return lista;
}

function renderRankingTabela() {
  const lista = oficinasOrdenadas();
  const tbody = $("#rank-corpo");
  if (!lista.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="vazio-tabela">${icone("busca")} Nenhuma oficina encontrada.</td></tr>`;
    $("#rank-contador").textContent = "0 oficinas";
    return;
  }
  tbody.innerHTML = lista.map((o) => `
    <tr class="linha-rank" data-id="${o.oficina_id}">
      <td><span class="nome">${escapar(o.nome)}${icone("arrow", "icon ir")}</span></td>
      ${celulaMetrica(o, "pecas_mes")}
      ${celulaMetrica(o, "pecas_mes_total")}
      ${celulaMetrica(o, "pecas_semana")}
      ${celulaMetrica(o, "pecas_semana_total")}
      ${celulaMetrica(o, "absenteismo")}
      ${celulaMetrica(o, "eficiencia")}
    </tr>`).join("");
  $("#rank-contador").textContent = `${lista.length} de ${estado.dados.oficinas.length} oficinas`;
}

function desenharGraficoRanking() {
  GraficosDash.renderRanking($("#grafico-ranking"), estado.dados.oficinas, estado.rank.metricaGrafico);
}

/* ---------------- Tela 2: Ficha ---------------- */
function preencherDatalist() {
  $("#lista-oficinas").innerHTML = estado.dados.oficinas
    .map((o) => `<option value="${escapar(o.nome)}">`).join("");
}

function acharOficinaPorNome(nome) {
  const alvo = norm(nome);
  return estado.dados.oficinas.find((o) => norm(o.nome) === alvo);
}

function selecionarFicha(id) {
  estado.fichaId = id;
  const o = estado.dados.oficinas.find((x) => x.oficina_id === id);
  if (o) $("#ficha-busca").value = o.nome;
  desenharFicha();
}

function desenharFicha() {
  const o = estado.dados.oficinas.find((x) => x.oficina_id === estado.fichaId);
  const conteudo = $("#ficha-conteudo"), vazio = $("#ficha-vazio");
  if (!o) { conteudo.hidden = true; vazio.style.display = ""; return; }
  vazio.style.display = "none"; conteudo.hidden = false;

  $("#ficha-nome").textContent = o.nome;
  $("#ficha-papeis").innerHTML = PAPEIS
    .map((p) => {
      const ativo = o.papeis.includes(p.chave);
      return `<span class="tag ${ativo ? p.chave : "ausente"}"><span class="dot"></span>${p.rotulo}</span>`;
    }).join("");

  const treinos = o.treinos.length
    ? o.treinos.map((t) => {
        // Com data (EP 2025), mostra mm/aaaa; sem data, cai no ano (+ ciclo, se
        // ele acrescenta algo além do próprio ano — ex.: "2021/2022").
        const quando = t.mes
          ? `${String(t.mes).padStart(2, "0")}/${t.ano}`
          : `${t.ano ?? "?"}${t.ciclo && t.ciclo !== String(t.ano) ? " (" + escapar(t.ciclo) + ")" : ""}`;
        return `<span class="treino-chip">${icone("treino")}${escapar(t.modulo || "—")} · ${quando}</span>`;
      }).join("")
    : `<span class="meta-linha">Sem treinamentos registrados.</span>`;
  $("#ficha-treinos").innerHTML = treinos;

  desenharSerie("#grafico-pecas-mes", o.series.pecas_mes, "pecas_mes", o.treinos);
  desenharSerie("#grafico-pecas-sem", o.series.pecas_semana, "pecas_semana", o.treinos);
  desenharSerie("#grafico-abse", o.series.absenteismo, "absenteismo", o.treinos);
  renderFichaEfic(o);
  requestAnimationFrame(() => GraficosDash.redimensionar());
}

function renderFichaEfic(o) {
  const el = $("#ficha-efic");
  const cel = o.ranking.eficiencia;
  if (!cel) {
    el.innerHTML = `<div class="serie-vazia">Sem eficiência registrada na planilha para esta oficina.</div>`;
    return;
  }
  const rotulo = { ok: "na meta (≥ 65%)", alerta: "abaixo da meta (55–65%)", critico: "crítico (< 65%)" }[cel.semaforo] || "";
  el.innerHTML = `
    <div class="efic-num ${cel.semaforo}">${fmtPct(cel.valor)}</div>
    <div class="efic-tag"><span class="semaforo ${cel.semaforo}"></span>${rotulo}</div>
    <div class="efic-nota">Valor oficial da planilha de estoque — média das últimas 4 semanas de
      entrega ÷ capacidade 100%. Referência ${cel.ano}.</div>`;
}

function desenharSerie(sel, serie, metrica, treinos) {
  const el = $(sel);
  if (!serie.length) {
    // Descarta qualquer gráfico antes de trocar o container por uma mensagem —
    // senão a instância fica órfã e o próximo desenho sai em branco.
    GraficosDash.descartar(el);
    el.innerHTML = `<div class="serie-vazia">Sem dados desta métrica para a oficina.</div>`;
    return;
  }
  // Se o container mostrava uma mensagem (sem instância), limpa antes de criar.
  if (!GraficosDash.temInstancia(el)) el.innerHTML = "";
  GraficosDash.renderSerie(el, serie, metrica, treinos);
}

/* ---------------- Tela 3: Impacto ---------------- */
function renderImpactoOficinaTabela() {
  const ok = estado.dados.impacto_por_oficina.filter((l) => l.status === "ok" && l.delta != null);
  ok.sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));
  const tbody = $("#impacto-oficina-corpo");
  if (!ok.length) {
    tbody.innerHTML = `<tr><td colspan="8" class="vazio-tabela">Nenhuma oficina com pré e pós fechados ainda.</td></tr>`;
    return;
  }
  tbody.innerHTML = ok.map((l) => {
    const bom = l.delta * (l.sentido || 1) > 0;
    const delta = `${l.delta > 0 ? "+" : ""}${fmtValor(l.metrica, l.delta)}`;
    return `<tr>
      <td>${escapar(l.oficina_nome)}</td>
      <td>${escapar(l.modulo || "—")}</td>
      <td class="num">${l.ano_treino}</td>
      <td>${escapar(l.metrica)}</td>
      <td class="num">${fmtValor(l.metrica, l.pre_valor)}</td>
      <td class="num">${fmtValor(l.metrica, l.pos_valor)}</td>
      <td class="num ${bom ? "delta-bom" : "delta-ruim"}">${delta}</td>
      <td>${bom ? icone("check") + " melhora" : icone("alerta") + " piora"}</td>
    </tr>`;
  }).join("");
}

/* ---------------- eventos ---------------- */
function ligarEventos() {
  $$(".nav-tab[data-view]").forEach((t) =>
    t.addEventListener("click", () => mostrarView(t.dataset.view)));

  $("#rank-busca").addEventListener("input", (e) => {
    estado.rank.termo = e.target.value; renderRankingTabela();
  });
  $("#rank-ordena").addEventListener("click", (e) => {
    const b = e.target.closest(".chip-btn");
    if (!b) return;
    estado.rank.ordena = b.dataset.ord;
    $$("#rank-ordena .chip-btn").forEach((x) => {
      const on = x === b; x.classList.toggle("ativa", on); x.setAttribute("aria-pressed", String(on));
    });
    renderRankingTabela();
  });
  $("#rank-metrica").addEventListener("change", (e) => {
    estado.rank.metricaGrafico = e.target.value; desenharGraficoRanking();
  });
  $("#rank-corpo").addEventListener("click", (e) => {
    const linha = e.target.closest("tr.linha-rank");
    if (!linha) return;
    mostrarView("ficha");
    selecionarFicha(linha.dataset.id);
  });

  $("#ficha-busca").addEventListener("change", (e) => {
    const o = acharOficinaPorNome(e.target.value);
    if (o) { estado.fichaId = o.oficina_id; desenharFicha(); }
  });

  [["q-ano", "ano"], ["q-mes", "mes"], ["q-min", "min"], ["q-top", "top"], ["q-setor", "setor"]]
    .forEach(([id, chave]) => {
      const el = document.getElementById(id);
      if (!el) return;
      el.addEventListener("change", (e) => {
        const v = e.target.value;
        estadoQ[chave] = (chave === "min" || chave === "top") ? +v : v;
        desenharQualidade();
      });
    });

  $("#tema").addEventListener("click", alternarTema);
}

function alternarTema() {
  const raiz = document.documentElement;
  const escuro = raiz.getAttribute("data-theme") === "dark"
    || (!raiz.getAttribute("data-theme") && matchMedia("(prefers-color-scheme: dark)").matches);
  raiz.setAttribute("data-theme", escuro ? "light" : "dark");
  // Redesenha os gráficos da tela ativa para acompanhar as cores do tema.
  if (estado.view === "ranking") desenharGraficoRanking();
  if (estado.view === "ficha") desenharFicha();
  if (estado.view === "qualidade") desenharQualidade();
}

/* ---------------- Tela 4: Qualidade ---------------- */
/* Dados crus compactos em data/qualidade.json (gerado por build_qualidade).
   Colunas — oficinas: [oficina, ano, mes, n_apr, n_rep, n_conc, soma_2qa, soma_prod];
   causas:  [defeito, tipo, setor, ano, mes, qntd]. O ranking replica a fórmula
   testada em services/qualidade.py. */
const MESES_Q = ["", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
  "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
const estadoQ = { dados: null, ano: "todos", mes: "todos", min: 10, top: 20, setor: null };

async function carregarQualidade() {
  if (window.__QUALIDADE__) return window.__QUALIDADE__;
  const cands = ["../data/qualidade.json", "data/qualidade.json", "/data/qualidade.json"];
  for (const url of cands) {
    try { const r = await fetch(url, { cache: "no-store" }); if (r.ok) return await r.json(); }
    catch (_) { /* tenta o próximo */ }
  }
  return null;
}

function iniciarQualidade() {
  const meta = estadoQ.dados.meta;
  estadoQ.setor = meta.setor_padrao;
  const cap = (s) => s ? s[0] + s.slice(1).toLowerCase() : s;
  $("#q-ano").innerHTML = `<option value="todos">Todos</option>` +
    meta.anos.map((a) => `<option value="${a}">${a}</option>`).join("");
  $("#q-mes").innerHTML = `<option value="todos">Todos</option>` +
    meta.meses.map((m) => `<option value="${m}">${MESES_Q[m]} (${String(m).padStart(2, "0")})</option>`).join("");
  $("#q-setor").innerHTML = meta.setores
    .map((s) => `<option value="${s}"${s === meta.setor_padrao ? " selected" : ""}>${cap(s)}</option>`).join("");
}

function somarOficinasQ() {
  const { dados, ano, mes } = estadoQ;
  const somas = new Map();
  for (const [of, a, m, na, nr, nc, s2, sp] of dados.oficinas) {
    if (ano !== "todos" && a !== +ano) continue;
    if (mes !== "todos" && m !== +mes) continue;
    let s = somas.get(of);
    if (!s) { s = { na: 0, nr: 0, nc: 0, s2: 0, sp: 0 }; somas.set(of, s); }
    s.na += na; s.nr += nr; s.nc += nc; s.s2 += s2; s.sp += sp;
  }
  return somas;
}

function rankingQ(somas, comoNota) {
  const out = [];
  for (const [of, s] of somas) {
    const t = s.na + s.nr + s.nc;
    if (t < estadoQ.min) continue;
    const idx = s.sp > 0 ? s.s2 / s.sp : 0;
    const valor = comoNota ? (0.6 * (s.nr / t) + 0.3 * (s.nc / t) + 0.1 * idx) : idx;
    out.push({ rotulo: of, valor });
  }
  out.sort((a, b) => b.valor - a.valor);
  return out.slice(0, estadoQ.top);
}

function causasQ() {
  const { dados, ano, mes, setor } = estadoQ;
  const somas = new Map();
  for (const [def, tipo, se, a, m, q] of dados.causas) {
    if (!tipo.includes("SEGUNDA")) continue;
    if (setor && se !== setor) continue;
    if (ano !== "todos" && a !== +ano) continue;
    if (mes !== "todos" && m !== +mes) continue;
    somas.set(def, (somas.get(def) || 0) + q);
  }
  const out = [...somas].map(([def, q]) => ({ rotulo: def, valor: q }));
  out.sort((a, b) => b.valor - a.valor);
  return out.slice(0, 10);
}

function desenharBarrasQ(sel, itens, opts) {
  const el = $(sel);
  if (!itens.length) {
    GraficosDash.descartar(el);
    el.innerHTML = `<div class="serie-vazia">Sem dados para o filtro selecionado.</div>`;
    return;
  }
  if (!GraficosDash.temInstancia(el)) el.innerHTML = "";
  GraficosDash.renderBarras(el, itens, opts);
}

function desenharQualidade() {
  const alerta = $("#q-alerta");
  if (!estadoQ.dados) {
    alerta.hidden = false;
    $("#q-alerta-txt").textContent = "Não foi possível carregar data/qualidade.json. Rode: python -m scripts.build_qualidade";
    return;
  }
  const somas = somarOficinasQ();
  if (somas.size === 0) {
    alerta.hidden = false;
    $("#q-alerta-txt").textContent = "Não há inspeções registradas no período selecionado.";
  } else {
    alerta.hidden = true;
  }
  desenharBarrasQ("#g-nota", rankingQ(somas, true), { cor: "--critico", ehPct: true });
  desenharBarrasQ("#g-2qa", rankingQ(somas, false), { cor: "--alerta", ehPct: true });
  desenharBarrasQ("#g-causas", causasQ(), { cor: "--treino", sufixo: "peças" });
  requestAnimationFrame(() => GraficosDash.redimensionar());
}

/* ---------------- init ---------------- */
async function iniciar() {
  ligarEventos();
  try {
    estado.dados = await carregar();
  } catch (err) {
    $("#erro-carga").innerHTML = `<div class="erro-carga">
      <strong>Não foi possível carregar o dashboard.</strong>
      <p>Gere o arquivo e sirva a pasta pela raiz do projeto:</p>
      <p><code>python -m scripts.build_dashboard</code><br>
         <code>python -m http.server</code> e abra <code>/web/</code></p>
      <p style="color:var(--muted)">Detalhe: ${escapar(err.message)}</p></div>`;
    return;
  }
  $("#gerado-em").textContent =
    estado.dados.gerado_em?.replace("T", " ").replace("+00:00", " UTC") || "";
  preencherDatalist();
  renderRankingTabela();
  renderImpactoOficinaTabela();

  // Qualidade carrega em separado (tolerante): a falta do seu JSON não derruba
  // o resto do dashboard — a aba mostra um aviso pedindo o build.
  estadoQ.dados = await carregarQualidade();
  if (estadoQ.dados) iniciarQualidade();

  // Rota inicial: aceita #ficha / #impacto / #qualidade vindos de links externos.
  const hash = (location.hash || "").replace("#", "");
  mostrarView(["ficha", "impacto", "qualidade"].includes(hash) ? hash : "ranking");
}

document.addEventListener("DOMContentLoaded", iniciar);
