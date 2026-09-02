<script>
  import { api } from "../lib/api.js";
  import Icon from "../lib/components/Icon.svelte";
  import Chart from "../lib/components/Chart.svelte";
  import { CHART_COLORS, baseScales } from "../lib/chartTheme.js";
  import { plannedApplies } from "../lib/planned.js";

  const NON_SPESA = ["Entrata", "Rimborso ricevuto", "Altro"];

  let activeTab = $state("spese");
  let allTx = $state([]);
  let notionSummaries = $state([]);
  let revolutMonths = $state([]);
  let notionMonths = $state([]);
  let plannedExpenses = $state([]);
  let overrides = $state({});
  let budget = $state(null);
  let categories = $state([]);
  let colors = $state({});
  let selectedMonth = $state("");
  let error = $state("");

  function monthLabel(m) {
    if (!m) return "";
    const label = new Date(`${m}-01T00:00:00`).toLocaleDateString("it-IT", { month: "long", year: "numeric" });
    return label.charAt(0).toUpperCase() + label.slice(1);
  }
  function monthLabelShort(m) {
    const label = new Date(`${m}-01T00:00:00`).toLocaleDateString("it-IT", { month: "short", year: "2-digit" });
    return label.charAt(0).toUpperCase() + label.slice(1);
  }

  async function loadBase() {
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
        const current = new Date().toISOString().slice(0, 7);
        const all = Array.from(new Set([...rMonths, ...nMonths, current])).sort().reverse();
        selectedMonth = all[0];
      }
    } catch (e) {
      error = e.message;
    }
  }

  async function loadMonthData() {
    if (!selectedMonth) return;
    try {
      overrides = await api.get(`/planning/overrides/${selectedMonth}`);
    } catch (e) {
      overrides = {};
    }
    try {
      budget = await api.get(`/planning/budget/${selectedMonth}`);
    } catch (e) {
      budget = null;
    }
  }

  $effect(() => {
    api.get("/categories").then((c) => {
      categories = c.categories;
      colors = c.colors;
    });
    loadBase();
  });

  $effect(() => {
    selectedMonth;
    loadMonthData();
  });

  let allMonths = $derived(
    Array.from(new Set([...revolutMonths, ...notionMonths, selectedMonth].filter(Boolean))).sort().reverse()
  );
  let spendableCategories = $derived(categories.filter((c) => !NON_SPESA.includes(c)));

  let unifiedRows = $derived.by(() => {
    const rows = [];
    for (const r of notionSummaries) rows.push({ month: r.month, category: r.category, amount: r.amount });
    const agg = {};
    for (const tx of allTx) {
      if (tx.amount >= 0) continue;
      const month = tx.date.slice(0, 7);
      const key = month + "||" + tx.category;
      if (!agg[key]) agg[key] = { month, category: tx.category, amount: 0 };
      agg[key].amount += Math.abs(tx.amount);
    }
    rows.push(...Object.values(agg));
    return rows;
  });

  let historyMonths = $derived(Array.from(new Set([...revolutMonths, ...notionMonths])));
  let nHistoryMonths = $derived(historyMonths.length);

  let catAverages = $derived.by(() => {
    const out = {};
    if (nHistoryMonths === 0) return out;
    for (const cat of spendableCategories) {
      let sum = 0;
      for (const m of historyMonths) {
        sum += unifiedRows.filter((r) => r.month === m && r.category === cat).reduce((s, r) => s + r.amount, 0);
      }
      out[cat] = sum / nHistoryMonths;
    }
    return out;
  });
  let totalAvg = $derived(Object.values(catAverages).reduce((s, v) => s + v, 0));

  // ─── Tab: Spese pianificate ───────────────────────────────────────────────
  let showManageList = $state(false);
  let pDesc = $state("");
  let pAmount = $state("");
  let pCategory = $state("");
  let pError = $state("");
  let editingId = $state(null);
  let editDesc = $state("");
  let editAmount = $state("");
  let editCategory = $state("");

  $effect(() => {
    if (!pCategory && spendableCategories.length) pCategory = spendableCategories[0];
  });

  async function addPlanned(e) {
    e.preventDefault();
    if (!pDesc.trim() || !pAmount) {
      pError = "Descrizione e importo sono obbligatori.";
      return;
    }
    try {
      await api.post("/planning/planned-expenses", { description: pDesc, amount: Number(pAmount), category: pCategory });
      pDesc = "";
      pAmount = "";
      pError = "";
      await loadBase();
    } catch (e2) {
      pError = e2.message;
    }
  }

  function startEdit(p) {
    editingId = p.id;
    editDesc = p.description;
    editAmount = p.amount;
    editCategory = p.category;
  }

  async function saveEdit(pid) {
    try {
      await api.put(`/planning/planned-expenses/${pid}`, {
        description: editDesc,
        amount: Number(editAmount),
        category: editCategory,
      });
      editingId = null;
      await loadBase();
    } catch (e) {
      pError = e.message;
    }
  }

  async function deletePlanned(pid) {
    try {
      await api.delete(`/planning/planned-expenses/${pid}`);
      await loadBase();
    } catch (e) {
      pError = e.message;
    }
  }

  let monthRows = $derived(
    plannedExpenses.map((p) => {
      const ov = overrides[p.id];
      return {
        id: p.id,
        desc: p.description,
        cat: p.category,
        amount: ov ? ov.amount : p.amount,
        isExceptional: ov ? !!ov.is_exceptional : false,
        note: ov ? ov.note || "" : "",
      };
    })
  );
  let totalPlanned = $derived(monthRows.reduce((s, r) => s + r.amount, 0));
  let exceptionalTotal = $derived(monthRows.filter((r) => r.isExceptional).reduce((s, r) => s + r.amount, 0));

  // Ricostruito interamente ogni volta che monthRows cambia (nuovo mese, nuovi
  // override salvati) — mai mutato dentro il markup durante il render.
  let rowEdits = $state({});
  $effect(() => {
    const edits = {};
    for (const row of monthRows) {
      edits[row.id] = { amount: row.amount, isExceptional: row.isExceptional, note: row.note };
    }
    rowEdits = edits;
  });

  async function saveOverride(row) {
    const edit = rowEdits[row.id] || row;
    try {
      await api.post("/planning/overrides", {
        month: selectedMonth,
        planned_id: row.id,
        amount: Number(edit.amount),
        is_exceptional: edit.isExceptional ? 1 : 0,
        note: edit.note || "",
      });
      await loadMonthData();
    } catch (e) {
      pError = e.message;
    }
  }

  // ─── Tab: Budget ──────────────────────────────────────────────────────────
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

  // Tutte le categorie di spesa, non solo quelle con storico o budget già
  // impostato — così se ne può impostare il budget anche per categorie mai
  // usate finora. Ordinate per media storica decrescente (quelle senza storico
  // restano in fondo).
  let budgetCatKeys = $derived(
    [...spendableCategories].sort((a, b) => (catAverages[b] || 0) - (catAverages[a] || 0))
  );
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
      await loadMonthData();
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

  // ─── Tab: Consuntivo ──────────────────────────────────────────────────────
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

  let exceptionalRows = $derived(monthRows.filter((r) => r.isExceptional));

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

