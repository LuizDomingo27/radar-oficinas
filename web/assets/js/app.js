/* Controlador da página de revisão do De-Para.
   Responsabilidades: carregar dados, aplicar filtros/busca, renderizar a
   tabela HTML e delegar o gráfico à camada Graficos. Sem regra de negócio —
   apenas apresentação do que o backend (data/depara.json) já consolidou. */

const PAPEIS = [
  { chave: "producao", rotulo: "Produção" },
  { chave: "absenteismo", rotulo: "Absent." },
  { chave: "eficiencia", rotulo: "Eficiência" },
  { chave: "treino", rotulo: "Treino" },
];

const estado = {
  oficinas: [],
  termo: "",
  papeisAtivos: new Set(),
  soRevisao: false,
  expandidas: new Set(),
};

const $ = (sel) => document.querySelector(sel);
const norm = (t) => (t || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");

/** Tenta os caminhos prováveis do JSON conforme onde o site é servido. */
async function carregarDados() {
  const candidatos = ["../data/depara.json", "data/depara.json", "/data/depara.json"];
  for (const url of candidatos) {
    try {
      const resp = await fetch(url, { cache: "no-store" });
      if (resp.ok) return await resp.json();
    } catch (_) { /* tenta o próximo */ }
  }
  throw new Error("Não foi possível carregar data/depara.json");
}

function icone(id, cls = "icon") {
  return `<svg class="${cls}" aria-hidden="true"><use href="#ic-${id}"></use></svg>`;
}

/** Aplica busca + filtros de papel + toggle de revisão sobre as oficinas. */
function filtrar() {
  const termo = norm(estado.termo);
  return estado.oficinas.filter((o) => {
    if (estado.soRevisao && !o.precisa_revisao) return false;
    for (const p of estado.papeisAtivos) if (!o.papeis.includes(p)) return false;
    if (!termo) return true;
    const alvo = norm(o.nome_canonico + " " + o.variantes.join(" "));
    return alvo.includes(termo);
  });
}

function tagsPapeis(o) {
  return PAPEIS.map((p) => {
    const ativo = o.papeis.includes(p.chave);
    const cls = ativo ? p.chave : "ausente";
    return `<span class="tag ${cls}" title="${p.rotulo}: ${ativo ? "com dados" : "sem dados"}">
      <span class="dot"></span>${p.rotulo}</span>`;
  }).join("");
}

function linhaDetalhe(o) {
  const variantes = o.variantes.map((v) => `<li>${escapar(v)}</li>`).join("");
  const revisao = o.revisao.length
    ? `<ul class="revisao-lista">${o.revisao
        .map((r) => `<li>${icone("alerta")}<span>${escapar(r)}</span></li>`)
        .join("")}</ul>`
    : `<div class="revisao-vazio">${icone("check")} Sem pendências de revisão.</div>`;
  const unidades = o.unidades.length
    ? `<div class="meta-linha">Unidades: ${o.unidades.join(", ")}</div>` : "";
  return `<tr class="detalhe"><td colspan="4"><div class="detalhe-box">
      <div>
        <h3>Variantes de nome (${o.qtd_variantes})</h3>
        <ul class="variantes">${variantes}</ul>
        ${unidades}
        <div class="meta-linha">ID: ${o.oficina_id} · Fontes: ${o.fontes.join(", ")}</div>
      </div>
      <div><h3>Revisão</h3>${revisao}</div>
    </div></td></tr>`;
}

function render() {
  const dados = filtrar();
  const tbody = $("#corpo-tabela");
  if (!dados.length) {
    tbody.innerHTML = `<tr><td colspan="4" class="vazio-tabela">
      ${icone("busca")} Nenhuma oficina corresponde aos filtros.</td></tr>`;
    $("#contador").textContent = "0 oficinas";
    return;
  }
  const linhas = [];
  for (const o of dados) {
    const aberta = estado.expandidas.has(o.oficina_id);
    const status = o.precisa_revisao
      ? `<span class="status rev">${icone("alerta")} Revisar</span>`
      : `<span class="status ok">${icone("check")} OK</span>`;
    linhas.push(`<tr class="linha ${aberta ? "aberta" : ""}" data-id="${o.oficina_id}">
      <td><span class="nome">${icone("chevron", "icon chev")}${escapar(o.nome_canonico)}</span></td>
      <td><div class="papeis">${tagsPapeis(o)}</div></td>
      <td class="num">${o.qtd_variantes}</td>
      <td>${status}</td></tr>`);
    if (aberta) linhas.push(linhaDetalhe(o));
  }
  tbody.innerHTML = linhas.join("");
  $("#contador").textContent = `${dados.length} de ${estado.oficinas.length} oficinas`;
}

function renderKpis(resumo) {
  $("#kpi-total").textContent = resumo.oficinas;
  $("#kpi-3metricas").textContent = resumo.cobertura_3_metricas;
  $("#kpi-treino").textContent = resumo.com_treino;
  $("#kpi-revisao").textContent = resumo.precisam_revisao;
}

/* ------- utilidades de formatação e segurança ------- */
function escapar(t) {
  return String(t).replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

/* ------- ligação de eventos ------- */
function ligarEventos() {
  $("#busca").addEventListener("input", (e) => { estado.termo = e.target.value; render(); });

  $("#filtros").addEventListener("click", (e) => {
    const btn = e.target.closest(".chip-btn");
    if (!btn) return;
    const p = btn.dataset.papel;
    if (btn.classList.contains("rev")) {
      estado.soRevisao = !estado.soRevisao;
      btn.setAttribute("aria-pressed", String(estado.soRevisao));
    } else {
      estado.papeisAtivos.has(p) ? estado.papeisAtivos.delete(p) : estado.papeisAtivos.add(p);
      btn.setAttribute("aria-pressed", String(estado.papeisAtivos.has(p)));
    }
    render();
  });

  $("#corpo-tabela").addEventListener("click", (e) => {
    const linha = e.target.closest("tr.linha");
    if (!linha) return;
    const id = linha.dataset.id;
    estado.expandidas.has(id) ? estado.expandidas.delete(id) : estado.expandidas.add(id);
    render();
  });

  $("#tema").addEventListener("click", alternarTema);
}

function alternarTema() {
  const raiz = document.documentElement;
  const escuro = raiz.getAttribute("data-theme") === "dark"
    || (!raiz.getAttribute("data-theme")
        && matchMedia("(prefers-color-scheme: dark)").matches);
  raiz.setAttribute("data-theme", escuro ? "light" : "dark");
  Graficos.renderCobertura($("#grafico-cobertura"), estado.oficinas);
}

/* ------- inicialização ------- */
async function iniciar() {
  ligarEventos();
  try {
    const dados = await carregarDados();
    estado.oficinas = dados.oficinas;
    renderKpis(dados.resumo);
    $("#gerado-em").textContent = dados.gerado_em?.replace("T", " ").replace("+00:00", " UTC") || "";
    Graficos.renderCobertura($("#grafico-cobertura"), estado.oficinas);
    render();
  } catch (err) {
    $("#conteudo").innerHTML = `<div class="erro-carga">
      <strong>Não foi possível carregar os dados do De-Para.</strong>
      <p>Gere o arquivo e sirva a pasta pela raiz do projeto:</p>
      <p><code>python -m scripts.build_depara</code><br>
         <code>python -m http.server</code> e abra <code>/web/</code></p>
      <p style="color:var(--muted)">Detalhe: ${escapar(err.message)}</p></div>`;
  }
}

document.addEventListener("DOMContentLoaded", iniciar);
