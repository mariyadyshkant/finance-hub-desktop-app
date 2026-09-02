<script>
  import { api } from "../lib/api.js";
  import Icon from "../lib/components/Icon.svelte";
  import TransactionRow from "../lib/components/TransactionRow.svelte";
  import { plannedApplies } from "../lib/planned.js";

  let transactions = $state([]);
  let months = $state([]);
  let categories = $state([]);
  let colors = $state({});
  let icons = $state({});
  let selectedMonth = $state("");

  // Spese pianificate: non compaiono nella lista, ma il loro totale è affiancato
  // al "Totale spese" del mese selezionato.
  let plannedExpenses = $state([]);
  let plannedOverrides = $state({});
  let search = $state("");
  let categoryFilter = $state([]);
  let typeFilter = $state("tutto");
  let error = $state("");
  let showAddForm = $state(false);

  let addDate = $state(new Date().toISOString().slice(0, 10));
  let addDesc = $state("");
  let addAmount = $state(-10);
  let addCategory = $state("");
  let addNote = $state("");
  let addError = $state("");

  $effect(() => {
    api.get("/categories").then((c) => {
      categories = c.categories;
      colors = c.colors;
      icons = c.icons || {};
      if (!addCategory && categories.length) addCategory = categories[0];
    });
    // Il selettore mese resta vuoto finché non se ne carica l'elenco: senza
    // questa chiamata i mesi comparivano solo dopo aver aggiunto una transazione
    // (unico altro punto che popola `months`).
    api.get("/transactions/months").then((m) => (months = m)).catch(() => {});
    api.get("/planning/planned-expenses").then((p) => (plannedExpenses = p)).catch(() => {});
  });

  $effect(() => {
    if (!selectedMonth) {
      plannedOverrides = {};
      return;
    }
    api
      .get(`/planning/overrides/${selectedMonth}`)
      .then((o) => (plannedOverrides = o))
      .catch(() => (plannedOverrides = {}));
  });

  let plannedTotal = $derived(
    plannedExpenses.reduce((s, p) => s + (plannedOverrides[p.id]?.amount ?? p.amount), 0)
  );

  async function loadTransactions() {
    try {
      const path = selectedMonth ? `/transactions?month=${selectedMonth}` : "/transactions";
      transactions = await api.get(path);
      error = "";
    } catch (e) {
      error = e.message;
    }
  }

  $effect(() => {
    selectedMonth;
    loadTransactions();
  });

  function monthLabel(m) {
    const label = new Date(`${m}-01T00:00:00`).toLocaleDateString("it-IT", {
      month: "long",
      year: "numeric",
    });
    return label.charAt(0).toUpperCase() + label.slice(1);
  }

  let filtered = $derived(
    transactions.filter((tx) => {
      if (search && !tx.description.toLowerCase().includes(search.toLowerCase())) return false;
      if (categoryFilter.length && !categoryFilter.includes(tx.category)) return false;
      if (typeFilter === "spese" && tx.amount >= 0) return false;
      if (typeFilter === "entrate" && tx.amount < 0) return false;
      return true;
    })
  );

  let totalSpese = $derived(
    filtered.filter((tx) => tx.amount < 0).reduce((sum, tx) => sum + Math.abs(tx.amount), 0)
  );
  let speseCount = $derived(filtered.filter((tx) => tx.amount < 0).length);
  let entrateCount = $derived(filtered.filter((tx) => tx.amount >= 0).length);

  const HIDDEN_FROM_FILTER = ["Entrata", "Rimborso ricevuto", "Altro"];
  let filterableCategories = $derived(categories.filter((c) => !HIDDEN_FROM_FILTER.includes(c)));

  function toggleCategoryFilter(cat) {
    categoryFilter = categoryFilter.includes(cat)
      ? categoryFilter.filter((c) => c !== cat)
      : [...categoryFilter, cat];
  }

  async function submitAdd(e) {
    e.preventDefault();
    if (!addDesc.trim()) {
      addError = "Inserisci una descrizione.";
      return;
    }
    try {
      await api.post("/transactions", {
        date: addDate,
        description: addDesc,
        amount: Number(addAmount),
        category: addCategory,
        source: "manual",
        note: addNote,
      });
      addDesc = "";
      addNote = "";
      addAmount = -10;
      addError = "";
      showAddForm = false;
      await loadTransactions();
      months = await api.get("/transactions/months");
    } catch (e2) {
      addError = e2.message;
    }
  }
