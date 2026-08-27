/* Camada de gráficos do dashboard (Fase 5) — ECharts.
   Responsabilidade única: desenhar. Recebe dados prontos do controlador; não
   conhece filtros, roteamento nem carga.

   Instâncias: a fonte de verdade é o próprio ECharts (getInstanceByDom). Nunca
   guardamos uma instância cujo DOM possa ser apagado por fora — se o container
   volta a ser um <div> de mensagem, a instância é descartada (dispose) para não
   sobrar um gráfico órfão desenhando no vazio. */

const GraficosDash = (() => {
  const conhecidos = new Set(); // elementos já usados como gráfico (para resize)

  function corTema(nome) {
    return getComputedStyle(document.documentElement).getPropertyValue(nome).trim();
  }

  /** Instância ECharts do elemento (cria na primeira vez, renderer SVG). */
  function inst(el) {
    let g = window.echarts.getInstanceByDom(el);
    if (!g) g = window.echarts.init(el, null, { renderer: "svg" });
    conhecidos.add(el);
    return g;
  }

  function temInstancia(el) { return !!window.echarts.getInstanceByDom(el); }

  /** Descarta o gráfico do elemento — use antes de trocar por uma mensagem. */
  function descartar(el) {
    const g = window.echarts.getInstanceByDom(el);
    if (g) g.dispose();
    conhecidos.delete(el);
  }

  const COR_METRICA = {
    pecas_mes: "--producao",
    pecas_semana: "--producao",
    absenteismo: "--absenteismo",
    eficiencia: "--eficiencia",
  };
  const CORES_SEMAFORO = { ok: "--ok", alerta: "--alerta", critico: "--critico", neutro: "--faint" };

  // Métricas em fração 0..1 (%). O resto é volume de peças (inteiro).
  const ehPercentual = (metrica) => metrica === "absenteismo" || metrica === "eficiencia";

  const base = () => ({
    grid: { left: 8, right: 18, top: 16, bottom: 8, containLabel: true },
    textStyle: { fontFamily: "IBM Plex Sans" },
  });
  const eixoTexto = () => ({ color: corTema("--muted"), fontFamily: "IBM Plex Sans", fontSize: 11 });
  const linhaEixo = () => ({ lineStyle: { color: corTema("--line") } });

  function pctFmt(v) { return (v * 100).toFixed(1) + "%"; }
  function intFmt(v) { return Math.round(v).toLocaleString("pt-BR"); }

  /** Tela 1 — barras horizontais do top-N por métrica (cor = semáforo). */
  function renderRanking(el, oficinas, metrica) {
    if (!window.echarts) return;
    const menorMelhor = metrica === "absenteismo";
    const linhas = oficinas
      .filter((o) => o.ranking[metrica])
      .map((o) => ({ nome: o.nome, cel: o.ranking[metrica] }));
    linhas.sort((a, b) => menorMelhor
      ? a.cel.valor - b.cel.valor : b.cel.valor - a.cel.valor);
    const top = linhas.slice(0, 12).reverse(); // reverse: maior no topo do eixo Y
    const ehPct = ehPercentual(metrica);
    const fmt = (v) => ehPct ? pctFmt(v) : intFmt(v);
    const g = inst(el);
    g.setOption({
      ...base(),
      grid: { left: 8, right: 52, top: 10, bottom: 8, containLabel: true },
      tooltip: {
        trigger: "axis", axisPointer: { type: "shadow" },
        valueFormatter: (v) => ehPct ? pctFmt(v) : intFmt(v) + " peças",
      },
      xAxis: {
        type: "value", axisLabel: { ...eixoTexto(),
          formatter: (v) => ehPct ? Math.round(v * 100) + "%" : intFmt(v) },
        axisLine: linhaEixo(), splitLine: { lineStyle: { color: corTema("--line") } },
      },
      yAxis: {
        type: "category", data: top.map((l) => l.nome),
        axisLabel: { ...eixoTexto(), width: 150, overflow: "truncate" },
        axisLine: linhaEixo(), axisTick: { show: false },
      },
      series: [{
        type: "bar", barWidth: "62%",
        data: top.map((l) => ({
          value: l.cel.valor,
          // Volume não tem semáforo — usa a cor da produção; % usa o semáforo.
          itemStyle: { color: corTema(CORES_SEMAFORO[l.cel.semaforo] || "--producao"), borderRadius: [0, 3, 3, 0] },
        })),
        label: { show: true, position: "right", color: corTema("--muted"),
          fontFamily: "IBM Plex Sans", fontSize: 10.5,
          formatter: (p) => fmt(p.value) },
      }],
    }, true);
  }

  /** Marcos de treino que caem dentro do eixo da série (mesmo ano presente).
   *  Cada marco é uma linha vertical tracejada roxa com uma etiqueta-"chip".
   *  As etiquetas alternam de altura para não colidirem quando os anos ficam
   *  próximos no eixo. */
  function marcasTreino(serie, treinos) {
    if (!serie.length || !treinos.length) return [];
    const treino = corTema("--treino");
    const inkChip = corTema("--surface"); // texto do chip: contrasta em claro e escuro
    const dados = [];
    const vistos = new Set();
    let i = 0;
    for (const t of treinos) {
      if (t.ano == null) continue;
      const alvo = serie.find((p) => p.periodo.startsWith(String(t.ano) + "-"));
      if (!alvo || vistos.has(alvo.periodo)) { if (alvo) vistos.add(alvo.periodo); continue; }
      vistos.add(alvo.periodo);
      const modulo = t.modulo ? t.modulo.split(" ")[0] : "Treino";
      dados.push({
        xAxis: alvo.periodo,
        lineStyle: { color: treino, width: 1.6, type: "dashed", opacity: 0.95 },
        label: {
          show: true, formatter: `${modulo} ${t.ano}`, position: "end",
          rotate: 0, align: "left", distance: 5 + (i % 2) * 15, // abre p/ a direita, fora do eixo Y
          color: inkChip, backgroundColor: treino, padding: [2, 5], borderRadius: 3,
          fontFamily: "IBM Plex Sans", fontSize: 9.5, fontWeight: 600,
        },
      });
      i++;
    }
    return dados;
  }

  /** Tela 2 — série temporal de uma métrica, com marcos de treino e meta. */
  function renderSerie(el, serie, metrica, treinos) {
    if (!window.echarts) return;
    const g = inst(el);
    const cor = corTema(COR_METRICA[metrica] || "--producao");
    const ehPct = ehPercentual(metrica);
    const markLines = marcasTreino(serie, treinos);
    g.setOption({
      ...base(),
      grid: { left: 8, right: 48, top: 42, bottom: 8, containLabel: true }, // topo folgado p/ chips de treino; direita p/ a etiqueta da meta
      tooltip: { trigger: "axis",
        valueFormatter: (v) => v == null ? "—" : (ehPct ? pctFmt(v) : intFmt(v) + " peças") },
      xAxis: {
        type: "category", data: serie.map((p) => p.periodo), boundaryGap: false,
        axisLabel: { ...eixoTexto(), fontSize: 9.5, hideOverlap: true },
        axisLine: linhaEixo(), axisTick: { show: false },
      },
      yAxis: {
        type: "value",
        axisLabel: { ...eixoTexto(), formatter: (v) => ehPct ? Math.round(v * 100) + "%" : intFmt(v) },
        axisLine: { show: false }, splitLine: { show: false }, // sem gridlines horizontais — leitura limpa
      },
      series: [{
        type: "line", smooth: true, symbol: "circle", symbolSize: 5,
        data: serie.map((p) => p.valor),
        lineStyle: { color: cor, width: 2 }, itemStyle: { color: cor },
        areaStyle: { color: cor, opacity: 0.10 },
        // Rótulos com o valor de cada ponto. Em séries densas (semanal) o
        // ECharts esconde os que colidem (hideOverlap) — mantém legível.
        label: { show: true, position: "top", distance: 4,
          color: corTema("--muted"), fontFamily: "IBM Plex Sans", fontSize: 9.5,
          formatter: (p) => p.value == null ? "" : (ehPct ? pctFmt(p.value) : intFmt(p.value)) },
        labelLayout: { hideOverlap: true },
        markLine: markLines.length ? {
          symbol: "none", silent: true, data: markLines,
          // Estilo/etiqueta padrão dos marcos de treino (a meta sobrescreve o seu).
          lineStyle: { color: corTema("--treino"), width: 1.6, type: "dashed", opacity: 0.95 },
        } : undefined,
      }],
    }, true);
  }

  /** Aba Qualidade — barras horizontais genéricas (maior no topo do eixo Y).
   *  itens: [{rotulo, valor}] já ordenados desc. opts: {cor, ehPct, sufixo}. */
  function renderBarras(el, itens, opts = {}) {
    if (!window.echarts) return;
    const cor = opts.cor && opts.cor.startsWith("--") ? corTema(opts.cor)
      : (opts.cor || corTema("--producao"));
    const ehPct = !!opts.ehPct;
    const casas = opts.casas;               // nº de casas decimais (ex.: nota)
    const sufixo = opts.sufixo || "";
    const fmt = (v) => ehPct ? pctFmt(v)
      : casas != null ? v.toFixed(casas)
      : intFmt(v) + (sufixo ? " " + sufixo : "");
    const fmtEixo = (v) => ehPct ? Math.round(v * 100) + "%"
      : casas != null ? v.toFixed(casas) : intFmt(v);
    const dados = itens.slice().reverse(); // maior no topo
    const g = inst(el);
    g.setOption({
      ...base(),
      grid: { left: 8, right: 64, top: 10, bottom: 8, containLabel: true },
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" },
        valueFormatter: fmt },
      xAxis: {
        type: "value",
        axisLabel: { ...eixoTexto(), formatter: fmtEixo },
        axisLine: linhaEixo(), splitLine: { lineStyle: { color: corTema("--line") } },
      },
      yAxis: {
        type: "category", data: dados.map((l) => l.rotulo),
        axisLabel: { ...eixoTexto(), width: 220, overflow: "truncate" },
        axisLine: linhaEixo(), axisTick: { show: false },
      },
      series: [{
        type: "bar", barWidth: "62%",
        data: dados.map((l) => ({ value: l.valor,
          itemStyle: { color: cor, borderRadius: [0, 3, 3, 0] } })),
        label: { show: true, position: "right", color: corTema("--muted"),
          fontFamily: "IBM Plex Sans", fontSize: 10.5, formatter: (p) => fmt(p.value) },
      }],
    }, true);
  }

  function redimensionar() {
    conhecidos.forEach((el) => {
      const g = window.echarts.getInstanceByDom(el);
      if (g) g.resize(); else conhecidos.delete(el);
    });
  }

  return { renderRanking, renderSerie, renderBarras, redimensionar, inst, temInstancia, descartar };
})();

window.addEventListener("resize", () => GraficosDash.redimensionar());
