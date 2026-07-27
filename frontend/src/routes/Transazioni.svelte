<script>
  import { api } from "../lib/api.js";
  import TransactionRow from "../lib/components/TransactionRow.svelte";

  let transactions = $state([]);
  let months = $state([]);
  let categories = $state([]);
  let colors = $state({});
  let selectedMonth = $state("");
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
      if (!addCategory && categories.length) addCategory = categories[0];
    });
  });

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
  <h2>💳 Transazioni</h2>

  <div class="toolbar">
    <select bind:value={selectedMonth}>
      <option value="">Tutti i mesi</option>
      {#each months as m}<option value={m}>{monthLabel(m)}</option>{/each}
    </select>
    <button class="primary" onclick={() => (showAddForm = !showAddForm)}>
      ➕ Aggiungi spesa / entrata
    </button>
  </div>

  {#if showAddForm}
    <form class="panel" onsubmit={submitAdd}>
      <div class="fields">
        <input type="date" bind:value={addDate} />
        <input type="text" bind:value={addDesc} placeholder="Descrizione" />
        <input type="number" step="0.01" bind:value={addAmount} placeholder="Importo (negativo = spesa)" />
        <select bind:value={addCategory}>
          {#each categories as c}<option value={c}>{c}</option>{/each}
        </select>
        <input type="text" bind:value={addNote} placeholder="Note (opzionale)" />
      </div>
      <button type="submit">Aggiungi</button>
      {#if addError}<p class="error">{addError}</p>{/if}
    </form>
  {/if}

  {#if error}
    <p class="error">Backend non raggiungibile: {error}</p>
  {:else}
    <div class="filters">
      <input type="text" bind:value={search} placeholder="🔍 Cerca..." />
      <div class="cat-filters">
        {#each categories as c}
          <button
            class="cat-chip"
            class:active={categoryFilter.includes(c)}
            style="--chip-color:{colors[c] || '#888'}"
            onclick={() => toggleCategoryFilter(c)}
          >{c}</button>
        {/each}
      </div>
      <div class="type-filter">
        <label><input type="radio" bind:group={typeFilter} value="tutto" /> Tutto</label>
        <label><input type="radio" bind:group={typeFilter} value="spese" /> Solo spese</label>
        <label><input type="radio" bind:group={typeFilter} value="entrate" /> Solo entrate</label>
      </div>
    </div>

    <p class="summary">
      <strong>{filtered.length}</strong> transazioni — totale spese: <strong>€{totalSpese.toFixed(2)}</strong>
    </p>

    {#if filtered.length === 0}
      <p>Nessuna transazione. Aggiungine una manuale, oppure importa un estratto Revolut dalla Dashboard.</p>
    {:else}
      {#each filtered as tx (tx.id)}
        <TransactionRow {tx} {categories} {colors} onchange={loadTransactions} />
      {/each}
    {/if}
  {/if}
</section>

<style>
  .toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
    gap: 1rem;
  }

  select {
    padding: 0.4rem 0.6rem;
    border: 1px solid #ddd;
    border-radius: 6px;
  }

  button.primary {
    padding: 0.5rem 1rem;
    border: none;
    border-radius: 6px;
    background: #185fa5;
    color: white;
    cursor: pointer;
  }

  .panel {
    background: #fff;
    border-radius: 10px;
    padding: 1rem;
    margin-bottom: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .panel .fields {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .panel input, .panel select {
    padding: 0.4rem 0.6rem;
    border: 1px solid #ddd;
    border-radius: 6px;
  }

  .panel button[type="submit"] {
    align-self: flex-start;
    padding: 0.4rem 1rem;
    border: none;
    border-radius: 6px;
    background: #185fa5;
    color: white;
    cursor: pointer;
  }

  .filters {
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
    margin-bottom: 1rem;
  }

  .filters > input {
    padding: 0.45rem 0.7rem;
    border: 1px solid #ddd;
    border-radius: 6px;
    max-width: 20rem;
  }

  .cat-filters {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
  }

  .cat-chip {
    border: 1px solid var(--chip-color);
    color: var(--chip-color);
    background: none;
    border-radius: 999px;
    padding: 2px 10px;
    font-size: 0.75rem;
    cursor: pointer;
  }

  .cat-chip.active {
    background: var(--chip-color);
    color: white;
  }

  .type-filter {
    display: flex;
    gap: 1rem;
    font-size: 0.85rem;
  }

  .type-filter label {
    display: flex;
    align-items: center;
    gap: 0.3rem;
  }

  .summary {
    color: #555;
    margin-bottom: 0.75rem;
  }

  .error {
    color: #d85a30;
  }
</style>
