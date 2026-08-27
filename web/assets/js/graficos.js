/* Camada de gráficos — ECharts. Responsabilidade única: desenhar visualizações.
   Não conhece filtros nem DOM da tabela; recebe dados prontos. */

const Graficos = (() => {
  let instancia = null;

  /** Lê uma variável de tema do CSS para o ECharts acompanhar claro/escuro. */
  function corTema(nome) {
    return getComputedStyle(document.documentElement).getPropertyValue(nome).trim();
  }

  /** Classifica oficinas em faixas de cobertura de métricas. */
  function faixasCobertura(oficinas) {
    let completa = 0, parcial = 0, semMetrica = 0;
    const tem = (o, p) => o.papeis.includes(p);
    for (const o of oficinas) {
      const m = ["producao", "absenteismo", "eficiencia"].filter((p) => tem(o, p)).length;
      if (m === 3) completa++;
      else if (m > 0) parcial++;
      else semMetrica++;
    }
    return { completa, parcial, semMetrica };
  }

  /** Desenha (ou redesenha) o donut de cobertura no container informado. */
  function renderCobertura(el, oficinas) {
    if (!window.echarts) return;
    if (!instancia) instancia = window.echarts.init(el, null, { renderer: "svg" });
    const f = faixasCobertura(oficinas);
    instancia.setOption({
      tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
      legend: {
        bottom: 0, icon: "circle", itemWidth: 9, itemHeight: 9,
        textStyle: { color: corTema("--muted"), fontFamily: "IBM Plex Mono", fontSize: 11 },
      },
      series: [{
        type: "pie", radius: ["52%", "76%"], center: ["50%", "44%"],
        avoidLabelOverlap: true, label: { show: false },
        itemStyle: { borderColor: corTema("--surface"), borderWidth: 2 },
        data: [
          { value: f.completa, name: "3 métricas", itemStyle: { color: corTema("--eficiencia") } },
          { value: f.parcial, name: "Parcial", itemStyle: { color: corTema("--absenteismo") } },
          { value: f.semMetrica, name: "Só treino", itemStyle: { color: corTema("--faint") } },
        ],
      }],
    });
  }

  function redimensionar() { if (instancia) instancia.resize(); }

  return { renderCobertura, redimensionar };
})();

window.addEventListener("resize", () => Graficos.redimensionar());
