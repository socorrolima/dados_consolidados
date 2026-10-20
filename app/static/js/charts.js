// Duas funções genéricas, reaproveitadas por todas as abas do dashboard —
// evita cada aba reimplementar configuração de Chart.js.
const Charts = (function () {
  const instancias = {};

  function _destroiSeExistir(canvasId) {
    if (instancias[canvasId]) {
      instancias[canvasId].destroy();
      delete instancias[canvasId];
    }
  }

  // series: [{ nome: "Município", valores: [1,2,null,4] }, ...]
  function linhaComparativa(canvasId, labels, series) {
    _destroiSeExistir(canvasId);
    const ctx = document.getElementById(canvasId).getContext("2d");
    instancias[canvasId] = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: series.map((s) => ({
          label: s.nome,
          data: s.valores,
          spanGaps: true,
          tension: 0.2,
        })),
      },
      options: {
        responsive: true,
        plugins: { legend: { position: "bottom" } },
        scales: { y: { beginAtZero: true } },
      },
    });
  }

  // labels: ["Município", "Média UF", "Média piloto"], valores: [100, 80, 90]
  function barraRanking(canvasId, labels, valores) {
    _destroiSeExistir(canvasId);
    const ctx = document.getElementById(canvasId).getContext("2d");
    instancias[canvasId] = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [{ data: valores }],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true } },
      },
    });
  }

  return { linhaComparativa, barraRanking };
})();
