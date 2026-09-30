<script>
  import { api } from "../lib/api.js";
  import SpesePianificate from "../lib/components/planning/SpesePianificate.svelte";
  import Budget from "../lib/components/planning/Budget.svelte";
  import Consuntivo from "../lib/components/planning/Consuntivo.svelte";

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

  // Tutte le categorie di spesa, non solo quelle con storico o budget già
  // impostato — così se ne può impostare il budget anche per categorie mai
  // usate finora. Ordinate per media storica decrescente (quelle senza storico
  // restano in fondo).
  let budgetCatKeys = $derived(
    [...spendableCategories].sort((a, b) => (catAverages[b] || 0) - (catAverages[a] || 0))
  );

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
  let exceptionalRows = $derived(monthRows.filter((r) => r.isExceptional));
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
    <SpesePianificate
      {plannedExpenses}
      {monthRows}
      {totalPlanned}
      {exceptionalTotal}
      {colors}
      {spendableCategories}
      {selectedMonth}
      {monthLabel}
      onBaseChange={loadBase}
      onOverrideChange={loadMonthData}
    />
  {:else if activeTab === "budget"}
    <Budget
      {budget}
      {catAverages}
      {totalAvg}
      {nHistoryMonths}
      {budgetCatKeys}
      {colors}
      {selectedMonth}
      {monthLabel}
      onchange={loadMonthData}
    />
  {:else}
    <Consuntivo
      {budget}
      {unifiedRows}
      {selectedMonth}
      {totalPlanned}
      {exceptionalRows}
      {colors}
      {monthLabelShort}
    />
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

  .error {
    color: var(--danger);
    font-size: var(--text-sm);
  }
</style>
