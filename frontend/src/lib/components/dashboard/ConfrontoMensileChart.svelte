<script>
  import Chart from "../Chart.svelte";
  import { CHART_COLORS, baseScales } from "../../chartTheme.js";

  let { rowsWithPlanned, revolutMonths, monthLabelShort } = $props();

  let monthlyTotals = $derived.by(() => {
    const byMonth = {};
    for (const r of rowsWithPlanned) byMonth[r.month] = (byMonth[r.month] || 0) + r.amount;
    return Object.entries(byMonth).sort((a, b) => a[0].localeCompare(b[0]));
  });

  let monthlyChartData = $derived({
    labels: monthlyTotals.map(([m]) => monthLabelShort(m)),
    datasets: [
      {
        label: "Totale spese",
        data: monthlyTotals.map(([, v]) => v),
        backgroundColor: monthlyTotals.map(([m]) =>
          revolutMonths.includes(m) ? CHART_COLORS.sourceRevolut : CHART_COLORS.sourceNotion
        ),
        borderRadius: 4,
        maxBarThickness: 28,
      },
    ],
  });

  const monthlyChartOptions = {
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: (ctx) => `€${ctx.parsed.y.toFixed(2)}` } },
    },
    scales: baseScales({ y: { ticks: { callback: (v) => `€${v}` } } }),
  };
</script>

<div class="metric-card chart-card">
  <h3>Confronto ultimi mesi</h3>
  <div class="legend-inline">
    <span><i class="dot" style="background:{CHART_COLORS.sourceRevolut}"></i>Revolut</span>
    <span><i class="dot" style="background:{CHART_COLORS.sourceNotion}"></i>Notion</span>
  </div>
  <Chart type="bar" data={monthlyChartData} options={monthlyChartOptions} height={260} />
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

  .legend-inline {
    display: flex;
    gap: var(--space-4);
    font-size: var(--text-xs);
    color: var(--text-secondary);
  }

  .legend-inline .dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 999px;
    margin-right: 4px;
  }
</style>
