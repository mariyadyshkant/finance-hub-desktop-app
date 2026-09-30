<script>
  import Chart from "../Chart.svelte";
  import { CHART_COLORS, baseScales } from "../../chartTheme.js";

  let { rowsWithPlanned, allMonths, selectedMonth, monthLabel } = $props();

  let avgVsMonth = $derived.by(() => {
    const n = allMonths.length || 1;
    const byCat = {};
    for (const r of rowsWithPlanned) {
      byCat[r.category] = byCat[r.category] || {};
      byCat[r.category][r.month] = (byCat[r.category][r.month] || 0) + r.amount;
    }
    const rows = [];
    for (const [cat, monthMap] of Object.entries(byCat)) {
      const avg = allMonths.reduce((s, m) => s + (monthMap[m] || 0), 0) / n;
      const thisMonthVal = monthMap[selectedMonth] || 0;
      if (avg === 0 && thisMonthVal === 0) continue;
      rows.push({ cat, avg, thisMonthVal, diff: thisMonthVal - avg });
    }
    rows.sort((a, b) => b.avg - a.avg);
    return rows;
  });

  let avgChartData = $derived({
    labels: avgVsMonth.map((r) => r.cat),
    datasets: [
      {
        label: "Media mensile",
        data: avgVsMonth.map((r) => r.avg),
        backgroundColor: CHART_COLORS.textMuted,
        borderRadius: 4,
      },
      {
        label: monthLabel(selectedMonth),
        data: avgVsMonth.map((r) => r.thisMonthVal),
        backgroundColor: avgVsMonth.map((r) => (r.diff > 0 ? CHART_COLORS.danger : CHART_COLORS.success)),
        borderRadius: 4,
      },
    ],
  });

  const avgChartOptions = {
    plugins: {
      legend: { position: "bottom", labels: { color: CHART_COLORS.textSecondary } },
      tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: €${ctx.parsed.y.toFixed(2)}` } },
    },
    scales: baseScales({ y: { ticks: { callback: (v) => `€${v}` } } }),
  };
</script>

{#if avgVsMonth.length > 0}
  <div class="metric-card chart-card">
    <h3>Media mensile per categoria</h3>
    <p class="hint">Calcolata su {allMonths.length} {allMonths.length === 1 ? "mese" : "mesi"} — confronto con {monthLabel(selectedMonth)}</p>
    <Chart type="bar" data={avgChartData} options={avgChartOptions} height={300} />
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

  .hint {
    font-size: var(--text-sm);
    color: var(--text-secondary);
    margin: 0;
  }
</style>
