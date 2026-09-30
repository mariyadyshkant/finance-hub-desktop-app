<script>
  import Chart from "../Chart.svelte";
  import { CHART_COLORS, baseScales } from "../../chartTheme.js";

  let { allTx, selectedMonth, isRevolutMonth } = $props();

  let dailyTrend = $derived.by(() => {
    if (!isRevolutMonth) return null;
    const byDay = {};
    for (const tx of allTx) {
      if (tx.amount >= 0) continue;
      if (tx.date.slice(0, 7) !== selectedMonth) continue;
      byDay[tx.date] = (byDay[tx.date] || 0) + Math.abs(tx.amount);
    }
    const days = Object.keys(byDay).sort();
    return {
      labels: days.map((d) =>
        new Date(d + "T00:00:00").toLocaleDateString("it-IT", { day: "2-digit", month: "short" })
      ),
      values: days.map((d) => byDay[d]),
    };
  });

  let dailyChartData = $derived(
    dailyTrend && {
      labels: dailyTrend.labels,
      datasets: [
        {
          data: dailyTrend.values,
          backgroundColor: CHART_COLORS.accent,
          borderRadius: 4,
          maxBarThickness: 18,
        },
      ],
    }
  );

  const dailyChartOptions = {
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: (ctx) => `€${ctx.parsed.y.toFixed(2)}` } },
    },
    scales: baseScales({ y: { ticks: { callback: (v) => `€${v}` } } }),
  };
</script>

{#if dailyChartData}
  <div class="metric-card chart-card">
    <h3>Andamento giornaliero</h3>
    <Chart type="bar" data={dailyChartData} options={dailyChartOptions} height={280} />
  </div>
{/if}

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
</style>
