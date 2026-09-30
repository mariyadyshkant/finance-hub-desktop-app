<script>
  import { api } from "../../api.js";
  import Icon from "../Icon.svelte";
  import Chart from "../Chart.svelte";
  import { CHART_COLORS, baseScales } from "../../chartTheme.js";

  let { salaryRecords, monthLabel, monthLabelShort, onchange, onerror } = $props();

  let addSalMonth = $state(new Date().toISOString().slice(0, 7));
  let addSalNet = $state("");
  let addSalGross = $state("");
  let addSalHours = $state("");
  let addSalNote = $state("");
  let addSalError = $state("");
  let showAddSalary = $state(false);

  let salarySorted = $derived(salaryRecords.slice().sort((a, b) => b.month.localeCompare(a.month)));
  let netValues = $derived(salaryRecords.map((s) => s.net));
  let avgNet = $derived(netValues.length ? netValues.reduce((s, v) => s + v, 0) / netValues.length : 0);
  let maxNet = $derived(netValues.length ? Math.max(...netValues) : 0);
  let minNet = $derived(netValues.length ? Math.min(...netValues) : 0);

  let salaryChartData = $derived({
    labels: salarySorted.slice().reverse().map((s) => monthLabelShort(s.month)),
    datasets: [
      {
        label: "Netto",
        data: salarySorted.slice().reverse().map((s) => s.net),
        backgroundColor: CHART_COLORS.accent,
        borderRadius: 4,
        maxBarThickness: 28,
      },
    ],
  });
  const salaryChartOptions = {
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: (ctx) => `€${ctx.parsed.y.toFixed(2)}` } },
    },
    scales: baseScales({ y: { ticks: { callback: (v) => `€${v}` } } }),
  };

  async function submitAddSalary(e) {
    e.preventDefault();
    if (!addSalMonth || !addSalNet) {
      addSalError = "Mese e netto sono obbligatori.";
      return;
    }
    try {
      await api.post("/salary", {
        month: addSalMonth,
        net: Number(addSalNet),
        gross: addSalGross ? Number(addSalGross) : null,
        hours_worked: addSalHours ? Number(addSalHours) : null,
        note: addSalNote,
      });
      addSalNet = "";
      addSalGross = "";
      addSalHours = "";
      addSalNote = "";
      addSalError = "";
      showAddSalary = false;
      await onchange();
    } catch (e2) {
      addSalError = e2.message;
    }
  }

  async function deleteSalary(id) {
    try {
      await api.delete(`/salary/${id}`);
      await onchange();
    } catch (e) {
      onerror(e.message);
    }
  }
</script>

<div class="toolbar">
  <button class="btn-secondary" onclick={() => (showAddSalary = !showAddSalary)}>
    <Icon name="plus" size={14} /> Aggiungi stipendio
  </button>
</div>

{#if showAddSalary}
  <form class="add-panel" onsubmit={submitAddSalary}>
    <div class="fields">
      <input type="month" bind:value={addSalMonth} />
      <input type="number" step="0.01" bind:value={addSalNet} placeholder="Netto €" />
      <input type="number" step="0.01" bind:value={addSalGross} placeholder="Lordo € (opz.)" />
      <input type="number" step="0.1" bind:value={addSalHours} placeholder="Ore lavorate (opz.)" />
      <input type="text" bind:value={addSalNote} placeholder="Note (opz.)" />
    </div>
    <button type="submit" class="btn-primary">Salva</button>
    {#if addSalError}<p class="error">{addSalError}</p>{/if}
  </form>
{/if}

{#if salaryRecords.length === 0}
  <p class="hint">Nessuno stipendio registrato ancora.</p>
{:else}
  <div class="kpi-grid three">
    <div class="metric-card">
      <span class="eyebrow">Media netto</span>
      <span class="kpi-value">€{avgNet.toFixed(2)}</span>
    </div>
    <div class="metric-card">
      <span class="eyebrow">Massimo</span>
      <span class="kpi-value positive">€{maxNet.toFixed(2)}</span>
    </div>
    <div class="metric-card">
      <span class="eyebrow">Minimo</span>
      <span class="kpi-value">€{minNet.toFixed(2)}</span>
    </div>
  </div>

  <div class="metric-card chart-card">
    <h3>Netto per mese</h3>
    <Chart type="bar" data={salaryChartData} options={salaryChartOptions} height={260} />
  </div>

  <div class="metric-card">
    <h3>Storico</h3>
    <div class="list">
      {#each salarySorted as s (s.id)}
        <div class="row">
          <span class="date">{monthLabel(s.month)}</span>
          <span class="desc">
            netto €{s.net.toFixed(2)}
            {#if s.gross}· lordo €{s.gross.toFixed(2)}{/if}
            {#if s.hours_worked}· {s.hours_worked}h ({(s.net / s.hours_worked).toFixed(2)}€/h){/if}
          </span>
          <button class="icon-btn" title="Elimina" onclick={() => deleteSalary(s.id)}>
            <Icon name="trash-2" size={14} />
          </button>
        </div>
      {/each}
    </div>
  </div>
{/if}

<style>
  .toolbar {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    margin-bottom: var(--space-4);
  }

  .btn-primary, .btn-secondary {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: 0.5rem var(--space-4);
    border-radius: var(--radius-md);
    font-size: var(--text-sm);
    font-weight: 500;
    cursor: pointer;
  }

  .btn-primary {
    border: none;
    background: var(--accent);
    color: var(--accent-foreground);
  }

  .btn-secondary {
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--text-primary);
  }

  .add-panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: var(--space-4);
    margin-bottom: var(--space-4);
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .add-panel .fields {
    display: flex;
    gap: var(--space-2);
    flex-wrap: wrap;
  }

  .add-panel input {
    padding: 0.5rem var(--space-3);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    background: var(--input-bg);
    font-size: var(--text-sm);
    font-family: inherit;
  }

  .kpi-grid {
    display: grid;
    gap: var(--space-3);
    margin-bottom: var(--space-4);
  }

  .kpi-grid.three {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .kpi-grid .metric-card {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .kpi-value {
    font-family: var(--font-heading);
    font-size: var(--text-xl);
    font-weight: 700;
    color: var(--text-primary);
  }

  .kpi-value.positive { color: var(--success); }

  .chart-card {
    margin-bottom: var(--space-4);
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .chart-card h3, .metric-card > h3 {
    font-size: var(--text-base);
    font-weight: 600;
    margin: 0 0 var(--space-2);
  }

  .metric-card {
    margin-bottom: var(--space-4);
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

  .row .date {
    color: var(--text-muted);
    font-size: var(--text-xs);
    width: 7rem;
    flex-shrink: 0;
  }

  .row .desc {
    flex: 1;
    color: var(--text-primary);
  }

  .icon-btn {
    background: none;
    border: none;
    cursor: pointer;
    padding: 5px;
    border-radius: var(--radius-sm);
    color: var(--text-secondary);
    display: flex;
  }

  .icon-btn:hover {
    background: var(--muted);
    color: var(--danger);
  }

  .hint {
    font-size: var(--text-sm);
    color: var(--text-secondary);
  }

  .error {
    color: var(--danger);
    font-size: var(--text-sm);
  }
</style>
