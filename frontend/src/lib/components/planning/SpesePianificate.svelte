<script>
  import { api } from "../../api.js";
  import Icon from "../Icon.svelte";

  let {
    plannedExpenses,
    monthRows,
    totalPlanned,
    exceptionalTotal,
    colors,
    spendableCategories,
    selectedMonth,
    monthLabel,
    onBaseChange,
    onOverrideChange,
  } = $props();

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
      await onBaseChange();
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
      await onBaseChange();
    } catch (e) {
      pError = e.message;
    }
  }

  async function deletePlanned(pid) {
    try {
      await api.delete(`/planning/planned-expenses/${pid}`);
      await onBaseChange();
    } catch (e) {
      pError = e.message;
    }
  }

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
      await onOverrideChange();
    } catch (e) {
      pError = e.message;
    }
  }
</script>

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

<style>
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

  .kpi-grid .metric-card {
    margin-bottom: 0;
  }

  .kpi-value {
    font-family: var(--font-heading);
    font-size: var(--text-xl);
    font-weight: 700;
    color: var(--text-primary);
  }

  .kpi-value.negative { color: var(--danger); }

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
