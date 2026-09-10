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
  // Linha de corte do desempenho (produção ÷ capacidade). O gerente ajusta pelo
  // seletor global; reclassifica o semáforo ao vivo, sem recalcular a métrica.
  meta: 0.70,
};

/* Semáforo do desempenho (produção ÷ capacidade) contra a meta escolhida:
   na meta ou acima = ok; até 10 pontos abaixo = alerta; senão crítico.
   A folga de 10 pontos espelha a faixa original (65%→55%). */
const semaforoDesempenho = (valor, meta) =>
  valor == null ? "neutro"
    : valor >= meta ? "ok"
    : valor >= meta - 0.10 ? "alerta" : "critico";

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
// Moeda (R$): valor cheio para tooltips/cards e compacto (mi/mil) para eixos e
// rótulos de barra — o faturamento é da ordem de milhões.
const fmtBRL = (v) => v == null ? "—"
  : v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
// Moeda com 2 casas decimais — usada nos cards da tela de Dívidas (o negócio
// pediu o centavo à mostra nesses KPIs).
const fmtBRL2 = (v) => v == null ? "—"
  : v.toLocaleString("pt-BR", { style: "currency", currency: "BRL",
    minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtBRLcurto = (v) => {
  if (v == null) return "—";
  if (v >= 1e6) return "R$ " + (v / 1e6).toFixed(1).replace(".", ",") + " mi";
  if (v >= 1e3) return "R$ " + Math.round(v / 1e3) + " mil";
  return "R$ " + Math.round(v);
};

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
  if (nome === "faturamento") desenharFaturamento();
  if (nome === "dividas") desenharDividas();
  requestAnimationFrame(() => GraficosDash.redimensionar());
}

/* ---------------- Tela 1: Ranking ---------------- */
function celulaMetrica(o, metrica) {
  const cel = o.ranking[metrica];
  if (!cel) return `<td class="cel-metrica vazio">—</td>`;
  const txt = fmtValor(metrica, cel.valor);
  // Desempenho (eficiência) usa a meta global ao vivo; absenteísmo mantém a faixa
  // fixa do backend. Volume (peças/min) não tem semáforo.
  const semaforo = metrica === "eficiencia"
    ? `<span class="semaforo ${semaforoDesempenho(cel.valor, estado.meta)}" title="meta ${Math.round(estado.meta * 100)}% · ano ${cel.ano}"></span>`
    : cel.semaforo
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
    tbody.innerHTML = `<tr><td colspan="8" class="vazio-tabela">${icone("busca")} Nenhuma oficina encontrada.</td></tr>`;
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
      ${celulaMetrica(o, "min_mes")}
      ${celulaMetrica(o, "absenteismo")}
      ${celulaMetrica(o, "eficiencia")}
    </tr>`).join("");
  $("#rank-contador").textContent = `${lista.length} de ${estado.dados.oficinas.length} oficinas`;
}

function desenharGraficoRanking() {
  GraficosDash.renderRanking($("#grafico-ranking"), estado.dados.oficinas,
    estado.rank.metricaGrafico, estado.meta);
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
  renderTopDesempenho(); // leaderboard independe da oficina selecionada
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
    el.innerHTML = `<div class="serie-vazia">Sem desempenho registrado na planilha para esta oficina.</div>`;
    return;
  }
  const meta = estado.meta;
  const sem = semaforoDesempenho(cel.valor, meta);
  const metaPct = Math.round(meta * 100);
  const rotulo = {
    ok: `na meta (≥ ${metaPct}%)`,
    alerta: `abaixo da meta (${metaPct - 10}–${metaPct}%)`,
    critico: `crítico (< ${metaPct - 10}%)`,
  }[sem] || "";
  el.innerHTML = `
    <div class="efic-num ${sem}">${fmtPct(cel.valor)}</div>
    <div class="efic-tag"><span class="semaforo ${sem}"></span>${rotulo}</div>`;
}

/* ---- Top 10 melhores/piores por desempenho (produção ÷ capacidade) ---- */
function renderTopDesempenho() {
  const comEfic = estado.dados.oficinas
    .filter((o) => o.ranking.eficiencia && o.ranking.eficiencia.valor != null)
    .map((o) => ({ nome: o.nome, id: o.oficina_id, valor: o.ranking.eficiencia.valor }));
  comEfic.sort((a, b) => b.valor - a.valor);

  const melhores = comEfic.slice(0, 10);
  const piores = comEfic.slice(-10).reverse(); // piores primeiro (menor no topo)

  const linha = (r, pos) => `
    <tr class="linha-top" data-id="${r.id}">
      <td class="col-pos">${pos}</td>
      <td>${escapar(r.nome)}</td>
      <td class="num"><span class="val">${fmtPct(r.valor)}</span>
        <span class="semaforo ${semaforoDesempenho(r.valor, estado.meta)}"></span></td>
    </tr>`;

  $("#top-melhores").innerHTML = melhores.length
    ? melhores.map((r, i) => linha(r, i + 1)).join("")
    : `<tr><td colspan="3" class="vazio-tabela">Sem dados de desempenho.</td></tr>`;
  $("#top-piores").innerHTML = piores.length
    ? piores.map((r, i) => linha(r, i + 1)).join("")
    : `<tr><td colspan="3" class="vazio-tabela">Sem dados de desempenho.</td></tr>`;

  const metaPct = Math.round(estado.meta * 100);
  const acima = comEfic.filter((r) => r.valor >= estado.meta).length;
  $("#top-meta-resumo").textContent = comEfic.length
    ? `meta ${metaPct}% · ${acima} de ${comEfic.length} oficinas na meta`
    : "";
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

  // Clique numa linha do Top 10 abre a ficha daquela oficina.
  $(".top-desempenho").addEventListener("click", (e) => {
    const linha = e.target.closest("tr.linha-top");
    if (linha) selecionarFicha(linha.dataset.id);
  });

  // Seletor global da meta de desempenho: reclassifica tudo ao vivo.
  $("#meta-desempenho").addEventListener("change", (e) => {
    estado.meta = +e.target.value;
    aplicarMeta();
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

  // Filtros do Faturamento: ano preenche o gráfico mensal; mês, o semanal.
  // Trocar de filtro reinicia a paginação da tabela (o conjunto muda).
  $("#fat-ano").addEventListener("change", (e) => {
    estadoF.ano = e.target.value;
    estadoF.pagina = 1;
    atualizarMesDisponivel();
    desenharFaturamento();
  });
  $("#fat-mes").addEventListener("change", (e) => {
    estadoF.mes = e.target.value;
    estadoF.pagina = 1;
    desenharFaturamento();
  });
  $("#fat-pag-anterior").addEventListener("click", () => {
    if (estadoF.pagina > 1) { estadoF.pagina--; renderTabelaF(); }
  });
  $("#fat-pag-proxima").addEventListener("click", () => {
    estadoF.pagina++; renderTabelaF();
  });

  // Tela de Dívidas: busca filtra a tabela e volta à 1ª página; paginação.
  $("#div-busca").addEventListener("input", (e) => {
    estadoD.termo = e.target.value; estadoD.pagina = 1; renderTabelaD();
  });
  $("#div-pag-anterior").addEventListener("click", () => {
    if (estadoD.pagina > 1) { estadoD.pagina--; renderTabelaD(); }
  });
  $("#div-pag-proxima").addEventListener("click", () => {
    estadoD.pagina++; renderTabelaD();
  });

  $("#tema").addEventListener("click", alternarTema);
}

/* Reaplica a meta global: atualiza o rótulo do cabeçalho e redesenha o que
   depende dela (tabela de ranking, gráfico de desempenho e a tela de ficha). */
function aplicarMeta() {
  const metaPct = Math.round(estado.meta * 100);
  const sub = $("#th-efic-sub");
  if (sub) sub.textContent = `prod./capac. · meta ${metaPct}%`;
  renderRankingTabela();
  if (estado.view === "ranking" && estado.rank.metricaGrafico === "eficiencia") {
    desenharGraficoRanking();
  }
  if (estado.view === "ficha") desenharFicha();
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
  if (estado.view === "faturamento") desenharFaturamento();
  if (estado.view === "dividas") desenharDividas();
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

/* ---------------- Tela 5: Faturamento ----------------
   Dados em data/faturamento.json (gerado por build_faturamento):
     meses:    [{ano, mes, total}]                         (cronológico)
     semanas:  [{ano, mes, semana, ini, fim, total}]       (semana-do-mês)
     oficinas: {todos:[{nome,total}], "<ano>":[...]}       (desc por total)
     oficinas_mes: {"<ano>-<mm>":[{nome,total}]}            (desc por total)
   O controlador só filtra por ano/mês e formata — o backend já agregou. */
// Linhas por página da tabela "Faturamento completo" (e do detalhamento de
// dívidas): mantém a tabela curta mesmo com dezenas de oficinas.
const POR_PAGINA = 15;
const estadoF = { dados: null, ano: "todos", mes: "todos", pagina: 1 };

async function carregarFaturamento() {
  if (window.__FATURAMENTO__) return window.__FATURAMENTO__;
  const cands = ["../data/faturamento.json", "data/faturamento.json", "/data/faturamento.json"];
  for (const url of cands) {
    try { const r = await fetch(url, { cache: "no-store" }); if (r.ok) return await r.json(); }
    catch (_) { /* tenta o próximo */ }
  }
  return null;
}

function iniciarFaturamento() {
  const d = estadoF.dados;
  $("#fat-ano").innerHTML = `<option value="todos">Todos</option>` +
    d.anos.map((a) => `<option value="${a}">${a}</option>`).join("");
  $("#fat-mes").innerHTML = `<option value="todos">Todos</option>` +
    MESES_Q.slice(1).map((rot, i) => `<option value="${i + 1}">${rot}</option>`).join("");
  atualizarMesDisponivel();
}

/* Mês só faz sentido com um ano escolhido (a semana pertence a um mês de um
   ano). Sem ano, o seletor de mês fica travado em "Todos". */
function atualizarMesDisponivel() {
  const semAno = estadoF.ano === "todos";
  const sel = $("#fat-mes");
  sel.disabled = semAno;
  if (semAno && estadoF.mes !== "todos") { sel.value = "todos"; estadoF.mes = "todos"; }
}

const escopoAno = () => estadoF.ano === "todos" ? "todo o período" : `ano ${estadoF.ano}`;
const escopoF = () => estadoF.mes === "todos"
  ? escopoAno()
  : `${MESES_Q[+estadoF.mes]}/${estadoF.ano}`;

// Faixa "dd–dd/mm" de uma semana a partir das datas ISO ini/fim.
function faixaSemana(s) {
  return `${s.ini.slice(8, 10)}–${s.fim.slice(8, 10)}/${s.ini.slice(5, 7)}`;
}
const rotuloSemana = (s) => `Sem ${s.semana} · ${MESES_Q[s.mes]}/${s.ano} (${faixaSemana(s)})`;

/* No eixo do gráfico semanal vale a semana do ano (ISO), que situa o bloco no
   calendário — "S30" em vez de "S1". Payloads antigos, sem semana_ano, caem no
   número da semana-do-mês para a tela não sair quebrada. */
const rotuloEixoSemana = (s) => s.semana_ano ? `S${s.semana_ano}` : `S${s.semana}`;
const tooltipSemana = (s) => s.semana_ano
  ? `Semana ${s.semana_ano} do ano · ${s.semana}ª de ${MESES_Q[s.mes]}/${s.ano} (${faixaSemana(s)})`
  : rotuloSemana(s);

function mesesEscopoF() {
  const { dados, ano, mes } = estadoF;
  return dados.meses.filter((m) =>
    (ano === "todos" || m.ano === +ano) && (mes === "todos" || m.mes === +mes));
}

/* Recorte apenas anual: Total acumulado, Média mensal e o gráfico mensal
   respondem só ao filtro de ano — escolher um mês não muda esses números. */
function mesesAnoF() {
  const { dados, ano } = estadoF;
  return dados.meses.filter((m) => ano === "todos" || m.ano === +ano);
}

function semanasEscopoF() {
  const { dados, ano, mes } = estadoF;
  return dados.semanas.filter((s) =>
    (ano === "todos" || s.ano === +ano) && (mes === "todos" || s.mes === +mes));
}

function setKpi(idNum, valor, titulo) {
  const el = $(idNum);
  el.textContent = valor == null ? "—" : fmtBRLcurto(valor);
  el.title = valor == null ? "" : (titulo || fmtBRL(valor));
}

function renderKpisF() {
  // Total e média são consolidados do ano (ou de todo o período): o filtro de
  // mês não entra nesse recorte.
  const mesesAno = mesesAnoF();
  const total = mesesAno.reduce((s, m) => s + m.total, 0);
  setKpi("#fat-kpi-total", mesesAno.length ? total : null, fmtBRL(total));
  $("#fat-kpi-total-l").textContent = `Total acumulado · ${escopoAno()}`;

  const media = mesesAno.length ? total / mesesAno.length : null;
  setKpi("#fat-kpi-media", media);

  // Melhor mês: segue o filtro de mês; sem mês, o maior do ano escolhido (ou
  // de todo o período quando não há ano).
  const meses = mesesEscopoF();
  if (meses.length) {
    const melhorMes = meses.reduce((a, b) => b.total > a.total ? b : a);
    setKpi("#fat-kpi-mes", melhorMes.total);
    $("#fat-kpi-mes-l").textContent = estadoF.mes === "todos"
      ? `Maior mês · ${MESES_Q[melhorMes.mes]}/${melhorMes.ano}`
      : `Faturamento do mês · ${MESES_Q[melhorMes.mes]}/${melhorMes.ano}`;
  } else {
    setKpi("#fat-kpi-mes", null);
    $("#fat-kpi-mes-l").textContent = "Mês com maior faturamento";
  }

  // Melhor semana: segue o filtro de mês; sem mês, a maior do escopo do ano
  // (ou de todo o período quando não há ano).
  const semanas = semanasEscopoF();
  if (semanas.length) {
    const melhor = semanas.reduce((a, b) => b.total > a.total ? b : a);
    setKpi("#fat-kpi-semana", melhor.total);
    $("#fat-kpi-semana-l").textContent = "Maior semana · " + rotuloSemana(melhor);
  } else {
    setKpi("#fat-kpi-semana", null);
    $("#fat-kpi-semana-l").textContent = "Semana com maior faturamento";
  }
}

/* Lista de oficinas do escopo atual (ano/mês), decrescente por faturamento —
   base tanto dos "tops" quanto da tabela completa. */
function listaFaturamentoEscopo() {
  const chave = estadoF.ano === "todos" ? "todos" : String(estadoF.ano);
  const chaveMes = `${estadoF.ano}-${String(estadoF.mes).padStart(2, "0")}`;
  return estadoF.mes !== "todos"
    ? (estadoF.dados.oficinas_mes?.[chaveMes] || [])
    : (estadoF.dados.oficinas[chave] || []);
}

/* Linhas extra do tooltip com a dívida da oficina (Descontos + Valor líquido),
   quando ela consta na planilha de endividamento. Sem correspondência, uma nota. */
function extraDividaTooltip(nome) {
  const d = dividaDe(nome);
  if (!d) return [{ sep: true }, { rot: "Dívida", val: "sem registro" }];
  return [
    { sep: true },
    { rot: "Dívida", val: fmtBRL(d.divida_total), destaque: true },
    { rot: "Descontos", val: fmtBRL(d.encargos) },
    { rot: "Valor líquido", val: fmtBRL(d.tributos) },
  ];
}

function renderTopsF() {
  const lista = listaFaturamentoEscopo();
  const comExtra = (o) => ({
    rotulo: o.nome, valor: o.total, extra: extraDividaTooltip(o.nome),
  });
  const maiores = lista.slice(0, 10).map(comExtra);
  const menores = lista.slice(-10).map(comExtra);
  const escopo = `top 10 · ${escopoF()}`;
  $("#fat-tops-escopo").textContent = escopo;
  $("#fat-tops-escopo2").textContent = escopo;
  const opts = { fmt: fmtBRLcurto, fmtEixo: fmtBRLcurto, rotulo: "Faturamento" };
  desenharBarrasF("#fat-g-maiores", maiores, { ...opts, cor: "--ok" });
  desenharBarrasF("#fat-g-menores", menores, { ...opts, cor: "--critico" });
}

/* Tabela "Faturamento completo": todas as oficinas do escopo, 15 por página. */
function renderTabelaF() {
  const lista = listaFaturamentoEscopo();
  const tbody = $("#fat-tabela-corpo");
  $("#fat-tabela-escopo").textContent = escopoF();
  if (!lista.length) {
    tbody.innerHTML = `<tr><td colspan="3" class="vazio-tabela">Sem faturamento para o filtro selecionado.</td></tr>`;
    aplicarPaginacao("#fat-paginacao", "#fat-pag-status", "#fat-pag-anterior", "#fat-pag-proxima", 0, 1);
    return;
  }
  const totalPag = Math.max(1, Math.ceil(lista.length / POR_PAGINA));
  estadoF.pagina = Math.min(Math.max(1, estadoF.pagina), totalPag);
  const ini = (estadoF.pagina - 1) * POR_PAGINA;
  const pagina = lista.slice(ini, ini + POR_PAGINA);
  tbody.innerHTML = pagina.map((o, i) => `
    <tr>
      <td class="col-pos">${ini + i + 1}</td>
      <td>${escapar(o.nome)}</td>
      <td class="num"><span class="val">${fmtBRL(o.total)}</span></td>
    </tr>`).join("");
  aplicarPaginacao("#fat-paginacao", "#fat-pag-status", "#fat-pag-anterior",
    "#fat-pag-proxima", lista.length, estadoF.pagina);
}

/* Ajusta os controles de paginação (status + botões) e mostra/esconde a barra.
   ``total`` é o nº de linhas filtradas; ``pagina`` a página atual (1-based). */
function aplicarPaginacao(selBarra, selStatus, selAnt, selProx, total, pagina) {
  const barra = $(selBarra);
  const totalPag = Math.max(1, Math.ceil(total / POR_PAGINA));
  barra.hidden = total <= POR_PAGINA;
  $(selStatus).textContent = `Página ${pagina} de ${totalPag} · ${total} oficinas`;
  $(selAnt).disabled = pagina <= 1;
  $(selProx).disabled = pagina >= totalPag;
}

function renderMensalF() {
  // A série mensal é a leitura do ano inteiro — filtrar um mês não a reduz.
  const meses = mesesAnoF();
  const anoTodos = estadoF.ano === "todos";
  const itens = meses.map((m) => ({
    rotulo: anoTodos ? `${MESES_Q[m.mes]}/${String(m.ano).slice(2)}` : MESES_Q[m.mes],
    valor: m.total,
    tip: `${MESES_Q[m.mes]}/${m.ano}`,
  }));
  $("#fat-mensal-escopo").textContent = escopoAno();
  desenharColunasF("#fat-g-mensal", itens, { cor: "--accent", fmt: fmtBRL, fmtEixo: fmtBRLcurto },
    "Sem dados de faturamento para o período.");
}

function renderSemanalF() {
  const rot = $("#fat-semanal-escopo");
  if (estadoF.ano === "todos" || estadoF.mes === "todos") {
    rot.textContent = "selecione ano e mês";
    desenharColunasF("#fat-g-semanal", [], {},
      "Selecione um ano e um mês para ver o faturamento semanal.");
    return;
  }
  const itens = semanasEscopoF().map((s) => ({
    rotulo: rotuloEixoSemana(s), valor: s.total, tip: tooltipSemana(s),
  }));
  rot.textContent = `${MESES_Q[+estadoF.mes]}/${estadoF.ano}`;
  desenharColunasF("#fat-g-semanal", itens, { cor: "--eficiencia", fmt: fmtBRL, fmtEixo: fmtBRLcurto },
    "Sem faturamento registrado neste mês.");
}

function desenharBarrasF(sel, itens, opts) {
  const el = $(sel);
  if (!itens.length) {
    GraficosDash.descartar(el);
    el.innerHTML = `<div class="serie-vazia">Sem dados para o filtro selecionado.</div>`;
    return;
  }
  if (!GraficosDash.temInstancia(el)) el.innerHTML = "";
  GraficosDash.renderBarras(el, itens, opts);
}

function desenharColunasF(sel, itens, opts, msgVazio) {
  const el = $(sel);
  if (!itens.length) {
    GraficosDash.descartar(el);
    el.innerHTML = `<div class="serie-vazia">${escapar(msgVazio || "Sem dados.")}</div>`;
    return;
  }
  if (!GraficosDash.temInstancia(el)) el.innerHTML = "";
  GraficosDash.renderColunas(el, itens, opts);
}

function desenharFaturamento() {
  const alerta = $("#fat-alerta");
  if (!estadoF.dados) {
    alerta.hidden = false;
    $("#fat-alerta-txt").textContent =
      "Não foi possível carregar data/faturamento.json. Rode: python -m scripts.build_faturamento";
    return;
  }
  alerta.hidden = true;
  renderKpisF();
  renderTopsF();
  renderMensalF();
  renderSemanalF();
  renderTabelaF();
  requestAnimationFrame(() => GraficosDash.redimensionar());
}

/* ---------------- Tela 6: Dívidas ----------------
   Dados em data/dividas.json (gerado por build_dividas):
     total_divida / total_tributos / total_encargos : somas gerais
     oficinas: [{nome, divida_total, tributos, encargos}]  (desc por dívida)
   Rótulos de tela (só a apresentação; as chaves do payload seguem as mesmas):
     divida_total → "Dívida" · encargos → "Descontos" · tributos → "Valor líquido"
   O controlador só filtra por texto, pagina e formata — o backend já somou. */
const estadoD = { dados: null, termo: "", pagina: 1, index: null };

async function carregarDividas() {
  if (window.__DIVIDAS__) return window.__DIVIDAS__;
  const cands = ["../data/dividas.json", "data/dividas.json", "/data/dividas.json"];
  for (const url of cands) {
    try { const r = await fetch(url, { cache: "no-store" }); if (r.ok) return await r.json(); }
    catch (_) { /* tenta o próximo */ }
  }
  return null;
}

/* Forma comparável de uma razão social: maiúsculas, sem acento, só letras/
   números/espaço (espelha ``services.normalizacao.limpar`` do backend). É a
   chave que casa o nome do fornecedor (faturamento) com a razão social da
   planilha de dívidas, que costuma ser o começo do nome do fornecedor. */
function limparNome(t) {
  return (t || "").normalize("NFKD").replace(/[̀-ͯ]/g, "")
    .toUpperCase().replace(/[^0-9A-Z ]+/g, " ").replace(/\s+/g, " ").trim();
}

/* Palavras genéricas do ramo têxtil: presentes em quase toda razão social, não
   servem para distinguir uma oficina de outra no casamento aproximado. */
const DIV_GENERICOS = new Set(["CONFECCOES", "CONFECAO", "CONFECCAO", "TEXTIL",
  "INDUSTRIA", "COMERCIO", "LTDA", "ME", "EPP", "EIRELI", "CIA", "LTD",
  "SERVICOS", "PRODUCAO", "EMPREENDIMENTOS", "FACCAO", "VESTUARIO", "IND",
  "COM", "ROUPAS"]);

/* Índice das dívidas por nome limpo, para o join com o faturamento. Guarda o
   nome limpo, seus tokens e o registro, ordenado do nome MAIS longo para o mais
   curto — assim o casamento por prefixo prefere a correspondência mais
   específica. */
function construirIndiceDividas(dados) {
  const exato = new Map();
  const pares = [];
  for (const o of dados.oficinas) {
    const chave = limparNome(o.nome);
    if (!chave) continue;
    if (!exato.has(chave)) exato.set(chave, o);
    pares.push({ chave, tokens: chave.split(" "), o });
  }
  pares.sort((a, b) => b.chave.length - a.chave.length);
  return { exato, pares };
}

/* Alinhamento de dois nomes por tokens, do início para o fim. Conta os tokens
   que alinham (iguais, ou um prefixo do outro) e, entre eles, os "fortes":
   palavras reais (≥3 letras) e não genéricas — as que de fato identificam a
   oficina. Um token inicial (1–2 letras) casando com uma palavra longa
   (ex.: "B"→"BRAGA") é aceito no MEIO do nome, mas nunca como 1º token, senão
   uma inicial casaria com qualquer nome ("J"→"JOSENI"). */
function alinhamentoDivida(ft, dt) {
  const n = Math.min(ft.length, dt.length);
  let aligned = 0, fortes = 0;
  for (let i = 0; i < n; i++) {
    const a = ft[i], b = dt[i];
    let kind;
    if (a === b) kind = "exact";
    else if ((a.length >= 3 && b.startsWith(a)) || (b.length >= 3 && a.startsWith(b))) kind = "strong";
    else if (b.startsWith(a) || a.startsWith(b)) kind = "initial";
    else break;
    if (i === 0 && kind === "initial") break;
    aligned++;
    if (kind !== "initial" && Math.max(a.length, b.length) >= 3
        && !DIV_GENERICOS.has(a) && !DIV_GENERICOS.has(b)) fortes++;
  }
  return { aligned, fortes };
}

/* Dívida de uma oficina pelo nome (do faturamento ou da própria tela), ou
   ``null`` se ela não estiver na planilha de endividamento. Três níveis, do
   mais seguro ao mais tolerante: (1) nome limpo idêntico; (2) a razão social da
   dívida é o começo do nome do fornecedor; (3) alinhamento de tokens, para
   nomes que divergem no meio (ex.: "FLAVIA GEORGIA B SILVA…" no faturamento vs
   "FLAVIA GEORGIA BRAGA SILVA…" na dívida). Exige ≥2 tokens alinhados e ≥1
   forte para não casar oficinas diferentes que só compartilham iniciais. */
function dividaDe(nome) {
  if (!estadoD.index) return null;
  const alvo = limparNome(nome);
  if (!alvo) return null;
  const hit = estadoD.index.exato.get(alvo);
  if (hit) return hit;
  for (const { chave, o } of estadoD.index.pares) {
    if (alvo === chave || alvo.startsWith(chave + " ")) return o;
  }
  const ft = alvo.split(" ");
  let melhor = null;
  for (const { tokens, o } of estadoD.index.pares) {
    const { aligned, fortes } = alinhamentoDivida(ft, tokens);
    if (aligned >= 2 && fortes >= 1) {
      const nota = fortes * 1000 + aligned;   // + fortes, depois + tokens
      if (!melhor || nota > melhor.nota) melhor = { nota, o };
    }
  }
  return melhor ? melhor.o : null;
}

function iniciarDividas() {
  estadoD.index = construirIndiceDividas(estadoD.dados);
}

function renderKpisD() {
  const d = estadoD.dados;
  const set = (id, v) => {
    const el = $(id); el.textContent = fmtBRL2(v); el.title = fmtBRL(v);
  };
  // Ordem de negócio: Dívida · Descontos · Valor líquido (Descontos = encargos;
  // Valor líquido = tributos, só o rótulo mudou — as chaves do payload seguem).
  set("#div-kpi-total", d.total_divida);
  set("#div-kpi-encargos", d.total_encargos);
  set("#div-kpi-tributos", d.total_tributos);
  const on = $("#div-kpi-oficinas");
  on.textContent = String(d.oficinas.length); on.title = "";
  // Percentual das oficinas com dívida sobre o total da rede (dataset do
  // ranking). Sem esse dataset carregado, mostra só o rótulo — nunca quebra.
  const totalRede = estado.dados && estado.dados.oficinas
    ? estado.dados.oficinas.length : null;
  $("#div-kpi-oficinas-l").textContent = totalRede
    ? `Oficinas com dívida · ${fmtPct(d.oficinas.length / totalRede)} da rede`
    : "Oficinas com dívida";
}

function renderMaioresD() {
  const top = estadoD.dados.oficinas.slice(0, 12).map((o) => ({
    rotulo: o.nome, valor: o.divida_total,
    extra: [
      { rot: "Descontos", val: fmtBRL(o.encargos) },
      { rot: "Valor líquido", val: fmtBRL(o.tributos) },
    ],
  }));
  desenharBarrasF("#div-g-maiores", top,
    { cor: "--critico", fmt: fmtBRLcurto, fmtEixo: fmtBRLcurto, rotulo: "Dívida" });
}

/* Tabela de detalhamento: filtra por texto, 15 por página, com linha de total
   do conjunto FILTRADO ao pé da última página. */
function renderTabelaD() {
  const termo = norm(estadoD.termo);
  const lista = estadoD.dados.oficinas.filter((o) => !termo || norm(o.nome).includes(termo));
  const tbody = $("#div-tabela-corpo");
  $("#div-tabela-escopo").textContent = termo
    ? `${lista.length} de ${estadoD.dados.oficinas.length} oficinas`
    : `${lista.length} oficinas`;
  if (!lista.length) {
    tbody.innerHTML = `<tr><td colspan="4" class="vazio-tabela">${icone("busca")} Nenhuma oficina encontrada.</td></tr>`;
    aplicarPaginacao("#div-paginacao", "#div-pag-status", "#div-pag-anterior", "#div-pag-proxima", 0, 1);
    return;
  }
  const totalPag = Math.max(1, Math.ceil(lista.length / POR_PAGINA));
  estadoD.pagina = Math.min(Math.max(1, estadoD.pagina), totalPag);
  const ini = (estadoD.pagina - 1) * POR_PAGINA;
  const pagina = lista.slice(ini, ini + POR_PAGINA);
  let html = pagina.map((o) => `
    <tr>
      <td>${escapar(o.nome)}</td>
      <td class="num"><span class="val">${fmtBRL(o.divida_total)}</span></td>
      <td class="num">${fmtBRL(o.encargos)}</td>
      <td class="num">${fmtBRL(o.tributos)}</td>
    </tr>`).join("");
  if (estadoD.pagina === totalPag) {
    const soma = (f) => lista.reduce((s, o) => s + o[f], 0);
    html += `
      <tr class="linha-total">
        <td>Total${termo ? " (filtrado)" : ""}</td>
        <td class="num">${fmtBRL(soma("divida_total"))}</td>
        <td class="num">${fmtBRL(soma("encargos"))}</td>
        <td class="num">${fmtBRL(soma("tributos"))}</td>
      </tr>`;
  }
  tbody.innerHTML = html;
  aplicarPaginacao("#div-paginacao", "#div-pag-status", "#div-pag-anterior",
    "#div-pag-proxima", lista.length, estadoD.pagina);
}

function desenharDividas() {
  const alerta = $("#div-alerta");
  if (!estadoD.dados) {
    alerta.hidden = false;
    $("#div-alerta-txt").textContent =
      "Não foi possível carregar data/dividas.json. Rode: python -m scripts.build_dividas";
    return;
  }
  alerta.hidden = true;
  renderKpisD();
  renderMaioresD();
  renderTabelaD();
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
  preencherDatalist();
  renderRankingTabela();
  renderImpactoOficinaTabela();

  // Qualidade carrega em separado (tolerante): a falta do seu JSON não derruba
  // o resto do dashboard — a aba mostra um aviso pedindo o build.
  estadoQ.dados = await carregarQualidade();
  if (estadoQ.dados) iniciarQualidade();

  // Faturamento carrega em separado (tolerante): a falta do seu JSON não derruba
  // o resto do dashboard — a aba mostra um aviso pedindo o build.
  estadoF.dados = await carregarFaturamento();
  if (estadoF.dados) iniciarFaturamento();

  // Dívidas carrega em separado (tolerante): a falta do seu JSON não derruba o
  // resto do dashboard — a aba mostra um aviso pedindo o build. O índice fica
  // pronto aqui para enriquecer também os tooltips do Faturamento.
  estadoD.dados = await carregarDividas();
  if (estadoD.dados) iniciarDividas();

  // Rota inicial: aceita #ficha / #impacto / #qualidade / #faturamento / #dividas.
  const hash = (location.hash || "").replace("#", "");
  mostrarView(["ficha", "impacto", "qualidade", "faturamento", "dividas"].includes(hash) ? hash : "ranking");
}

document.addEventListener("DOMContentLoaded", iniciar);
