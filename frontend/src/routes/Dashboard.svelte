<script>
  import { api, apiBaseUrl } from "../lib/api.js";
  import Icon from "../lib/components/Icon.svelte";
  import Chart from "../lib/components/Chart.svelte";
  import { CHART_COLORS, baseScales } from "../lib/chartTheme.js";
  import { plannedApplies } from "../lib/planned.js";

  const NON_SPESA = ["Entrata", "Rimborso ricevuto", "Altro"];

  let allTx = $state([]);
  let notionSummaries = $state([]);
  let revolutMonths = $state([]);
  let notionMonths = $state([]);
  let categories = $state([]);
  let colors = $state({});
  let selectedMonth = $state("");
  let error = $state("");

  // Spese pianificate (lista base + override del mese) — non entrano nella
  // lista transazioni, ma vanno conteggiate accanto al totale speso del mese.
  let plannedExpenses = $state([]);
  let plannedOverrides = $state({});

  let showImport = $state(false);
  let importRecords = $state([]);
  let importError = $state("");
  let importBusy = $state(false);

  let trendCategories = $state(["Bar & Ristoranti", "Spesa", "Abbonamenti", "Auto"]);

  function monthLabel(m) {
    if (!m) return "";
    const label = new Date(`${m}-01T00:00:00`).toLocaleDateString("it-IT", {
      month: "long",
      year: "numeric",
    });
    return label.charAt(0).toUpperCase() + label.slice(1);
  }

  function monthLabelShort(m) {
    const label = new Date(`${m}-01T00:00:00`).toLocaleDateString("it-IT", {
      month: "short",
      year: "2-digit",
    });
    return label.charAt(0).toUpperCase() + label.slice(1);
  }

  async function loadAll() {
    try {
      const [tx, summaries, rMonths, nMonths, planned] = await Promise.all([
        api.get("/transactions"),
        api.get("/summaries"),
        api.get("/transactions/months"),
        api.get("/summaries/months"),
        api.get("/planning/planned-expenses"),
      ]);
      allTx = tx;
      notionSummaries = summaries;
      revolutMonths = rMonths;
      notionMonths = nMonths;
      plannedExpenses = planned;
      error = "";
      if (!selectedMonth) {
        const all = Array.from(new Set([...rMonths, ...nMonths])).sort().reverse();
        if (all.length) selectedMonth = all[0];
      }
    } catch (e) {
      error = e.message;
    }
  }

  $effect(() => {
    api.get("/categories").then((c) => {
      categories = c.categories;
      colors = c.colors;
    });
    loadAll();
  });

  $effect(() => {
    if (!selectedMonth) return;
    api
      .get(`/planning/overrides/${selectedMonth}`)
      .then((o) => (plannedOverrides = o))
      .catch(() => (plannedOverrides = {}));
  });

  let allMonths = $derived(
    Array.from(new Set([...revolutMonths, ...notionMonths])).sort().reverse()
  );

  let spendableCategories = $derived(categories.filter((c) => !NON_SPESA.includes(c)));

  // righe unificate: {month, category, amount (spesa, positivo), source}
  let unifiedRows = $derived.by(() => {
    const rows = [];
    for (const r of notionSummaries) {
      rows.push({ month: r.month, category: r.category, amount: r.amount, source: "notion" });
    }
    const agg = {};
    for (const tx of allTx) {
      if (tx.amount >= 0) continue;
      const month = tx.date.slice(0, 7);
      const key = month + "||" + tx.category;
      if (!agg[key]) agg[key] = { month, category: tx.category, amount: 0, source: "revolut" };
      agg[key].amount += Math.abs(tx.amount);
    }
    rows.push(...Object.values(agg));
    return rows;
  });

  // Le spese pianificate del mese selezionato, nella stessa forma delle righe
  // unificate — così entrano in ogni calcolo e grafico del mese (tranne
  // l'andamento giornaliero, che non hanno una data). Rappresentano spesa
  // attesa non ancora a estratto conto: si sommano solo al mese selezionato,
  // non retroattivamente agli altri mesi del confronto.
  let plannedMonthRows = $derived(
    plannedApplies(selectedMonth)
      ? plannedExpenses.map((p) => ({
          month: selectedMonth,
          category: p.category,
          amount: plannedOverrides[p.id]?.amount ?? p.amount,
          source: "planned",
        }))
      : []
  );
  let plannedTotal = $derived(plannedMonthRows.reduce((s, r) => s + r.amount, 0));

  let rowsWithPlanned = $derived([...unifiedRows, ...plannedMonthRows]);

  let monthRows = $derived(rowsWithPlanned.filter((r) => r.month === selectedMonth));
  let txSpese = $derived(
    monthRows.filter((r) => r.source !== "planned").reduce((s, r) => s + r.amount, 0)
  );
  let totSpese = $derived(monthRows.reduce((s, r) => s + r.amount, 0));
  let isRevolutMonth = $derived(revolutMonths.includes(selectedMonth));
  let totEntrate = $derived(
    isRevolutMonth
      ? allTx
          .filter((tx) => tx.date.slice(0, 7) === selectedMonth && tx.amount > 0)
          .reduce((s, tx) => s + tx.amount, 0)
      : 0
  );
  let saldo = $derived(totEntrate - totSpese);
  let affittoMese = $derived(
    monthRows.filter((r) => r.category === "Affitto").reduce((s, r) => s + r.amount, 0)
  );
  let senzaAffitto = $derived(totSpese - affittoMese);

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

  async function handleFileSelect(e) {
    const file = e.target.files[0];
    if (!file) return;
    importBusy = true;
    importError = "";
    try {
      const formData = new FormData();
      formData.append("file", file);
      const base = await apiBaseUrl();
      const res = await fetch(`${base}/api/transactions/parse-revolut`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const data = await res.json();
      importRecords = data.records || [];
      if (importRecords.length === 0) importError = "Nessuna transazione trovata nel file.";
    } catch (err) {
      importError = err.message;
      importRecords = [];
    } finally {
      importBusy = false;
    }
  }

  async function confirmImport() {
    try {
      await api.post("/transactions/import", importRecords);
      importRecords = [];
      showImport = false;
      await loadAll();
    } catch (err) {
      importError = err.message;
    }
  }

  let importSpese = $derived(
    importRecords.filter((r) => r.amount < 0).reduce((s, r) => s + Math.abs(r.amount), 0)
  );
  let importEntrate = $derived(
    importRecords.filter((r) => r.amount > 0).reduce((s, r) => s + r.amount, 0)
  );
</script>

<section>
  <div class="page-header">
    <div>
      <h2>Dashboard</h2>
      <p class="subtitle">Panoramica mensile</p>
    </div>
    <button class="btn-secondary" onclick={() => (showImport = !showImport)}>
      <Icon name="file-text" size={14} />
      Importa estratto Revolut
    </button>
  </div>

  {#if showImport}
    <div class="import-panel">
      <p class="hint">Carica il PDF (estratto conto) o il CSV esportato da Revolut.</p>
      <input type="file" accept=".pdf,.csv" onchange={handleFileSelect} />
      {#if importBusy}<p class="hint">Analisi in corso...</p>{/if}
      {#if importError}<p class="error">{importError}</p>{/if}
      {#if importRecords.length > 0}
        <p class="hint">
          Trovate <strong>{importRecords.length}</strong> transazioni — spese €{importSpese.toFixed(2)}, entrate €{importEntrate.toFixed(2)}
        </p>
        <button class="btn-primary" onclick={confirmImport}>Importa tutto nel database</button>
      {/if}
    </div>
  {/if}

  {#if error}
    <p class="error">Backend non raggiungibile: {error}</p>
  {:else if allMonths.length === 0}
    <p class="hint">Nessun dato ancora. Importa un estratto Revolut o aggiungi mesi storici da Notion.</p>
  {:else}
    <div class="toolbar">
      <select bind:value={selectedMonth}>
        {#each allMonths as m}<option value={m}>{monthLabel(m)}</option>{/each}
      </select>
      <span class="source-badge">
        {#if isRevolutMonth && notionMonths.includes(selectedMonth)}
          Dati da: Revolut + Notion
        {:else if isRevolutMonth}
          Dati da: Revolut
        {:else}
          Dati da: Notion (riepilogo mensile)
        {/if}
      </span>
    </div>

    <div class="kpi-grid">
      <div class="metric-card">
        <span class="eyebrow">Totale spese</span>
        <span class="kpi-value negative">−€{totSpese.toFixed(2)}</span>
        {#if plannedTotal > 0}
          <span class="kpi-addon">
            €{txSpese.toFixed(2)} transazioni + €{plannedTotal.toFixed(2)} pianificate
          </span>
        {/if}
      </div>
      <div class="metric-card">
        <span class="eyebrow">Entrate</span>
        <span class="kpi-value" class:positive={totEntrate > 0}>
          {isRevolutMonth ? `+€${totEntrate.toFixed(2)}` : "n/d"}
        </span>
      </div>
      <div class="metric-card">
        <span class="eyebrow">Saldo</span>
        <span class="kpi-value" class:positive={saldo >= 0} class:negative={saldo < 0}>
          {isRevolutMonth ? `${saldo >= 0 ? "+" : ""}€${saldo.toFixed(2)}` : "n/d"}
        </span>
      </div>
      <div class="metric-card">
        <span class="eyebrow">Senza affitto</span>
        <span class="kpi-value negative">−€{senzaAffitto.toFixed(2)}</span>
      </div>
    </div>

    <div class="charts-row" class:single={!dailyChartData}>
      <div class="metric-card chart-card">
        <h3>Spese per categoria</h3>
        {#if categoryBreakdown.length > 0}
          <Chart type="bar" data={categoryChartData} options={categoryChartOptions} height={Math.max(180, categoryBreakdown.length * 26)} />
        {:else}
          <p class="hint">Nessuna spesa per questo mese.</p>
        {/if}
      </div>
      {#if dailyChartData}
        <div class="metric-card chart-card">
          <h3>Andamento giornaliero</h3>
          <Chart type="bar" data={dailyChartData} options={dailyChartOptions} height={280} />
        </div>
      {/if}
    </div>

    <div class="metric-card chart-card">
      <h3>Confronto ultimi mesi</h3>
      <div class="legend-inline">
        <span><i class="dot" style="background:{CHART_COLORS.sourceRevolut}"></i>Revolut</span>
        <span><i class="dot" style="background:{CHART_COLORS.sourceNotion}"></i>Notion</span>
      </div>
      <Chart type="bar" data={monthlyChartData} options={monthlyChartOptions} height={260} />
    </div>

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

    {#if avgVsMonth.length > 0}
      <div class="metric-card chart-card">
        <h3>Media mensile per categoria</h3>
        <p class="hint">Calcolata su {allMonths.length} {allMonths.length === 1 ? "mese" : "mesi"} — confronto con {monthLabel(selectedMonth)}</p>
        <Chart type="bar" data={avgChartData} options={avgChartOptions} height={300} />
      </div>
    {/if}
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

  .btn-secondary {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: 0.5rem var(--space-4);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    background: var(--surface);
    color: var(--text-primary);
    font-size: var(--text-sm);
    font-weight: 500;
    cursor: pointer;
  }

  .btn-primary {
    padding: 0.5rem var(--space-4);
    border: none;
    border-radius: var(--radius-md);
    background: var(--accent);
    color: var(--accent-foreground);
    font-size: var(--text-sm);
    font-weight: 500;
    cursor: pointer;
  }

  .import-panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: var(--space-4);
    margin-bottom: var(--space-5);
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .hint {
    font-size: var(--text-sm);
    color: var(--text-secondary);
    margin: 0;
  }

  .toolbar {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    margin-bottom: var(--space-5);
  }

  .toolbar select {
    padding: 0.5rem var(--space-3);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    background: var(--input-bg);
    font-size: var(--text-sm);
  }

  .source-badge {
    font-size: var(--text-xs);
    color: var(--text-muted);
  }

  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: var(--space-3);
    margin-bottom: var(--space-5);
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

  .kpi-value.negative { color: var(--danger); }
  .kpi-value.positive { color: var(--success); }

  .kpi-addon {
    font-size: var(--text-xs);
    color: var(--text-muted);
  }

  .charts-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-4);
    margin-bottom: var(--space-4);
  }

  .charts-row.single {
    grid-template-columns: 1fr;
  }

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

  .error {
    color: var(--danger);
    font-size: var(--text-sm);
  }
</style>
