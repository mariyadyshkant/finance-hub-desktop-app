<script>
  import { api } from "../lib/api.js";
  import Icon from "../lib/components/Icon.svelte";
  import Chart from "../lib/components/Chart.svelte";
  import { CHART_COLORS, hexToRgba, baseScales } from "../lib/chartTheme.js";

  const ALL = "__all__";
  const NO_LABEL = "Senza conto";

  // Palette per distinguere i conti nel grafico generale.
  const ACCOUNT_COLORS = [
    CHART_COLORS.accent,
    "#0369a1",
    "#15803d",
    "#b45309",
    "#be123c",
    "#6d28d9",
    "#0f766e",
    "#a21caf",
  ];

  let savings = $state([]);
  let error = $state("");
  let showAddForm = $state(false);
  let activeAccount = $state(ALL);

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

  function accountOf(r) {
    return r.label && r.label.trim() ? r.label.trim() : NO_LABEL;
  }

  let sortedAsc = $derived(savings.slice().sort((a, b) => a.date.localeCompare(b.date)));

  let accounts = $derived(
    Array.from(new Set(sortedAsc.map(accountOf))).sort((a, b) => a.localeCompare(b))
  );

  // Se il conto attivo sparisce (ultimo movimento eliminato) torna al generale.
  $effect(() => {
    if (activeAccount !== ALL && !accounts.includes(activeAccount)) {
      activeAccount = ALL;
    }
  });

  let colorByAccount = $derived(
    Object.fromEntries(accounts.map((a, i) => [a, ACCOUNT_COLORS[i % ACCOUNT_COLORS.length]]))
  );

  // Saldo corrente per ogni conto.
  let perAccount = $derived(
    accounts.map((name) => ({
      name,
      balance: sortedAsc.filter((r) => accountOf(r) === name).reduce((s, r) => s + r.amount, 0),
      count: sortedAsc.filter((r) => accountOf(r) === name).length,
    }))
  );

  let saldoTotale = $derived(savings.reduce((s, r) => s + r.amount, 0));

  // ─── Vista corrente (generale o singolo conto) ────────────────────────────
  let viewAsc = $derived(
    activeAccount === ALL ? sortedAsc : sortedAsc.filter((r) => accountOf(r) === activeAccount)
  );
  let viewDesc = $derived(viewAsc.slice().reverse());
  let viewBalance = $derived(viewAsc.reduce((s, r) => s + r.amount, 0));

  let viewCumulative = $derived.by(() => {
    let running = 0;
    return viewAsc.map((r) => {
      running += r.amount;
      return { date: r.date, balance: running };
    });
  });

  // Grafico: nel generale una linea per conto (saldo cumulativo riportato lungo
  // l'asse comune delle date) + la linea totale; nel singolo conto solo la sua.
  function cumulativeByDate(rows) {
    const byDate = new Map();
    let running = 0;
    for (const r of rows) {
      running += r.amount;
      byDate.set(r.date, running);
    }
    return byDate;
  }

  function seriesAlong(labels, byDate) {
    let last = null;
    return labels.map((d) => {
      if (byDate.has(d)) last = byDate.get(d);
      return last;
    });
  }

  let generalChartData = $derived.by(() => {
    const labels = Array.from(new Set(sortedAsc.map((r) => r.date))).sort();
    const totalByDate = cumulativeByDate(sortedAsc);
    const datasets = accounts.map((name) => {
      const rows = sortedAsc.filter((r) => accountOf(r) === name);
      const color = colorByAccount[name];
      return {
        label: name,
        data: seriesAlong(labels, cumulativeByDate(rows)),
        borderColor: color,
        backgroundColor: color,
        tension: 0.25,
        pointRadius: 2,
        spanGaps: true,
      };
    });
    datasets.push({
      label: "Totale",
      data: seriesAlong(labels, totalByDate),
      borderColor: CHART_COLORS.textPrimary || "#271d6b",
      backgroundColor: hexToRgba(CHART_COLORS.accent, 0.1),
      borderDash: [4, 3],
      fill: true,
      tension: 0.25,
      pointRadius: 0,
    });
    return { labels, datasets };
  });

  let accountChartData = $derived({
    labels: viewCumulative.map((p) => p.date),
    datasets: [
      {
        label: activeAccount,
        data: viewCumulative.map((p) => p.balance),
        borderColor: colorByAccount[activeAccount] || CHART_COLORS.accent,
        backgroundColor: hexToRgba(colorByAccount[activeAccount] || CHART_COLORS.accent, 0.14),
        fill: true,
        tension: 0.25,
        pointRadius: 2,
      },
    ],
  });

  const lineOptions = {
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: €${(ctx.parsed.y ?? 0).toFixed(2)}` } },
    },
    scales: baseScales({ y: { ticks: { callback: (v) => `€${v}` } } }),
  };
  const generalOptions = {
    ...lineOptions,
    plugins: {
      ...lineOptions.plugins,
      legend: { display: true, position: "bottom", labels: { color: CHART_COLORS.textSecondary, boxWidth: 12 } },
    },
  };

  async function submitAdd(e) {
    e.preventDefault();
    if (!addAmount || !addLabel.trim()) {
      addError = "Importo e conto sono obbligatori.";
      return;
    }
    try {
      await api.post("/savings", {
        date: addDate,
        amount: Number(addAmount),
        label: addLabel.trim(),
        note: addNote,
      });
      addAmount = "";
      addNote = "";
      addError = "";
      showAddForm = false;
      await loadAll();
    } catch (e2) {
      addError = e2.message;
    }
  }

  function openAddForm() {
    showAddForm = !showAddForm;
    if (showAddForm && activeAccount !== ALL) addLabel = activeAccount;
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
      <p class="subtitle">Saldo accantonato per conto e complessivo</p>
    </div>
    <button class="btn-primary" onclick={openAddForm}>
      <Icon name="plus" size={14} />
      Aggiungi movimento
    </button>
  </div>

  {#if showAddForm}
    <form class="add-panel" onsubmit={submitAdd}>
      <div class="fields">
        <input type="date" bind:value={addDate} />
        <input type="number" step="0.01" bind:value={addAmount} placeholder="Importo (negativo = prelievo)" />
        <input
          type="text"
          bind:value={addLabel}
          placeholder="Conto / modalità (es. Conto deposito Revolut)"
          list="savings-accounts"
        />
        <datalist id="savings-accounts">
          {#each accounts as a}<option value={a}></option>{/each}
        </datalist>
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
    <div class="tab-bar">
      <button class:active={activeAccount === ALL} onclick={() => (activeAccount = ALL)}>Generale</button>
      {#each accounts as a}
        <button class:active={activeAccount === a} onclick={() => (activeAccount = a)}>
          <i class="dot" style="background:{colorByAccount[a]}"></i>{a}
        </button>
      {/each}
    </div>

    {#if activeAccount === ALL}
      <div class="metric-card kpi-card">
        <span class="eyebrow">Saldo totale</span>
        <span class="kpi-value" class:positive={saldoTotale >= 0} class:negative={saldoTotale < 0}>
          €{saldoTotale.toFixed(2)}
        </span>
      </div>

      <div class="metric-card">
        <h3>Saldo per conto</h3>
        <div class="list">
          {#each perAccount as acc (acc.name)}
            <button class="row account-row" onclick={() => (activeAccount = acc.name)}>
              <i class="dot" style="background:{colorByAccount[acc.name]}"></i>
              <span class="desc-cell"><span class="desc">{acc.name}</span>
                <span class="note-inline">{acc.count} {acc.count === 1 ? "movimento" : "movimenti"}</span>
              </span>
              <span class="amount" class:positive={acc.balance >= 0} class:negative={acc.balance < 0}>
                €{acc.balance.toFixed(2)}
              </span>
              <Icon name="chevron-right" size={14} />
            </button>
          {/each}
        </div>
      </div>

      <div class="metric-card chart-card">
        <h3>Andamento per conto</h3>
        <Chart type="line" data={generalChartData} options={generalOptions} height={300} />
      </div>
    {:else}
      <div class="metric-card kpi-card">
        <span class="eyebrow">Saldo — {activeAccount}</span>
        <span class="kpi-value" class:positive={viewBalance >= 0} class:negative={viewBalance < 0}>
          €{viewBalance.toFixed(2)}
        </span>
        <span class="note-inline">{viewAsc.length} {viewAsc.length === 1 ? "movimento" : "movimenti"} · {(saldoTotale ? (viewBalance / saldoTotale) * 100 : 0).toFixed(0)}% del totale</span>
      </div>

      <div class="metric-card chart-card">
        <h3>Andamento saldo — {activeAccount}</h3>
        <Chart type="line" data={accountChartData} options={lineOptions} height={280} />
      </div>
    {/if}

    <div class="metric-card">
      <h3>Storico movimenti{activeAccount === ALL ? "" : ` — ${activeAccount}`}</h3>
      <div class="list">
        {#each viewDesc as r (r.id)}
          <div class="row">
            <span class="date">{r.date}</span>
            <div class="desc-cell">
              <span class="desc">
                {#if activeAccount === ALL}<i class="dot" style="background:{colorByAccount[accountOf(r)]}"></i>{/if}
                {accountOf(r)}
              </span>
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

  .tab-bar {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
    margin-bottom: var(--space-5);
  }

  .tab-bar button {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: 0.4rem var(--space-4);
    border: none;
    border-radius: var(--radius-md);
    background: var(--muted);
    color: var(--text-primary);
    font-size: var(--text-sm);
    font-weight: 500;
    cursor: pointer;
  }

  .tab-bar button.active {
    background: var(--accent);
    color: var(--accent-foreground);
  }

  .dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 999px;
    flex-shrink: 0;
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

  .account-row {
    width: 100%;
    background: none;
    border: none;
    border-bottom: 1px solid var(--border);
    cursor: pointer;
    text-align: left;
    font: inherit;
    color: inherit;
  }

  .account-row:hover { background: var(--muted); }

  .row .date {
    color: var(--text-muted);
    font-size: var(--text-xs);
    width: 6rem;
    flex-shrink: 0;
  }

  .desc-cell {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
  }

  .desc {
    display: flex;
    align-items: center;
    gap: var(--space-2);
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
