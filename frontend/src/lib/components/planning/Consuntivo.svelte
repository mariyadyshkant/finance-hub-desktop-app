<script>
  import Chart from "../Chart.svelte";
  import { CHART_COLORS, baseScales } from "../../chartTheme.js";
  import { plannedApplies } from "../../planned.js";

  let {
    budget,
    unifiedRows,
    selectedMonth,
    totalPlanned,
    exceptionalRows,
    colors,
    monthLabelShort,
  } = $props();

  let monthActualRows = $derived(unifiedRows.filter((r) => r.month === selectedMonth));
  let actualTotal = $derived(monthActualRows.reduce((s, r) => s + r.amount, 0));
  // Le pianificate contano nel consuntivo solo per i mesi in cui la regola
  // esisteva (da agosto 2026) — vedi lib/planned.js.
  let consuntivoPlanned = $derived(plannedApplies(selectedMonth) ? totalPlanned : 0);
  let combinedTotal = $derived(actualTotal + consuntivoPlanned);
  let remaining = $derived(budget ? budget.total - combinedTotal : 0);
  let pct = $derived(budget && budget.total > 0 ? (combinedTotal / budget.total) * 100 : 0);
  let barColor = $derived(pct <= 85 ? CHART_COLORS.success : pct <= 100 ? CHART_COLORS.textMuted : CHART_COLORS.danger);

  let catBudgetRows = $derived.by(() => {
    if (!budget) return [];
    const catB = JSON.parse(budget.cat_budgets || "{}");
    const rows = [];
    for (const [cat, bud] of Object.entries(catB)) {
      if (bud <= 0) continue;
      const spent = monthActualRows.filter((r) => r.category === cat).reduce((s, r) => s + r.amount, 0);
      rows.push({ cat, bud, spent, diff: spent - bud });
    }
    rows.sort((a, b) => b.spent - a.spent);
    return rows;
  });

  let catBudgetChartData = $derived({
    labels: catBudgetRows.map((r) => r.cat),
    datasets: [
      { label: "Budget", data: catBudgetRows.map((r) => r.bud), backgroundColor: CHART_COLORS.textMuted, borderRadius: 4 },
      {
        label: "Speso",
        data: catBudgetRows.map((r) => r.spent),
        backgroundColor: catBudgetRows.map((r) => (r.diff > 0 ? CHART_COLORS.danger : CHART_COLORS.success)),
        borderRadius: 4,
      },
    ],
  });
  const catBudgetOptions = {
    plugins: {
      legend: { position: "bottom", labels: { color: CHART_COLORS.textSecondary } },
      tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: €${ctx.parsed.y.toFixed(2)}` } },
    },
    scales: baseScales({ y: { ticks: { callback: (v) => `€${v}` } } }),
  };

  let monthlyTotals = $derived.by(() => {
    const byMonth = {};
    for (const r of unifiedRows) byMonth[r.month] = (byMonth[r.month] || 0) + r.amount;
    return Object.entries(byMonth).sort((a, b) => a[0].localeCompare(b[0]));
  });
  let grandAvg = $derived(monthlyTotals.length ? monthlyTotals.reduce((s, [, v]) => s + v, 0) / monthlyTotals.length : 0);
  let grandMax = $derived(monthlyTotals.length ? Math.max(...monthlyTotals.map(([, v]) => v)) : 0);
  let grandMin = $derived(monthlyTotals.length ? Math.min(...monthlyTotals.map(([, v]) => v)) : 0);

  let historyChartData = $derived({
    labels: monthlyTotals.map(([m]) => monthLabelShort(m)),
    datasets: [
      { label: "Totale", data: monthlyTotals.map(([, v]) => v), backgroundColor: CHART_COLORS.accent, borderRadius: 4, maxBarThickness: 28 },
    ],
  });
  const historyChartOptions = {
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: (ctx) => `€${ctx.parsed.y.toFixed(2)}` } },
    },
    scales: baseScales({ y: { ticks: { callback: (v) => `€${v}` } } }),
  };
</script>

{#if !budget}
  <p class="hint">Nessun budget impostato per questo mese. Vai alla tab Budget per impostarlo.</p>
{:else}
  <div class="kpi-grid four">
    <div class="metric-card">
      <span class="eyebrow">Budget</span>
      <span class="kpi-value">€{budget.total.toFixed(2)}</span>
    </div>
    <div class="metric-card">
      <span class="eyebrow">Spese effettive</span>
      <span class="kpi-value">€{actualTotal.toFixed(2)}</span>
    </div>
    <div class="metric-card">
      <span class="eyebrow">Pianificate</span>
      <span class="kpi-value">€{consuntivoPlanned.toFixed(2)}</span>
    </div>
    <div class="metric-card">
      <span class="eyebrow">Rimanente</span>
      <span class="kpi-value" class:positive={remaining >= 0} class:negative={remaining < 0}>
        {remaining >= 0 ? "+" : ""}€{remaining.toFixed(2)}
      </span>
    </div>
  </div>

  <div class="metric-card">
    <div class="progress-header">
      <span>Speso + pianificato</span>
      <span>{pct.toFixed(0)}% del budget</span>
    </div>
    <div class="progress-track">
      <div class="progress-fill" style="width:{Math.min(pct, 100)}%; background:{barColor}"></div>
    </div>
  </div>

  {#if catBudgetRows.length > 0}
    <div class="metric-card chart-card">
      <h3>Dettaglio per categoria</h3>
      <Chart type="bar" data={catBudgetChartData} options={catBudgetOptions} height={280} />
      <div class="list">
        {#each catBudgetRows as r}
          <div class="row">
            <span class="desc" style="color:{colors[r.cat] || 'inherit'}">{r.cat}</span>
            <span class="hours">€{r.spent.toFixed(2)} / €{r.bud.toFixed(2)}</span>
            <span class:negative={r.diff > 0} class:positive={r.diff <= 0}>
              {r.diff > 0 ? "🔴 Sforato" : "🟢 OK"}
            </span>
          </div>
        {/each}
      </div>
    </div>
  {/if}

  {#if exceptionalRows.length > 0}
    <div class="metric-card">
      <h3>⚠️ Spese eccezionali questo mese</h3>
      {#each exceptionalRows as r}
        <p class="exceptional-item"><strong>{r.desc}</strong> — €{r.amount.toFixed(2)}{r.note ? ` · ${r.note}` : ""}</p>
      {/each}
    </div>
  {/if}
{/if}

{#if monthlyTotals.length > 0}
  <div class="metric-card chart-card">
    <h3>Media totale mensile storica</h3>
    <div class="kpi-grid three">
      <div class="metric-card">
        <span class="eyebrow">Media mensile</span>
        <span class="kpi-value">€{grandAvg.toFixed(2)}</span>
      </div>
      <div class="metric-card">
        <span class="eyebrow">Mese più caro</span>
        <span class="kpi-value negative">€{grandMax.toFixed(2)}</span>
      </div>
      <div class="metric-card">
        <span class="eyebrow">Mese più economico</span>
        <span class="kpi-value positive">€{grandMin.toFixed(2)}</span>
      </div>
    </div>
    <Chart type="bar" data={historyChartData} options={historyChartOptions} height={260} />
  </div>
{/if}

<style>
  .metric-card {
    margin-bottom: var(--space-4);
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .metric-card h3 {
    font-size: var(--text-base);
    font-weight: 600;
    margin: 0;
  }

  .list {
    display: flex;
    flex-direction: column;
  }

  .row {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-2) 0;
    border-bottom: 1px solid var(--border);
    font-size: var(--text-sm);
  }

  .row:last-child { border-bottom: none; }

  .row .desc {
    flex: 1;
    display: flex;
    align-items: center;
    gap: var(--space-2);
    color: var(--text-primary);
  }

  .row .hours {
    font-family: var(--font-heading);
    font-weight: 600;
  }

  .kpi-grid {
    display: grid;
    gap: var(--space-3);
    margin-bottom: var(--space-4);
  }

  .kpi-grid.three { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .kpi-grid.four { grid-template-columns: repeat(4, minmax(0, 1fr)); }

  .kpi-grid .metric-card {
    margin-bottom: 0;
  }

  .kpi-value {
    font-family: var(--font-heading);
    font-size: var(--text-xl);
    font-weight: 700;
    color: var(--text-primary);
  }

  .kpi-value.positive { color: var(--success); }
  .kpi-value.negative { color: var(--danger); }

  .progress-header {
    display: flex;
    justify-content: space-between;
    font-size: var(--text-xs);
    color: var(--text-muted);
  }

  .progress-track {
    background: var(--muted);
    border-radius: 6px;
    height: 10px;
    overflow: hidden;
  }

  .progress-fill {
    height: 10px;
    border-radius: 6px;
    transition: width 0.3s ease;
  }

  .chart-card {
    gap: var(--space-3);
  }

  .exceptional-item {
    font-size: var(--text-sm);
    color: var(--danger);
    margin: 0;
  }

  .hint {
    font-size: var(--text-sm);
    color: var(--text-secondary);
    margin: 0;
  }
</style>
