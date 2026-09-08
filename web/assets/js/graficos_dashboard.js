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
  // Rótulo legível de cada métrica, usado no cabeçalho/linhas do tooltip.
  const ROTULO_METRICA = { pecas_mes: "Peças", pecas_semana: "Peças",
    pecas_mes_total: "Total do mês", pecas_semana_total: "Total da semana",
    min_mes: "Minutos", min_semana: "Minutos",
    absenteismo: "Absenteísmo", eficiencia: "Desempenho" };
  const rotuloMetrica = (m) => ROTULO_METRICA[m] || "Valor";

  // Métricas em fração 0..1 (%). O resto é volume (peças ou minutos, inteiro).
  const ehPercentual = (metrica) => metrica === "absenteismo" || metrica === "eficiencia";

  /* Semáforo do desempenho contra a meta global (espelha o do controlador):
     na meta = ok; até 10 pontos abaixo = alerta; senão crítico. */
  const semDesempenho = (valor, meta) =>
    valor == null ? "neutro"
      : valor >= meta ? "ok"
      : valor >= meta - 0.10 ? "alerta" : "critico";

  const base = () => ({
    grid: { left: 8, right: 18, top: 16, bottom: 8, containLabel: true },
    textStyle: { fontFamily: "IBM Plex Sans" },
  });
  const eixoTexto = () => ({ color: corTema("--muted"), fontFamily: "IBM Plex Sans", fontSize: 11 });
  const linhaEixo = () => ({ lineStyle: { color: corTema("--line") } });

  function pctFmt(v) { return (v * 100).toFixed(1) + "%"; }
  function intFmt(v) { return Math.round(v).toLocaleString("pt-BR"); }

  /* ---- Tooltip moderno, compartilhado por todos os gráficos ----
     Caixa com blur, barra de acento à esquerda, cabeçalho e linhas alinhadas.
     `linhas`: itens {cor?, rot, val, destaque?} ou {sep:true}. Mantém a config
     base (fundo/borda zerados) separada para os gatilhos "axis" e "item". */
  const tipBaseAxis = () => ({ trigger: "axis", backgroundColor: "transparent",
    borderWidth: 0, padding: 0, extraCssText: "box-shadow:none;" });
  const tipBaseItem = () => ({ trigger: "item", backgroundColor: "transparent",
    borderWidth: 0, padding: 0, extraCssText: "box-shadow:none;",
    axisPointer: { type: "shadow" } });

  function caixaTip(titulo, linhas) {
    const surf = corTema("--surface"), line = corTema("--line"), accent = corTema("--accent"),
      ink = corTema("--ink"), muted = corTema("--muted"),
      prod = corTema("--producao"), efic = corTema("--eficiencia");
    const linhaHtml = (it) => {
      if (it.sep) return `<div style="height:1px;background:${line};margin:7px 0 6px 6px;opacity:.7"></div>`;
      const dot = it.cor
        ? `<span style="width:10px;height:10px;border-radius:3px;background:${it.cor};flex:none"></span>` : "";
      return `<div style="display:flex;align-items:center;gap:9px;padding:3px 0 3px 6px;font-size:.86rem;color:${muted}">
        <span style="display:flex;align-items:center;gap:8px">${dot}${it.rot}</span>
        <span style="margin-left:auto;font-weight:600;color:${it.destaque ? efic : ink};font-variant-numeric:tabular-nums">${it.val}</span></div>`;
    };
    return `<div style="position:relative;min-width:186px;border-radius:12px;padding:12px 14px 11px;
      background:color-mix(in srgb, ${surf} 84%, transparent);
      -webkit-backdrop-filter:blur(9px) saturate(1.3);backdrop-filter:blur(9px) saturate(1.3);
      border:1px solid color-mix(in srgb, ${accent} 38%, ${line});
      box-shadow:0 16px 40px rgba(0,0,0,.28),0 2px 6px rgba(0,0,0,.18);overflow:hidden;
      font-family:'IBM Plex Sans',sans-serif">
      <div style="position:absolute;left:0;top:0;bottom:0;width:4px;background:linear-gradient(180deg, ${prod}, ${efic})"></div>
      <div style="font-family:Archivo,'IBM Plex Sans',sans-serif;font-weight:700;font-size:.94rem;color:${ink};margin:0 0 8px;padding-left:6px">${titulo}</div>
      ${linhas.map(linhaHtml).join("")}</div>`;
  }

  /* Tamanho de fonte dos rótulos conforme a largura do container — legível em
     monitores grandes sem espremer em telas estreitas. */
  function escalaRotulo(el) {
    const w = el.clientWidth || 480;
    return w < 380 ? { valor: 10.5, eixo: 9.5 }
      : w < 560 ? { valor: 11.5, eixo: 10.5 }
      : { valor: 12.5, eixo: 11 };
  }

  /** Tela 1 — barras horizontais do top-N por métrica (cor = semáforo).
   *  ``meta`` (fração 0..1) colore o desempenho ao vivo contra a meta global. */
  function renderRanking(el, oficinas, metrica, meta = 0.70) {
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
      tooltip: { ...tipBaseItem(),
        formatter: (p) => caixaTip(p.name, [{ cor: corTema(COR_METRICA[metrica] || "--producao"),
          rot: rotuloMetrica(metrica), val: fmt(p.value) }]) },
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
        data: top.map((l) => {
          // Desempenho: semáforo pela meta global; absenteísmo: faixa do backend;
          // volume (peças/min): sem semáforo, usa a cor da produção.
          const sem = metrica === "eficiencia"
            ? semDesempenho(l.cel.valor, meta) : l.cel.semaforo;
          return {
            value: l.cel.valor,
            itemStyle: { color: corTema(CORES_SEMAFORO[sem] || "--producao"), borderRadius: [0, 3, 3, 0] },
          };
        }),
        label: { show: true, position: "right", color: corTema("--muted"),
          fontFamily: "IBM Plex Sans", fontSize: 10.5,
          formatter: (p) => fmt(p.value) },
      }],
    }, true);
  }

  const MESES_CURTOS = ["", "jan", "fev", "mar", "abr", "mai", "jun",
    "jul", "ago", "set", "out", "nov", "dez"];

  /** Categoria do eixo X onde o marco de treino deve cair, conforme a
   *  granularidade da série (mensal ``AAAA-MM`` ou semanal ``AAAA-Www``).
   *  Usa o mês/semana do treino quando a fonte tem data (EP 2025); se o período
   *  exato não existir na série, ancora no primeiro ponto igual ou posterior
   *  (senão no último). Sem mês/semana, cai no 1º período do ano — o
   *  comportamento antigo das fontes que só têm ano/ciclo. */
  function periodoAlvo(serie, t) {
    if (t.ano == null) return null;
    const semanal = serie[0].periodo.includes("W");
    const ano = String(t.ano);
    let alvo;
    if (semanal) {
      alvo = t.semana_iso ? `${ano}-W${String(t.semana_iso).padStart(2, "0")}` : `${ano}-`;
    } else {
      alvo = t.mes ? `${ano}-${String(t.mes).padStart(2, "0")}` : `${ano}-`;
    }
    // Exato — ou o 1º período do ano, no fallback só-ano (fontes antigas).
    const exato = serie.find((p) => p.periodo === alvo || p.periodo.startsWith(alvo));
    if (exato) return exato.periodo;
    // Fora da janela do gráfico (antes do 1º ou depois do último ponto): NÃO
    // marca. Empilhar no extremo poria um marco num período que não é o do
    // treino (ex.: "Lean 2022" caindo em jan/2026). O marco aparece só nos
    // gráficos cujo intervalo cobre o treino.
    const primeiro = serie[0].periodo, ultimo = serie[serie.length - 1].periodo;
    if (alvo < primeiro || alvo > ultimo) return null;
    // Dentro da janela, sem ponto exato: ancora no 1º ponto igual ou posterior.
    const posterior = serie.find((p) => p.periodo >= alvo);
    return posterior ? posterior.periodo : null;
  }

  /** Etiqueta curta do marco: módulo + mês/ano quando há data, senão + ano. */
  function rotuloTreino(t) {
    const modulo = t.modulo ? t.modulo.split(" ")[0] : "Treino";
    if (t.mes) return `${modulo} ${MESES_CURTOS[t.mes]}/${String(t.ano).slice(2)}`;
    return `${modulo} ${t.ano ?? ""}`.trim();
  }

  /** Marcos de treino ancorados no MÊS/semana do treino dentro do eixo da série.
   *  Cada marco é uma linha vertical tracejada roxa com uma etiqueta-"chip". As
   *  etiquetas alternam de altura para não colidirem quando ficam próximas. */
  function marcasTreino(serie, treinos) {
    if (!serie.length || !treinos.length) return [];
    const treino = corTema("--treino");
    const inkChip = corTema("--surface"); // texto do chip: contrasta em claro e escuro
    const dados = [];
    const vistos = new Set();
    let i = 0;
    for (const t of treinos) {
      const periodo = periodoAlvo(serie, t);
      if (periodo == null || vistos.has(periodo)) continue;
      vistos.add(periodo);
      dados.push({
        xAxis: periodo,
        lineStyle: { color: treino, width: 1.6, type: "dashed", opacity: 0.95 },
        label: {
          show: true, formatter: rotuloTreino(t), position: "end",
          rotate: 0, align: "left", distance: 5 + (i % 2) * 15, // abre p/ a direita, fora do eixo Y
          color: inkChip, backgroundColor: treino, padding: [2, 5], borderRadius: 3,
          fontFamily: "IBM Plex Sans", fontSize: 9.5, fontWeight: 600,
        },
      });
      i++;
    }
    return dados;
  }

  /** Título legível do período para o tooltip: ``AAAA-MM`` → "Mar/2026";
   *  ``AAAA-Www`` → "Semana 12 · 2026". */
  function tituloPeriodo(periodo) {
    const s = String(periodo);
    const mSem = s.match(/^(\d{4})-W(\d{2})$/);
    if (mSem) return `Semana ${+mSem[2]} · ${mSem[1]}`;
    const mMes = s.match(/^(\d{4})-(\d{2})$/);
    if (mMes) return `${MESES_CURTOS[+mMes[2]] || mMes[2]}/${mMes[1]}`;
    return s;
  }

  /** Etiqueta curta de minutos: em milhares com "k" (ex.: 124011 → "124k"). */
  const minK = (v) => v == null ? "" : Math.round(v / 1000) + "k";

  /** Tela 2 — série temporal de uma métrica, com marcos de treino e meta.
   *  Produção ganha uma 2ª linha (minutos, eixo secundário à direita) e tooltip
   *  moderno com peças/min e min/peça. Sem gridlines horizontais. */
  function renderSerie(el, serie, metrica, treinos) {
    if (!window.echarts) return;
    const g = inst(el);
    const cor = corTema(COR_METRICA[metrica] || "--producao");
    const corMin = corTema("--eficiencia");
    const ehPct = ehPercentual(metrica);
    const ehProducao = metrica === "pecas_mes" || metrica === "pecas_semana";
    const markLines = marcasTreino(serie, treinos);
    const fz = escalaRotulo(el);

    const tooltip = ehProducao
      ? { ...tipBaseAxis(), formatter: (params) => {
          const it = serie[params[0].dataIndex] || {};
          const linhas = [{ cor, rot: "Peças", val: intFmt(it.valor) }];
          if (it.minutos != null) linhas.push({ cor: corMin, rot: "Minutos", val: intFmt(it.minutos) });
          if (it.minutos > 0) {
            linhas.push({ sep: true });
            linhas.push({ rot: "Peças / min", val: (it.valor / it.minutos).toFixed(3).replace(".", ","), destaque: true });
            linhas.push({ rot: "Min / peça", val: (it.minutos / it.valor).toFixed(1).replace(".", ","), destaque: true });
          }
          if (it.dias_uteis != null) linhas.push({ rot: "Dias úteis", val: it.dias_uteis });
          return caixaTip(tituloPeriodo(params[0].axisValue), linhas);
        } }
      : { ...tipBaseAxis(), formatter: (params) => {
          const p = params[0];
          const val = p.value == null ? "—" : (ehPct ? pctFmt(p.value) : intFmt(p.value) + " peças");
          return caixaTip(tituloPeriodo(p.axisValue), [{ cor, rot: rotuloMetrica(metrica), val }]);
        } };

    // Eixo Y: produção usa dois (peças à esquerda, minutos "k" à direita); as
    // demais métricas usam um só. Nenhum desenha gridline horizontal.
    const yAxis = ehProducao
      ? [
          { type: "value", axisLabel: { ...eixoTexto(), fontSize: fz.eixo, formatter: intFmt },
            axisLine: { show: false }, splitLine: { show: false } },
          { type: "value", position: "right", axisLabel: { ...eixoTexto(), fontSize: fz.eixo, formatter: minK },
            axisLine: { show: false }, splitLine: { show: false } },
        ]
      : { type: "value",
          axisLabel: { ...eixoTexto(), fontSize: fz.eixo, formatter: (v) => ehPct ? Math.round(v * 100) + "%" : intFmt(v) },
          axisLine: { show: false }, splitLine: { show: false } };

    const serieValores = {
      type: "line", smooth: true, symbol: "circle", symbolSize: 6, yAxisIndex: 0,
      data: serie.map((p) => p.valor),
      lineStyle: { color: cor, width: 2.4 }, itemStyle: { color: cor },
      areaStyle: { color: cor, opacity: 0.10 },
      label: { show: true, position: "top", distance: 6,
        color: cor, fontFamily: "IBM Plex Sans", fontSize: fz.valor, fontWeight: 600,
        formatter: (p) => p.value == null ? "" : (ehPct ? pctFmt(p.value) : intFmt(p.value)) },
      labelLayout: { hideOverlap: true },
      markLine: markLines.length ? {
        symbol: "none", silent: true, data: markLines,
        lineStyle: { color: corTema("--treino"), width: 1.6, type: "dashed", opacity: 0.95 },
      } : undefined,
    };

    const series = [serieValores];
    if (ehProducao) {
      // 2ª linha: minutos (tracejada), rótulos abaixo p/ nunca colidir com peças.
      series.push({
        type: "line", smooth: true, symbol: "circle", symbolSize: 6, yAxisIndex: 1,
        data: serie.map((p) => p.minutos ?? null),
        lineStyle: { color: corMin, width: 2.4, type: [6, 4] }, itemStyle: { color: corMin },
        label: { show: true, position: "bottom", distance: 6,
          color: corMin, fontFamily: "IBM Plex Sans", fontSize: fz.valor, fontWeight: 600,
          formatter: (p) => minK(p.value) },
        labelLayout: { hideOverlap: true },
      });
    }

    g.setOption({
      ...base(),
      grid: { left: 8, right: ehProducao ? 20 : 48, top: 46, bottom: 8, containLabel: true },
      tooltip,
      legend: { show: false },
      xAxis: {
        type: "category", data: serie.map((p) => p.periodo), boundaryGap: false,
        axisLabel: { ...eixoTexto(), fontSize: fz.eixo, hideOverlap: true,
          // No mensal com dias úteis, mostra o período e, abaixo, os dias úteis
          // do mês — sazonalidade de calendário visível sem precisar do tooltip.
          formatter: metrica === "pecas_mes" && serie[0] && serie[0].dias_uteis != null
            ? (periodo, i) => {
                const du = serie[i] && serie[i].dias_uteis;
                return du != null ? `${periodo}\n{du|${du}d úteis}` : periodo;
              }
            : undefined,
          rich: { du: { fontSize: fz.eixo - 1.5, color: corTema("--faint"), padding: [3, 0, 0, 0] } },
        },
        axisLine: linhaEixo(), axisTick: { show: false },
      },
      yAxis,
      series,
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
      tooltip: { ...tipBaseItem(),
        formatter: (p) => caixaTip(p.name, [{ cor, rot: "Valor", val: fmt(p.value) }]) },
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
