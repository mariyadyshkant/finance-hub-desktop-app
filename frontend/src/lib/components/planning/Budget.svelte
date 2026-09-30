<script>
  import { api } from "../../api.js";
  import Chart from "../Chart.svelte";
  import { CHART_COLORS, baseScales } from "../../chartTheme.js";

  let {
    budget,
    catAverages,
    totalAvg,
    nHistoryMonths,
    budgetCatKeys,
    colors,
    selectedMonth,
    monthLabel,
    onchange,
  } = $props();

  let budgetTotal = $state(0);
  let budgetCats = $state({});
  let budgetNote = $state("");
  let budgetError = $state("");
  let budgetSaving = $state(false);

  $effect(() => {
    if (budget) {
      budgetTotal = budget.total;
      budgetCats = JSON.parse(budget.cat_budgets || "{}");
      budgetNote = budget.note || "";
    } else {
      const suggestedTotal = totalAvg > 0 ? Math.round(totalAvg * 1.05) : 1500;
      budgetTotal = suggestedTotal;
      const cats = {};
      for (const [cat, avg] of Object.entries(catAverages)) {
        if (avg > 0) cats[cat] = Math.round(avg * 1.1);
      }
      budgetCats = cats;
      budgetNote = "";
    }
  });

  let budgetCatTotal = $derived(Object.values(budgetCats).reduce((s, v) => s + (Number(v) || 0), 0));
  let budgetDiff = $derived(budgetCatTotal - budgetTotal);

  async function saveBudget() {
    budgetSaving = true;
    budgetError = "";
    try {
      await api.post("/planning/budget", {
        month: selectedMonth,
        total: Number(budgetTotal),
        cat_budgets: Object.fromEntries(Object.entries(budgetCats).map(([k, v]) => [k, Number(v) || 0])),
        note: budgetNote,
      });
      await onchange();
    } catch (e) {
      budgetError = e.message;
    } finally {
      budgetSaving = false;
    }
  }

  let budgetAllocation = $derived(
    budget
      ? Object.entries(JSON.parse(budget.cat_budgets || "{}"))
          .filter(([, v]) => v > 0)
          .sort((a, b) => b[1] - a[1])
      : []
  );
  let budgetAllocationChartData = $derived({
    labels: budgetAllocation.map(([cat]) => cat),
    datasets: [
      {
        data: budgetAllocation.map(([, v]) => v),
        backgroundColor: budgetAllocation.map(([cat]) => colors[cat] || CHART_COLORS.accent),
        borderRadius: 4,
        maxBarThickness: 22,
      },
    ],
  });
  const budgetAllocationOptions = {
    indexAxis: "y",
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: (ctx) => `€${ctx.parsed.x.toFixed(2)}` } },
    },
    scales: baseScales({ x: { ticks: { callback: (v) => `€${v}` } } }),
  };
</script>

<div class="metric-card">
  <h3>Imposta budget per {monthLabel(selectedMonth)}</h3>
  {#if nHistoryMonths > 0}
    <p class="hint">Media storica totale: <strong>€{totalAvg.toFixed(2)}/mese</strong> su {nHistoryMonths} mesi — usata come base per i suggerimenti.</p>
  {/if}
  <label class="total-field">
    Budget totale mensile €
    <input type="number" step="10" bind:value={budgetTotal} />
  </label>

  <p class="hint">Budget per categoria (0 = nessun limite)</p>
  <div class="budget-grid">
    {#each budgetCatKeys as cat}
      <label>
        <span style="color:{colors[cat] || 'inherit'}">{cat}</span>
        <input type="number" step="5" min="0" bind:value={budgetCats[cat]} />
      </label>
    {/each}
  </div>

  {#if budgetCatTotal > 0}
    {#if Math.abs(budgetDiff) < 0.01}
      <p class="notice ok">Totale categorie: €{budgetCatTotal.toFixed(2)} — corrisponde al budget totale.</p>
    {:else if budgetDiff > 0}
      <p class="notice warn">Totale categorie: €{budgetCatTotal.toFixed(2)} — supera il budget di €{budgetDiff.toFixed(2)}.</p>
    {:else}
      <p class="notice info">Totale categorie: €{budgetCatTotal.toFixed(2)} — mancano €{Math.abs(budgetDiff).toFixed(2)} al budget totale.</p>
    {/if}
  {/if}

  <input type="text" bind:value={budgetNote} placeholder="Note (opzionale)" class="note-field" />
  <button class="btn-primary" onclick={saveBudget} disabled={budgetSaving}>
    {budgetSaving ? "Salvataggio..." : "Salva budget"}
  </button>
  {#if budgetError}<p class="error">{budgetError}</p>{/if}
</div>

{#if budget}
  <div class="metric-card">
    <h3>Budget attivo per {monthLabel(selectedMonth)}</h3>
    <div class="kpi-grid three">
      <div class="metric-card">
        <span class="eyebrow">Budget totale</span>
        <span class="kpi-value">€{budget.total.toFixed(2)}</span>
      </div>
      <div class="metric-card">
        <span class="eyebrow">Assegnato</span>
        <span class="kpi-value">€{budgetAllocation.reduce((s, [, v]) => s + v, 0).toFixed(2)}</span>
      </div>
      <div class="metric-card">
        <span class="eyebrow">Non assegnato</span>
        <span class="kpi-value">€{(budget.total - budgetAllocation.reduce((s, [, v]) => s + v, 0)).toFixed(2)}</span>
      </div>
    </div>
    {#if budgetAllocation.length > 0}
      <Chart type="bar" data={budgetAllocationChartData} options={budgetAllocationOptions} height={Math.max(160, budgetAllocation.length * 26)} />
    {/if}
  </div>
{/if}

<style>
  .btn-primary {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: 0.5rem var(--space-4);
    border-radius: var(--radius-md);
    font-size: var(--text-sm);
    font-weight: 500;
    cursor: pointer;
    border: none;
    background: var(--accent);
    color: var(--accent-foreground);
  }

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

  .kpi-grid {
    display: grid;
    gap: var(--space-3);
    margin-bottom: var(--space-4);
  }

  .kpi-grid.three { grid-template-columns: repeat(3, minmax(0, 1fr)); }

  .kpi-grid .metric-card {
    margin-bottom: 0;
  }

  .kpi-value {
    font-family: var(--font-heading);
    font-size: var(--text-xl);
    font-weight: 700;
    color: var(--text-primary);
  }

  .total-field {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    font-size: var(--text-sm);
    color: var(--text-secondary);
  }

  .total-field input {
    width: 8rem;
    padding: 0.4rem var(--space-2);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
  }

  .budget-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: var(--space-2) var(--space-4);
  }

  .budget-grid label {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-2);
    font-size: var(--text-sm);
  }

  .budget-grid input {
    width: 6rem;
    padding: 0.3rem var(--space-2);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    text-align: right;
  }

  .notice {
    font-size: var(--text-sm);
    padding: var(--space-2) var(--space-3);
    border-radius: var(--radius-sm);
  }

  .notice.ok { background: color-mix(in srgb, var(--success) 12%, white); color: var(--success); }
  .notice.warn { background: color-mix(in srgb, var(--danger) 12%, white); color: var(--danger); }
  .notice.info { background: var(--muted); color: var(--text-secondary); }

  .note-field {
    padding: 0.5rem var(--space-3);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    background: var(--input-bg);
    font-size: var(--text-sm);
  }

  .hint {
    font-size: var(--text-sm);
    color: var(--text-secondary);
    margin: 0;
  }

  .error {
    color: var(--danger);
    font-size: var(--text-sm);
  }
</style>
