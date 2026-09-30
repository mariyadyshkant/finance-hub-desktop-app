<script>
  import Chart from "../Chart.svelte";
  import { CHART_COLORS, baseScales } from "../../chartTheme.js";

  let { monthRows, colors } = $props();

  let categoryBreakdown = $derived.by(() => {
    const byCat = {};
    for (const r of monthRows) byCat[r.category] = (byCat[r.category] || 0) + r.amount;
    return Object.entries(byCat).sort((a, b) => b[1] - a[1]);
  });

  let categoryChartData = $derived({
    labels: categoryBreakdown.map(([cat]) => cat),
    datasets: [
      {
        data: categoryBreakdown.map(([, amt]) => amt),
        backgroundColor: categoryBreakdown.map(([cat]) => colors[cat] || CHART_COLORS.accent),
        borderRadius: 4,
        maxBarThickness: 22,
      },
    ],
  });

  const categoryChartOptions = {
    indexAxis: "y",
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: (ctx) => `€${ctx.parsed.x.toFixed(2)}` } },
    },
    scales: baseScales({ x: { ticks: { callback: (v) => `€${v}` } } }),
  };
</script>

<div class="metric-card chart-card">
  <h3>Spese per categoria</h3>
  {#if categoryBreakdown.length > 0}
    <Chart type="bar" data={categoryChartData} options={categoryChartOptions} height={Math.max(180, categoryBreakdown.length * 26)} />
  {:else}
    <p class="hint">Nessuna spesa per questo mese.</p>
  {/if}
</div>

<style>
  .chart-card {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    margin-bottom: var(--space-4);
  }

  .chart-card h3 {
    font-size: var(--text-lg);
    font-weight: 600;
  }

  .hint {
    font-size: var(--text-sm);
    color: var(--text-secondary);
    margin: 0;
  }
</style>