</script>

<section>
  <div class="page-header">
    <div>
      <h2>Transazioni</h2>
      <p class="subtitle">Tutte le spese e le entrate</p>
    </div>
    <div class="header-actions">
      <div class="input-box search-box">
        <Icon name="search" size={14} />
        <input type="text" bind:value={search} placeholder="Cerca..." />
      </div>
      <div class="input-box">
        <Icon name="calendar" size={14} />
        <select bind:value={selectedMonth}>
          <option value="">Tutti i mesi</option>
          {#each months as m}<option value={m}>{monthLabel(m)}</option>{/each}
        </select>
      </div>
      <button class="btn-primary" onclick={() => (showAddForm = !showAddForm)}>
        <Icon name="plus" size={14} />
        Aggiungi transazione
      </button>
    </div>
  </div>

  {#if showAddForm}
    <form class="add-panel" onsubmit={submitAdd}>
      <div class="fields">
        <input type="date" bind:value={addDate} />
        <input type="text" bind:value={addDesc} placeholder="Descrizione" />
        <input type="number" step="0.01" bind:value={addAmount} placeholder="Importo (negativo = spesa)" />
        <select bind:value={addCategory}>
          {#each categories as c}<option value={c}>{c}</option>{/each}
        </select>
        <input type="text" bind:value={addNote} placeholder="Note (opzionale)" />
      </div>
      <button type="submit" class="btn-primary">Salva</button>
      {#if addError}<p class="error">{addError}</p>{/if}
    </form>
  {/if}

  {#if error}
    <p class="error">Backend non raggiungibile: {error}</p>
  {:else}
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-head">
          <span class="eyebrow">Totale spese</span>
          <div class="stat-icon"><Icon name="trending-down" size={14} /></div>
        </div>
        <span class="stat-value">€{totalSpese.toFixed(2)}</span>
        {#if plannedApplies(selectedMonth) && plannedTotal > 0}
          <span class="stat-caption">
            + €{plannedTotal.toFixed(2)} pianificate → <strong>€{(totalSpese + plannedTotal).toFixed(2)}</strong> con pianificate
          </span>
        {:else}
          <span class="stat-caption">nel periodo selezionato</span>
        {/if}
      </div>
      <div class="stat-card">
        <div class="stat-head">
          <span class="eyebrow">Transazioni</span>
          <div class="stat-icon"><Icon name="list" size={14} /></div>
        </div>
        <span class="stat-value">{filtered.length}</span>
        <span class="stat-caption">{speseCount} spese · {entrateCount} entrate</span>
      </div>
    </div>

    <div class="filters-row">
      <div class="filter-group">
        <span class="eyebrow">Tipo</span>
        <div class="status-pill-group">
          <button class:active={typeFilter === "tutto"} onclick={() => (typeFilter = "tutto")}>Tutto</button>
          <button class:active={typeFilter === "spese"} onclick={() => (typeFilter = "spese")}>Spese</button>
          <button class:active={typeFilter === "entrate"} onclick={() => (typeFilter = "entrate")}>Entrate</button>
        </div>
      </div>
      <div class="filter-group divider">
        <span class="eyebrow">Categorie</span>
        <div class="pill-group cat-pills">
          {#each filterableCategories as c}
            <button
              class="cat-pill"
              class:active={categoryFilter.includes(c)}
              style="--pill-color: {colors[c] || '#6966a0'}"
              onclick={() => toggleCategoryFilter(c)}
            >{c}</button>
          {/each}
        </div>
      </div>
    </div>

    <div class="table-card">
      {#if filtered.length === 0}
        <p class="empty">Nessuna transazione. Aggiungine una manuale, oppure importa un estratto Revolut dalla Dashboard.</p>
      {:else}
        <div class="table-header">
          <div class="th-icon"></div>
          <div class="th-desc eyebrow">Descrizione</div>
          <div class="th-cat eyebrow">Categoria</div>
          <div class="th-date eyebrow">Data</div>
          <div class="th-amount eyebrow">Importo</div>
          <div class="th-actions"></div>
        </div>
        {#each filtered as tx (tx.id)}
          <TransactionRow {tx} {categories} {colors} {icons} onchange={loadTransactions} />
        {/each}
      {/if}
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

  .header-actions {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    flex-shrink: 0;
  }

  .input-box {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    background: var(--input-bg);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 0.5rem var(--space-3);
    color: var(--text-secondary);
  }

  .search-box {
    width: 140px;
    min-width: 0;
    flex-shrink: 1;
  }

  .input-box input, .input-box select {
    min-width: 0;
    width: 100%;
    border: none;
    background: none;
    font-size: var(--text-sm);
    color: var(--text-primary);
    outline: none;
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

  .btn-primary:hover {
    background: var(--accent-hover);
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

  .add-panel input, .add-panel select {
    padding: 0.5rem var(--space-3);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    background: var(--input-bg);
    font-size: var(--text-sm);
  }

  .add-panel .btn-primary {
    align-self: flex-start;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--space-3);
    margin-bottom: var(--space-5);
  }

  .stat-card {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: var(--space-5);
    box-shadow: var(--shadow-sm);
  }

  .stat-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .stat-icon {
    width: 32px;
    height: 32px;
    border-radius: var(--radius-md);
    background: var(--muted);
    color: var(--text-secondary);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .stat-value {
    font-family: var(--font-heading);
    font-size: var(--text-2xl);
    font-weight: 700;
    color: var(--text-primary);
  }

  .stat-caption {
    font-size: var(--text-xs);
    color: var(--text-muted);
  }

  .filters-row {
    display: flex;
    gap: var(--space-6);
    margin-bottom: var(--space-5);
  }

  .filter-group {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .filter-group.divider {
    padding-left: var(--space-6);
    border-left: 1px solid var(--border);
  }

  .pill-group {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
  }

  .pill-group > button {
    padding: 0.3rem var(--space-3);
    border: none;
    border-radius: var(--radius-md);
    background: var(--muted);
    color: var(--text-primary);
    font-size: var(--text-xs);
    font-weight: 500;
    cursor: pointer;
  }

  .pill-group > button.active {
    background: var(--accent);
    color: var(--accent-foreground);
  }

  /* gruppo separato da .pill-group: solo i filtri Tutto/Spese/Entrate,
     con un onclick e uno stato attivo indipendenti da quelli delle categorie */
  .status-pill-group {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-2);
  }

  .status-pill-group > button {
    position: relative;
    padding: 0.3rem var(--space-3);
    border: none;
    border-radius: var(--radius-md);
    background: var(--muted);
    color: var(--text-primary);
    font-size: var(--text-xs);
    font-weight: 500;
    cursor: pointer;
    transform: scale(1);
    transition: transform 0.5s;
  }

  .status-pill-group > button::after {
    content: "";
    position: absolute;
    bottom: -2px;
    left: 50%;
    width: 28px;
    height: 2px;
    border-radius: 1px;
    background: var(--accent);
    transform: translateX(-50%) scaleX(0);
    transition: transform 0.2s ease;
  }

  .status-pill-group > button.active {
    transform: scale(1.08);
  }

  .status-pill-group > button.active::after {
    transform: translateX(-50%) scaleX(1);
  }

  .cat-pill {
    background: color-mix(in srgb, var(--pill-color) 12%, white) !important;
    color: var(--pill-color) !important;
  }

  .cat-pill.active {
    background: var(--pill-color) !important;
    color: white !important;
  }

  .table-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    overflow: hidden;
  }

  .empty {
    padding: var(--space-6);
    color: var(--text-secondary);
    font-size: var(--text-sm);
  }

  .table-header {
    display: flex;
    align-items: center;
    gap: var(--space-4);
    padding: var(--space-3) var(--space-5);
    background: var(--muted);
    border-bottom: 1px solid var(--border);
  }

  /* .eyebrow ha un margin-left globale (usato per le stat card) che qui
     sfaserebbe ogni intestazione rispetto alla colonna dati sottostante */
  .table-header .eyebrow {
    margin-left: 0;
  }

  .th-icon { width: 36px; flex-shrink: 0; }
  .th-desc { flex: 1; }
  .th-cat { width: 150px; text-align: center; flex-shrink: 0; }
  .th-date { width: 150px; text-align: center; flex-shrink: 0; }
  .th-amount { width: 150px; text-align: center; flex-shrink: 0; }
  .th-actions { width: 104px; flex-shrink: 0; }

  .error {
    color: var(--danger);
    font-size: var(--text-sm);
  }
</style>
