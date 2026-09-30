<script>
  import Chart from "../Chart.svelte";
  import { CHART_COLORS, baseScales } from "../../chartTheme.js";

  let { rowsWithPlanned, allMonths, spendableCategories, colors, monthLabelShort } = $props();

  let trendCategories = $state(["Bar & Ristoranti", "Spesa", "Abbonamenti", "Auto"]);

  function toggleTrendCategory(cat) {
    if (trendCategories.includes(cat)) {
      trendCategories = trendCategories.filter((c) => c !== cat);
    } else if (trendCategories.length < 6) {
      trendCategories = [...trendCategories, cat];
    }
  }

  let trendChartData = $derived.by(() => {
    const monthsSorted = allMonths.slice().sort();
    const datasets = trendCategories.map((cat) => {
      const byMonth = {};
      for (const r of rowsWithPlanned) {
        if (r.category === cat) byMonth[r.month] = (byMonth[r.month] || 0) + r.amount;
      }
      const color = colors[cat] || CHART_COLORS.accent;
      return {
        label: cat,
        data: monthsSorted.map((m) => byMonth[m] || 0),
        borderColor: color,
        backgroundColor: color,
        tension: 0.3,
        pointRadius: 3,
      };
    });
    return { labels: monthsSorted.map(monthLabelShort), datasets };
  });

  const trendChartOptions = {
    plugins: {
      legend: { position: "bottom", labels: { color: CHART_COLORS.textSecondary } },
      tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: €${ctx.parsed.y.toFixed(2)}` } },
    },
    scales: baseScales({ y: { ticks: { callback: (v) => `€${v}` } } }),
  };
</script>

<div class="metric-card chart-card">
  <h3>Andamento per categoria</h3>
  <p class="hint">Seleziona fino a 6 categorie da confrontare.</p>
  <div class="pill-group">
    {#each spendableCategories as c}
      <button
        class="cat-pill"
        class:active={trendCategories.includes(c)}
        style="--pill-color: {colors[c] || '#6966a0'}"
        onclick={() => toggleTrendCategory(c)}
      >{c}</button>
    {/each}
  </div>
  {#if trendCategories.length > 0}
    <Chart type="line" data={trendChartData} options={trendChartOptions} height={280} />
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

  .pill-group {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-1);
    margin-bottom: var(--space-2);
  }

  .cat-pill {
    border: 1px solid var(--pill-color);
    color: var(--pill-color);
    background: none;
    border-radius: 999px;
    padding: 2px 10px;
    font-size: var(--text-xs);
    cursor: pointer;
  }

  .cat-pill.active {
    background: var(--pill-color);
    color: white;
  }
</style>
