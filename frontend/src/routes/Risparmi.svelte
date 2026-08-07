<script>
  import { api } from "../lib/api.js";
  import Icon from "../lib/components/Icon.svelte";
  import Chart from "../lib/components/Chart.svelte";
  import { CHART_COLORS, hexToRgba, baseScales } from "../lib/chartTheme.js";

  let savings = $state([]);
  let error = $state("");
  let showAddForm = $state(false);

  let addDate = $state(new Date().toISOString().slice(0, 10));
  let addAmount = $state("");
  let addLabel = $state("");
  let addNote = $state("");
  let addError = $state("");

  async function loadAll() {
    try {
      savings = await api.get("/savings");
      error = "";
    } catch (e) {
      error = e.message;
    }
  }

  $effect(() => {
    loadAll();
  });

  let sortedAsc = $derived(savings.slice().sort((a, b) => a.date.localeCompare(b.date)));
  let sortedDesc = $derived(savings.slice().sort((a, b) => b.date.localeCompare(a.date)));

  let saldoAttuale = $derived(savings.reduce((s, r) => s + r.amount, 0));

  let cumulativeSeries = $derived.by(() => {
    let running = 0;
    return sortedAsc.map((r) => {
      running += r.amount;
      return { date: r.date, balance: running };
    });
  });

  let balanceChartData = $derived({
    labels: cumulativeSeries.map((p) => p.date),
    datasets: [
      {
        label: "Saldo",
        data: cumulativeSeries.map((p) => p.balance),
        borderColor: CHART_COLORS.accent,
        backgroundColor: hexToRgba(CHART_COLORS.accent, 0.12),
        fill: true,
        tension: 0.25,
        pointRadius: 2,
      },
    ],
  });

  const balanceChartOptions = {
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: (ctx) => `€${ctx.parsed.y.toFixed(2)}` } },
    },
    scales: baseScales({ y: { ticks: { callback: (v) => `€${v}` } } }),
  };

  async function submitAdd(e) {
    e.preventDefault();
    if (!addAmount || !addLabel.trim()) {
      addError = "Importo ed etichetta sono obbligatori.";
      return;
    }
    try {
      await api.post("/savings", {
        date: addDate,
        amount: Number(addAmount),
        label: addLabel,
        note: addNote,
      });
      addAmount = "";
      addLabel = "";
      addNote = "";
      addError = "";
      showAddForm = false;
      await loadAll();
    } catch (e2) {
      addError = e2.message;
    }
  }

  async function removeEntry(id) {
    try {
      await api.delete(`/savings/${id}`);
      await loadAll();
    } catch (e) {
      error = e.message;
    }
  }
</script>

<section>
  <div class="page-header">
    <div>
      <h2>Risparmi</h2>
      <p class="subtitle">Saldo accantonato nel tempo</p>
    </div>
    <button class="btn-primary" onclick={() => (showAddForm = !showAddForm)}>
      <Icon name="plus" size={14} />
      Aggiungi movimento
    </button>
  </div>

  {#if showAddForm}
    <form class="add-panel" onsubmit={submitAdd}>
      <div class="fields">
        <input type="date" bind:value={addDate} />
        <input type="number" step="0.01" bind:value={addAmount} placeholder="Importo (negativo = prelievo)" />
        <input type="text" bind:value={addLabel} placeholder="Etichetta (es. Accantonamento mensile)" />
        <input type="text" bind:value={addNote} placeholder="Note (opzionale)" />
      </div>
      <button type="submit" class="btn-primary">Salva</button>
      {#if addError}<p class="error">{addError}</p>{/if}
    </form>
  {/if}

  {#if error}
    <p class="error">Backend non raggiungibile: {error}</p>
  {:else if savings.length === 0}
    <p class="hint">Nessun movimento ancora.</p>
  {:else}
    <div class="metric-card kpi-card">
      <span class="eyebrow">Saldo attuale</span>
      <span class="kpi-value" class:positive={saldoAttuale >= 0} class:negative={saldoAttuale < 0}>
        €{saldoAttuale.toFixed(2)}
      </span>
    </div>

    <div class="metric-card chart-card">
      <h3>Andamento saldo</h3>
      <Chart type="line" data={balanceChartData} options={balanceChartOptions} height={280} />
    </div>

    <div class="metric-card">
      <h3>Storico movimenti</h3>
      <div class="list">
        {#each sortedDesc as r (r.id)}
          <div class="row">
            <span class="date">{r.date}</span>
            <div class="desc-cell">
              <span class="desc">{r.label || "Movimento"}</span>
              {#if r.note}<span class="note-inline">{r.note}</span>{/if}
            </div>
            <span class="amount" class:positive={r.amount >= 0} class:negative={r.amount < 0}>
              {r.amount >= 0 ? "+" : ""}€{r.amount.toFixed(2)}
            </span>
            <button class="icon-btn" title="Elimina" onclick={() => removeEntry(r.id)}>
              <Icon name="trash-2" size={14} />
            </button>
          </div>
        {/each}
      </div>
    </div>
  {/if}
</section>

<style>
  .page-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--space-6);
    margin-bottom: var(--space-5);
  }

  .subtitle {
    font-size: var(--text-sm);
    color: var(--text-secondary);
    margin: 4px 0 0;
  }

  .btn-primary {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: 0.5rem var(--space-4);
    border: none;
    border-radius: var(--radius-md);
    background: var(--accent);
    color: var(--accent-foreground);
    font-size: var(--text-sm);
    font-weight: 500;
    cursor: pointer;
  }

  .add-panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: var(--space-4);
    margin-bottom: var(--space-5);
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
  }

  .kpi-card {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    margin-bottom: var(--space-4);
  }

  .kpi-value {
    font-family: var(--font-heading);
    font-size: var(--text-2xl);
    font-weight: 700;
    color: var(--text-primary);
  }

  .kpi-value.positive { color: var(--success); }
  .kpi-value.negative { color: var(--danger); }

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
    width: 6rem;
    flex-shrink: 0;
  }

  .desc-cell {
    flex: 1;
    display: flex;
    flex-direction: column;
  }

  .desc {
    color: var(--text-primary);
    font-weight: 500;
  }

  .note-inline {
    color: var(--text-muted);
    font-size: var(--text-xs);
  }

  .amount {
    font-family: var(--font-heading);
    font-weight: 600;
  }

  .amount.positive { color: var(--success); }
  .amount.negative { color: var(--danger); }

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