<section>
  <div class="page-header">
    <h2>Pianificazione & Budget</h2>
    <select bind:value={selectedMonth}>
      {#each allMonths as m}<option value={m}>{monthLabel(m)}</option>{/each}
    </select>
  </div>

  <div class="status-pill-group">
    <button class:active={activeTab === "spese"} onclick={() => (activeTab = "spese")}>Spese pianificate</button>
    <button class:active={activeTab === "budget"} onclick={() => (activeTab = "budget")}>Budget</button>
    <button class:active={activeTab === "consuntivo"} onclick={() => (activeTab = "consuntivo")}>Consuntivo</button>
  </div>

  {#if error}
    <p class="error">Backend non raggiungibile: {error}</p>
  {:else if activeTab === "spese"}
    <div class="toolbar">
      <button class="btn-secondary" onclick={() => (showManageList = !showManageList)}>
        <Icon name="pencil" size={14} /> Gestisci lista base
      </button>
    </div>

    {#if showManageList}
      <div class="metric-card">
        <form class="fields-row" onsubmit={addPlanned}>
          <input type="text" bind:value={pDesc} placeholder="Descrizione (es. Affitto)" />
          <input type="number" step="0.01" bind:value={pAmount} placeholder="Importo €" />
          <select bind:value={pCategory}>
            {#each spendableCategories as c}<option value={c}>{c}</option>{/each}
          </select>
          <button type="submit" class="btn-primary"><Icon name="plus" size={14} /> Aggiungi</button>
        </form>
        {#if pError}<p class="error">{pError}</p>{/if}
        <div class="list">
          {#each plannedExpenses as p (p.id)}
            {#if editingId === p.id}
              <div class="row edit-row">
                <input type="text" bind:value={editDesc} />
                <input type="number" step="0.01" bind:value={editAmount} />
                <select bind:value={editCategory}>
                  {#each spendableCategories as c}<option value={c}>{c}</option>{/each}
                </select>
                <button class="icon-btn" onclick={() => saveEdit(p.id)}><Icon name="check" size={14} /></button>
              </div>
            {:else}
              <div class="row">
                <span class="desc">{p.description}</span>
                <span class="cat-pill" style="background:{(colors[p.category] || '#888')}1f; color:{colors[p.category] || '#888'}">{p.category}</span>
                <span class="hours">€{p.amount.toFixed(2)}</span>
                <button class="icon-btn" title="Modifica" onclick={() => startEdit(p)}><Icon name="pencil" size={14} /></button>
                <button class="icon-btn" title="Elimina" onclick={() => deletePlanned(p.id)}><Icon name="trash-2" size={14} /></button>
              </div>
            {/if}
          {/each}
        </div>
      </div>
    {/if}

    {#if plannedExpenses.length === 0}
      <p class="hint">Aggiungi spese fisse nella lista base qui sopra.</p>
    {:else}
      <div class="metric-card">
        <h3>Spese per {monthLabel(selectedMonth)}</h3>
        <div class="list">
          {#each monthRows as row (row.id)}
            {@const edit = rowEdits[row.id] ?? row}
            <div class="row plan-row">
              <span class="desc">
                {row.desc}
                <span class="cat-pill" style="background:{(colors[row.cat] || '#888')}1f; color:{colors[row.cat] || '#888'}">{row.cat}</span>
                {#if row.isExceptional}<span class="exc-badge">eccezionale</span>{/if}
              </span>
              <input type="number" step="0.01" bind:value={edit.amount} class="amt-input" />
              <label class="exc-check">
                <input type="checkbox" bind:checked={edit.isExceptional} /> Eccez.
              </label>
              <input type="text" bind:value={edit.note} placeholder="nota" class="note-input" />
              <button class="icon-btn" title="Salva" onclick={() => saveOverride(row)}><Icon name="check" size={14} /></button>
            </div>
          {/each}
        </div>
      </div>

      <div class="kpi-grid three">
        <div class="metric-card">
          <span class="eyebrow">Totale pianificato</span>
          <span class="kpi-value">€{totalPlanned.toFixed(2)}</span>
        </div>
        <div class="metric-card">
          <span class="eyebrow">Spese eccezionali</span>
          <span class="kpi-value negative">€{exceptionalTotal.toFixed(2)}</span>
        </div>
        <div class="metric-card">
          <span class="eyebrow">Spese ordinarie</span>
          <span class="kpi-value">€{(totalPlanned - exceptionalTotal).toFixed(2)}</span>
        </div>
      </div>
    {/if}
  {:else if activeTab === "budget"}
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
  {:else}
    <!-- Consuntivo -->
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
  {/if}
</section>

<style>
  .page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-4);
    margin-bottom: var(--space-4);
  }

  .page-header select {
    padding: 0.5rem var(--space-3);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    background: var(--input-bg);
    font-size: var(--text-sm);
  }

  .status-pill-group {
    display: flex;
    gap: var(--space-2);
    margin-bottom: var(--space-5);
  }

  .status-pill-group button {
    padding: 0.4rem var(--space-4);
    border: none;
    border-radius: var(--radius-md);
    background: var(--muted);
    color: var(--text-primary);
    font-size: var(--text-sm);
    font-weight: 500;
    cursor: pointer;
  }

  .status-pill-group button.active {
    background: var(--accent);
    color: var(--accent-foreground);
  }

  .toolbar {
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

  .fields-row {
    display: flex;
    gap: var(--space-2);
    flex-wrap: wrap;
  }

  .fields-row input, .fields-row select {
    padding: 0.5rem var(--space-3);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    background: var(--input-bg);
    font-size: var(--text-sm);
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

  .cat-pill {
    padding: 2px 8px;
    border-radius: var(--radius-sm);
    font-size: var(--text-xs);
  }

  .exc-badge {
    font-size: var(--text-xs);
    color: var(--danger);
  }

  .edit-row input, .edit-row select {
    padding: 0.35rem var(--space-2);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    font-size: var(--text-sm);
  }

  .plan-row {
    gap: var(--space-3);
    flex-wrap: wrap;
  }

  .amt-input {
    width: 6rem;
    padding: 0.35rem var(--space-2);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    font-size: var(--text-sm);
  }

  .exc-check {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: var(--text-xs);
    color: var(--text-secondary);
  }

  .note-input {
    flex: 1;
    min-width: 8rem;
    padding: 0.35rem var(--space-2);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    font-size: var(--text-sm);
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
    color: var(--accent);
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

  .error {
    color: var(--danger);
    font-size: var(--text-sm);
  }
</style>
