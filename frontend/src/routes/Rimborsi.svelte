<script>
  import { api } from "../lib/api.js";
  import Icon from "../lib/components/Icon.svelte";

  let reimbursements = $state([]);
  let error = $state("");
  let statusFilter = $state("tutti");
  let showAddForm = $state(false);

  let addDate = $state(new Date().toISOString().slice(0, 10));
  let addDesc = $state("");
  let addAmount = $state(10);
  let addFrom = $state("");
  let addNote = $state("");
  let addError = $state("");

  async function loadAll() {
    try {
      reimbursements = await api.get("/reimbursements");
      error = "";
    } catch (e) {
      error = e.message;
    }
  }

  $effect(() => {
    loadAll();
  });

  let filtered = $derived(
    reimbursements.filter((r) => {
      if (statusFilter === "attesa") return r.status !== "ricevuto";
      if (statusFilter === "ricevuti") return r.status === "ricevuto";
      return true;
    })
  );

  let totaleAttesa = $derived(
    reimbursements.filter((r) => r.status !== "ricevuto").reduce((s, r) => s + r.amount, 0)
  );
  let totaleRicevuto = $derived(
    reimbursements.filter((r) => r.status === "ricevuto").reduce((s, r) => s + r.amount, 0)
  );

  async function markReceived(id) {
    try {
      await api.put(`/reimbursements/${id}`, { status: "ricevuto" });
      await loadAll();
    } catch (e) {
      error = e.message;
    }
  }

  async function removeReimbursement(id) {
    try {
      await api.delete(`/reimbursements/${id}`);
      await loadAll();
    } catch (e) {
      error = e.message;
    }
  }

  async function submitAdd(e) {
    e.preventDefault();
    if (!addDesc.trim() || !addFrom.trim()) {
      addError = "Descrizione e persona sono obbligatorie.";
      return;
    }
    try {
      await api.post("/reimbursements", {
        date: addDate,
        description: addDesc,
        amount: Number(addAmount),
        from_person: addFrom,
        note: addNote,
      });
      addDesc = "";
      addFrom = "";
      addNote = "";
      addAmount = 10;
      addError = "";
      showAddForm = false;
      await loadAll();
    } catch (e2) {
      addError = e2.message;
    }
  }
</script>

<section>
  <div class="page-header">
    <div>
      <h2>Rimborsi</h2>
      <p class="subtitle">Crediti in attesa e ricevuti</p>
    </div>
    <button class="btn-primary" onclick={() => (showAddForm = !showAddForm)}>
      <Icon name="plus" size={14} />
      Aggiungi rimborso
    </button>
  </div>

  {#if showAddForm}
    <form class="add-panel" onsubmit={submitAdd}>
      <div class="fields">
        <input type="date" bind:value={addDate} />
        <input type="text" bind:value={addDesc} placeholder="Descrizione" />
        <input type="number" step="0.01" min="0.01" bind:value={addAmount} placeholder="Importo" />
        <input type="text" bind:value={addFrom} placeholder="Da chi (es. Marco)" />
        <input type="text" bind:value={addNote} placeholder="Note (opzionale)" />
      </div>
      <button type="submit" class="btn-primary">Salva</button>
      {#if addError}<p class="error">{addError}</p>{/if}
    </form>
  {/if}

  {#if error}
    <p class="error">Backend non raggiungibile: {error}</p>
  {:else}
    <div class="kpi-grid">
      <div class="metric-card">
        <span class="eyebrow">In attesa</span>
        <span class="kpi-value negative">€{totaleAttesa.toFixed(2)}</span>
      </div>
      <div class="metric-card">
        <span class="eyebrow">Ricevuto</span>
        <span class="kpi-value positive">€{totaleRicevuto.toFixed(2)}</span>
      </div>
    </div>

    <div class="status-pill-group">
      <button class:active={statusFilter === "tutti"} onclick={() => (statusFilter = "tutti")}>Tutti</button>
      <button class:active={statusFilter === "attesa"} onclick={() => (statusFilter = "attesa")}>In attesa</button>
      <button class:active={statusFilter === "ricevuti"} onclick={() => (statusFilter = "ricevuti")}>Ricevuti</button>
    </div>

    {#if filtered.length === 0}
      <p class="hint">Nessun rimborso {statusFilter === "tutti" ? "ancora" : "in questa categoria"}.</p>
    {:else}
      <div class="list">
        {#each filtered as r (r.id)}
          <div class="row">
            <div class="icon-cell" class:done={r.status === "ricevuto"}>
              <Icon name={r.status === "ricevuto" ? "check" : "clock"} size={16} />
            </div>
            <div class="desc-cell">
              <span class="desc">{r.description}</span>
              <span class="note-inline">{r.date} · da {r.from_person}{r.note ? ` · ${r.note}` : ""}</span>
            </div>
            <div class="amount-cell" class:done={r.status === "ricevuto"}>€{r.amount.toFixed(2)}</div>
            <div class="actions-cell">
              {#if r.status !== "ricevuto"}
                <button title="Segna come ricevuto" onclick={() => markReceived(r.id)}>
                  <Icon name="check" size={14} />
                </button>
              {/if}
              <button title="Elimina" onclick={() => removeReimbursement(r.id)}>
                <Icon name="trash-2" size={14} />
              </button>
            </div>
          </div>
        {/each}
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

  .add-panel .btn-primary {
    align-self: flex-start;
  }

  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
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
  }

  .kpi-value.negative { color: var(--danger); }
  .kpi-value.positive { color: var(--success); }

  .status-pill-group {
    display: flex;
    gap: var(--space-2);
    margin-bottom: var(--space-5);
  }

  .status-pill-group button {
    padding: 0.3rem var(--space-3);
    border: none;
    border-radius: var(--radius-md);
    background: var(--muted);
    color: var(--text-primary);
    font-size: var(--text-xs);
    font-weight: 500;
    cursor: pointer;
  }

  .status-pill-group button.active {
    background: var(--accent);
    color: var(--accent-foreground);
  }

  .list {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    overflow: hidden;
  }

  .row {
    display: flex;
    align-items: center;
    gap: var(--space-4);
    padding: var(--space-3) var(--space-5);
    border-bottom: 1px solid var(--border);
  }

  .row:last-child {
    border-bottom: none;
  }

  .icon-cell {
    width: 36px;
    height: 36px;
    border-radius: var(--radius-md);
    background: var(--muted);
    color: var(--warning);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .icon-cell.done {
    color: var(--success);
  }

  .desc-cell {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
  }

  .desc {
    font-size: var(--text-base);
    font-weight: 500;
    color: var(--text-primary);
  }

  .note-inline {
    font-size: var(--text-xs);
    color: var(--text-muted);
  }

  .amount-cell {
    font-family: var(--font-heading);
    font-weight: 600;
    color: var(--danger);
    flex-shrink: 0;
  }

  .amount-cell.done {
    color: var(--success);
  }

  .actions-cell {
    display: flex;
    gap: 2px;
    flex-shrink: 0;
  }

  .actions-cell button {
    background: none;
    border: none;
    cursor: pointer;
    padding: 5px;
    border-radius: var(--radius-sm);
    color: var(--text-secondary);
    display: flex;
  }

  .actions-cell button:hover {
    background: var(--muted);
    color: var(--accent);
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
